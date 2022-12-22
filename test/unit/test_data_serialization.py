# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for runtime data serialization."""

import json
import os
import subprocess
import tempfile
import warnings
from datetime import datetime
from unittest import skipIf

import numpy as np
import scipy.sparse
from qiskit.algorithms.optimizers import (
    ADAM,
    GSLS,
    IMFIL,
    SPSA,
    QNSPSA,
    SNOBFIT,
    L_BFGS_B,
    NELDER_MEAD,
)
from qiskit.circuit import Parameter, QuantumCircuit
from qiskit.test.reference_circuits import ReferenceCircuits
from qiskit.circuit.library import EfficientSU2, CXGate, PhaseGate, U2Gate
from qiskit.opflow import (
    PauliSumOp,
    MatrixOp,
    PauliOp,
    CircuitOp,
    EvolvedOp,
    TaperedPauliSumOp,
    Z2Symmetries,
    I,
    X,
    Y,
    Z,
    StateFn,
    CircuitStateFn,
    DictStateFn,
    VectorStateFn,
    OperatorStateFn,
    SparseVectorStateFn,
    CVaRMeasurement,
    ComposedOp,
    SummedOp,
    TensoredOp,
)
from qiskit.providers.fake_provider import FakeNairobi
from qiskit.quantum_info import SparsePauliOp, Pauli, Statevector
from qiskit.result import Result
from qiskit_aer.noise import NoiseModel

from qiskit_ibm_runtime.utils import RuntimeEncoder, RuntimeDecoder
from .mock.fake_runtime_client import CustomResultRuntimeJob
from .mock.fake_runtime_service import FakeRuntimeService
from ..ibm_test_case import IBMTestCase
from ..program import run_program
from ..serialization import (
    SerializableClass,
    SerializableClassDecoder,
    get_complex_types,
)


class TestDataSerialization(IBMTestCase):
    """Class for testing runtime data serialization."""

    def test_coder(self):
        """Test runtime encoder and decoder."""
        result = Result(
            backend_name="ibmqx2",
            backend_version="1.1",
            qobj_id="12345",
            job_id="67890",
            success=False,
            results=[],
        )

        data = {
            "string": "foo",
            "float": 1.5,
            "complex": 2 + 3j,
            "array": np.array([[1, 2, 3], [4, 5, 6]]),
            "result": result,
            "sclass": SerializableClass("foo"),
        }
        encoded = json.dumps(data, cls=RuntimeEncoder)
        decoded = json.loads(encoded, cls=RuntimeDecoder)
        decoded["sclass"] = SerializableClass.from_json(decoded["sclass"])

        decoded_result = decoded.pop("result")
        data.pop("result")

        decoded_array = decoded.pop("array")
        orig_array = data.pop("array")

        self.assertEqual(decoded, data)
        self.assertIsInstance(decoded_result, Result)
        self.assertTrue((decoded_array == orig_array).all())

    def test_coder_qc(self):
        """Test runtime encoder and decoder for circuits."""
        bell = ReferenceCircuits.bell()
        unbound = EfficientSU2(num_qubits=4, reps=1, entanglement="linear")
        subtests = (bell, unbound, [bell, unbound])
        for circ in subtests:
            with self.subTest(circ=circ):
                encoded = json.dumps(circ, cls=RuntimeEncoder)
                self.assertIsInstance(encoded, str)
                decoded = json.loads(encoded, cls=RuntimeDecoder)
                if not isinstance(circ, list):
                    decoded = [decoded]
                self.assertTrue(
                    all(isinstance(item, QuantumCircuit) for item in decoded)
                )

    def test_coder_operators(self):
        """Test runtime encoder and decoder for operators."""
        coeff_x = Parameter("x")
        coeff_y = coeff_x + 1
        quantum_circuit = QuantumCircuit(1)
        quantum_circuit.h(0)
        operator = 2.0 * I ^ I
        z2_symmetries = Z2Symmetries(
            [Pauli("IIZI"), Pauli("ZIII")],
            [Pauli("IIXI"), Pauli("XIII")],
            [1, 3],
            [-1, 1],
        )
        isqrt2 = 1 / np.sqrt(2)
        sparse = scipy.sparse.csr_matrix([[0, isqrt2, 0, isqrt2]])

        subtests = (
            PauliSumOp(SparsePauliOp(Pauli("XYZX"), coeffs=[2]), coeff=3),
            PauliSumOp(SparsePauliOp(Pauli("XYZX"), coeffs=[1]), coeff=coeff_y),
            PauliSumOp(SparsePauliOp(Pauli("XYZX"), coeffs=[1 + 2j]), coeff=3 - 2j),
            PauliSumOp.from_list(
                [("II", -1.052373245772859), ("IZ", 0.39793742484318045)]
            ),
            MatrixOp(primitive=np.array([[0, -1j], [1j, 0]]), coeff=coeff_x),
            PauliOp(primitive=Pauli("Y"), coeff=coeff_x),
            CircuitOp(quantum_circuit, coeff=coeff_x),
            EvolvedOp(operator, coeff=coeff_x),
            TaperedPauliSumOp(SparsePauliOp(Pauli("XYZX"), coeffs=[2]), z2_symmetries),
            StateFn(quantum_circuit, coeff=coeff_x),
            CircuitStateFn(quantum_circuit, is_measurement=True),
            DictStateFn("1" * 3, is_measurement=True),
            VectorStateFn(np.ones(2**3, dtype=complex)),
            OperatorStateFn(CircuitOp(QuantumCircuit(1))),
            SparseVectorStateFn(sparse),
            Statevector([1, 0]),
            CVaRMeasurement(Z, 0.2),
            ComposedOp([(X ^ Y ^ Z), (Z ^ X ^ Y ^ Z).to_matrix_op()]),
            SummedOp([X ^ X * 2, Y ^ Y], 2),
            TensoredOp([(X ^ Y), (Z ^ I)]),
            (Z ^ Z) ^ (I ^ 2),
        )
        for operator in subtests:
            with self.subTest(operator=operator):
                encoded = json.dumps(operator, cls=RuntimeEncoder)
                self.assertIsInstance(encoded, str)
                decoded = json.loads(encoded, cls=RuntimeDecoder)
                self.assertEqual(operator, decoded)

    @skipIf(os.name == "nt", "Test not supported on Windows")
    def test_coder_optimizers(self):
        """Test runtime encoder and decoder for optimizers."""
        subtests = (
            (ADAM, {"maxiter": 100, "amsgrad": True}),
            (GSLS, {"maxiter": 50, "min_step_size": 0.01}),
            (IMFIL, {"maxiter": 20}),
            (SPSA, {"maxiter": 10, "learning_rate": 0.01, "perturbation": 0.1}),
            (SNOBFIT, {"maxiter": 200, "maxfail": 20}),
            (QNSPSA, {"fidelity": 123, "maxiter": 25, "resamplings": {1: 100, 2: 50}}),
            # some SciPy optimizers only work with default arguments due to Qiskit/qiskit-terra#6682
            (L_BFGS_B, {}),
            (NELDER_MEAD, {}),
        )
        for opt_cls, settings in subtests:
            with self.subTest(opt_cls=opt_cls):
                optimizer = opt_cls(**settings)
                encoded = json.dumps(optimizer, cls=RuntimeEncoder)
                self.assertIsInstance(encoded, str)
                decoded = json.loads(encoded, cls=RuntimeDecoder)
                self.assertTrue(isinstance(decoded, opt_cls))
                for key, value in settings.items():
                    self.assertEqual(decoded.settings[key], value)

    def test_coder_noise_model(self):
        """Test encoding and decoding a noise model."""
        noise_model = NoiseModel.from_backend(FakeNairobi())
        self.assertIsInstance(noise_model, NoiseModel)
        encoded = json.dumps(noise_model, cls=RuntimeEncoder)
        self.assertIsInstance(encoded, str)
        decoded = json.loads(encoded, cls=RuntimeDecoder)
        self.assertIsInstance(decoded, NoiseModel)
        self.assertEqual(noise_model.noise_qubits, decoded.noise_qubits)
        self.assertEqual(noise_model.noise_instructions, decoded.noise_instructions)

    def test_encoder_datetime(self):
        """Test encoding a datetime."""
        subtests = (
            {"datetime": datetime.now()},
            {"datetime": datetime(2021, 8, 4)},
            {"datetime": datetime.fromtimestamp(1326244364)},
        )
        for obj in subtests:
            encoded = json.dumps(obj, cls=RuntimeEncoder)
            self.assertIsInstance(encoded, str)
            decoded = json.loads(encoded, cls=RuntimeDecoder)
            self.assertEqual(decoded, obj)

    def test_encoder_ndarray(self):
        """Test encoding and decoding a numpy ndarray."""
        subtests = (
            {"ndarray": np.array([[1, 2, 3], [{"obj": 123}, 5, 6]], dtype=object)},
            {"ndarray": np.array([[1, 2, 3], [{"obj": 123}, 5, 6]])},
            {"ndarray": np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=int)},
        )
        for obj in subtests:
            encoded = json.dumps(obj, cls=RuntimeEncoder)
            self.assertIsInstance(encoded, str)
            decoded = json.loads(encoded, cls=RuntimeDecoder)
            self.assertTrue(np.array_equal(decoded["ndarray"], obj["ndarray"]))

    def test_encoder_instruction(self):
        """Test encoding and decoding instructions"""
        subtests = (
            {"instruction": CXGate()},
            {"instruction": PhaseGate(theta=1)},
            {"instruction": U2Gate(phi=1, lam=1)},
            {"instruction": U2Gate(phi=Parameter("phi"), lam=Parameter("lambda"))},
        )
        for obj in subtests:
            encoded = json.dumps(obj, cls=RuntimeEncoder)
            self.assertIsInstance(encoded, str)
            decoded = json.loads(encoded, cls=RuntimeDecoder)
            self.assertEqual(decoded, obj)

    def test_encoder_callable(self):
        """Test encoding a callable."""
        with warnings.catch_warnings(record=True) as warn_cm:
            encoded = json.dumps({"fidelity": lambda x: x}, cls=RuntimeEncoder)
            decoded = json.loads(encoded, cls=RuntimeDecoder)
            self.assertIsNone(decoded["fidelity"])
            self.assertEqual(len(warn_cm), 1)

    def test_decoder_import(self):
        """Test runtime decoder importing modules."""
        script = """
import sys
import json
from qiskit_ibm_runtime import RuntimeDecoder
if __name__ == '__main__':
    obj = json.loads(sys.argv[1], cls=RuntimeDecoder)
    print(obj.__class__.__name__)
"""
        temp_fp = tempfile.NamedTemporaryFile(mode="w", delete=False)
        self.addCleanup(os.remove, temp_fp.name)
        temp_fp.write(script)
        temp_fp.close()

        subtests = (
            PauliSumOp(SparsePauliOp(Pauli("XYZX"), coeffs=[2]), coeff=3),
            DictStateFn("1" * 3, is_measurement=True),
            Statevector([1, 0]),
        )
        for operator in subtests:
            with self.subTest(operator=operator):
                encoded = json.dumps(operator, cls=RuntimeEncoder)
                self.assertIsInstance(encoded, str)
                cmd = ["python", temp_fp.name, encoded]
                proc = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    check=True,
                )
                self.assertIn(operator.__class__.__name__, proc.stdout)

    def test_result_decoder(self):
        """Test result decoder."""
        custom_result = get_complex_types()
        job_cls = CustomResultRuntimeJob
        job_cls.custom_result = custom_result
        ibm_quantum_service = FakeRuntimeService(
            channel="ibm_quantum", token="some_token"
        )

        sub_tests = [(SerializableClassDecoder, None), (None, SerializableClassDecoder)]
        for result_decoder, decoder in sub_tests:
            with self.subTest(decoder=decoder):
                job = run_program(
                    service=ibm_quantum_service,
                    job_classes=job_cls,
                    decoder=result_decoder,
                )
                result = job.result(decoder=decoder)
                self.assertIsInstance(result["serializable_class"], SerializableClass)

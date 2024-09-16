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

import numpy as np
from ddt import data, ddt

from qiskit.circuit import Parameter, ParameterVector, QuantumCircuit
from qiskit.circuit.library import EfficientSU2, CXGate, PhaseGate, U2Gate

import qiskit.quantum_info as qi
from qiskit.quantum_info import SparsePauliOp, Pauli, PauliList
from qiskit.result import Result, Counts
from qiskit.primitives.containers.bindings_array import BindingsArray
from qiskit.primitives.containers.observables_array import ObservablesArray
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.primitives.containers.sampler_pub import SamplerPub
from qiskit.primitives.containers import (
    BitArray,
    DataBin,
    PubResult,
    SamplerPubResult,
    PrimitiveResult,
)
from qiskit_aer.noise import NoiseModel
from qiskit_ibm_runtime.utils import RuntimeEncoder, RuntimeDecoder
from qiskit_ibm_runtime.utils.noise_learner_result import (
    PauliLindbladError,
    LayerError,
    NoiseLearnerResult,
)
from qiskit_ibm_runtime.fake_provider import FakeNairobi
from qiskit_ibm_runtime.execution_span import SliceSpan, ExecutionSpans

from .mock.fake_runtime_client import CustomResultRuntimeJob
from .mock.fake_runtime_service import FakeRuntimeService
from ..ibm_test_case import IBMTestCase
from ..program import run_program
from ..serialization import (
    SerializableClass,
    SerializableClassDecoder,
    get_complex_types,
)
from ..utils import mock_wait_for_final_state, bell


@ddt
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

        base_types = {
            "string": "foo",
            "float": 1.5,
            "complex": 2 + 3j,
            "array": np.array([[1, 2, 3], [4, 5, 6]]),
            "result": result,
            "sclass": SerializableClass("foo"),
        }
        encoded = json.dumps(base_types, cls=RuntimeEncoder)
        decoded = json.loads(encoded, cls=RuntimeDecoder)
        decoded["sclass"] = SerializableClass.from_json(decoded["sclass"])

        decoded_result = decoded.pop("result")
        base_types.pop("result")

        decoded_array = decoded.pop("array")
        orig_array = base_types.pop("array")

        self.assertEqual(decoded, base_types)
        self.assertIsInstance(decoded_result, Result)
        self.assertTrue((decoded_array == orig_array).all())

    def test_coder_qc(self):
        """Test runtime encoder and decoder for circuits."""
        bell_circuit = bell()
        unbound = EfficientSU2(num_qubits=4, reps=1, entanglement="linear")
        subtests = (bell_circuit, unbound, [bell_circuit, unbound])
        for circ in subtests:
            with self.subTest(circ=circ):
                encoded = json.dumps(circ, cls=RuntimeEncoder)
                self.assertIsInstance(encoded, str)
                decoded = json.loads(encoded, cls=RuntimeDecoder)
                if not isinstance(circ, list):
                    decoded = [decoded]
                self.assertTrue(all(isinstance(item, QuantumCircuit) for item in decoded))

    def test_coder_operators(self):
        """Test runtime encoder and decoder for operators."""

        subtests = (
            SparsePauliOp(Pauli("XYZX"), coeffs=[2]),
            SparsePauliOp(Pauli("XYZX"), coeffs=[1 + 2j]),
            Pauli("XYZ"),
        )

        for operator in subtests:
            with self.subTest(operator=operator):
                encoded = json.dumps(operator, cls=RuntimeEncoder)
                self.assertIsInstance(encoded, str)

                with warnings.catch_warnings():
                    # in L146 of utils/json.py
                    warnings.filterwarnings(
                        "ignore",
                        category=DeprecationWarning,
                        module=r"qiskit_ibm_runtime\.utils\.json",
                    )
                    decoded = json.loads(encoded, cls=RuntimeDecoder)
                    self.assertEqual(operator, decoded)

    def test_coder_noise_model(self):
        """Test encoding and decoding a noise model."""
        noise_model = NoiseModel.from_backend(FakeNairobi())
        self.assertIsInstance(noise_model, NoiseModel)
        encoded = json.dumps(noise_model, cls=RuntimeEncoder)
        self.assertIsInstance(encoded, str)
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                category=DeprecationWarning,
            )
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
            {"ndarray": np.array([1, {"obj": 123}], dtype=object)},
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

    def test_encoder_np_number(self):
        """Test encoding and decoding instructions"""
        encoded = json.dumps(np.int64(100), cls=RuntimeEncoder)
        self.assertIsInstance(encoded, str)
        decoded = json.loads(encoded, cls=RuntimeDecoder)
        self.assertEqual(decoded, 100)

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
            SparsePauliOp(Pauli("XYZX"), coeffs=[2]),
            Pauli("XYZX"),
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
        ibm_quantum_service = FakeRuntimeService(channel="ibm_quantum", token="some_token")

        sub_tests = [(SerializableClassDecoder, None), (None, SerializableClassDecoder)]
        for result_decoder, decoder in sub_tests:
            with self.subTest(decoder=decoder):
                job = run_program(
                    service=ibm_quantum_service,
                    job_classes=job_cls,
                    decoder=result_decoder,
                )
                with mock_wait_for_final_state(ibm_quantum_service, job):
                    result = job.result(decoder=decoder)
                self.assertIsInstance(result["serializable_class"], SerializableClass)

    def test_circuit_metadata(self):
        """Test serializing circuit metadata."""

        circ = QuantumCircuit(1)
        circ.metadata = {"test": np.arange(0, 10)}
        payload = {"circuits": [circ]}

        self.assertTrue(json.dumps(payload, cls=RuntimeEncoder))


@ddt
class TestContainerSerialization(IBMTestCase):
    """Class for testing primitive containers serialization."""

    # Container specific assertEqual methods
    def assert_observable_arrays_equal(self, obs1, obs2):
        """Tests that two ObservableArray objects are equal"""
        self.assertEqual(obs1.tolist(), obs2.tolist())

    def assert_binding_arrays_equal(self, barr1, barr2):
        """Tests that two BindingArray objects are equal"""

        def _to_str_keyed(_in_dict):
            _out_dict = {}
            for a_key_tuple, val in _in_dict.items():
                str_key = tuple(
                    a_key.name if isinstance(a_key, Parameter) else a_key for a_key in a_key_tuple
                )
                _out_dict[str_key] = val
            return _out_dict

        self.assertEqual(barr1.shape, barr2.shape)
        barr1_str_keyed = _to_str_keyed(barr1.data)
        barr2_str_keyed = _to_str_keyed(barr2.data)
        for key, val in barr1_str_keyed.items():
            self.assertIn(key, barr2_str_keyed)
            np.testing.assert_allclose(val, barr2_str_keyed[key])

    def assert_data_bins_equal(self, dbin1, dbin2):
        """Compares two DataBins
        Field types are compared up to their string representation
        """
        self.assertEqual(tuple(dbin1), tuple(dbin2))
        self.assertEqual(dbin1.shape, dbin2.shape)
        for field_name in dbin1:
            field_1 = dbin1[field_name]
            field_2 = dbin2[field_name]
            if isinstance(field_1, np.ndarray):
                np.testing.assert_allclose(field_1, field_2)
            else:
                self.assertEqual(field_1, field_2)

    def assert_estimator_pubs_equal(self, pub1, pub2):
        """Tests that two EstimatorPub objects are equal"""
        self.assertEqual(pub1.circuit, pub2.circuit)
        self.assert_observable_arrays_equal(pub1.observables, pub2.observables)
        self.assert_binding_arrays_equal(pub1.parameter_values, pub2.parameter_values)
        self.assertEqual(pub1.precision, pub2.precision)

    def assert_sampler_pubs_equal(self, pub1, pub2):
        """Tests that two SamplerPub objects are equal"""
        self.assertEqual(pub1.circuit, pub2.circuit)
        self.assert_binding_arrays_equal(pub1.parameter_values, pub2.parameter_values)
        self.assertEqual(pub1.shots, pub2.shots)

    def assert_pub_results_equal(self, pub_result1, pub_result2):
        """Tests that two PubResult objects are equal"""
        self.assert_data_bins_equal(pub_result1.data, pub_result2.data)
        self.assertEqual(pub_result1.metadata, pub_result2.metadata)

    def assert_primitive_results_equal(self, primitive_result1, primitive_result2):
        """Tests that two PrimitiveResult objects are equal"""
        self.assertEqual(len(primitive_result1), len(primitive_result2))
        for pub_result1, pub_result2 in zip(primitive_result1, primitive_result2):
            self.assert_pub_results_equal(pub_result1, pub_result2)

        self.assertEqual(primitive_result1.metadata, primitive_result2.metadata)

    def assert_pauli_lindblad_error_equal(self, error1, error2):
        """Tests that two PauliLindbladError objects are equal"""
        self.assertEqual(error1.generators, error2.generators)
        self.assertEqual(error1.rates.tolist(), error2.rates.tolist())

    def assert_layer_errors_equal(self, layer_error1, layer_error2):
        """Tests that two LayerError objects are equal"""
        self.assertEqual(layer_error1.circuit, layer_error2.circuit)
        self.assertEqual(layer_error1.qubits, layer_error2.qubits)
        self.assert_pauli_lindblad_error_equal(layer_error1.error, layer_error2.error)

    def assert_noise_learner_results_equal(self, result1, result2):
        """Tests that two NoiseLearnerResult objects are equal"""
        self.assertEqual(len(result1), len(result2))
        for layer_error1, layer_error2 in zip(result1, result2):
            self.assert_layer_errors_equal(layer_error1, layer_error2)

        self.assertEqual(result1.metadata, result2.metadata)

    # Data generation methods

    def make_test_data_bins(self):
        """Generates test data for DataBin test"""
        result_bins = []
        alpha = np.empty((10, 20), dtype=np.uint16)
        beta = np.empty((10, 20), dtype=int)
        my_bin = DataBin(alpha=alpha, beta=beta, shape=(10, 20))
        result_bins.append(my_bin)
        return result_bins

    def make_test_estimator_pubs(self):
        """Generates test data for EstimatorPub test"""
        pubs = []
        params = (Parameter("a"), Parameter("b"))
        circuit = QuantumCircuit(2)
        circuit.rx(params[0], 0)
        circuit.ry(params[1], 1)
        parameter_values = BindingsArray(data={params: np.ones((10, 2))})
        observables = ObservablesArray([{"XX": 0.1}])
        precision = 0.05

        pub = EstimatorPub(
            circuit=circuit,
            observables=observables,
            parameter_values=parameter_values,
            precision=precision,
        )
        pubs.append(pub)
        return pubs

    def make_test_sampler_pubs(self):
        """Generates test data for SamplerPub test"""
        pubs = []
        params = (Parameter("a"), Parameter("b"))
        circuit = QuantumCircuit(2)
        circuit.rx(params[0], 0)
        circuit.ry(params[1], 1)
        circuit.measure_all()
        parameter_values = BindingsArray(data={params: np.ones((10, 2))})
        shots = 1000

        pub = SamplerPub(
            circuit=circuit,
            parameter_values=parameter_values,
            shots=shots,
        )
        pubs.append(pub)
        return pubs

    def make_test_pub_results(self):
        """Generates test data for PubResult test"""
        pub_results = []
        pub_result = PubResult(DataBin(a=1.0, b=2))
        pub_results.append(pub_result)
        pub_result = PubResult(DataBin(a=1.0, b=2), {"x": 1})
        pub_results.append(pub_result)
        return pub_results

    def make_test_sampler_pub_results(self):
        """Generates test data for SamplerPubResult test"""
        pub_results = []
        pub_result = SamplerPubResult(DataBin(a=1.0, b=2))
        pub_results.append(pub_result)
        pub_result = SamplerPubResult(DataBin(a=1.0, b=2), {"x": 1})
        pub_results.append(pub_result)
        return pub_results

    def make_test_primitive_results(self):
        """Generates test data for PrimitiveResult test"""
        primitive_results = []

        alpha = np.empty((10, 20), dtype=np.uint16)
        beta = np.empty((10, 20), dtype=int)

        pub_results = [
            PubResult(DataBin(alpha=alpha, beta=beta, shape=(10, 20))),
            PubResult(DataBin(alpha=alpha, beta=beta, shape=(10, 20))),
            PubResult(DataBin()),
        ]

        metadata = {
            "execution": {
                "execution_spans": ExecutionSpans(
                    [
                        SliceSpan(
                            datetime(2022, 1, 1),
                            datetime(2023, 1, 1),
                            {1: ((100,), slice(4, 9)), 0: ((2, 5), slice(5, 7))},
                        ),
                        SliceSpan(
                            datetime(2024, 8, 20), datetime(2024, 8, 21), {0: ((14,), slice(2, 3))}
                        ),
                    ]
                )
            }
        }

        result = PrimitiveResult(pub_results, metadata)
        primitive_results.append(result)
        return primitive_results

    def make_test_noise_learner_results(self):
        """Generates test data for NoiseLearnerResult test"""
        noise_learner_results = []
        circuit = QuantumCircuit(2)
        circuit.cx(0, 1)
        circuit.measure_all()
        error = PauliLindbladError(PauliList(["XX", "ZZ"]), [0.1, 0.2])
        layer_error = LayerError(circuit, [3, 5], error)

        noise_learner_result = NoiseLearnerResult([layer_error])
        noise_learner_results.append(noise_learner_result)
        return noise_learner_results

    # Tests
    @data(
        ObservablesArray([["X", "Y", "Z"], ["0", "1", "+"]]),
        ObservablesArray(qi.pauli_basis(2)),
        ObservablesArray([qi.random_pauli_list(2, 3, phase=False) for _ in range(5)]),
        ObservablesArray(np.array([["X", "Y"], ["Z", "I"]], dtype=object)),
        ObservablesArray(
            [
                [SparsePauliOp(qi.random_pauli_list(2, 3, phase=False)) for _ in range(3)]
                for _ in range(5)
            ]
        ),
    )
    def test_obs_array(self, oarray):
        """Test encoding and decoding ObservablesArray"""
        payload = {"array": oarray}
        encoded = json.dumps(payload, cls=RuntimeEncoder)
        decoded = json.loads(encoded, cls=RuntimeDecoder)["array"]
        self.assertIsInstance(decoded, ObservablesArray)
        self.assert_observable_arrays_equal(decoded, oarray)

    @data(
        BindingsArray({"a": [1, 2, 3.4]}),
        BindingsArray({("a", "b", "c"): [4.0, 5.0, 6.0]}, shape=()),
        BindingsArray({Parameter("a"): np.random.uniform(size=(5,))}),
        BindingsArray({ParameterVector("a", 5): np.linspace(0, 1, 30).reshape((2, 3, 5))}),
        BindingsArray(data={Parameter("a"): [0.0], Parameter("b"): [1.0]}, shape=1),
        BindingsArray(
            data={
                (Parameter("a"), Parameter("b")): np.random.random((4, 3, 2)),
                Parameter("c"): np.random.random((4, 3)),
            }
        ),
        BindingsArray(
            data={
                (Parameter("a"), Parameter("b")): np.random.random((2, 3, 2)),
                Parameter("c"): np.random.random((2, 3)),
            },
        ),
        BindingsArray(data={Parameter("c"): [3.0, 3.1]}),
        BindingsArray(data={"param1": [1, 2, 3], "param2": [3, 4, 5]}),
    )
    def test_bindings_array(self, barray):
        """Test encoding and decoding BindingsArray."""
        payload = {"array": barray}
        encoded = json.dumps(payload, cls=RuntimeEncoder)
        decoded = json.loads(encoded, cls=RuntimeDecoder)["array"]
        self.assertIsInstance(decoded, BindingsArray)
        self.assert_binding_arrays_equal(decoded, barray)

    @data(
        BitArray(
            np.array([[[3, 5], [3, 5], [234, 100]], [[0, 1], [1, 0], [1, 0]]], dtype=np.uint8),
            num_bits=15,
        ),
        BitArray.from_bool_array([[1, 0, 0], [1, 1, 0]]),
        BitArray.from_counts(Counts({"0b101010": 2, "0b1": 3, "0x010203": 4})),
    )
    def test_bit_array(self, barray):
        """Test encoding and decoding BitArray."""
        payload = {"array": barray}
        encoded = json.dumps(payload, cls=RuntimeEncoder)
        decoded = json.loads(encoded, cls=RuntimeDecoder)["array"]
        self.assertIsInstance(decoded, BitArray)
        self.assertEqual(barray, decoded)

    def test_data_bin(self):
        """Test encoding and decoding DataBin."""
        for dbin in self.make_test_data_bins():
            payload = {"bin": dbin}
            encoded = json.dumps(payload, cls=RuntimeEncoder)
            decoded = json.loads(encoded, cls=RuntimeDecoder)["bin"]
            self.assertIsInstance(decoded, DataBin)
            self.assert_data_bins_equal(dbin, decoded)

    def test_estimator_pub(self):
        """Test encoding and decoding EstimatorPub"""
        for pub in self.make_test_estimator_pubs():
            payload = {"pub": pub}
            encoded = json.dumps(payload, cls=RuntimeEncoder)
            decoded = json.loads(encoded, cls=RuntimeDecoder)["pub"]
            self.assertIsInstance(decoded, (list, tuple))
            self.assertEqual(len(decoded), 4)
            decoded_pub = EstimatorPub.coerce(decoded)
            self.assert_estimator_pubs_equal(pub, decoded_pub)

    def test_sampler_pub(self):
        """Test encoding and decoding SamplerPub"""
        for pub in self.make_test_sampler_pubs():
            payload = {"pub": pub}
            encoded = json.dumps(payload, cls=RuntimeEncoder)
            decoded = json.loads(encoded, cls=RuntimeDecoder)["pub"]
            self.assertIsInstance(decoded, (list, tuple))
            self.assertEqual(len(decoded), 3)
            decoded_pub = SamplerPub.coerce(decoded)
            self.assert_sampler_pubs_equal(pub, decoded_pub)

    def test_pub_result(self):
        """Test encoding and decoding PubResult"""
        for pub_result in self.make_test_pub_results():
            payload = {"pub_result": pub_result}
            encoded = json.dumps(payload, cls=RuntimeEncoder)
            decoded = json.loads(encoded, cls=RuntimeDecoder)["pub_result"]
            self.assertIsInstance(decoded, PubResult)
            self.assert_pub_results_equal(pub_result, decoded)

    def test_sampler_pub_result(self):
        """Test encoding and decoding SamplerPubResult"""
        for pub_result in self.make_test_sampler_pub_results():
            payload = {"sampler_pub_result": pub_result}
            encoded = json.dumps(payload, cls=RuntimeEncoder)
            decoded = json.loads(encoded, cls=RuntimeDecoder)["sampler_pub_result"]
            self.assertIsInstance(decoded, SamplerPubResult)
            self.assert_pub_results_equal(pub_result, decoded)

    def test_primitive_result(self):
        """Test encoding and decoding PubResult"""
        for primitive_result in self.make_test_primitive_results():
            payload = {"primitive_result": primitive_result}
            encoded = json.dumps(payload, cls=RuntimeEncoder)
            decoded = json.loads(encoded, cls=RuntimeDecoder)["primitive_result"]
            self.assertIsInstance(decoded, PrimitiveResult)
            self.assert_primitive_results_equal(primitive_result, decoded)

    def test_noise_learner_result(self):
        """Test encoding and decoding NoiseLearnerResult"""
        for noise_learner_result in self.make_test_noise_learner_results():
            payload = {"noise_learner_result": noise_learner_result}
            encoded = json.dumps(payload, cls=RuntimeEncoder)
            decoded = json.loads(encoded, cls=RuntimeDecoder)["noise_learner_result"]
            self.assertIsInstance(decoded, NoiseLearnerResult)
            self.assert_noise_learner_results_equal(noise_learner_result, decoded)

    def test_unknown_settings(self):
        """Test settings not on whitelisted path."""
        random_settings = {
            "__type__": "settings",
            "__module__": "subprocess",
            "__class__": "Popen",
            "__value__": {"args": ["echo", "hi"]},
        }
        encoded = json.dumps(random_settings)
        decoded = json.loads(encoded, cls=RuntimeDecoder)
        self.assertIsInstance(decoded, dict)
        self.assertDictEqual(decoded, random_settings)

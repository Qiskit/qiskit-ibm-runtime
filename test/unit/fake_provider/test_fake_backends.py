# This code is part of Qiskit.
#
# (C) Copyright IBM 2020, 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test of generated fake backends."""
import math
import unittest

from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit, transpile
from qiskit.utils import optionals

from qiskit_ibm_runtime import SamplerV2
from qiskit_ibm_runtime.fake_provider import FakeAthens, FakePerth, FakeProviderForBackendV2
from ...ibm_test_case import IBMTestCase


def get_test_circuit():
    """Generates simple circuit for tests."""
    desired_vector = [1 / math.sqrt(2), 0, 0, 1 / math.sqrt(2)]
    qreg = QuantumRegister(2, "qr")
    creg = ClassicalRegister(2, "cr")
    qc = QuantumCircuit(qreg, creg)  # pylint: disable=invalid-name
    qc.initialize(desired_vector, [qreg[0], qreg[1]])
    qc.measure(qreg[0], creg[0])
    qc.measure(qreg[1], creg[1])
    return qc


class FakeBackendsTest(IBMTestCase):
    """fake backends test."""

    @unittest.skipUnless(optionals.HAS_AER, "qiskit-aer is required to run this test")
    def test_fake_backends_get_kwargs(self):
        """Fake backends honor kwargs passed."""
        backend = FakeAthens()

        qc = QuantumCircuit(2)  # pylint: disable=invalid-name
        qc.x(range(0, 2))
        qc.measure_all()

        trans_qc = transpile(qc, backend)
        sampler = SamplerV2(backend)
        job = sampler.run([trans_qc])
        pub_result = job.result()[0]
        counts = pub_result.data.meas.get_counts()

        self.assertEqual(sum(counts.values()), 1024)

    @unittest.skipUnless(optionals.HAS_AER, "qiskit-aer is required to run this test")
    def test_fake_backend_v2_noise_model_always_present(self):
        """Test that FakeBackendV2 instances always run with noise."""
        backend = FakePerth()
        qc = QuantumCircuit(1)  # pylint: disable=invalid-name
        qc.x(0)
        qc.measure_all()
        sampler = SamplerV2(backend)
        job = sampler.run([qc])
        pub_result = job.result()[0]
        counts = pub_result.data.meas.get_counts()
        # Assert noise was present and result wasn't ideal
        self.assertNotEqual(counts, {"1": 1000})

    def test_retrieving_single_backend(self):
        """Test retrieving a single backend."""
        provider = FakeProviderForBackendV2()
        backend_name = "fake_jakarta"
        backend = provider.backend(backend_name)
        self.assertEqual(backend.name, backend_name)

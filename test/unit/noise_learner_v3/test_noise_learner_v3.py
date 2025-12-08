# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests the `NoiseLearnerV3` class."""

from qiskit_ibm_runtime.noise_learner_v3 import NoiseLearnerV3

from test.utils import get_mocked_backend

from ...ibm_test_case import IBMTestCase


class TestNoiseLearnerV3(IBMTestCase):
    """Tests the `NoiseLearnerV3` class."""

    def test_init_with_backend_instance(self):
        """Test `NoiseLearnerV3.init` when the input mode is an IBMBackend."""
        backend = get_mocked_backend()
        noise_learner = NoiseLearnerV3(mode=backend)
        assert noise_learner._backend == backend
        assert noise_learner._service == backend.service

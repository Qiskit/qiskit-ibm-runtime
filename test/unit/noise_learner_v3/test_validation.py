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

"""Tests the noise learner v3 validation."""

from qiskit_ibm_runtime.noise_learner_v3.validation import validate_options
from qiskit_ibm_runtime.models.backend_configuration import BackendConfiguration

from ...ibm_test_case import IBMTestCase


class TestValidation(IBMTestCase):
    """Tests the noise learner v3 validation."""

    def test_validate_options(self):
        """Test the function :func:`~qiskit_ibm_runtime/noise_learner_v3/validate_options`."""
        configuration = BackendConfiguration(
            backend_name="im_a_backend",
            backend_version="0.0",
            n_qubits=1e100,
            basis_gates=["rx"],
            gates=[],
            local=False,
            simulator=False,
            conditional=True,
            open_pulse=False,
            memory=True,
            coupling_map=[],
        )

        valid_options_ps_enabled = NoiseLearnerV3Options(
            post_selection={"enable": True, "x_pulse_type": "rx"}
        )
        validate_options(options=valid_options_ps_enabled, configuration=configuration)

        valid_options_ps_disabled = NoiseLearnerV3Options(
            post_selection={"enable": False, "x_pulse_type": "xslow"}
        )
        validate_options(options=valid_options_ps_disabled, configuration=configuration)

        invalid_options = NoiseLearnerV3Options(
            post_selection={"enable": True, "x_pulse_type": "xslow"}
        )
        with self.assertRaisesRegex(ValueError, "xslow"):
            validate_options(options=invalid_options, configuration=configuration)

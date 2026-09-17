# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for the `api/` package."""

from __future__ import annotations

from qiskit_ibm_runtime.api.rest.base import RestAdapterBase
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ..account import custom_envs
from ..decorators import mock_responses
from ..ibm_test_case import IBMTestCase


class TestAPISession(IBMTestCase):
    """Class for testing API sessions."""

    @mock_responses(expose_responses_mock=True)
    def test_functions_identifier_header(self, registry, responses):
        """Test for appending the HTTP header for functions identifier."""
        job_post_mock = next(
            mock
            for mock in responses.registered()
            if mock.url == "https://my-region.quantum.cloud.ibm.com/api/v1/jobs"
        )

        # Sending a job with default environment variables.
        service = QiskitRuntimeService(token="my_token")
        service._run("sampler", {}, {"backend": "common_backend"})
        headers = job_post_mock.calls[-1].request.headers

        # The job POST should receive the usual headers.
        self.assertEqual(
            RestAdapterBase._HEADER_API_VERSION["IBM-API-Version"], headers["IBM-API-Version"]
        )
        self.assertEqual(registry.instances["a"].crn, headers["Service-CRN"])
        self.assertIn("qiskit_ibm_runtime", headers["X-Qx-Client-Application"])
        # The job POST should not receive the function id header.
        self.assertNotIn("IBM-API-Function-Id", headers)

        with custom_envs({"QISKIT_FUNCTIONS_IDENTIFIER": "my-cool-id"}):
            service._run("sampler", {}, {"backend": "common_backend"})
            headers = job_post_mock.calls[-1].request.headers

            # The job POST should receive the usual headers.
            self.assertEqual(
                RestAdapterBase._HEADER_API_VERSION["IBM-API-Version"], headers["IBM-API-Version"]
            )
            self.assertEqual(registry.instances["a"].crn, headers["Service-CRN"])
            self.assertIn("qiskit_ibm_runtime", headers["X-Qx-Client-Application"])
            # The job POST should receive the function id header.
            self.assertEqual("my-cool-id", headers["IBM-API-Function-Id"])

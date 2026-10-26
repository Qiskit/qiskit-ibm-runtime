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

"""Utilities to be used with registries."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from qiskit_ibm_runtime.json import RuntimeDecoder

if TYPE_CHECKING:
    from responses import RequestsMock


def get_submitted_jobs(responses: RequestsMock) -> list[dict]:
    """Return the decoded payloads of the jobs submitted to the mocked ``/jobs`` endpoint.

    Args:
        responses: The mock of the HTTP responses, as returned by the ``responses`` fixture.
    """
    return [
        json.loads(str(call.request.body), cls=RuntimeDecoder)
        for call in responses.calls
        if call.request.method == "POST" and str(call.request.url).endswith("/jobs")
    ]

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

"""Utility functions for runtime testing."""

import uuid
import copy
from datetime import datetime, timezone
from qiskit_ibm_runtime import QiskitRuntimeService


DEFAULT_DATA = "def main() {}"
DEFAULT_METADATA = {
    "name": "qiskit-test",
    "description": "Test program.",
    "max_execution_time": 300,
    "spec": {
        "backend_requirements": {"min_num_qubits": 5},
        "parameters": {
            "properties": {
                "param1": {
                    "description": "Desc 1",
                    "type": "string",
                    "enum": ["a", "b", "c"],
                },
                "param2": {"description": "Desc 2", "type": "integer", "min": 0},
            },
            "required": ["param1"],
        },
        "return_values": {
            "type": "object",
            "description": "Return values",
            "properties": {
                "ret_val": {"description": "Some return value.", "type": "string"}
            },
        },
        "interim_results": {
            "properties": {
                "int_res": {"description": "Some interim result", "type": "string"}
            }
        },
    },
}


def upload_program(
    service: QiskitRuntimeService,
    name: str = None,
    max_execution_time: int = 300,
    is_public: bool = False,
) -> str:
    """Upload a new program."""
    name = name or uuid.uuid4().hex
    data = DEFAULT_DATA
    metadata = copy.deepcopy(DEFAULT_METADATA)
    metadata.update(name=name)
    metadata.update(is_public=is_public)
    metadata.update(max_execution_time=max_execution_time)
    program_id = service.upload_program(data=data, metadata=metadata)
    return program_id


def run_program(
    service,
    program_id=None,
    inputs=None,
    job_classes=None,
    final_status=None,
    decoder=None,
    image="",
    instance=None,
    backend_name=None,
    log_level=None,
    job_tags=None,
    max_execution_time=None,
    session_id=None,
):
    """Run a program."""
    backend_name = backend_name if backend_name is not None else "common_backend"
    options = {
        "backend": backend_name,
        "image": image,
        "log_level": log_level,
        "job_tags": job_tags,
        "max_execution_time": max_execution_time,
        "instance": instance,
    }
    if final_status is not None:
        service._api_client.set_final_status(final_status)
    elif job_classes:
        service._api_client.set_job_classes(job_classes)
    if program_id is None:
        program_id = upload_program(service)
    job = service.run(
        program_id=program_id,
        options=options,
        inputs=inputs,
        result_decoder=decoder,
        session_id=session_id,
    )
    job._creation_date = datetime.now(timezone.utc)
    return job

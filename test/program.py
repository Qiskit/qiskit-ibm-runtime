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


def upload_program(service, name=None, max_execution_time=300, is_public: bool = False):
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
):
    """Run a program."""
    backend_name = backend_name if backend_name is not None else "common_backend"
    options = {"backend_name": backend_name, "image": image, "log_level": log_level}
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
        instance=instance,
    )
    return job

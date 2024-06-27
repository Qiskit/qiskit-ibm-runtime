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

from datetime import datetime, timezone


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
        "session_time": None,
    }
    if final_status is not None:
        service._api_client.set_final_status(final_status)
    elif job_classes:
        service._api_client.set_job_classes(job_classes)
    if not program_id:
        program_id = "sampler"
    job = service._run(
        program_id=program_id,
        options=options,
        inputs=inputs,
        result_decoder=decoder,
        session_id=session_id,
    )
    job._creation_date = datetime.now(timezone.utc)
    return job

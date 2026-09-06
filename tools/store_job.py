#!/usr/bin/env python3
# This code is part of Qiskit.
#
# (C) Copyright IBM 2024-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Retrieve and store a job for using with backwards-compatibility tests.

Retrieve a job from an instance, and store the json responsed for its details and results in the
tests directory used for backwards-compatibility tests.
"""

import argparse
import json
from pathlib import Path

from responses import PassthroughResponse, RequestsMock

from qiskit_ibm_runtime import QiskitRuntimeService


def main(instance: str, job_id: str, cloud_url: str, dir_: Path) -> None:
    """Retrieve and store a job for using with backwards-compatibility tests.

    Args:
        instance: CRN of the instance.
        job_id: ID of the job to retrieve and store.
        cloud_url: Cloud URL for the endpoints.
        dir_: Path where to write the responses to.
    """
    job_url = f"{cloud_url}/api/v1/jobs/{job_id}"
    results_url = f"{cloud_url}/api/v1/jobs/{job_id}/results"

    service = QiskitRuntimeService(instance=instance)
    # Force additional queries to take place outside mocking responses.
    service.backends()

    # Intercept HTTP responses for the jobs endpoints.
    with RequestsMock() as responses:
        job_details_endpoint = responses.add(PassthroughResponse(method="GET", url=job_url))
        job_results_endpoint = responses.add(PassthroughResponse(method="GET", url=results_url))
        job = service.job(job_id)
        job.result()

        job_details = job_details_endpoint.calls[0].response.text
        job_results = job_results_endpoint.calls[0].response.text

    # Anonymize some data.
    job_details = json.dumps(
        {**json.loads(job_details), "user_id": "unknown"}, separators=(",", ":")
    )

    # Write the responses to files.
    (dir_ / f"{job_id}_details.json").write_text(job_details, encoding="utf-8")
    (dir_ / f"{job_id}_results.json").write_text(job_results, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", type=str, help="Instance CRN.")
    parser.add_argument("--job-id", type=str, help="Job ID.")
    parser.add_argument(
        "--cloud-url",
        type=str,
        default="https://quantum.cloud.ibm.com",
        help="Cloud URL for the endpoints.",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path("test/unit/backwards_compatibility/resources"),
        help="Path where to write the responses.",
    )
    args = parser.parse_args()
    main(
        instance=args.instance,
        job_id=args.job_id,
        cloud_url=args.cloud_url,
        dir_=args.dir,
    )

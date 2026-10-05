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

"""Benchmarks for `qiskit-ibm-runtime`."""

import subprocess
import sys
from functools import partial

from qiskit_ibm_runtime import QiskitRuntimeService

from ..integration.case import integration_test_dependencies


def run_in_subprocess(cmd: str) -> None:
    """Run a Python `cmd` in a separate Python subprocess.

    This allows for benchmarking cases where the import time is meaningful.

    Args:
        cmd: a valid Python program as a string.
    """
    command = [sys.executable, "-c", cmd]
    subprocess.run(command, check=True)


def test_import_qiskit_ibm_runtime(benchmark):
    """Benchmark the importing of the package."""
    benchmark(partial(run_in_subprocess, "import qiskit_ibm_runtime"))


def test_instantiate_qiskit_runtime_service(benchmark):
    """Benchmark the instantating of `QiskitRuntimeService`."""
    dependencies = integration_test_dependencies(init_service=False)

    benchmark(
        partial(
            QiskitRuntimeService,
            instance=dependencies.instance,
            channel=dependencies.channel,
            token=dependencies.token,
            url=dependencies.url,
        )
    )

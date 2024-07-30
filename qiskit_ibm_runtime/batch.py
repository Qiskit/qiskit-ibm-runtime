# This code is part of Qiskit.
#
# (C) Copyright IBM 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Qiskit Runtime batch mode."""

from typing import Optional, Union

from qiskit.providers.backend import BackendV1, BackendV2

from qiskit_ibm_runtime import QiskitRuntimeService
from .session import Session
from .utils.deprecation import issue_deprecation_msg


class Batch(Session):
    """Class for running jobs in batch execution mode.

    The ``batch`` mode is designed to efficiently perform experiments that comprise multiple
    independent jobs.

    Using the ``batch`` mode provides the following benefits:
        - The jobs' classical computation, such as compilation, is run in parallel.
          Thus, running multiple jobs in a batch is significantly faster than running them serially.

        - There is usually minimal delay between job, which can help avoid drift.

        - If you partition your workload into multiple jobs and run them in ``batch`` mode, you can
          get results from individual jobs, which makes them more flexible to work with. For example,
          if a job's results do not meet your expectations, you can cancel the remaining jobs, or
          simply re-submit that individual job and avoid re-running the entire workload.

    All jobs need to be provided at the outset. To submit iterative jobs, use the ``session``
    mode instead.

    You can open a Qiskit Runtime batch by using this ``Batch`` class, then submit jobs
    to one or more primitives.

    For example::

        from qiskit.circuit.random import random_circuit
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        from qiskit_ibm_runtime import Batch, SamplerV2 as Sampler, QiskitRuntimeService

        service = QiskitRuntimeService()
        backend = service.least_busy(operational=True, simulator=False)
        pm = generate_preset_pass_manager(backend=backend, optimization_level=1)

        # generate fifty unique three-qubit random circuits
        circuits = [pm.run(random_circuit(3, 2, measure=True)) for _ in range(50)]

        # split up the list of circuits into partitions
        max_circuits = 10
        partitions = [circuits[i : i + max_circuits] for i in range(0, len(circuits), max_circuits)]

        # run the circuits in batched mode
        with Batch(backend=backend):
            sampler = Sampler()
            for partition in partitions:
                job = sampler.run(partition)
                pub_result = job.result()[0]
                print(f"Sampler job ID: {job.job_id()}")
                print(f"Counts for the first PUB: {pub_result.data.cr.get_counts()}")

    For more details, check the "`Run jobs in a batch
    <https://docs.quantum.ibm.com/run/run-jobs-batch>`_" tutorial.
    """

    def __init__(
        self,
        service: Optional[QiskitRuntimeService] = None,
        backend: Optional[Union[str, BackendV1, BackendV2]] = None,
        max_time: Optional[Union[int, str]] = None,
    ):
        """Batch constructor.

        Args:
            service: (DEPRECATED) Optional instance of the ``QiskitRuntimeService`` class.
                If ``None``, the service associated with the backend, if known, is used.
                Otherwise ``QiskitRuntimeService()`` is used to initialize
                your default saved account.
            backend: Instance of ``Backend`` class or backend string name. Note that passing a
                backend name is deprecated.

            max_time:
                Maximum amount of time a runtime session can be open before being
                forcibly closed. Can be specified as seconds (int) or a string like "2h 30m 40s".
                This value must be less than the
                `system imposed maximum
                <https://docs.quantum.ibm.com/run/max-execution-time>`_.

        Raises:
            ValueError: If an input value is invalid.
        """
        if service:
            issue_deprecation_msg(
                msg="The service parameter is deprecated",
                version="0.26.0",
                remedy=(
                    "The service can be extracted from the backend object so "
                    "it is no longer necessary."
                ),
                period="3 months",
            )
        if isinstance(backend, str):
            issue_deprecation_msg(
                msg="Passing a backend as a string is deprecated",
                version="0.26.0",
                remedy="Use the actual backend object instead.",
                period="3 months",
            )

        super().__init__(service=service, backend=backend, max_time=max_time)

    def _create_session(self) -> Optional[str]:
        """Create a session."""
        if isinstance(self._service, QiskitRuntimeService):
            session = self._service._api_client.create_session(
                self.backend(), self._instance, self._max_time, self._service.channel, "batch"
            )
            return session.get("id")
        return None

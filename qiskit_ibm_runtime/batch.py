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


class Batch(Session):
    """Class for creating a batch mode in Qiskit Runtime.

    Just like `session`, a Qiskit Runtime ``batch`` allows you to group a collection of
    iterative calls to the quantum computer. Batch mode can shorten processing time if all jobs
    can be provided at the outset. If you want to submit iterative jobs, use sessions instead.

    Using batch mode has these benefits:
        - The jobs' classical computation, such as compilation, is run in parallel.
          Thus, running multiple jobs in a batch is significantly faster than running them serially.

        - There is no delay between job, which can help avoid drift.

    You can open a Qiskit Runtime batch using this ``Batch`` class and submit jobs
    to one or more primitives.

    For example::

        from qiskit.circuit import QuantumCircuit, QuantumRegister, ClassicalRegister
        from qiskit_ibm_runtime import Sampler, Batch, Options

        # Bell Circuit
        qr = QuantumRegister(2, name="qr")
        cr = ClassicalRegister(2, name="cr")
        qc = QuantumCircuit(qr, cr, name="bell")
        qc.h(qr[0])
        qc.cx(qr[0], qr[1])
        qc.measure(qr, cr)

        options = Options(optimization_level=3)

        with Batch(backend="ibmq_qasm_simulator") as batch:
            sampler = Sampler(batch, options=options)
            job = sampler.run(qc)
            print(f"Sampler job ID: {job.job_id()}")
            print(f"Sampler job result: {job.result()}")

    """

    def __init__(
        self,
        service: Optional[QiskitRuntimeService] = None,
        backend: Optional[Union[str, BackendV1, BackendV2]] = None,
        max_time: Optional[Union[int, str]] = None,
    ):
        """Batch constructor.

        Args:
            service: Optional instance of the ``QiskitRuntimeService`` class.
                If ``None``, the service associated with the backend, if known, is used.
                Otherwise ``QiskitRuntimeService()`` is used to initialize
                your default saved account.
            backend: Optional instance of :class:`qiskit_ibm_runtime.IBMBackend` class or
                string name of backend. An instance of :class:`qiskit_ibm_provider.IBMBackend`
                will not work.

            max_time: (EXPERIMENTAL setting, can break between releases without warning)
                Maximum amount of time, a runtime session can be open before being
                forcibly closed. Can be specified as seconds (int) or a string like "2h 30m 40s".
                This value must be less than the
                `system imposed maximum
                <https://docs.quantum.ibm.com/run/max-execution-time>`_.

        Raises:
            ValueError: If an input value is invalid.
        """
        super().__init__(service=service, backend=backend, max_time=max_time)

    def _create_session(self) -> Optional[str]:
        """Create a session."""
        if isinstance(self._service, QiskitRuntimeService):
            session = self._service._api_client.create_session(
                self.backend(), self._instance, self._max_time, self._service.channel, "batch"
            )
            return session.get("id")
        return None

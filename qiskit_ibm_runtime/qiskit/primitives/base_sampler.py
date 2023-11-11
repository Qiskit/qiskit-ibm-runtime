# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

r"""
===================
Overview of Sampler
===================

Sampler class calculates probabilities or quasi-probabilities of bitstrings from quantum circuits.

A sampler is initialized with an empty parameter set. The sampler is used to
create a :class:`~qiskit.providers.JobV1`, via the :meth:`qiskit.primitives.Sampler.run()`
method. This method is called with the following parameters

* quantum circuits (:math:`\psi_i(\theta)`): list of (parameterized) quantum circuits.
  (a list of :class:`~qiskit.circuit.QuantumCircuit` objects)

* parameter values (:math:`\theta_k`): list of sets of parameter values
  to be bound to the parameters of the quantum circuits.
  (list of list of float)

The method returns a :class:`~qiskit.providers.JobV1` object, calling
:meth:`qiskit.providers.JobV1.result()` yields a :class:`~qiskit.primitives.SamplerResult`
object, which contains probabilities or quasi-probabilities of bitstrings,
plus optional metadata like error bars in the samples.

Here is an example of how sampler is used.

.. code-block:: python

    from qiskit.primitives import Sampler
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import RealAmplitudes

    # a Bell circuit
    bell = QuantumCircuit(2)
    bell.h(0)
    bell.cx(0, 1)
    bell.measure_all()

    # two parameterized circuits
    pqc = RealAmplitudes(num_qubits=2, reps=2)
    pqc.measure_all()
    pqc2 = RealAmplitudes(num_qubits=2, reps=3)
    pqc2.measure_all()

    theta1 = [0, 1, 1, 2, 3, 5]
    theta2 = [0, 1, 2, 3, 4, 5, 6, 7]

    # initialization of the sampler
    sampler = Sampler()

    # Sampler runs a job on the Bell circuit
    job = sampler.run(circuits=[bell], parameter_values=[[]], parameters=[[]])
    job_result = job.result()
    print([q.binary_probabilities() for q in job_result.quasi_dists])

    # Sampler runs a job on the parameterized circuits
    job2 = sampler.run(
        circuits=[pqc, pqc2],
        parameter_values=[theta1, theta2],
        parameters=[pqc.parameters, pqc2.parameters])
    job_result = job2.result()
    print([q.binary_probabilities() for q in job_result.quasi_dists])
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar, Optional, Iterable

from qiskit.circuit import QuantumCircuit
from qiskit.providers import JobV1 as Job

from .base_primitive import BasePrimitiveV2
from .options import BasePrimitiveOptionsLike
from .sampler_task import SamplerTask, SamplerTaskLike

T = TypeVar("T", bound=Job)  # pylint: disable=invalid-name


class BaseSamplerV2(BasePrimitiveV2, Generic[T]):
    """Sampler base class

    Base class of Sampler that calculates quasi-probabilities of bitstrings from quantum circuits.
    """

    def __init__(self, options: Optional[BasePrimitiveOptionsLike] = None):
        super().__init__(options=options)

    def run(self, tasks: SamplerTaskLike | Iterable[SamplerTaskLike]) -> T:
        """TODO: docstring"""
        if isinstance(tasks, SamplerTask):
            tasks = [tasks]
        elif isinstance(tasks, tuple) and isinstance(tasks[0], QuantumCircuit):
            tasks = [SamplerTask.coerce(tasks)]
        elif tasks is not SamplerTask:
            tasks = [SamplerTask.coerce(task) for task in tasks]

        for task in tasks:
            task.validate()

        return self._run(tasks)

    @abstractmethod
    def _run(self, tasks: list[SamplerTask]) -> T:
        pass

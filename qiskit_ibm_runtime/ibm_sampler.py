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

"""Qiskit Runtime Sampler primitive service."""

from typing import Optional, Iterable, Dict

from qiskit.circuit import QuantumCircuit, Parameter

from .base_primitive import BasePrimitive
from .sessions.sampler_session import SamplerSession


class IBMSampler(BasePrimitive):
    """Class for interacting with Qiskit Runtime Sampler primitive service.

    Qiskit Runtime Sampler primitive service calculates probabilities or quasi-probabilities
    of bitstrings from quantum circuits.

    Example::

        from qiskit import QuantumCircuit
        from qiskit.circuit.library import RealAmplitudes

        from qiskit_ibm_runtime import IBMRuntimeService, IBMSampler

        service = IBMRuntimeService(auth="cloud")
        sampler = IBMSampler(service=service, backend="ibmq_qasm_simulator")

        bell = QuantumCircuit(2)
        bell.h(0)
        bell.cx(0, 1)
        bell.measure_all()

        # executes a Bell circuit
        with sampler(circuits=[bell], parameters=[[]]) as session:
            result = session(parameters=[[]], circuits=[0])
            print([q.binary_probabilities() for q in result.quasi_dists])

        # executes three Bell circuits
        with sampler([bell]*3, [[]]) as session:
            result = session([0, 1, 2], [[]]*3)
            print([q.binary_probabilities() for q in result.quasi_dists])

        # parametrized circuit
        pqc = RealAmplitudes(num_qubits=2, reps=2)
        pqc.measure_all()
        pqc2 = RealAmplitudes(num_qubits=2, reps=3)
        pqc2.measure_all()

        theta1 = [0, 1, 1, 2, 3, 5]
        theta2 = [1, 2, 3, 4, 5, 6]
        theta3 = [0, 1, 2, 3, 4, 5, 6, 7]

        with sampler(circuits=[pqc, pqc2], parameters=[pqc.parameters, pqc2.parameters]) as session:
            result = session([0, 0, 1], [theta1, theta2, theta3])
            # result of pqc(theta1)
            print([q.binary_probabilities() for q in result.quasi_dists[0]])
            # result of pqc(theta2)
            print([q.binary_probabilities() for q in result.quasi_dists[1]])
            # result of pqc2(theta3)
            print([q.binary_probabilities() for q in result.quasi_dists[2]])
    """

    def __call__(  # type: ignore[override]
        self,
        circuits: Iterable[QuantumCircuit],
        parameters: Optional[Iterable[Iterable[Parameter]]] = None,
        transpile_options: Optional[Dict] = None,
        skip_transpilation: bool = False,
    ) -> SamplerSession:
        # pylint: disable=arguments-differ
        inputs = {
            "circuits": circuits,
            "parameters": parameters,
            "transpile_options": transpile_options,
            "skip_transpilation": skip_transpilation,
        }

        options = {}
        if self._backend:
            options["backend_name"] = self._backend

        return SamplerSession(
            runtime=self._service,
            program_id="sampler",
            inputs=inputs,
            options=options,
        )

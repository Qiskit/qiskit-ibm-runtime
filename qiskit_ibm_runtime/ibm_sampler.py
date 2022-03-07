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

    IBMSampler can be initialized with following parameters. It returns a factory.

    * service: Optional instance of :class:`qiskit_ibm_runtime.IBMRuntimeService` class,
        defaults to `IBMRuntimeService()` which tries to initialize your default saved account

    * backend: Optional instance of :class:`qiskit_ibm_runtime.IBMBackend` class or
        string name of backend, if not specified a backend will be selected automatically
        (IBM Cloud only)

    The factory can then be called with the following parameters to initialize the Sampler
    primitive. It returns a :class:`qiskit_ibm_runtime.sessions.SamplerSession` instance.

    * circuits: list of (parameterized) quantum circuits
        (a list of :class:`~qiskit.circuit.QuantumCircuit`))

    * parameters: a list of parameters of the quantum circuits.
        (:class:`~qiskit.circuit.parametertable.ParameterView` or
        a list of :class:`~qiskit.circuit.Parameter`)

    The :class:`qiskit_ibm_runtime.sessions.SamplerSession` instance can be called repeatedly
    with the following parameters to calculate probabilites or quasi-probabilities.

    * circuits: A list of circuit indices.

    * parameters: Concrete parameters to be bound.

    All the above lists should be of the same length.

    Example::

        from qiskit import QuantumCircuit
        from qiskit.circuit.library import RealAmplitudes

        from qiskit_ibm_runtime import IBMRuntimeService, IBMSampler

        service = IBMRuntimeService(auth="cloud")
        sampler_factory = IBMSampler(service=service, backend="ibmq_qasm_simulator")

        bell = QuantumCircuit(2)
        bell.h(0)
        bell.cx(0, 1)
        bell.measure_all()

        # executes a Bell circuit
        with sampler_factory(circuits=[bell], parameters=[[]]) as sampler:
            result = sampler(parameters=[[]], circuits=[0])
            print([q.binary_probabilities() for q in result.quasi_dists])

        # executes three Bell circuits
        with sampler_factory([bell]*3, [[]]) as sampler:
            result = sampler([0, 1, 2], [[]]*3)
            print([q.binary_probabilities() for q in result.quasi_dists])

        # parametrized circuit
        pqc = RealAmplitudes(num_qubits=2, reps=2)
        pqc.measure_all()
        pqc2 = RealAmplitudes(num_qubits=2, reps=3)
        pqc2.measure_all()

        theta1 = [0, 1, 1, 2, 3, 5]
        theta2 = [1, 2, 3, 4, 5, 6]
        theta3 = [0, 1, 2, 3, 4, 5, 6, 7]

        with sampler_factory(circuits=[pqc, pqc2], parameters=[pqc.parameters, pqc2.parameters])
            as sampler:
            result = sampler([0, 0, 1], [theta1, theta2, theta3])
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
        """Initializes the Sampler primitive.

        Args:
            circuits: list of (parameterized) quantum circuits
                (a list of :class:`~qiskit.circuit.QuantumCircuit`))
            parameters: a list of parameters of the quantum circuits.
                (:class:`~qiskit.circuit.parametertable.ParameterView` or
                a list of :class:`~qiskit.circuit.Parameter`)
            transpile_options: A collection of kwargs passed to transpile.
                Ignored if skip_transpilation is set to True.
            skip_transpilation: Transpilation is skipped if set to True.
                False by default.

        Returns:
            An instance of :class:`qiskit_ibm_runtime.sessions.SamplerSession`.
        """
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

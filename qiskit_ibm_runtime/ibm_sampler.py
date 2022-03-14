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

from typing import Optional, Iterable, Dict, Union

from qiskit.circuit import QuantumCircuit, Parameter

from .base_primitive import BasePrimitive
from .sampler import Sampler


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

    * circuits: a (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
        a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.

    * parameters: a list of parameters of the quantum circuits.
        (:class:`~qiskit.circuit.parametertable.ParameterView` or
        a list of :class:`~qiskit.circuit.Parameter`) specifying the order
        in which parameter values will be bound.

    The :class:`qiskit_ibm_runtime.sessions.SamplerSession` instance can be called repeatedly
    with the following parameters to calculate probabilites or quasi-probabilities.

    * circuit_indices: A list of circuit indices.

    * parameter_values: An optional list of concrete parameters to be bound.

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
        with sampler_factory(circuits=[bell]) as sampler:
            result = sampler(circuit_indices=[0], parameter_values=[[]])
            print(result)

        # executes three Bell circuits
        with sampler_factory([bell]*3) as sampler:
            result = sampler(circuit_indices=[0, 1, 2], parameter_values=[[]]*3)
            print(result)

        # parameterized circuit
        pqc = RealAmplitudes(num_qubits=2, reps=2)
        pqc.measure_all()
        pqc2 = RealAmplitudes(num_qubits=2, reps=3)
        pqc2.measure_all()

        theta1 = [0, 1, 1, 2, 3, 5]
        theta2 = [1, 2, 3, 4, 5, 6]
        theta3 = [0, 1, 2, 3, 4, 5, 6, 7]

        with sampler_factory(circuits=[pqc, pqc2]) as sampler:
            result = sampler(circuit_indices=[0, 0, 1], parameter_values=[theta1, theta2, theta3])
            print(result)
    """

    def __call__(  # type: ignore[override]
        self,
        circuits: Union[QuantumCircuit, Iterable[QuantumCircuit]],
        parameters: Optional[Iterable[Iterable[Parameter]]] = None,
        skip_transpilation: bool = False,
    ) -> Sampler:
        """Initializes the Sampler primitive.

        Args:
            circuits: a (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.
            parameters: A list of parameters of the quantum circuits
                (:class:`~qiskit.circuit.parametertable.ParameterView` or
                a list of :class:`~qiskit.circuit.Parameter`).
            skip_transpilation: Transpilation is skipped if set to True.
                False by default.

        Returns:
            An instance of :class:`qiskit_ibm_runtime.sampler.Sampler`.
        """
        # pylint: disable=arguments-differ
        return Sampler(
            circuits=circuits,
            parameters=parameters,
            skip_transpilation=skip_transpilation,
            service=self._service,
            backend_name=self._backend_name,
        )

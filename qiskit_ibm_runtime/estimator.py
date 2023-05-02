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

"""Estimator primitive."""

from __future__ import annotations
import os
import copy
from typing import Optional, Dict, Sequence, Any, Union
import logging
from dataclasses import asdict

from qiskit.circuit import QuantumCircuit
from qiskit.opflow import PauliSumOp
from qiskit.quantum_info.operators.base_operator import BaseOperator
from qiskit.providers.options import Options as TerraOptions
from qiskit.primitives import BaseEstimator, EstimatorResult

# TODO import _circuit_key from terra once 0.23 is released
from .runtime_job import RuntimeJob
from .ibm_backend import IBMBackend
from .session import get_default_session
from .options import Options
from .options.utils import set_default_error_levels
from .constants import DEFAULT_DECODERS

# pylint: disable=unused-import,cyclic-import
from .session import Session

logger = logging.getLogger(__name__)


class Estimator(BaseEstimator):
    """Class for interacting with Qiskit Runtime Estimator primitive service.

    Qiskit Runtime Estimator primitive service estimates expectation values of quantum circuits and
    observables.

    The :meth:`run` can be used to submit circuits, observables, and parameters
    to the Estimator primitive.

    You are encouraged to use :class:`~qiskit_ibm_runtime.Session` to open a session,
    during which you can invoke one or more primitive programs. Jobs submitted within a session
    are prioritized by the scheduler, and data is cached for efficiency.

    Example::

        from qiskit.circuit.library import RealAmplitudes
        from qiskit.quantum_info import SparsePauliOp

        from qiskit_ibm_runtime import QiskitRuntimeService, Estimator

        service = QiskitRuntimeService(channel="ibm_cloud")

        psi1 = RealAmplitudes(num_qubits=2, reps=2)

        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
        H2 = SparsePauliOp.from_list([("IZ", 1)])
        H3 = SparsePauliOp.from_list([("ZI", 1), ("ZZ", 1)])

        with Session(service=service, backend="ibmq_qasm_simulator") as session:
            estimator = Estimator(session=session)

            theta1 = [0, 1, 1, 2, 3, 5]

            # calculate [ <psi1(theta1)|H1|psi1(theta1)> ]
            psi1_H1 = estimator.run(circuits=[psi1], observables=[H1], parameter_values=[theta1])
            print(psi1_H1.result())

            # calculate [ <psi1(theta1)|H2|psi1(theta1)>, <psi1(theta1)|H3|psi1(theta1)> ]
            psi1_H23 = estimator.run(
                circuits=[psi1, psi1],
                observables=[H2, H3],
                parameter_values=[theta1]*2
            )
            print(psi1_H23.result())
            # Close the session only if all jobs are finished
            # and you don't need to run more in the session
            session.close()
    """

    _PROGRAM_ID = "estimator"

    def __init__(
        self,
        session: Optional[Union[Session, str, IBMBackend]] = None,
        options: Optional[Union[Dict, Options]] = None,
    ):
        """Initializes the Estimator primitive.

        Args:
            session: Session in which to call the primitive.

                * If an instance of :class:`qiskit_ibm_runtime.IBMBackend` class or
                  string name of a backend is specified, a new session is created for
                  that backend, unless a default session for the same backend
                  and channel already exists.

                * If ``None``, a new session is created using the default saved
                  account and a default backend (IBM Cloud channel only), unless
                  a default session already exists.

            options: Primitive options, see :class:`Options` for detailed description.
                The ``backend`` keyword is still supported but is deprecated.
        """
        # `self._options` in this class is a Dict.
        # The base class, however, uses a `_run_options` which is an instance of
        # qiskit.providers.Options. We largely ignore this _run_options because we use
        # a nested dictionary to categorize options.
        super().__init__()

        backend = None
        self._session: Session = None

        if options is None:
            self._options = asdict(Options())
        elif isinstance(options, Options):
            self._options = asdict(copy.deepcopy(options))
        else:
            options_copy = copy.deepcopy(options)
            default_options = asdict(Options())
            self._options = Options._merge_options(default_options, options_copy)

        if isinstance(session, Session):
            self._session = session
        else:
            backend = session or backend
            self._session = get_default_session(None, backend)

        # self._first_run = True
        # self._circuits_map = {}
        # if self.circuits:
        #     for circuit in self.circuits:
        #         circuit_id = _hash(
        #             json.dumps(_circuit_key(circuit), cls=RuntimeEncoder)
        #         )
        #         if circuit_id not in self._session._circuits_map:
        #             self._circuits_map[circuit_id] = circuit
        #             self._session._circuits_map[circuit_id] = circuit

    def run(  # pylint: disable=arguments-differ
        self,
        circuits: QuantumCircuit | Sequence[QuantumCircuit],
        observables: BaseOperator | PauliSumOp | Sequence[BaseOperator | PauliSumOp],
        parameter_values: Sequence[float] | Sequence[Sequence[float]] | None = None,
        **kwargs: Any,
    ) -> RuntimeJob:
        """Submit a request to the estimator primitive program.

        Args:
            circuits: a (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.

            observables: Observable objects.

            parameter_values: Concrete parameters to be bound.

            **kwargs: Individual options to overwrite the default primitive options.
                These include the runtime options in :class:`qiskit_ibm_runtime.RuntimeOptions`.

        Returns:
            Submitted job.
            The result of the job is an instance of :class:`qiskit.primitives.EstimatorResult`.

        Raises:
            ValueError: Invalid arguments are given.
        """
        # To bypass base class merging of options.
        user_kwargs = {"_user_kwargs": kwargs}
        return super().run(
            circuits=circuits,
            observables=observables,
            parameter_values=parameter_values,
            **user_kwargs,
        )

    def _run(  # pylint: disable=arguments-differ
        self,
        circuits: Sequence[QuantumCircuit],
        observables: Sequence[BaseOperator | PauliSumOp],
        parameter_values: Sequence[Sequence[float]],
        **kwargs: Any,
    ) -> RuntimeJob:
        """Submit a request to the estimator primitive program.

        Args:
            circuits: a (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.

            observables: A list of observable objects.

            parameter_values: An optional list of concrete parameters to be bound.

            **kwargs: Individual options to overwrite the default primitive options.
                These include the runtime options in :class:`~qiskit_ibm_runtime.RuntimeOptions`.

        Returns:
            Submitted job
        """
        # TODO: Re-enable data caching when ntc 1748 is fixed
        # circuits_map = {}
        # circuit_ids = []
        # for circuit in circuits:
        #     circuit_id = _hash(json.dumps(_circuit_key(circuit), cls=RuntimeEncoder))
        #     circuit_ids.append(circuit_id)
        #     if circuit_id in self._session._circuits_map:
        #         continue
        #     self._session._circuits_map[circuit_id] = circuit
        #     circuits_map[circuit_id] = circuit

        # if self._first_run:
        #     self._first_run = False
        #     circuits_map.update(self._circuits_map)

        # inputs = {
        #     "circuits": circuits_map,
        #     "circuit_ids": circuit_ids,
        #     "observables": observables,
        #     "observable_indices": list(range(len(observables))),
        #     "parameter_values": parameter_values,
        # }
        inputs = {
            "circuits": circuits,
            "circuit_indices": list(range(len(circuits))),
            "observables": observables,
            "observable_indices": list(range(len(observables))),
            "parameters": [circ.parameters for circ in circuits],
            "parameter_values": parameter_values,
        }

        combined = Options._merge_options(self._options, kwargs.get("_user_kwargs", {}))

        backend_obj: Optional[IBMBackend] = None
        if self._session.backend():
            backend_obj = self._session.service.backend(self._session.backend())
            combined = set_default_error_levels(
                combined,
                backend_obj,
                Options._DEFAULT_OPTIMIZATION_LEVEL,
                Options._DEFAULT_RESILIENCE_LEVEL,
            )
        else:
            combined["optimization_level"] = Options._DEFAULT_OPTIMIZATION_LEVEL
            combined["resilience_level"] = Options._DEFAULT_RESILIENCE_LEVEL
        logger.info("Submitting job using options %s", combined)
        self._validate_options(combined)
        inputs.update(Options._get_program_inputs(combined))

        if backend_obj and combined["transpilation"]["skip_transpilation"]:
            for circ in circuits:
                backend_obj.check_faulty(circ)

        return self._session.run(
            program_id=self._PROGRAM_ID,
            inputs=inputs,
            options=Options._get_runtime_options(combined),
            callback=combined.get("environment", {}).get("callback", None),
            result_decoder=DEFAULT_DECODERS.get(self._PROGRAM_ID),
        )

    def _call(
        self,
        circuits: Sequence[int],
        observables: Sequence[int],
        parameter_values: Optional[
            Union[Sequence[float], Sequence[Sequence[float]]]
        ] = None,
        **run_options: Any,
    ) -> EstimatorResult:
        """Estimates expectation values for given inputs in a runtime session.

        Args:
            circuits: A list of circuit indices.
            observables: A list of observable indices.
            parameter_values: An optional list of concrete parameters to be bound.
            **run_options: A collection of kwargs passed to `backend.run()`.

                shots: Number of repetitions of each circuit, for sampling.
                qubit_lo_freq: List of default qubit LO frequencies in Hz.
                meas_lo_freq: List of default measurement LO frequencies in Hz.
                schedule_los: Experiment LO configurations, frequencies are given in Hz.
                rep_delay: Delay between programs in seconds. Only supported on certain
                    backends (if ``backend.configuration().dynamic_reprate_enabled=True``).
                init_qubits: Whether to reset the qubits to the ground state for each shot.
                use_measure_esp: Whether to use excited state promoted (ESP) readout for measurements
                    which are the terminal instruction to a qubit. ESP readout can offer higher fidelity
                    than standard measurement sequences.

        Returns:
            An instance of :class:`qiskit.primitives.EstimatorResult`.
        """
        inputs = {
            "circuits": self._initial_inputs["circuits"],
            "parameters": self._initial_inputs["parameters"],
            "observables": self._initial_inputs["observables"],
            "circuit_indices": circuits,
            "parameter_values": parameter_values,
            "observable_indices": observables,
        }
        combined = Options._merge_options(self._options, run_options)

        self._validate_options(combined)
        inputs.update(Options._get_program_inputs(combined))

        return self._session.run(
            program_id=self._PROGRAM_ID,
            inputs=inputs,
            options=Options._get_runtime_options(combined),
            result_decoder=DEFAULT_DECODERS.get(self._PROGRAM_ID),
        ).result()

    @property
    def session(self) -> Session:
        """Return session used by this primitive.

        Returns:
            Session used by this primitive.
        """
        return self._session

    @property
    def options(self) -> TerraOptions:
        """Return options values for the estimator.

        Returns:
            options
        """
        return TerraOptions(**self._options)

    def set_options(self, **fields: Any) -> None:
        """Set options values for the estimator.

        Args:
            **fields: The fields to update the options
        """
        self._options = Options._merge_options(self._options, fields)

    def _validate_options(self, options: dict) -> None:
        """Validate that program inputs (options) are valid
        Raises:
            ValueError: if resilience_level is out of the allowed range.
            ValueError: if resilience_level==3, backend is simulator and no coupling map
        """
        if os.getenv("QISKIT_RUNTIME_SKIP_OPTIONS_VALIDATION"):
            return

        if not options.get("resilience_level") in list(
            range(Options._MAX_RESILIENCE_LEVEL_ESTIMATOR + 1)
        ):
            raise ValueError(
                f"resilience_level can only take the values "
                f"{list(range(Options._MAX_RESILIENCE_LEVEL_ESTIMATOR + 1))} in Estimator"
            )

        if options.get("resilience_level") == 3 and self._session.backend() in [
            b.name for b in self._session.service.backends(simulator=True)
        ]:
            if not options.get("simulator").get("coupling_map"):
                raise ValueError(
                    "When the backend is a simulator and resilience_level == 3,"
                    "a coupling map is required."
                )
        Options.validate_options(options)

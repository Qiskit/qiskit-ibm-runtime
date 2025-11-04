# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
=============================================
Executor (:mod:`qiskit_ibm_runtime.executor`)
=============================================

.. currentmodule:: qiskit_ibm_runtime.executor

Overview
========

The :class:`~.Executor` allows running :class:`~.QuantumProgram`\\s on IBM backends.

To see how to use the executor, let us first take a look at how to instantiate a
:class:`~.QuantumProgram`\\s.

Quantum Programs
~~~~~~~~~~~~~~~~

    :class:`~.QuantumProgram`\\s and related classes are part of the
    :mod:`qiskit_ibm_runtime.quantum_program` module.

A :class:`~.QuantumProgram` is an iterable of
:class:`~.qiskit_ibm_runtime.quantum_program.QuantumProgramItem`\\s. These items can own:

* a :class:`~qiskit.circuit.QuantumCircuit` with non-parametrized gates;
* or a parametrized :class:`~qiskit.circuit.QuantumCircuit`, together with an array of parameter values;
* or a parametrized :class:`~qiskit.circuit.QuantumCircuit`, together with a
  :class:`~samplomatic.samplex.Samplex` to generate randomize arrays of parameter values.

Let us take a closer look at each of these items and how to add them to a :class:`~.QuantumProgram`\\. In
the cell below, we initialize a :class:`~.QuantumProgram` and append a
:class:`~qiskit.circuit.QuantumCircuit` with non-parametrized gates.

.. code-block:: python

    from qiskit.circuit import QuantumCircuit
    from qiskit_ibm_runtime.quantum_program import QuantumProgram

    # Initialize an empty program
    program = QuantumProgram(shots=1024)

    # Initialize circuit to generate and measure GHZ state
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    circuit.measure_all()

    # Append the circuit to the program
    program.append(circuit)

Next, we append a second item that contains a parametrized :class:`~qiskit.circuit.QuantumCircuit`
and an array of parameter values.

.. code-block:: python

    from qiskit.circuit import Parameter
    import numpy as np

    # Initialize circuit to generate a GHZ state, rotate it around the Pauli-X
    # axis, and measure it
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    circuit.rx(Parameter("theta"), 0)
    circuit.rx(Parameter("phi"), 1)
    circuit.rx(Parameter("lam"), 2)
    circuit.measure_all()

    # Append the circuit and the parameter value to the program
    program.append(
        circuit,
        circuit_arguments=np.random.rand(8, 3),  # 8 sets of parameters
    )

Finally, in the next cell we append a :class:`~qiskit.circuit.QuantumCircuit` and a
:class:`~samplomatic.samplex.Samplex`. We refer the reader to :mod:`~samplomatic`
and its documentation for more details on the :class:`~samplomatic.samplex.Samplex`
and its arguments.

.. code-block:: python

    from qiskit.quantum_info import PauliLindbladMap
    from samplomatic import build, Twirl, InjectNoise

    # Initialize a to generate a GHZ state, rotate it around the Pauli-X
    # axis, and measure it; its gates and measurements are grouped inside
    # annotated boxes
    boxed_circuit = QuantumCircuit(3)
    with boxed_circuit.box([Twirl()]):
        boxed_circuit.h(0)
        boxed_circuit.cx(0, 1)
    with boxed_circuit.box([Twirl()]):
        boxed_circuit.cx(1, 2)
    with boxed_circuit.box([Twirl(), InjectNoise(ref="ref")]):
        boxed_circuit.rx(Parameter("theta"), 0)
        boxed_circuit.rx(Parameter("phi"), 1)
        boxed_circuit.rx(Parameter("lam"), 2)
        boxed_circuit.measure_all()

    # Build the template and the samplex
    template, samplex = build(boxed_circuit)

    # Append the template and samplex as a samplex item
    program.append(
        template,
        samplex=samplex,
        samplex_arguments={  
            # the arguments required by the samplex.sample method
            "parameter_values": np.random.rand(8, 3),
            "pauli_lindblad_maps": {
                "ref": PauliLindbladMap.from_sparse_list(
                    [("ZX", (1, 2), 1.0), ("YY", (0, 1), 2)],
                    num_qubits=3,
                )
            }
        },
        shape=(12, 8)  # 12 randomizations per parameter set
    )

Executor
~~~~~~~~

The :class:`~.Executor` is a runtime program that allows executing quantum programs
on IBM backends. The next cell shows how to generate a quantum program with an ISA
circuit and submit an executor job.

    .. code-block:: python

        from qiskit.transpiler import generate_preset_pass_manager
        from qiskit_ibm_runtime import QiskitRuntimeService, Executor
        from samplomatic.transpiler import generate_boxing_pass_manager

        # Choose a backend
        service = QiskitRuntimeService()
        backend = service.least_busy(operational=True, simulator=False)

        # Initialize circuit to generate and measure GHZ state
        circuit = QuantumCircuit(3)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.measure_all()

        # Transpile the circuit into an ISA circuit and group gates and measurements into boxes
        preset_pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=0)
        preset_pass_manager.post_scheduling = generate_boxing_pass_manager(
            enable_gates=True,
            enable_measures=True,
        )
        boxed_circuit = preset_pass_manager.run(circuit)

        # Build the template and the samplex
        template, samplex = build(boxed_circuit)

        # Append them to a quantum program
        program = QuantumProgram(shots=1000)
        program.append(template, samplex=samplex, samplex_arguments={})

        # Initialize the executor and set its options
        executor = Executor(backend)
        executor.options.execution.init_qubits = True

        # Run the quantum program
        job = executor.run(program)

Classes
=======

.. autosummary::
    :toctree: ../stubs/
    :nosignatures:

    Executor
"""

from __future__ import annotations

from typing import Optional

from dataclasses import asdict
import json
import logging

from ibm_quantum_schemas.models.executor.version_0_1.models import (
    QuantumProgramResultModel,
)
from ibm_quantum_schemas.models.base_params_model import BaseParamsModel

from .ibm_backend import IBMBackend, DEFAULT_IMAGE
from .session import Session  # pylint: disable=cyclic-import
from .batch import Batch  # pylint: disable=cyclic-import
from .options.executor_options import ExecutorOptions
from .qiskit_runtime_service import QiskitRuntimeService
from .quantum_program import QuantumProgram
from .quantum_program.converters import quantum_program_result_from_0_1, quantum_program_to_0_1
from .runtime_job_v2 import RuntimeJobV2
from .runtime_options import RuntimeOptions
from .utils.default_session import get_cm_session

logger = logging.getLogger()


class _Decoder:
    @classmethod
    def decode(cls, data: str):  # type: ignore[no-untyped-def]
        """Decode raw json to result type."""
        obj = QuantumProgramResultModel(**json.loads(data))
        return quantum_program_result_from_0_1(obj)


class Executor:
    """Executor to run :class:`~.QuantumProgram`\\s.

    .. code-block:: python

        from qiskit.circuit import QuantumCircuit
        from qiskit.transpiler import generate_preset_pass_manager
        from qiskit_ibm_runtime import QiskitRuntimeService, Executor
        from qiskit_ibm_runtime.quantum_program import QuantumProgram
        from samplomatic import build
        from samplomatic.transpiler import generate_boxing_pass_manager

        # Choose a backend
        service = QiskitRuntimeService()
        backend = service.least_busy(operational=True, simulator=False)

        # Initialize circuit to generate and measure GHZ state
        circuit = QuantumCircuit(3)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.measure_all()

        # Transpile the circuit into an ISA circuit and group gates and measurements into boxes
        preset_pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=0)
        preset_pass_manager.post_scheduling = generate_boxing_pass_manager(
            enable_gates=True,
            enable_measures=True,
        )
        boxed_circuit = preset_pass_manager.run(circuit)

        # Build the template and the samplex
        template, samplex = build(boxed_circuit)

        # Append them to a quantum program
        program = QuantumProgram(shots=1000)
        program.append(template, samplex=samplex, samplex_arguments={})

        # Initialize the executor and set its options
        executor = Executor(backend)
        executor.options.execution.init_qubits = True

        # Run the quantum program
        job = executor.run(program)

    Args:
        mode: The execution mode used to make the primitive query. It can be:

            * A :class:`Backend` if you are using job mode.
            * A :class:`Session` if you are using session execution mode.
            * A :class:`Batch` if you are using batch execution mode.

            Refer to the
            `Qiskit Runtime documentation <https://quantum.cloud.ibm.com/docs/guides/execution-modes>`__
            for more information about the execution modes.

        options: The desired options.
    """

    _PROGRAM_ID = "executor"
    _DECODER = _Decoder

    def __init__(
        self, mode: IBMBackend | Session | Batch | None, options: Optional[ExecutorOptions] = None
    ):

        self._session: Session | None = None
        self._backend: IBMBackend
        self._service: QiskitRuntimeService

        self._options = options or ExecutorOptions()

        if isinstance(mode, (Session, Batch)):
            self._session = mode
            self._backend = self._session._backend
            self._service = self._session.service

        elif open_session := get_cm_session():
            if open_session != mode:
                if open_session._backend != mode:
                    raise ValueError(
                        "The backend passed in to the primitive is different from the session "
                        "backend. Please check which backend you intend to use or leave the mode "
                        "parameter empty to use the session backend."
                    )
                logger.warning(
                    "A backend was passed in as the mode but a session context manager "
                    "is open so this job will run inside this session/batch "
                    "instead of in job mode."
                )
            self._session = open_session
            self._backend = self._session._backend
            self._service = self._session.service

        elif isinstance(mode, IBMBackend):
            self._backend = mode
            self._service = self._backend.service

        else:
            raise ValueError(
                "A backend or session/batch must be specified, or a session/batch must be open."
            )

    @property
    def options(self) -> ExecutorOptions:
        """The options of this executor."""
        return self._options

    def _runtime_options(self) -> RuntimeOptions:
        return RuntimeOptions(
            backend=self._backend.name,
            image=self.options.environment.image or DEFAULT_IMAGE,
            job_tags=self.options.environment.job_tags,
            log_level=self.options.environment.log_level,
            private=self.options.environment.private,
        )

    def _run(self, params: BaseParamsModel) -> RuntimeJobV2:
        runtime_options = self._runtime_options()

        if self._session:
            run = self._session._run
        else:
            run = self._service._run
            runtime_options.instance = self._backend._instance

            if get_cm_session():
                logger.warning(
                    "Even though a session/batch context manager is open this job will run in job "
                    "mode because the %s primitive was initialized outside the context manager. "
                    "Move the %s initialization inside the context manager to run in a "
                    "session/batch.",
                    self._PROGRAM_ID,
                    self._PROGRAM_ID,
                )

        inputs = params.model_dump()

        return run(
            program_id=self._PROGRAM_ID,
            options=asdict(runtime_options),
            inputs=inputs,
            result_decoder=_Decoder,
        )

    def run(self, program: QuantumProgram) -> RuntimeJobV2:
        """Run a quantum program.

        Args:
            program: The program to run.

        Returns:
            A job.
        """
        return self._run(quantum_program_to_0_1(program, self.options))

# This code is part of Qiskit.
#
# (C) Copyright IBM 2025
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
=============================================================
Noise learner V3 (:mod:`qiskit_ibm_runtime.noise_learner_v3`)
=============================================================

.. currentmodule:: qiskit_ibm_runtime.noise_learner_v3

The :class:`~.NoiseLearnerV3` is a runtime program to learn the noise process affecting target
instructions. The :meth:`~run` method expects instructions that contain a twirled-annotated
:class:`~.qiskit.circuit.BoxOp`. For instructions whose boxes contain one- and two-qubit gates,
it runs the Pauli-Lindblad learning protocol described in Ref. [1]. For instructions whose boxes
contain measurements, it runs the Twirled Readout Error eXtinction (or TREX) protocol in Ref. [2].

.. code-block:: python

    from qiskit.circuit import QuantumCircuit
    from qiskit_ibm_runtime import QiskitRuntimeService
    from qiskit_ibm_runtime.noise_learner_v3 import NoiseLearnerV3\
    from samplomatic import Twirl

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
        inject_noise_targets="all",
    )
    boxed_circuit = preset_pass_manager.run(circuit)

    # Initialize a noise learner and set its options
    learner = NoiseLearnerV3(backend)
    learner.options.shots_per_randomization = 128
    learner.options.num_randomizations = 32

    # Run a job to learn the noise affecting the instructions in the GHZ circuit
    instructions = boxed_circuit.data
    job = learner.run(instructions)

    # Retrieve the results
    result = job.result()

The ``result`` object can be converted to a dictionary mapping the :meth:`samplomatic.InjectNoise.ref`
of each instruction to a :class:`qiskit.quantum_info.PauliLindbladMap` object-the structure needed by
the :class:`~samplomatic.samplex.Samplex.sample` method. 

.. code-block:: python

    # Create a map between the instructions' `refs` and the noise models, in Pauli Lindblad
    # format
    noise_maps = result.to_dict(instructions=boxed_circuit.data)

Classes
=======

.. autosummary::
   :toctree: ../stubs/

   NoiseLearnerV3
   NoiseLearnerV3Result
   NoiseLearnerV3Results

"""

from .noise_learner_v3 import NoiseLearnerV3
from .noise_learner_v3_result import (  # type: ignore[attr-defined]
    NoiseLearnerV3Result,
    NoiseLearnerV3Results,
)

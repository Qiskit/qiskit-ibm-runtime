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

"""
=====================================================================================
Transpiler scheduling passes (:mod:`qiskit_ibm_runtime.transpiler.passes.scheduling`)
=====================================================================================

.. currentmodule:: qiskit_ibm_runtime.transpiler.passes.scheduling

A collection of scheduling passes for working with IBM Quantum's next-generation
backends that support advanced "dynamic circuit" capabilities. Ie.,
circuits with support for classical control-flow/feedback based off
of measurement results. For more information on dynamic circuits, see our
`Classical feedforward and control flow
<https://quantum.cloud.ibm.com/docs/guides/classical-feedforward-and-control-flow>`_ guide.

.. warning::
    You should not mix these scheduling passes with Qiskit's built in scheduling
    passes as they will negatively interact with the scheduling routines for
    dynamic circuits. This includes setting ``scheduling_method`` in
    :func:`~qiskit.compiler.transpile` or
    :func:`~qiskit.transpiler.preset_passmanagers.generate_preset_pass_manager`.

Classes
=======
.. autosummary::
   :toctree: ../stubs/
   :nosignatures:

    BlockBasePadder
    ALAPScheduleAnalysis
    ASAPScheduleAnalysis
    DynamicCircuitInstructionDurations
    PadDelay
    PadDynamicalDecoupling

Example usage
=============

Below we demonstrate how to schedule and pad a teleportation circuit with delays
for a dynamic circuit backend's execution model:

.. plot::
   :alt: Circuit diagram output by the previous code.
   :include-source:
   :context: close-figs

    from qiskit.circuit import ClassicalRegister, QuantumCircuit, QuantumRegister
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit.transpiler.passmanager import PassManager

    from qiskit_ibm_runtime.transpiler.passes.scheduling import ALAPScheduleAnalysis
    from qiskit_ibm_runtime.transpiler.passes.scheduling import PadDelay
    from qiskit_ibm_runtime.fake_provider import FakeJakartaV2

    backend = FakeJakartaV2()

    # Use this duration class to get appropriate durations for dynamic
    # circuit backend scheduling
    # Generate the main Qiskit transpile passes.
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
    # Configure the as-late-as-possible scheduling pass
    pm.scheduling = PassManager([
        ALAPScheduleAnalysis(target=backend.target), 
        PadDelay(target=backend.target)]
        )

    qr = QuantumRegister(3)
    crz = ClassicalRegister(1, name="crz")
    crx = ClassicalRegister(1, name="crx")
    result = ClassicalRegister(1, name="result")

    teleport = QuantumCircuit(qr, crz, crx, result, name="Teleport")

    teleport.h(qr[1])
    teleport.cx(qr[1], qr[2])
    teleport.cx(qr[0], qr[1])
    teleport.h(qr[0])
    teleport.measure(qr[0], crz)
    teleport.measure(qr[1], crx)
    with teleport.if_test((crz, 1)):
        teleport.z(qr[2])
    with teleport.if_test((crx, 1)):
        teleport.x(qr[2])
    teleport.measure(qr[2], result)

    # Transpile.
    scheduled_teleport = pm.run(teleport)

    scheduled_teleport.draw(output="mpl", style="iqp")


Instead of padding with delays we may also insert a dynamical decoupling sequence
using the :class:`PadDynamicalDecoupling` pass as shown below:

.. plot::
   :alt: Circuit diagram output by the previous code.
   :include-source:
   :context: close-figs

    from qiskit.circuit.library import XGate

    from qiskit_ibm_runtime.transpiler.passes.scheduling import PadDynamicalDecoupling


    dd_sequence = [XGate(), XGate()]

    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
    pm.scheduling = PassManager(
        [
            ALAPScheduleAnalysis(target=backend.target),
            PadDynamicalDecoupling(target=backend.target, dd_sequences=dd_sequence),
        ]
    )

    dd_teleport = pm.run(teleport)

    dd_teleport.draw(output="mpl", style="iqp")

When compiling a circuit with Qiskit, it is more efficient and more robust to perform all the
transformations in a single transpilation.  This has been done above by extending Qiskit's preset
pass managers.  For example, Qiskit's :func:`~qiskit.compiler.transpile` function internally builds
its pass set by using :func:`~qiskit.transpiler.preset_passmanagers.generate_preset_pass_manager`.
This returns instances of :class:`~qiskit.transpiler.StagedPassManager`, which can be extended.
"""

from .block_base_padder import BlockBasePadder
from .dynamical_decoupling import PadDynamicalDecoupling
from .pad_delay import PadDelay
from .scheduler import ALAPScheduleAnalysis, ASAPScheduleAnalysis
from .utils import DynamicCircuitInstructionDurations

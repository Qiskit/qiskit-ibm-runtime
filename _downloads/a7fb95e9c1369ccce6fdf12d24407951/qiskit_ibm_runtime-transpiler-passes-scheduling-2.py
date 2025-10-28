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
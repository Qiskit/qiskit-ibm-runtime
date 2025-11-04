# Uhrig sequence on qubit 0
n = 8
dd_sequence = [XGate()] * n
def uhrig_pulse_location(k):
    return np.sin(np.pi * (k + 1) / (2 * n + 2)) ** 2
spacings = []
for k in range(n):
    spacings.append(uhrig_pulse_location(k) - sum(spacings))
spacings.append(1 - sum(spacings))
pm = PassManager(
    [
        ALAPScheduleAnalysis(durations),
        PadDynamicalDecoupling(durations, dd_sequence, qubits=[0], spacings=spacings),
    ]
)
circ_dd = pm.run(circ)
circ_dd.draw('mpl', style="iqp")
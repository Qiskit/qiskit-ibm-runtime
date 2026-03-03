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
Fake Nighthawk device (120 qubit).
"""

import os
import warnings
from qiskit_ibm_runtime.fake_provider import fake_backend
from qiskit_ibm_runtime import QiskitRuntimeService

DISPLAY_WARNING = True


class FakeNighthawk(fake_backend.FakeBackendV2):
    """
    A fake 120 qubit backend. Its coupling map and basis gates match those of a
    real Nighthawk backend, but the properties are not  intended to represent
    typical Nighthawk error values. You can use this fake backend to, for
    example, transpile and optimize your circuits in preparation of the
    forthcoming Nighthawk backends.

    For a 100-qubit square lattice Ising circuit with 10 Trotter steps,
    fake_nighthawk showed a 600% improvement in circuit depth compared to
    a Heron backend.

    # Example


    ```
    from qiskit import QuantumCircuit
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime.fake_provider import FakeNighthawk
    from qiskit_ibm_runtime import SamplerV2 as Sampler

    # Initialize fake_nighthawk
    backend = FakeNighthawk()

    # Initialize quantum circuit
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)

    # Transpile circuit against fake_nighthawk
    pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
    isa_circuit = pm.run(qc)

    # Run using local simulator
    sampler = Sampler(backend)
    job = sampler.run([isa_circuit])
    result = job.result()
    ```
    """

    dirname = os.path.dirname(__file__)
    conf_filename = "conf_nighthawk.json"
    props_filename = "props_nighthawk.json"
    backend_name = "fake_nighthawk"

    def __init__(self, *args, **kwargs) -> None:  # type: ignore
        # Only display the warning statement once
        global DISPLAY_WARNING  # pylint: disable=global-statement
        if DISPLAY_WARNING:
            warnings.warn(
                "Properties of fake_nighthawk are not intended to represent "
                "typical nighthawk error values."
            )
            DISPLAY_WARNING = False

        super().__init__(*args, **kwargs)

    def refresh(self, service: QiskitRuntimeService, use_fractional_gates: bool = False) -> None:
        raise NotImplementedError("fake_nighthawk does not have calibration data to pull.")

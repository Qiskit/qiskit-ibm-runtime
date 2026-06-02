# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Helper functions for the PEC error mitigation method."""

from qiskit import QuantumCircuit
from qiskit.quantum_info import PauliLindbladMap
from samplomatic import InjectNoise
from samplomatic.utils import get_annotation


def calculate_gamma(
    boxed_circuit: QuantumCircuit,
    noise_model_mapping: dict[str, PauliLindbladMap],
    noise_factor: float,
) -> float:
    """Calculate the PEC gamma factor of a circuit based on a noise model.

    The returned gamma is that associated with the inverse noise maps needed
    to cancel the noise in the circuit.

    Args:
        boxed_circuit: The annotated circuit to calculate the PEC gamma for.
        noise_model_mapping: Mapping between layer ref to a noise model
        noise_factor: The noise factor of the noise amplification.

    Returns:
        The PEC gamma factor.
    """
    gamma = 1.0
    for instr in boxed_circuit:
        if annot := get_annotation(instr.operation, InjectNoise):
            plm = noise_model_mapping[annot.ref]
            # scale the noise by noise_factor
            plm = plm.scale_rates(noise_factor)
            gamma *= plm.inverse().gamma()
    return gamma

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

"""Functions for running a QuantumProgram on a local Aer simulator."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

import numpy as np
from qiskit.primitives.containers.bindings_array import BindingsArray
from qiskit.primitives.containers.sampler_pub import SamplerPub
from qiskit.transpiler import PassManager
from qiskit.utils.optionals import HAS_AER

from ..quantum_program import CircuitItem, SamplexItem
from ..results import QuantumProgramResult
from .broadcast_sample import broadcast_sample
from .insert_noise_pass import InsertNoisePass

if TYPE_CHECKING:
    from qiskit.quantum_info import PauliLindbladMap
    from qiskit_aer import AerSimulator

    from ..quantum_program import QuantumProgram

if HAS_AER:
    from qiskit_aer.primitives import SamplerV2 as AerSamplerV2


def _round_to_clifford(values: np.ndarray, decimals: int) -> np.ndarray:
    """Round angles to the nearest multiple of π/2 at ``decimals`` decimal places.

    This prevents floating-point drift from disqualifying nominally-Clifford circuits
    from the stabilizer simulation method.
    """
    return np.round(values / (np.pi / 2), decimals=decimals) * (np.pi / 2)


@HAS_AER.require_in_call
def run_quantum_program(
    qasm_simulator: AerSimulator,
    program: QuantumProgram,
    noise_dict: dict[str, PauliLindbladMap] | None = None,
    angle_decimals: int = 5,
    warn_absent: bool = True,
) -> QuantumProgramResult:
    """Run a quantum program on a simulator.

    Args:
        qasm_simulator: The simulator to use.
        program: The program to run.
        noise_dict: A map from barrier label refs to noise maps.
        angle_decimals: Gate angles are rounded to the nearest multiple of π/2 at this
            decimal precision before simulation.  See :func:`AerExecutor` for details.
        warn_absent: Passed to :class:`InsertNoisePass`; see :class:`AerExecutor`.

    Returns:
        Results of simulation.
    """
    # Generate a sampler
    backend = deepcopy(qasm_simulator)
    backend.set_max_qubits(10000)
    aer_sampler = AerSamplerV2.from_backend(backend)

    # _seed is private but is the only way to obtain the sampler's RNG seed for reproducibility.
    rng = np.random.default_rng(aer_sampler._seed)

    result_list = []
    metadata_list = []

    for prog_item in program.items:
        if noise_dict is not None:
            circuit = PassManager(
                [InsertNoisePass(noise_dict=noise_dict, warn_absent=warn_absent)]
            ).run(prog_item.circuit)
        else:
            circuit = prog_item.circuit

        if isinstance(prog_item, CircuitItem):
            if prog_item.circuit_arguments is not None:
                bindings_array = BindingsArray(
                    {tuple(prog_item.circuit.parameters): prog_item.circuit_arguments}
                )
                for k, v in bindings_array._data.items():
                    bindings_array._data[k] = _round_to_clifford(v, angle_decimals)
            else:
                bindings_array = None
            sampler_res = aer_sampler.run(
                [
                    SamplerPub(
                        circuit=circuit,
                        parameter_values=bindings_array,
                        shots=program.shots,
                    )  # type: ignore
                ]
            ).result()
            metadata_list.append(sampler_res[0].metadata)
            bit_array = sampler_res[0].data
            data = {key: ba.to_bool_array(order="little") for key, ba in dict(bit_array).items()}
            result_list.append(data)

        elif isinstance(prog_item, SamplexItem):
            samplex_data = broadcast_sample(
                prog_item.samplex,
                prog_item.samplex_arguments,
                prog_item.shape,
                rng,
            )
            bindings_array = BindingsArray(
                {tuple(prog_item.circuit.parameters): samplex_data.pop("parameter_values")}
            )
            for k, v in bindings_array._data.items():
                bindings_array._data[k] = _round_to_clifford(v, angle_decimals)
            sampler_res = aer_sampler.run(
                [
                    SamplerPub(
                        circuit=circuit,
                        parameter_values=bindings_array,
                        shots=program.shots,
                    )  # type: ignore
                ]
            ).result()
            metadata_list.append(sampler_res[0].metadata)
            bit_array = sampler_res[0].data
            bool_arrays = {
                key: ba.to_bool_array(order="little") for key, ba in dict(bit_array).items()
            }
            data = {**samplex_data, **bool_arrays}
            result_list.append(data)

        else:
            raise TypeError(f"Unsupported QuantumProgramItem type: {type(prog_item)}")

    return QuantumProgramResult(
        data=result_list,
        # metadata=dict(enumerate(metadata_list)),
        metadata=None,  # TODO: Figure this out
        passthrough_data=program.passthrough_data,
    )

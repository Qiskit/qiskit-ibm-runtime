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
    from qiskit.providers import BackendV2

    from ..options_models.simulator import ExperimentalSimulatorOptions
    from ..quantum_program import QuantumProgram

if HAS_AER:
    from qiskit_aer import AerSimulator
    from qiskit_aer.primitives import SamplerV2 as AerSamplerV2


def _round_to_clifford(values: np.ndarray, decimals: int) -> np.ndarray:
    """Round angles to the nearest multiple of π/2 at ``decimals`` decimal places.

    This prevents floating-point drift from disqualifying nominally-Clifford circuits
    from the stabilizer simulation method.
    """
    return np.round(values / (np.pi / 2), decimals=decimals) * (np.pi / 2)


@HAS_AER.require_in_call
def run_quantum_program(
    backend: BackendV2,
    program: QuantumProgram,
    options: ExperimentalSimulatorOptions,
) -> QuantumProgramResult:
    """Run a quantum program on a simulator.

    Args:
        backend: The backend to simulate.
        program: The program to run.
        options: The simulator options to use.

    Returns:
        Results of simulation.
    """
    seed = options.seed_simulator

    # Generate a sampler
    if isinstance(backend, AerSimulator):
        backend = deepcopy(backend)
        backend.set_max_qubits(10000)
        backend.set_options(seed_simulator=seed)

    aer_sampler = AerSamplerV2.from_backend(backend, seed=seed)

    rng = np.random.default_rng(seed)

    result_list = []
    metadata_list = []

    for prog_item in program.items:
        if (noise_dict := options.noise_model) is not None:
            circuit = PassManager(
                [InsertNoisePass(noise_dict=noise_dict, warn_absent=options.warn_absent)]
            ).run(prog_item.circuit)
        else:
            circuit = prog_item.circuit

        if isinstance(prog_item, CircuitItem):
            if prog_item.circuit_arguments is not None:
                bindings_array = BindingsArray(
                    {tuple(prog_item.circuit.parameters): prog_item.circuit_arguments}
                )
                for k, v in bindings_array._data.items():
                    bindings_array._data[k] = _round_to_clifford(v, options.angle_decimals)
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
                bindings_array._data[k] = _round_to_clifford(v, options.angle_decimals)
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

    ret = QuantumProgramResult(
        data=result_list,
        metadata=None,
        passthrough_data=program.passthrough_data,
    )
    ret._semantic_role = program._semantic_role
    return ret

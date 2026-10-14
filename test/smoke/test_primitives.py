# This code is part of Qiskit.
#
# (C) Copyright IBM 2025-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Testing simple primitive jobs for smoke tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit.library import real_amplitudes
from qiskit.primitives import PrimitiveResult
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from samplomatic.transpiler import generate_boxing_pass_manager

from qiskit_ibm_runtime import EstimatorV2, SamplerV2
from qiskit_ibm_runtime.noise_learner import NoiseLearner
from qiskit_ibm_runtime.noise_learner_v3 import NoiseLearnerV3
from qiskit_ibm_runtime.options import NoiseLearnerOptions
from qiskit_ibm_runtime.results import NoiseLearnerV3Result, NoiseLearnerV3Results
from qiskit_ibm_runtime.results.noise_learner import NoiseLearnerResult

from ..integration.dependencies import integration_test_dependencies

if TYPE_CHECKING:
    from qiskit_ibm_runtime.ibm_backend import IBMBackend

    from ..integration.dependencies import Dependencies


@pytest.fixture(scope="class")
def dependencies() -> Dependencies:
    """Return the dependencies of a smoke test, from the environment configuration."""
    return integration_test_dependencies()


@pytest.fixture(scope="class")
def backend(dependencies: Dependencies) -> IBMBackend:
    """Return the backend under test, as specified by the environment configuration."""
    return dependencies.service.backend(dependencies.qpu)


class TestSmokePrimitives:
    """Smoke tests."""

    def test_sampler(self, backend: IBMBackend) -> None:
        """Test sampler job."""
        pass_manager = generate_preset_pass_manager(optimization_level=1, target=backend.target)
        bell = QuantumCircuit(2, name="Bell")
        bell.h(0)
        bell.cx(0, 1)
        bell.measure_all()
        isa_bell = pass_manager.run(bell)

        sampler = SamplerV2(mode=backend)
        sampler.options.default_shots = 4096
        sampler.options.execution.init_qubits = True  # type: ignore[union-attr]
        sampler.options.execution.rep_delay = 0.00025  # type: ignore[union-attr]
        job = sampler.run([isa_bell])
        assert isinstance(job.result(), PrimitiveResult)

    def test_estimator(self, backend: IBMBackend) -> None:
        """Test estimator job."""
        pass_manager = generate_preset_pass_manager(optimization_level=1, target=backend.target)
        psi1 = pass_manager.run(real_amplitudes(num_qubits=2, reps=2))

        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)]).apply_layout(psi1.layout)
        theta1 = [0, 1, 1, 2, 3, 5]

        estimator = EstimatorV2(mode=backend)
        job = estimator.run([(psi1, H1, [theta1])])
        assert isinstance(job.result(), PrimitiveResult)

    def test_noise_learner(self, backend: IBMBackend) -> None:
        """Test noise learner job."""
        c1 = QuantumCircuit(2)
        c1.ecr(0, 1)

        c2 = QuantumCircuit(3)
        c2.ecr(0, 1)
        c2.ecr(1, 2)
        c2.ecr(0, 1)

        options = NoiseLearnerOptions()
        learner = NoiseLearner(mode=backend, options=options)
        job = learner.run([c1, c2])
        assert isinstance(job.result(), NoiseLearnerResult)

    def test_noise_learner_v3(self, backend: IBMBackend) -> None:
        """Test noise learner V3 job."""
        pass_manager = generate_preset_pass_manager(optimization_level=1, target=backend.target)
        boxing_pass_manager = generate_boxing_pass_manager(inject_noise_site="after")

        circuit = QuantumCircuit(QuantumRegister(3, "q"))
        circuit.cz(0, 1)
        circuit.cz(1, 2)
        circuit.measure_all()

        isa_circuit = pass_manager.run(circuit)
        boxed_circuit = boxing_pass_manager.run(isa_circuit)

        learner = NoiseLearnerV3(mode=backend)
        instructions = [instr for instr in boxed_circuit if instr.operation.name == "box"]
        job = learner.run(instructions)
        results = job.result()

        assert isinstance(results, NoiseLearnerV3Results)
        assert len(results) == 3
        assert all(isinstance(res, NoiseLearnerV3Result) for res in results)  # type: ignore[attr-defined]

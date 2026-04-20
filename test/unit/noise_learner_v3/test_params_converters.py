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

"""Tests the decoder for the quantum program result model."""

from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from samplomatic.transpiler import generate_boxing_pass_manager
from samplomatic.utils import find_unique_box_instructions

from qiskit_ibm_runtime.options import NoiseLearnerV3Options
from qiskit_ibm_runtime.noise_learner_v3.params_converters import NOISE_LEARNER_V3_PARAMS_CONVERTERS
from qiskit_ibm_runtime.fake_provider import FakeFez
from ...ibm_test_case import IBMTestCase

from ddt import data, ddt


@ddt
class TestParamsConverters(IBMTestCase):
    """Tests for ParamConverters."""

    @data(*list(NOISE_LEARNER_V3_PARAMS_CONVERTERS))
    def test_round_trip(self, schema_version):
        """Test a round trip."""
        circuit = QuantumCircuit(3, name="GHZ with params")
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.rz(Parameter("theta"), 0)
        circuit.rz(Parameter("phi"), 1)
        circuit.rz(Parameter("lam"), 2)
        circuit.measure_all()

        boxing_pm = generate_preset_pass_manager(backend=FakeFez(), optimization_level=0)
        boxing_pm.post_scheduling = generate_boxing_pass_manager(
            enable_gates=True,
            enable_measures=True,
        )
        boxed_circuit = boxing_pm.run(circuit)
        instructions = find_unique_box_instructions(boxed_circuit)

        options = NoiseLearnerV3Options()
        options.layer_pair_depths = [0, 2, 4]

        converters = NOISE_LEARNER_V3_PARAMS_CONVERTERS[schema_version]
        encoded = converters.encoder(instructions, options).model_dump()
        decoded = converters.decoder(converters.model(**encoded))

        assert decoded[0] == instructions
        assert decoded[1] == options

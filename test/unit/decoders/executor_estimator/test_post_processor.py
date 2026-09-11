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

"""Unit tests for EstimatorV2 post-processor."""

import numpy as np
from ddt import data, ddt, unpack
from qiskit.circuit import QuantumCircuit
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import SparsePauliOp

from qiskit_ibm_runtime.decoders.executor_estimator.post_processor_v0_1 import (
    _build_program_result_metadata,
    estimator_v2_post_processor_v0_1,
)
from qiskit_ibm_runtime.executor_estimator.prepare import prepare
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions
from qiskit_ibm_runtime.results.quantum_program import (
    ItemMetadata,
    QuantumProgramItemResult,
    QuantumProgramResult,
    SchedulerTiming,
    StretchValues,
)

from ....ibm_test_case import IBMTestCase

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_circuit(num_qubits: int = 2) -> QuantumCircuit:
    """Return a simple non-parameterised circuit (H + CX)."""
    qc = QuantumCircuit(num_qubits)
    qc.h(0)
    if num_qubits > 1:
        qc.cx(0, 1)
    return qc


def _make_pub(circuit=None, observable="ZZ", num_qubits=2):
    """Return a coerced EstimatorPub for a simple circuit and observable."""
    if circuit is None:
        circuit = _make_circuit(num_qubits)
    obs = SparsePauliOp.from_list([(observable, 1.0)])
    return EstimatorPub.coerce((circuit, obs), precision=None)


def _prepare_result(pubs, options, meas_data_list, *, precision=None):
    """Run prepare() and inject fake measurement data into the items.

    Returns a ``QuantumProgramResult`` ready for the post-processor.

    Args:
        pubs: list of (circuit, observable) or EstimatorPub-like objects.
        options: EstimatorOptions.
        meas_data_list: one ``np.ndarray`` per pub (plus one per extra TREX item if any).
            Each array is injected as the ``"_meas"`` key for the corresponding result item.
        precision: optional precision forwarded to prepare().
    """
    qp, _ = prepare(pubs, options, precision=precision)

    result_data = []
    for i, item_data in enumerate(meas_data_list):
        if isinstance(item_data, dict):
            result_data.append(QuantumProgramItemResult(item_data))
        else:
            result_data.append(QuantumProgramItemResult({"_meas": item_data}))

    result = QuantumProgramResult(
        data=result_data,
        metadata=None,
        passthrough_data=qp.passthrough_data,
    )
    result._semantic_role = "estimator_v2"
    return result


def _options(resilience_level=0, **kwargs):
    opts = EstimatorOptions()
    opts.resilience_level = resilience_level
    for k, v in kwargs.items():
        parts = k.split(".")
        obj = opts
        for p in parts[:-1]:
            obj = getattr(obj, p)
        setattr(obj, parts[-1], v)
    return opts


# ---------------------------------------------------------------------------
# Tests for the dispatcher
# ---------------------------------------------------------------------------


class TestEstimatorV2PostProcessor(IBMTestCase):
    """Tests for ``estimator_v2_post_processor_v0_1``."""

    def test_post_processor_empty_result(self):
        """Empty result list returns an empty PrimitiveResult."""
        result = QuantumProgramResult(data=[], metadata=None, passthrough_data={})
        primitive_result = estimator_v2_post_processor_v0_1(result)
        self.assertEqual(len(primitive_result), 0)

    def test_post_processor_missing_passthrough_data(self):
        """Missing ``post_processor`` key raises ValueError."""
        result = QuantumProgramResult(
            data=[QuantumProgramItemResult({"_meas": np.zeros((1, 1, 1, 2), dtype=bool)})],
            metadata=None,
            passthrough_data={"qiskit_mitigation": []},
        )
        with self.assertRaises(ValueError):
            estimator_v2_post_processor_v0_1(result)

    def test_post_processor_single_pub_vanilla(self):
        """Single vanilla pub returns correct expectation value."""
        # All-zero shots on ZZ → eigenvalue +1 for both qubits → ZZ = +1
        meas_data = np.zeros((1, 1, 10, 2), dtype=bool)

        opts = _options(resilience_level=0)
        pub = _make_pub(observable="ZZ")
        result = _prepare_result([pub], opts, [meas_data])

        primitive_result = estimator_v2_post_processor_v0_1(result)

        self.assertEqual(len(primitive_result), 1)
        self.assertAlmostEqual(float(primitive_result[0].data.evs.ravel()[0]), 1.0)

    def test_post_processor_multiple_pubs(self):
        """Multiple vanilla pubs each return the correct expectation value."""
        # Pub 0: all zeros → ZZ = +1
        meas_0 = np.zeros((1, 1, 10, 2), dtype=bool)
        # Pub 1: all ones → ZZ = (−1)(−1) = +1
        meas_1 = np.ones((1, 1, 10, 2), dtype=bool)

        opts = _options(resilience_level=0)
        pub0 = _make_pub(observable="ZZ")
        pub1 = _make_pub(observable="ZZ")
        result = _prepare_result([pub0, pub1], opts, [meas_0, meas_1])

        primitive_result = estimator_v2_post_processor_v0_1(result)

        self.assertEqual(len(primitive_result), 2)
        self.assertAlmostEqual(float(primitive_result[0].data.evs.ravel()[0]), 1.0)
        self.assertAlmostEqual(float(primitive_result[1].data.evs.ravel()[0]), 1.0)

    def test_post_processor_with_circuit_metadata(self):
        """Circuit metadata stored in passthrough appears in pub result metadata."""
        circuit = _make_circuit()
        circuit.metadata = {"my_key": "my_value"}
        meas_data = np.zeros((1, 1, 10, 2), dtype=bool)

        opts = _options(resilience_level=0)
        pub = EstimatorPub.coerce((circuit, SparsePauliOp.from_list([("ZZ", 1.0)])), None)
        result = _prepare_result([pub], opts, [meas_data])

        primitive_result = estimator_v2_post_processor_v0_1(result)

        self.assertEqual(
            primitive_result[0].metadata["circuit_metadata"],
            {"my_key": "my_value"},
        )

    def test_post_processor_stds_without_twirling(self):
        """Without twirling (1 randomization), stds equals ensemble_standard_error."""
        # Shape: (1 rand, 1 config, 10 shots, 2 qubits)
        meas_data = np.array([[[[False, False]] * 8 + [[False, True], [True, False]]]])

        opts = _options(resilience_level=0)
        pub = _make_pub(observable="ZZ")
        result = _prepare_result([pub], opts, [meas_data])

        primitive_result = estimator_v2_post_processor_v0_1(result)
        data_bin = primitive_result[0].data

        self.assertAlmostEqual(
            float(data_bin.stds.ravel()[0]),
            float(data_bin.ensemble_standard_error.ravel()[0]),
        )

    def test_post_processor_stds_with_twirling(self):
        """With twirling, stds and ensemble_standard_error differ and match expected values."""
        # Shape: (3 rands, 1 config, 10 shots, 2 qubits)
        # Twirl 0: 8×00 + 01 + 10  → ZZ: 8×+1 + 2×-1 → ev = 0.6
        # Twirl 1: 5×00 + 5×01     → ZZ: 5×+1 + 5×-1 → ev = 0.0
        # Twirl 2: 7×00 + 3×01     → ZZ: 7×+1 + 3×-1 → ev = 0.4
        meas_data = np.array(
            [
                [[[False, False]] * 8 + [[False, True], [True, False]]],
                [[[False, False]] * 5 + [[False, True]] * 5],
                [[[False, False]] * 7 + [[False, True]] * 3],
            ]
        )

        opts = _options(
            resilience_level=0,
            **{"twirling.num_randomizations": 3, "twirling.shots_per_randomization": 10},
        )
        pub = _make_pub(observable="ZZ")
        result = _prepare_result([pub], opts, [meas_data])

        primitive_result = estimator_v2_post_processor_v0_1(result)
        data_bin = primitive_result[0].data

        self.assertAlmostEqual(float(data_bin.evs.ravel()[0]), 1 / 3, places=5)

        expected_ensemble_std = np.sqrt((1 - (1 / 3) ** 2) / 30)
        self.assertAlmostEqual(
            float(data_bin.ensemble_standard_error.ravel()[0]), expected_ensemble_std, places=5
        )

        twirl_variance = (0.36 + 0.0 + 0.16) / 3 - (1 / 3) ** 2
        expected_stds = np.sqrt(twirl_variance / 3)
        self.assertAlmostEqual(float(data_bin.stds.ravel()[0]), expected_stds, places=5)

        self.assertNotAlmostEqual(
            float(data_bin.stds.ravel()[0]),
            float(data_bin.ensemble_standard_error.ravel()[0]),
        )

    def test_post_processor_computes_program_metadata_from_passthrough(self):
        """Program-level metadata (shots, precision, options) appears in PrimitiveResult."""
        meas_data = np.zeros((1, 1, 10, 2), dtype=bool)

        opts = _options(resilience_level=0)
        pub = _make_pub(observable="ZZ")
        result = _prepare_result([pub], opts, [meas_data], precision=0.03125)

        primitive_result = estimator_v2_post_processor_v0_1(result)

        metadata = primitive_result.metadata
        self.assertIn("shots", metadata)
        self.assertIn("target_precision", metadata)
        self.assertIn("options", metadata)

    def test_populating_compilation_key(self):
        """``compilation`` key is populated when ``ItemMetadata`` is present."""
        timing = SchedulerTiming(timing=1.0, circuit_duration=2.0)
        stretch = StretchValues(name="cx", value=1, remainder=0, expanded_values=[(1, 2)])
        item_meta = ItemMetadata(scheduler_timing=timing, stretch_values=[stretch])

        meas_data = np.zeros((1, 1, 10, 2), dtype=bool)
        opts = _options(resilience_level=0)
        pub = _make_pub(observable="ZZ")
        result = _prepare_result([pub], opts, [meas_data])

        # Inject real ItemMetadata into the result item
        result._data[0] = QuantumProgramItemResult({"_meas": meas_data}, metadata=item_meta)

        primitive_result = estimator_v2_post_processor_v0_1(result)

        compilation = primitive_result[0].metadata.get("compilation", {})
        self.assertIn("scheduler_timing", compilation)
        self.assertIn("stretch_values", compilation)
        self.assertEqual(compilation["scheduler_timing"]["timing"], 1.0)

    def test_simulation_info_in_metadata(self):
        """Simulator dict metadata is stored under ``executor`` key."""
        sim_meta = {"simulator": "aer", "shots": 1024}
        meas_data = np.zeros((1, 1, 10, 2), dtype=bool)
        opts = _options(resilience_level=0)
        pub = _make_pub(observable="ZZ")
        result = _prepare_result([pub], opts, [meas_data])

        result._data[0] = QuantumProgramItemResult({"_meas": meas_data}, metadata=sim_meta)

        primitive_result = estimator_v2_post_processor_v0_1(result)

        self.assertIn("executor", primitive_result[0].metadata)
        self.assertEqual(primitive_result[0].metadata["executor"], sim_meta)


# ---------------------------------------------------------------------------
# Tests for PEC dispatch
# ---------------------------------------------------------------------------


class TestEstimatorV2PostProcessorPEC(IBMTestCase):
    """Integration tests for PEC dispatch in ``estimator_v2_post_processor_v0_1``."""

    def _make_pec_options(self, noise_gain="auto", max_overhead=100):
        opts = EstimatorOptions()
        opts.resilience.pec_mitigation = True
        opts.twirling.enable_gates = True
        opts.twirling.enable_measure = True
        opts.resilience.pec.noise_gain = noise_gain
        opts.resilience.pec.max_overhead = max_overhead
        return opts

    def test_post_processor_pec_dispatch_applies_gamma(self):
        """PEC gamma scaling is applied to the expectation value.

        Uses an empty circuit (no gates) so PEC doesn't need layer-specific
        noise map entries — the default empty-string key suffices.

        Passes ``pub.parameter_values`` (a scalar BindingsArray from EstimatorPub.coerce)
        so that broadcast_obs_and_params=True is honoured by qiskit-mitigation.
        When parameters=None is passed directly, qiskit-mitigation forces
        broadcast_obs_and_params=False internally.
        """
        from qiskit.quantum_info import PauliLindbladMap
        from qiskit_mitigation import PEC
        from samplomatic.quantum_program import QuantumProgram

        from qiskit_ibm_runtime.results.quantum_program import QuantumProgramResult

        # Empty circuit: no gates → no layer refs → noise_maps={"": ...} works.
        circuit = QuantumCircuit(2)
        obs = SparsePauliOp.from_list([("ZZ", 1.0)])
        pub = EstimatorPub.coerce((circuit, obs, None))  # gives scalar BindingsArray
        noise_map = PauliLindbladMap.from_sparse_list([], num_qubits=2)

        pec = PEC()
        qp = QuantumProgram(shots=64)
        pec.prepare(
            circuit=pub.circuit,
            observables=pub.observables,
            parameters=pub.parameter_values,  # scalar BindingsArray, not None
            shots_per_randomization=64,
            num_randomizations=1,
            broadcast_obs_and_params=True,
            quantum_program=qp,
            noise_maps={"": noise_map},
            noise_gain=0.0,  # full PEC removal → gamma = 1.0
        )
        qp.passthrough_data["post_processor"] = {
            "version": "v0.1",
            "options": EstimatorOptions().model_dump(exclude={"resilience": {"layer_noise_model"}}),
            "shots": 64,
            "precision": None,
            "circuits_metadata": [None],
            "num_pubs": 1,
        }

        gamma = pec.gamma
        num_configs = qp.items[0].shape[1]
        # All-zero meas, all-zero pauli_signs → raw ZZ ev = +1 → scaled by gamma
        meas_data = np.zeros((1, num_configs, 10, 2), dtype=bool)
        pauli_signs = np.zeros((1, num_configs, 1), dtype=np.int8)
        result = QuantumProgramResult(
            data=[QuantumProgramItemResult({"_meas": meas_data, "pauli_signs": pauli_signs})],
            metadata=None,
            passthrough_data=qp.passthrough_data,
        )
        result._semantic_role = "estimator_v2"

        primitive_result = estimator_v2_post_processor_v0_1(result)

        self.assertAlmostEqual(float(primitive_result[0].data.evs.ravel()[0]), gamma, places=5)

    def test_pec_post_processor_output_shape(self):
        """PEC output DataBin has the correct broadcast shape.

        Uses Z-only observables on an empty circuit so all terms are diagonal
        and commute with the computational-basis measurement.

        Passes ``pub.parameter_values`` (a scalar BindingsArray from EstimatorPub.coerce)
        so that broadcast_obs_and_params=True is honoured and the output shape
        matches ``np.broadcast_shapes(obs_shape, param_shape)``.
        """
        from qiskit.primitives.containers.estimator_pub import ObservablesArray
        from qiskit.quantum_info import PauliLindbladMap
        from qiskit_mitigation import PEC
        from samplomatic.quantum_program import QuantumProgram

        from qiskit_ibm_runtime.results.quantum_program import QuantumProgramResult

        obs_shape = (2, 2)
        num_qubits = 4
        # Z-only observables: all terms are diagonal → single computational-basis config.
        observables = ObservablesArray.coerce(
            [SparsePauliOp.from_list([("Z" * num_qubits, 1.0)])] * int(np.prod(obs_shape))
        ).reshape(obs_shape)

        circuit = QuantumCircuit(num_qubits)
        pub = EstimatorPub.coerce((circuit, observables, None))  # scalar BindingsArray
        noise_map = PauliLindbladMap.from_sparse_list([], num_qubits=num_qubits)

        pec = PEC()
        qp = QuantumProgram(shots=64)
        pec.prepare(
            circuit=pub.circuit,
            observables=pub.observables,
            parameters=pub.parameter_values,  # scalar BindingsArray, not None
            shots_per_randomization=64,
            num_randomizations=1,
            broadcast_obs_and_params=True,
            quantum_program=qp,
            noise_maps={"": noise_map},
            noise_gain=0.0,
        )
        qp.passthrough_data["post_processor"] = {
            "version": "v0.1",
            "options": EstimatorOptions().model_dump(exclude={"resilience": {"layer_noise_model"}}),
            "shots": 64,
            "precision": None,
            "circuits_metadata": [None],
            "num_pubs": 1,
        }

        # Infer num_configs from the quantum-program item shape (num_rands, num_configs).
        # pec.param_basis_pairs is computed lazily during postprocess, not during prepare.
        num_configs = qp.items[0].shape[1]
        meas_data = np.zeros((1, num_configs, 10, num_qubits), dtype=bool)
        pauli_signs = np.zeros((1, num_configs, 1), dtype=np.int8)

        result = QuantumProgramResult(
            data=[QuantumProgramItemResult({"_meas": meas_data, "pauli_signs": pauli_signs})],
            metadata=None,
            passthrough_data=qp.passthrough_data,
        )
        result._semantic_role = "estimator_v2"

        primitive_result = estimator_v2_post_processor_v0_1(result)

        # broadcast_shapes(obs_shape=(2,2), param_shape=()) == (2,2)
        expected_shape = np.broadcast_shapes(obs_shape, pub.parameter_values.shape)
        data_bin = primitive_result[0].data
        self.assertTupleEqual(data_bin.evs.shape, expected_shape)
        self.assertTupleEqual(data_bin.stds.shape, expected_shape)
        self.assertTupleEqual(data_bin.ensemble_standard_error.shape, expected_shape)


# ---------------------------------------------------------------------------
# Tests for the program metadata helper
# ---------------------------------------------------------------------------


@ddt
class TestBuildProgramMetadata(IBMTestCase):
    """Tests for the :func:`_build_program_result_metadata` helper."""

    @data(
        ("zne_mitigation", "zne"),
        ("pec_mitigation", "pec"),
        ("measure_mitigation", "measure_noise_learning"),
    )
    @unpack
    def test_drops_inactive_resilience_sub_options(self, flag_key, options_key):
        """Inactive-flag sub-option dicts are dropped from the metadata dict."""

        def _get_resilience_metadata(flag_value):
            options = EstimatorOptions()
            options.resilience_level = 0
            setattr(options.resilience, flag_key, flag_value)
            post_processor_data = {
                "options": options.model_dump(),
                "shots": 1024,
                "precision": None,
            }
            return _build_program_result_metadata(post_processor_data)["options"]["resilience"]

        resilience_off = _get_resilience_metadata(False)
        self.assertNotIn(options_key, resilience_off)

        resilience_on = _get_resilience_metadata(True)
        self.assertIn(options_key, resilience_on)

    def test_returns_shots_and_precision(self):
        """Shots and target_precision appear in the returned metadata."""
        post_processor_data = {
            "options": EstimatorOptions().model_dump(),
            "shots": 2048,
            "precision": 0.02,
        }
        meta = _build_program_result_metadata(post_processor_data)
        self.assertEqual(meta["shots"], 2048)
        self.assertEqual(meta["target_precision"], 0.02)

    def test_no_options_returns_empty(self):
        """Missing ``options`` returns empty dict."""
        meta = _build_program_result_metadata({"shots": 1024})
        self.assertEqual(meta, {})

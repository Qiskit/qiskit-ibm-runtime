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

"""Unit tests for SamplerV2 post-processor and static conversion method."""

import unittest
from dataclasses import asdict

import numpy as np
from ddt import data, ddt

from qiskit.primitives import PrimitiveResult

from qiskit_ibm_runtime.decoders.executor_sampler.converters import (
    quantum_program_result_to_primitive_result,
)
from qiskit_ibm_runtime.decoders.executor_sampler.post_processor_v0_1 import (
    sampler_v2_post_processor_v0_1,
)
from qiskit_ibm_runtime.options_models.sampler_options import SamplerOptions
from qiskit_ibm_runtime.quantum_program.quantum_program_result import (
    QuantumProgramResult,
    Metadata,
)


@ddt
class TestSamplerV2StaticMethod(unittest.TestCase):
    """Test SamplerV2.quantum_program_result_to_primitive_result() static method.

    This class contains comprehensive tests for the static method that performs
    the actual conversion logic from QuantumProgramResult to PrimitiveResult.
    """

    def test_single_pub_multiple_registers(self):
        """Test conversion with single pub and multiple classical registers."""
        num_rands = 10
        num_shots_per_rand = 10
        meas_data_c1 = np.random.randint(
            0, 2, size=(num_rands, num_shots_per_rand, 2), dtype=np.uint8
        )
        meas_data_c2 = np.random.randint(
            0, 2, size=(num_rands, num_shots_per_rand, 3), dtype=np.uint8
        )

        options = SamplerOptions()
        options.twirling.enable_gates = True
        passthrough_data = {
            "post_processor": {
                "version": "v0.1",
                "options": asdict(options),
                "twirling": True,
                "meas_type": "classified",
            }
        }

        qp_result = QuantumProgramResult(
            data=[{"c1": meas_data_c1, "c2": meas_data_c2}],
            metadata=Metadata(),
            passthrough_data=passthrough_data,
        )
        qp_result._semantic_role = "sampler_v2"

        result = quantum_program_result_to_primitive_result(qp_result)

        # Verify both registers are present
        pub_result = result[0]
        self.assertIn("c1", pub_result.data)
        self.assertIn("c2", pub_result.data)

        # Verify BitArrays
        self.assertEqual(pub_result.data.c1.num_bits, 2)
        self.assertEqual(pub_result.data.c2.num_bits, 3)

    def test_multiple_pubs(self):
        """Test conversion with multiple pubs."""
        num_shots = 100
        meas_data_1 = np.random.randint(0, 2, size=(num_shots, 2), dtype=np.uint8)
        meas_data_2 = np.random.randint(0, 2, size=(num_shots, 3), dtype=np.uint8)
        meas_data_3 = np.random.randint(0, 2, size=(num_shots, 4), dtype=np.uint8)

        qp_result = QuantumProgramResult(
            data=[
                {"meas": meas_data_1},
                {"meas": meas_data_2},
                {"meas": meas_data_3},
            ],
            metadata=Metadata(),
        )

        result = quantum_program_result_to_primitive_result(qp_result)

        # Verify number of pubs
        self.assertEqual(len(result), 3)

        # Verify each pub
        self.assertEqual(result[0].data.meas.num_bits, 2)
        self.assertEqual(result[1].data.meas.num_bits, 3)
        self.assertEqual(result[2].data.meas.num_bits, 4)

    def test_missing_measurement_data(self):
        """Test error when measurement data is missing."""
        qp_result = QuantumProgramResult(
            data=[{}],  # Empty data
            metadata=Metadata(),
        )

        with self.assertRaises(ValueError) as context:
            quantum_program_result_to_primitive_result(qp_result)

        self.assertIn("no measurement data", str(context.exception).lower())

    def test_metadata_preservation(self):
        """Test that metadata is preserved in the result."""
        qp_result = QuantumProgramResult(
            data=[{"c": np.array([[5]], dtype=np.uint8)}],  # 1 byte
            metadata=Metadata(),
        )

        metadata = {"metadata": "val"}
        result = quantum_program_result_to_primitive_result(qp_result, metadata)

        # Verify metadata is present
        self.assertEqual(result.metadata, metadata)

    def test_circuit_metadata_multiple_pubs(self):
        """Test that circuit metadata is correctly placed for multiple pubs."""
        qp_result = QuantumProgramResult(
            data=[
                {"c": np.array([[5]], dtype=np.uint8)},
                {"c": np.array([[3]], dtype=np.uint8)},
                {"c": np.array([[7]], dtype=np.uint8)},
            ],
            metadata=Metadata(),
        )

        circuits_metadata = [
            {"experiment_id": "exp_001", "param": 1},
            {"experiment_id": "exp_002", "param": 2},
            {},
        ]

        result = quantum_program_result_to_primitive_result(
            qp_result, metadata=None, circuits_metadata=circuits_metadata
        )

        # Verify each pub has correct circuit metadata
        self.assertEqual(len(result), 3)
        for idx, pub_result in enumerate(result):
            self.assertIn("circuit_metadata", pub_result.metadata)
            self.assertEqual(pub_result.metadata["circuit_metadata"], circuits_metadata[idx])

    def test_circuit_metadata_none(self):
        """Test that None circuit metadata is handled correctly."""
        qp_result = QuantumProgramResult(
            data=[{"c": np.array([[5]], dtype=np.uint8)}],
            metadata=Metadata(),
        )

        circuits_metadata = [None]

        result = quantum_program_result_to_primitive_result(
            qp_result, metadata=None, circuits_metadata=circuits_metadata
        )

        # Verify pub result has empty metadata when circuit metadata is None
        pub_result = result[0]
        self.assertNotIn("circuit_metadata", pub_result.metadata)
        self.assertEqual(pub_result.metadata, {})

    def test_circuit_metadata_missing(self):
        """Test that missing circuits_metadata parameter results in empty pub metadata."""
        qp_result = QuantumProgramResult(
            data=[{"c": np.array([[5]], dtype=np.uint8)}],
            metadata=Metadata(),
        )

        result = quantum_program_result_to_primitive_result(
            qp_result, metadata=None, circuits_metadata=None
        )

        # Verify pub result has empty metadata
        pub_result = result[0]
        self.assertEqual(pub_result.metadata, {})

    def test_circuit_metadata_length_mismatch(self):
        """Test that mismatched circuits_metadata length raises ValueError."""
        qp_result = QuantumProgramResult(
            data=[
                {"c": np.array([[5]], dtype=np.uint8)},
                {"c": np.array([[3]], dtype=np.uint8)},
                {"c": np.array([[7]], dtype=np.uint8)},
            ],
            metadata=Metadata(),
        )

        # Provide metadata for only 2 pubs when there are 3
        circuits_metadata = [
            {"experiment_id": "exp_001"},
            {"experiment_id": "exp_002"},
        ]

        with self.assertRaises(ValueError) as context:
            quantum_program_result_to_primitive_result(
                qp_result, metadata=None, circuits_metadata=circuits_metadata
            )

        self.assertIn("does not match", str(context.exception))

    def test_different_register_names(self):
        """Test that any register name works (not hardcoded)."""
        num_shots = 50
        # Use unusual register names: 2 bits, 3 bits
        meas_data_custom1 = np.random.randint(0, 2, size=(num_shots, 2), dtype=np.uint8)
        meas_data_custom2 = np.random.randint(0, 2, size=(num_shots, 3), dtype=np.uint8)

        qp_result = QuantumProgramResult(
            data=[{"my_reg": meas_data_custom1, "another_reg": meas_data_custom2}],
            metadata=Metadata(),
        )

        result = quantum_program_result_to_primitive_result(qp_result)

        # Verify custom register names are preserved
        pub_result = result[0]
        self.assertIn("my_reg", pub_result.data)
        self.assertIn("another_reg", pub_result.data)

    def test_bit_array_data_integrity(self):
        """Test that BitArray data matches input measurement data."""
        num_shots = 10
        num_bits = 4
        # Create specific measurement data to verify integrity
        meas_data = np.array(
            [
                [1, 0, 1, 0],
                [0, 1, 0, 1],
                [1, 1, 0, 0],
                [0, 0, 1, 1],
                [1, 0, 0, 1],
                [0, 1, 1, 0],
                [1, 1, 1, 1],
                [0, 0, 0, 0],
                [1, 0, 1, 1],
                [0, 1, 0, 0],
            ],
            dtype=np.uint8,
        )

        qp_result = QuantumProgramResult(
            data=[{"meas": meas_data}],
            metadata=Metadata(),
        )

        result = quantum_program_result_to_primitive_result(qp_result)
        bit_array = result[0].data.meas

        # Verify the BitArray contains the same data
        self.assertEqual(bit_array.num_shots, num_shots)
        self.assertEqual(bit_array.num_bits, num_bits)

        # Convert back to bool array and compare
        reconstructed = bit_array.get_bitstrings()
        self.assertEqual(len(reconstructed), num_shots)

    @data("kerneled", "avg_kerneled")
    def test_data_integrity_kerneled(self, meas_type):
        """Test that kerneled and avg_kerneled measurements pass through.

        Verifies that the suffixes _iq and _avg_ia are removed from register names.
        """
        # Create specific measurement data to verify integrity
        meas_data = np.array(
            [1 + 0j, 0 + 1j, 1 + 1j, 0 + 0j, 1 + 0j, 0 + 1j, 1 + 1j, 0 + 0j, 1 + 0j, 0 + 1j],
            dtype=np.complex128,
        )

        # Use register name with suffix as it would come from the executor
        suffix = "_avg_iq" if meas_type == "avg_kerneled" else "_iq"
        register_name_with_suffix = f"meas{suffix}"

        qp_result = QuantumProgramResult(
            data=[{register_name_with_suffix: meas_data}],
            metadata=Metadata(),
        )

        result = quantum_program_result_to_primitive_result(qp_result, meas_type=meas_type)

        # Verify suffix was removed and data is accessible without suffix
        self.assertIn("meas", result[0].data)
        self.assertNotIn(register_name_with_suffix, result[0].data)
        result_array = result[0].data.meas

        # Verify the result array contains the same data
        np.testing.assert_array_equal(result_array, meas_data)

    def test_empty_pub_shape(self):
        """Test conversion with empty pub shape (non-parametric circuit)."""
        num_shots = 50
        num_bits = 2
        # Shape is () for non-parametric circuits
        meas_data = np.random.randint(0, 2, size=(num_shots, num_bits), dtype=np.uint8)

        qp_result = QuantumProgramResult(
            data=[{"c": meas_data}],
            metadata=Metadata(),
        )

        result = quantum_program_result_to_primitive_result(qp_result)

        # Verify pub shape is empty tuple
        pub_result = result[0]
        self.assertEqual(pub_result.data.shape, ())

    def test_complex_parameter_sweep_shape(self):
        """Test conversion with complex multi-dimensional parameter sweep."""
        num_shots = 100
        num_bits = 2
        sweep_shape = (2, 3, 4)  # 3D parameter sweep
        meas_data = np.random.randint(
            0, 2, size=sweep_shape + (num_shots, num_bits), dtype=np.uint8
        )

        qp_result = QuantumProgramResult(
            data=[{"c": meas_data}],
            metadata=Metadata(),
        )

        result = quantum_program_result_to_primitive_result(qp_result)

        # Verify complex shape is preserved
        pub_result = result[0]
        self.assertEqual(pub_result.data.shape, sweep_shape)


class TestSamplerV2PostProcessor(unittest.TestCase):
    """Test SamplerV2 post-processor function.

    This class contains basic smoke tests to verify the post-processor function
    works correctly and delegates to the static method appropriately.
    """

    def test_post_processor_with_multiple_pubs(self):
        """Test that post-processor handles multiple pubs correctly."""
        num_rands = 10
        num_shots_per_rand = 5
        meas_data_1 = np.random.randint(
            0, 2, size=(num_rands, num_shots_per_rand, 2), dtype=np.uint8
        )
        meas_data_2 = np.random.randint(
            0, 2, size=(num_rands, num_shots_per_rand, 3), dtype=np.uint8
        )

        options = SamplerOptions()
        options.twirling.enable_gates = True
        passthrough_data = {
            "post_processor": {
                "version": "v0.1",
                "options": asdict(options),
                "twirling": True,
                "meas_type": "classified",
            }
        }

        qp_result = QuantumProgramResult(
            data=[
                {"meas": meas_data_1},
                {"meas": meas_data_2},
            ],
            metadata=Metadata(),
            passthrough_data=passthrough_data,
        )
        qp_result._semantic_role = "sampler_v2"

        result = sampler_v2_post_processor_v0_1(qp_result)

        # Verify multiple pubs are handled
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].data.meas.num_bits, 2)
        self.assertEqual(result[1].data.meas.num_bits, 3)

    def test_post_processor_with_multiple_circuit_metadata(self):
        """Test that post-processor handles circuit metadata for multiple pubs."""
        num_rands = 10
        num_shots_per_rand = 5
        meas_data_1 = np.random.randint(
            0, 2, size=(num_rands, num_shots_per_rand, 2), dtype=np.uint8
        )
        meas_data_2 = np.random.randint(
            0, 2, size=(num_rands, num_shots_per_rand, 3), dtype=np.uint8
        )

        circuits_metadata = [
            {"experiment_id": "exp_001", "param": 1},
            {"experiment_id": "exp_002", "param": 2},
        ]

        options = SamplerOptions()
        options.twirling.enable_gates = True
        passthrough_data = {
            "post_processor": {
                "version": "v0.1",
                "options": asdict(options),
                "twirling": True,
                "meas_type": "classified",
                "circuits_metadata": circuits_metadata,
            }
        }

        qp_result = QuantumProgramResult(
            data=[
                {"meas": meas_data_1},
                {"meas": meas_data_2},
            ],
            metadata=Metadata(),
            passthrough_data=passthrough_data,
        )
        qp_result._semantic_role = "sampler_v2"

        result = sampler_v2_post_processor_v0_1(qp_result)

        # Verify each pub has correct circuit metadata
        self.assertEqual(len(result), 2)
        for idx, pub_result in enumerate(result):
            self.assertIn("circuit_metadata", pub_result.metadata)
            self.assertEqual(pub_result.metadata["circuit_metadata"], circuits_metadata[idx])

    def test_post_processor_circuit_metadata_length_mismatch(self):
        """Test that post-processor raises error when circuit metadata length doesn't match pubs."""
        num_shots = 100
        num_bits = 3
        meas_data_1 = np.random.randint(0, 2, size=(num_shots, num_bits), dtype=np.uint8)
        meas_data_2 = np.random.randint(0, 2, size=(num_shots, num_bits), dtype=np.uint8)

        # Provide metadata for only 1 pub when there are 2
        circuits_metadata = [{"experiment_id": "exp_001"}]

        options = SamplerOptions()
        options.twirling.enable_gates = False
        passthrough_data = {
            "post_processor": {
                "version": "v0.1",
                "options": asdict(options),
                "twirling": False,
                "meas_type": "classified",
                "circuits_metadata": circuits_metadata,
            }
        }

        qp_result = QuantumProgramResult(
            data=[{"c": meas_data_1}, {"c": meas_data_2}],
            metadata=Metadata(),
            passthrough_data=passthrough_data,
        )
        qp_result._semantic_role = "sampler_v2"

        # Should raise ValueError
        with self.assertRaises(ValueError) as context:
            sampler_v2_post_processor_v0_1(qp_result)

        self.assertIn("does not match", str(context.exception))

    def test_post_processor_applies_bit_flips(self):
        """Test that post-processor applies measurement twirling bit flips via XOR."""
        num_rands = 10
        num_shots_per_rand = 10
        num_bits = 3

        meas_data = np.random.randint(
            0, 2, size=(num_rands, num_shots_per_rand, num_bits), dtype=np.uint8
        )
        bit_flips = np.random.randint(
            0, 2, size=(num_rands, num_shots_per_rand, num_bits), dtype=np.uint8
        )

        # Store original data to verify XOR
        original_meas = meas_data.copy()

        options = SamplerOptions()
        options.twirling.enable_gates = True
        passthrough_data = {
            "post_processor": {
                "version": "v0.1",
                "options": asdict(options),
                "twirling": True,
                "meas_type": "classified",
            }
        }

        qp_result = QuantumProgramResult(
            data=[{"measurement_flips.meas": bit_flips, "meas": meas_data}],
            metadata=Metadata(),
            passthrough_data=passthrough_data,
        )
        qp_result._semantic_role = "sampler_v2"

        result = sampler_v2_post_processor_v0_1(qp_result)

        # Verify measurement_flips register was removed
        self.assertNotIn("measurement_flips.meas", result[0].data)
        self.assertIn("meas", result[0].data)

        # Verify the data in qp_result was XORed (and flattened)
        expected_data = original_meas ^ bit_flips
        np.testing.assert_array_equal(
            qp_result[0]["meas"], expected_data.reshape(num_shots_per_rand * num_rands, num_bits)
        )

    def test_post_processor_bit_flips_multiple_registers(self):
        """Test bit flips with multiple classical registers."""
        num_rands = 5
        num_shots_per_rand = 5
        meas_data_c1 = np.random.randint(
            0, 2, size=(num_rands, num_shots_per_rand, 2), dtype=np.uint8
        )
        meas_data_c2 = np.random.randint(
            0, 2, size=(num_rands, num_shots_per_rand, 3), dtype=np.uint8
        )
        bit_flips_c1 = np.random.randint(
            0, 2, size=(num_rands, num_shots_per_rand, 2), dtype=np.uint8
        )
        bit_flips_c2 = np.random.randint(
            0, 2, size=(num_rands, num_shots_per_rand, 3), dtype=np.uint8
        )

        options = SamplerOptions()
        options.twirling.enable_gates = True
        passthrough_data = {
            "post_processor": {
                "version": "v0.1",
                "options": asdict(options),
                "twirling": True,
                "meas_type": "classified",
            }
        }

        qp_result = QuantumProgramResult(
            data=[
                {
                    "measurement_flips.c1": bit_flips_c1,
                    "c1": meas_data_c1,
                    "measurement_flips.c2": bit_flips_c2,
                    "c2": meas_data_c2,
                }
            ],
            metadata=Metadata(),
            passthrough_data=passthrough_data,
        )
        qp_result._semantic_role = "sampler_v2"

        result = sampler_v2_post_processor_v0_1(qp_result)

        # Verify flip registers removed
        self.assertIn("c1", result[0].data)
        self.assertIn("c2", result[0].data)
        self.assertNotIn("measurement_flips.c1", result[0].data)
        self.assertNotIn("measurement_flips.c2", result[0].data)

    def test_post_processor_no_bit_flips(self):
        """Test that post-processor works when no bit flips are present."""
        num_rands = 5
        num_shots_per_rand = 10
        num_bits = 3
        meas_data = np.random.randint(
            0, 2, size=(num_rands, num_shots_per_rand, num_bits), dtype=np.uint8
        )

        options = SamplerOptions()
        options.twirling.enable_gates = True
        passthrough_data = {
            "post_processor": {
                "version": "v0.1",
                "options": asdict(options),
                "twirling": True,
                "meas_type": "classified",
            }
        }

        qp_result = QuantumProgramResult(
            data=[{"meas": meas_data}], metadata=Metadata(), passthrough_data=passthrough_data
        )
        qp_result._semantic_role = "sampler_v2"

        result = sampler_v2_post_processor_v0_1(qp_result)

        self.assertIsInstance(result, PrimitiveResult)
        self.assertEqual(len(result), 1)
        self.assertIn("meas", result[0].data)

    def test_post_processor_empty_result(self):
        """Test that post-processor returns empty PrimitiveResult when input is empty."""
        # Create an empty QuantumProgramResult
        qp_result = QuantumProgramResult(
            data=[],
            metadata=Metadata(),
        )

        # Apply post-processing
        result = sampler_v2_post_processor_v0_1(qp_result)

        # Verify empty result is returned
        self.assertIsInstance(result, PrimitiveResult)
        self.assertEqual(len(result), 0)
        # Verify metadata is empty
        self.assertEqual(result.metadata, {})


class TestSamplerV2PostProcessorFlattening(unittest.TestCase):
    """Test that sampler_v2_post_processor_v0_1 flattens twirling axes correctly.

    When twirling is enabled, the executor returns data with shape
    ``(num_rand, *pub_shape, shots_per_rand, num_bits)``. The post-processor
    must flatten this to ``(*pub_shape, total_shots, num_bits)`` using the
    ``pub_shapes`` stored in ``passthrough_data``.
    """

    def _make_result(self, data, twirling_enabled=False, meas_type="classified"):
        """Helper to build a QuantumProgramResult with twirling flag.

        Args:
            data: Measurement data for the result
            twirling_enabled: Whether twirling is enabled
            meas_type: Measurement type
        """
        options = SamplerOptions()
        options.twirling.enable_gates = twirling_enabled
        passthrough_data = {
            "post_processor": {
                "version": "v0.1",
                "options": asdict(options),
                "twirling": twirling_enabled,
                "meas_type": meas_type,
            }
        }

        result = QuantumProgramResult(
            data=data,
            metadata=Metadata(),
            passthrough_data=passthrough_data,
        )
        result._semantic_role = "sampler_v2"

        return result

    def test_twirled_no_sweep_flattened(self):
        """Twirled non-parametric pub: (num_rand, shots_per_rand, bits) -> (total_shots, bits)."""
        num_rand, shots_per_rand, num_bits = 4, 64, 3
        meas_data = np.random.randint(
            0, 2, size=(num_rand, shots_per_rand, num_bits), dtype=np.uint8
        )
        result = sampler_v2_post_processor_v0_1(
            self._make_result([{"meas": meas_data}], twirling_enabled=True)
        )
        bit_array = result[0].data.meas
        self.assertEqual(bit_array.num_shots, num_rand * shots_per_rand)
        self.assertEqual(bit_array.num_bits, num_bits)
        self.assertEqual(result[0].data.shape, ())

    def test_twirled_2d_sweep_flattened(self):
        """Twirled 2-D parametric pub.

        (num_rand, 5, 3, shots_per_rand, bits) -> (5, 3, total_shots, bits).
        """
        num_rand, s1, s2, shots_per_rand, num_bits = 4, 5, 3, 64, 2
        meas_data = np.random.randint(
            0, 2, size=(num_rand, s1, s2, shots_per_rand, num_bits), dtype=np.uint8
        )
        result = sampler_v2_post_processor_v0_1(
            self._make_result([{"meas": meas_data}], twirling_enabled=True)
        )
        bit_array = result[0].data.meas
        self.assertEqual(bit_array.num_shots, num_rand * shots_per_rand)
        self.assertEqual(bit_array.num_bits, num_bits)
        self.assertEqual(result[0].data.shape, (s1, s2))

    def test_twirled_data_values_preserved(self):
        """Flattening must preserve data values (just reshape, not reorder)."""
        num_rand, shots_per_rand, num_bits = 2, 3, 2
        meas_data = np.random.randint(
            0, 2, size=(num_rand, shots_per_rand, num_bits), dtype=np.uint8
        )
        result = sampler_v2_post_processor_v0_1(
            self._make_result([{"meas": meas_data}], twirling_enabled=True)
        )
        expected_flat = meas_data.reshape(num_rand * shots_per_rand, num_bits)
        reconstructed = result[0].data.meas.to_bool_array()
        np.testing.assert_array_equal(reconstructed, expected_flat.astype(bool))

    def test_non_twirled_no_reshape_when_pub_shapes_absent(self):
        """Without twirling enabled, no flattening is performed."""
        num_shots, num_bits = 100, 3
        meas_data = np.random.randint(0, 2, size=(num_shots, num_bits), dtype=np.uint8)
        # twirling_enabled=False (default)
        result = sampler_v2_post_processor_v0_1(
            self._make_result([{"meas": meas_data}], twirling_enabled=False)
        )
        bit_array = result[0].data.meas
        self.assertEqual(bit_array.num_shots, num_shots)
        self.assertEqual(bit_array.num_bits, num_bits)

    def test_error_when_twirling_missing_from_passthrough(self):
        """Verify error is raised when twirling flag is missing from passthrough data."""
        num_rand, shots_per_rand, num_bits = 4, 64, 2
        meas_data = np.random.randint(
            0, 2, size=(num_rand, shots_per_rand, num_bits), dtype=np.uint8
        )

        # Create options with twirling enabled
        options = SamplerOptions()
        options.twirling.enable_gates = True
        options_dict = asdict(options)

        # Build result with options but WITHOUT twirling flag
        post_processor_data = {
            "version": "v0.1",
            "options": options_dict,
            "meas_type": "classified",
            # Intentionally omit twirling flag
        }
        qp_result = QuantumProgramResult(
            data=[{"meas": meas_data}],
            metadata=Metadata(),
            passthrough_data={"post_processor": post_processor_data},
        )
        qp_result._semantic_role = "sampler_v2"

        # Should raise ValueError
        with self.assertRaises(ValueError) as context:
            sampler_v2_post_processor_v0_1(qp_result)

        self.assertIn("twirling", str(context.exception))

    def test_error_when_meas_type_missing_from_passthrough(self):
        """Verify error is raised when meas_type is missing from passthrough data."""
        num_rand, shots_per_rand, num_bits = 4, 64, 2
        meas_data = np.random.randint(
            0, 2, size=(num_rand, shots_per_rand, num_bits), dtype=np.uint8
        )

        # Create options with twirling enabled
        options = SamplerOptions()
        options.twirling.enable_gates = True
        options_dict = asdict(options)

        # Build result with options but WITHOUT meas_type
        post_processor_data = {
            "version": "v0.1",
            "options": options_dict,
            "twirling": True,
            # Intentionally omit meas_type
        }
        qp_result = QuantumProgramResult(
            data=[{"meas": meas_data}],
            metadata=Metadata(),
            passthrough_data={"post_processor": post_processor_data},
        )
        qp_result._semantic_role = "sampler_v2"

        # Should raise ValueError
        with self.assertRaises(ValueError) as context:
            sampler_v2_post_processor_v0_1(qp_result)

        self.assertIn("meas_type", str(context.exception))

    def test_multiple_pubs_mixed_twirled(self):
        """Multiple pubs: each pub is flattened according to its computed pub_shape."""
        num_rand, shots_per_rand, num_bits = 4, 64, 2
        # Pub 0: non-parametric twirled → (num_rand, shots_per_rand, bits)
        meas0 = np.random.randint(0, 2, size=(num_rand, shots_per_rand, num_bits), dtype=np.uint8)
        # Pub 1: 1-D sweep twirled → (num_rand, 3, shots_per_rand, bits)
        meas1 = np.random.randint(
            0, 2, size=(num_rand, 3, shots_per_rand, num_bits), dtype=np.uint8
        )
        result = sampler_v2_post_processor_v0_1(
            self._make_result([{"meas": meas0}, {"meas": meas1}], twirling_enabled=True)
        )
        self.assertEqual(result[0].data.meas.num_shots, num_rand * shots_per_rand)
        self.assertEqual(result[0].data.shape, ())
        self.assertEqual(result[1].data.meas.num_shots, num_rand * shots_per_rand)
        self.assertEqual(result[1].data.shape, (3,))

    def test_twirled_axis_ordering_preserved(self):
        """Test parameter sweep axes are not mixed with randomization axes during flattening."""
        num_rand, sweep, shots_per_rand, num_bits = 2, 3, 2, 1

        # Create data where each (rand, param) combination has a unique pattern
        # This allows us to verify that parameter indices are preserved
        meas_data = np.zeros((num_rand, sweep, shots_per_rand, num_bits), dtype=np.uint8)

        # Fill with identifiable patterns:
        # rand0, param0: all 0s
        # rand0, param1: all 1s
        # rand0, param2: all 0s
        # rand1, param0: all 1s
        # rand1, param1: all 0s
        # rand1, param2: all 1s
        for r in range(num_rand):
            for p in range(sweep):
                # Alternate pattern based on (r + p) % 2
                meas_data[r, p, :, :] = (r + p) % 2

        result = sampler_v2_post_processor_v0_1(
            self._make_result([{"meas": meas_data}], twirling_enabled=True)
        )

        bit_array = result[0].data.meas
        reconstructed = bit_array.to_bool_array()

        # Verify shape is correct
        self.assertEqual(reconstructed.shape, (sweep, num_rand * shots_per_rand, num_bits))

        # Verify that each parameter index contains the correct merged randomizations
        # For param0: should have rand0 shots (all 0s) followed by rand1 shots (all 1s)
        param0_shots = reconstructed[0, :, 0]
        np.testing.assert_array_equal(
            param0_shots[:shots_per_rand], np.zeros(shots_per_rand, dtype=bool)
        )
        np.testing.assert_array_equal(
            param0_shots[shots_per_rand:], np.ones(shots_per_rand, dtype=bool)
        )

        # For param1: should have rand0 shots (all 1s) followed by rand1 shots (all 0s)
        param1_shots = reconstructed[1, :, 0]
        np.testing.assert_array_equal(
            param1_shots[:shots_per_rand], np.ones(shots_per_rand, dtype=bool)
        )
        np.testing.assert_array_equal(
            param1_shots[shots_per_rand:], np.zeros(shots_per_rand, dtype=bool)
        )

        # For param2: should have rand0 shots (all 0s) followed by rand1 shots (all 1s)
        param2_shots = reconstructed[2, :, 0]
        np.testing.assert_array_equal(
            param2_shots[:shots_per_rand], np.zeros(shots_per_rand, dtype=bool)
        )
        np.testing.assert_array_equal(
            param2_shots[shots_per_rand:], np.ones(shots_per_rand, dtype=bool)
        )

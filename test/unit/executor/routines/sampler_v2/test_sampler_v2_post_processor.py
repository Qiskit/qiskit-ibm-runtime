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
import numpy as np

from qiskit.primitives import PrimitiveResult
from qiskit.primitives.containers import BitArray, SamplerPubResult

from qiskit_ibm_runtime.executor.routines.sampler_v2 import SamplerV2
from qiskit_ibm_runtime.executor.routines.sampler_v2.sampler_post_processors import (
    sampler_v2_post_processor_v1,
)
from qiskit_ibm_runtime.quantum_program.quantum_program_result import (
    QuantumProgramResult,
    Metadata,
)


class TestSamplerV2StaticMethod(unittest.TestCase):
    """Test SamplerV2.quantum_program_result_to_primitive_result() static method.

    This class contains comprehensive tests for the static method that performs
    the actual conversion logic from QuantumProgramResult to PrimitiveResult.
    """

    def test_single_pub_single_register(self):
        """Test conversion with single pub and single classical register."""
        # Create mock QuantumProgramResult
        num_shots = 100
        num_bits = 3
        meas_data = np.random.randint(0, 2, size=(num_shots, num_bits), dtype=np.uint8)

        qp_result = QuantumProgramResult(
            data=[{"c": meas_data}],
            metadata=Metadata(),
        )

        # Apply conversion using static method
        result = SamplerV2.quantum_program_result_to_primitive_result(qp_result)

        # Verify result type
        self.assertIsInstance(result, PrimitiveResult)
        self.assertEqual(len(result), 1)

        # Verify pub result
        pub_result = result[0]
        self.assertIsInstance(pub_result, SamplerPubResult)
        self.assertIn("c", pub_result.data)

        # Verify BitArray
        bit_array = pub_result.data.c
        self.assertIsInstance(bit_array, BitArray)
        self.assertEqual(bit_array.num_shots, num_shots)
        self.assertEqual(bit_array.num_bits, num_bits)

    def test_single_pub_multiple_registers(self):
        """Test conversion with single pub and multiple classical registers."""
        num_shots = 50
        meas_data_c1 = np.random.randint(0, 2, size=(num_shots, 2), dtype=np.uint8)
        meas_data_c2 = np.random.randint(0, 2, size=(num_shots, 3), dtype=np.uint8)

        qp_result = QuantumProgramResult(
            data=[{"c1": meas_data_c1, "c2": meas_data_c2}],
            metadata=Metadata(),
        )

        result = SamplerV2.quantum_program_result_to_primitive_result(qp_result)

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

        result = SamplerV2.quantum_program_result_to_primitive_result(qp_result)

        # Verify number of pubs
        self.assertEqual(len(result), 3)

        # Verify each pub
        self.assertEqual(result[0].data.meas.num_bits, 2)
        self.assertEqual(result[1].data.meas.num_bits, 3)
        self.assertEqual(result[2].data.meas.num_bits, 4)

    def test_parameter_sweep(self):
        """Test conversion with parameter sweep (non-trivial pub shape)."""
        num_shots = 100
        num_bits = 3
        sweep_shape = (5, 3)  # 5x3 parameter sweep
        meas_data = np.random.randint(
            0, 2, size=sweep_shape + (num_shots, num_bits), dtype=np.uint8
        )

        qp_result = QuantumProgramResult(
            data=[{"c": meas_data}],
            metadata=Metadata(),
        )

        result = SamplerV2.quantum_program_result_to_primitive_result(qp_result)

        # Verify shape
        pub_result = result[0]
        self.assertEqual(pub_result.data.shape, sweep_shape)
        self.assertEqual(pub_result.data.c.num_bits, num_bits)

    def test_missing_measurement_data(self):
        """Test error when measurement data is missing."""
        qp_result = QuantumProgramResult(
            data=[{}],  # Empty data
            metadata=Metadata(),
        )

        with self.assertRaises(ValueError) as context:
            SamplerV2.quantum_program_result_to_primitive_result(qp_result)

        self.assertIn("no measurement data", str(context.exception).lower())

    def test_metadata_preservation(self):
        """Test that metadata is preserved in the result."""
        qp_result = QuantumProgramResult(
            data=[{"c": np.array([[5]], dtype=np.uint8)}],  # 1 byte
            metadata=Metadata(),
        )

        result = SamplerV2.quantum_program_result_to_primitive_result(qp_result)

        # Verify metadata is present
        self.assertIn("quantum_program_metadata", result.metadata)

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

        result = SamplerV2.quantum_program_result_to_primitive_result(qp_result)

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

        result = SamplerV2.quantum_program_result_to_primitive_result(qp_result)
        bit_array = result[0].data.meas

        # Verify the BitArray contains the same data
        self.assertEqual(bit_array.num_shots, num_shots)
        self.assertEqual(bit_array.num_bits, num_bits)

        # Convert back to bool array and compare
        reconstructed = bit_array.get_bitstrings()
        self.assertEqual(len(reconstructed), num_shots)

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

        result = SamplerV2.quantum_program_result_to_primitive_result(qp_result)

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

        result = SamplerV2.quantum_program_result_to_primitive_result(qp_result)

        # Verify complex shape is preserved
        pub_result = result[0]
        self.assertEqual(pub_result.data.shape, sweep_shape)


class TestSamplerV2PostProcessor(unittest.TestCase):
    """Test SamplerV2 post-processor function.

    This class contains basic smoke tests to verify the post-processor function
    works correctly and delegates to the static method appropriately.
    """

    def test_post_processor_basic_functionality(self):
        """Test that post-processor function works for basic case."""
        num_shots = 100
        num_bits = 3
        meas_data = np.random.randint(0, 2, size=(num_shots, num_bits), dtype=np.uint8)

        qp_result = QuantumProgramResult(
            data=[{"c": meas_data}],
            metadata=Metadata(),
        )

        # Apply post-processing
        result = sampler_v2_post_processor_v1(qp_result)

        # Verify basic structure
        self.assertIsInstance(result, PrimitiveResult)
        self.assertEqual(len(result), 1)
        self.assertIn("c", result[0].data)
        self.assertEqual(result[0].data.c.num_shots, num_shots)
        self.assertEqual(result[0].data.c.num_bits, num_bits)

    def test_post_processor_with_multiple_pubs(self):
        """Test that post-processor handles multiple pubs correctly."""
        num_shots = 50
        meas_data_1 = np.random.randint(0, 2, size=(num_shots, 2), dtype=np.uint8)
        meas_data_2 = np.random.randint(0, 2, size=(num_shots, 3), dtype=np.uint8)

        qp_result = QuantumProgramResult(
            data=[
                {"meas": meas_data_1},
                {"meas": meas_data_2},
            ],
            metadata=Metadata(),
        )

        result = sampler_v2_post_processor_v1(qp_result)

        # Verify multiple pubs are handled
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].data.meas.num_bits, 2)
        self.assertEqual(result[1].data.meas.num_bits, 3)

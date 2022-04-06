# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for program related runtime functions."""

import copy
import json
import os
import tempfile
import warnings
from io import StringIO
from unittest.mock import patch

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.exceptions import RuntimeProgramNotFound
from qiskit_ibm_runtime.runtime_program import ParameterNamespace
from ..ibm_test_case import IBMTestCase
from ..decorators import run_quantum_and_cloud_fake
from ..program import upload_program, DEFAULT_DATA, DEFAULT_METADATA


class TestPrograms(IBMTestCase):
    """Class for testing runtime modules."""

    @run_quantum_and_cloud_fake
    def test_list_programs(self, service):
        """Test listing programs."""
        program_id = upload_program(service)
        programs = service.programs()
        all_ids = [prog.program_id for prog in programs]
        self.assertIn(program_id, all_ids)

    @run_quantum_and_cloud_fake
    def test_list_programs_with_limit_skip(self, service):
        """Test listing programs with limit and skip."""
        program_ids = []
        for _ in range(3):
            program_ids.append(upload_program(service))
        programs = service.programs(limit=2, skip=1)
        all_ids = [prog.program_id for prog in programs]
        self.assertNotIn(program_ids[0], all_ids)
        self.assertIn(program_ids[1], all_ids)
        self.assertIn(program_ids[2], all_ids)
        programs = service.programs(limit=3)
        all_ids = [prog.program_id for prog in programs]
        self.assertIn(program_ids[0], all_ids)

    @run_quantum_and_cloud_fake
    def test_list_program(self, service):
        """Test listing a single program."""
        program_id = upload_program(service)
        program = service.program(program_id)
        self.assertEqual(program_id, program.program_id)

    @run_quantum_and_cloud_fake
    def test_print_programs(self, service):
        """Test printing programs."""
        ids = []
        for idx in range(3):
            ids.append(upload_program(service, name=f"name_{idx}"))

        programs = service.programs()
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            service.pprint_programs()
            stdout = mock_stdout.getvalue()
            for prog in programs:
                self.assertIn(prog.program_id, stdout)
                self.assertIn(prog.name, stdout)
                self.assertNotIn(str(prog.max_execution_time), stdout)
                self.assertNotIn("Backend requirements", stdout)
            service.pprint_programs(detailed=True)
            stdout_detailed = mock_stdout.getvalue()
            for prog in programs:
                self.assertIn(prog.program_id, stdout_detailed)
                self.assertIn(prog.name, stdout_detailed)
                self.assertIn(str(prog.max_execution_time), stdout_detailed)
                self.assertIn("Backend requirements", stdout_detailed)

    @run_quantum_and_cloud_fake
    def test_upload_program(self, service):
        """Test uploading a program."""
        max_execution_time = 3000
        is_public = True
        program_id = upload_program(
            service=service, max_execution_time=max_execution_time, is_public=is_public
        )
        self.assertTrue(program_id)
        program = service.program(program_id)
        self.assertTrue(program)
        self.assertEqual(max_execution_time, program.max_execution_time)
        self.assertEqual(program.is_public, is_public)

    @run_quantum_and_cloud_fake
    def test_update_program(self, service):
        """Test updating program."""
        new_data = "def main() {foo=bar}"
        new_metadata = copy.deepcopy(DEFAULT_METADATA)
        new_metadata["name"] = "test_update_program"
        new_name = "name2"
        new_description = "some other description"
        new_cost = DEFAULT_METADATA["max_execution_time"] + 100
        new_spec = copy.deepcopy(DEFAULT_METADATA["spec"])
        new_spec["backend_requirements"] = {"input_allowed": "runtime"}

        sub_tests = [
            {"data": new_data},
            {"metadata": new_metadata},
            {"data": new_data, "metadata": new_metadata},
            {"metadata": new_metadata, "name": new_name},
            {
                "data": new_data,
                "metadata": new_metadata,
                "description": new_description,
            },
            {"max_execution_time": new_cost, "spec": new_spec},
        ]

        for new_vals in sub_tests:
            with self.subTest(new_vals=new_vals.keys()):
                program_id = upload_program(service)
                service.update_program(program_id=program_id, **new_vals)
                updated = service.program(program_id, refresh=True)
                if "data" in new_vals:
                    raw_program = service._api_client.program_get(program_id)
                    self.assertEqual(new_data, raw_program["data"])
                if "metadata" in new_vals and "name" not in new_vals:
                    self.assertEqual(new_metadata["name"], updated.name)
                if "name" in new_vals:
                    self.assertEqual(new_name, updated.name)
                if "description" in new_vals:
                    self.assertEqual(new_description, updated.description)
                if "max_execution_time" in new_vals:
                    self.assertEqual(new_cost, updated.max_execution_time)
                if "spec" in new_vals:
                    raw_program = service._api_client.program_get(program_id)
                    self.assertEqual(new_spec, raw_program["spec"])

    @run_quantum_and_cloud_fake
    def test_update_program_no_new_fields(self, service):
        """Test updating a program without any new data."""
        program_id = upload_program(service)
        with warnings.catch_warnings(record=True) as warn_cm:
            service.update_program(program_id=program_id)
            self.assertEqual(len(warn_cm), 1)

    @run_quantum_and_cloud_fake
    def test_update_phantom_program(self, service):
        """Test updating a phantom program."""
        with self.assertRaises(RuntimeProgramNotFound):
            service.update_program("phantom_program", name="foo")

    @run_quantum_and_cloud_fake
    def test_delete_program(self, service):
        """Test deleting program."""
        program_id = upload_program(service)
        service.delete_program(program_id)
        with self.assertRaises(RuntimeProgramNotFound):
            service.program(program_id, refresh=True)

    @run_quantum_and_cloud_fake
    def test_double_delete_program(self, service):
        """Test deleting a deleted program."""
        program_id = upload_program(service)
        service.delete_program(program_id)
        with self.assertRaises(RuntimeProgramNotFound):
            service.delete_program(program_id)

    @run_quantum_and_cloud_fake
    def test_retrieve_program_data(self, service):
        """Test retrieving program data"""
        program_id = upload_program(service, name="qiskit-test")
        service.programs()
        program = service.program(program_id)
        self.assertEqual(program.data, DEFAULT_DATA)
        self._validate_program(program)

    @run_quantum_and_cloud_fake
    def test_program_params_validation(self, service):
        """Test program parameters validation process"""
        program_id = upload_program(service)
        program = service.program(program_id)
        params: ParameterNamespace = program.parameters()
        params.param1 = "Hello, World"
        # Check OK params
        params.validate()
        # Check OK params - contains unnecessary param
        params.param3 = "Hello, World"
        params.validate()
        # Check bad params - missing required param
        params.param1 = None
        with self.assertRaises(IBMInputValueError):
            params.validate()
        params.param1 = "foo"

    @run_quantum_and_cloud_fake
    def test_program_metadata(self, service):
        """Test program metadata."""
        temp_fp = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        json.dump(DEFAULT_METADATA, temp_fp)
        temp_fp.close()

        sub_tests = [temp_fp.name, DEFAULT_METADATA]
        try:
            for metadata in sub_tests:
                with self.subTest(metadata_type=type(metadata)):
                    program_id = service.upload_program(
                        data=DEFAULT_DATA, metadata=metadata
                    )
                    program = service.program(program_id)
                    service.delete_program(program_id)
                    self._validate_program(program)
        finally:
            os.remove(temp_fp.name)

    @run_quantum_and_cloud_fake
    def test_set_program_visibility(self, service):
        """Test setting program visibility."""
        program_id = upload_program(service, is_public=False)
        service.set_program_visibility(program_id, True)
        program = service.program(program_id)
        self.assertTrue(program.is_public)

    @run_quantum_and_cloud_fake
    def test_set_program_visibility_phantom_program(self, service):
        """Test setting program visibility for a phantom program."""
        with self.assertRaises(RuntimeProgramNotFound):
            service.set_program_visibility("foo", True)

    def _validate_program(self, program):
        """Validate a program."""
        self.assertEqual(DEFAULT_METADATA["name"], program.name)
        self.assertEqual(DEFAULT_METADATA["description"], program.description)
        self.assertEqual(
            DEFAULT_METADATA["max_execution_time"], program.max_execution_time
        )
        self.assertTrue(program.creation_date)
        self.assertTrue(program.update_date)
        self.assertEqual(
            DEFAULT_METADATA["spec"]["backend_requirements"],
            program.backend_requirements,
        )
        self.assertEqual(
            DEFAULT_METADATA["spec"]["parameters"], program.parameters().metadata
        )
        self.assertEqual(
            DEFAULT_METADATA["spec"]["return_values"], program.return_values
        )
        self.assertEqual(
            DEFAULT_METADATA["spec"]["interim_results"], program.interim_results
        )

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

"""Tests for runtime service."""

import os
import tempfile
import unittest

from qiskit_ibm_runtime.exceptions import IBMNotAuthorizedError
from qiskit_ibm_runtime.exceptions import (
    RuntimeProgramNotFound,
)
from qiskit_ibm_runtime.runtime_program import RuntimeProgram
from ..ibm_test_case import IBMIntegrationTestCase
from ..decorators import run_integration_test, quantum_only
from ..templates import RUNTIME_PROGRAM, PROGRAM_PREFIX


class TestIntegrationProgram(IBMIntegrationTestCase):
    """Integration tests for runtime modules."""

    @run_integration_test
    @quantum_only
    def test_list_programs(self, service):
        """Test listing programs."""
        program_id = self._upload_program(service)
        programs = service.programs()
        self.assertTrue(programs)
        found = False
        for prog in programs:
            self._validate_program(prog)
            if prog.program_id == program_id:
                found = True
        self.assertTrue(found, f"Program {program_id} not found!")

    @run_integration_test
    @quantum_only
    def test_list_programs_with_limit_skip(self, service):
        """Test listing programs with limit and skip."""
        for _ in range(4):
            self._upload_program(service)
        programs = service.programs(limit=3, refresh=True)
        all_ids = [prog.program_id for prog in programs]
        self.assertEqual(len(all_ids), 3, f"Retrieved programs: {all_ids}")
        programs = service.programs(limit=2, skip=1)
        some_ids = [prog.program_id for prog in programs]
        self.assertEqual(len(some_ids), 2, f"Retrieved programs: {some_ids}")
        self.assertNotIn(all_ids[0], some_ids)
        self.assertIn(all_ids[1], some_ids)
        self.assertIn(all_ids[2], some_ids)

    @run_integration_test
    @quantum_only
    def test_list_program(self, service):
        """Test listing a single program."""
        program_id = self._upload_program(service)
        program = service.program(program_id)
        self.assertEqual(program_id, program.program_id)
        self._validate_program(program)

    @run_integration_test
    @quantum_only
    def test_retrieve_program_data(self, service):
        """Test retrieving program data"""
        program_id = self._upload_program(service)
        program = service.program(program_id)
        self.assertEqual(RUNTIME_PROGRAM, program.data)
        self._validate_program(program)

    @run_integration_test
    def test_retrieve_unauthorized_program_data(self, service):
        """Test retrieving program data when user is not the program author"""
        programs = service.programs()
        not_mine = None
        for prog in programs:
            if prog.is_public:
                not_mine = prog
                break
        if not_mine is None:
            self.skipTest("Cannot find a program that's not mine!")
        with self.assertRaises(IBMNotAuthorizedError):
            return not_mine.data

    @run_integration_test
    @quantum_only
    def test_upload_program(self, service):
        """Test uploading a program."""
        max_execution_time = 3000
        program_id = self._upload_program(
            service, max_execution_time=max_execution_time
        )
        self.assertTrue(program_id)
        program = service.program(program_id)
        self.assertTrue(program)
        self.assertEqual(max_execution_time, program.max_execution_time)

    @run_integration_test
    @quantum_only
    def test_upload_program_file(self, service):
        """Test uploading a program using a file."""
        temp_fp = tempfile.NamedTemporaryFile(mode="w", delete=False)
        self.addCleanup(os.remove, temp_fp.name)
        temp_fp.write(RUNTIME_PROGRAM)
        temp_fp.close()

        program_id = self._upload_program(service, data=temp_fp.name)
        self.assertTrue(program_id)
        program = service.program(program_id)
        self.assertTrue(program)

    @unittest.skip("Skip until authorized to upload public on cloud")
    @unittest.skipIf(
        not os.environ.get("QISKIT_IBM_USE_STAGING_CREDENTIALS", ""),
        "Only runs on staging",
    )
    @run_integration_test
    def test_upload_public_program(self, service):
        """Test uploading a public program."""
        max_execution_time = 3000
        is_public = True
        program_id = self._upload_program(
            service, max_execution_time=max_execution_time, is_public=is_public
        )
        self.assertTrue(program_id)
        program = service.program(program_id)
        self.assertTrue(program)
        self.assertEqual(max_execution_time, program.max_execution_time)
        self.assertEqual(program.is_public, is_public)

    @unittest.skip("Skip until authorized to upload public on cloud")
    @unittest.skipIf(
        not os.environ.get("QISKIT_IBM_USE_STAGING_CREDENTIALS", ""),
        "Only runs on staging",
    )
    @run_integration_test
    def test_set_visibility(self, service):
        """Test setting the visibility of a program."""
        program_id = self._upload_program(service)
        # Get the initial visibility
        prog: RuntimeProgram = service.program(program_id)
        start_vis = prog.is_public
        # Flip the original value
        service.set_program_visibility(program_id, not start_vis)
        # Get the new visibility
        prog: RuntimeProgram = service.program(program_id, refresh=True)
        end_vis = prog.is_public
        # Verify changed
        self.assertNotEqual(start_vis, end_vis)

    @run_integration_test
    @quantum_only
    def test_delete_program(self, service):
        """Test deleting program."""
        program_id = self._upload_program(service)
        service.delete_program(program_id)
        with self.assertRaises(RuntimeProgramNotFound):
            service.program(program_id, refresh=True)

    @run_integration_test
    @quantum_only
    def test_double_delete_program(self, service):
        """Test deleting a deleted program."""
        program_id = self._upload_program(service)
        service.delete_program(program_id)
        with self.assertRaises(RuntimeProgramNotFound):
            service.delete_program(program_id)

    @run_integration_test
    @quantum_only
    def test_update_program_data(self, service):
        """Test updating program data."""
        program_v1 = """
def main(backend, user_messenger, **kwargs):
    return "version 1"
        """
        program_v2 = """
def main(backend, user_messenger, **kwargs):
    return "version 2"
        """
        program_id = self._upload_program(service, data=program_v1)
        self.assertEqual(program_v1, service.program(program_id).data)
        service.update_program(program_id=program_id, data=program_v2)
        self.assertEqual(program_v2, service.program(program_id).data)

    @run_integration_test
    @quantum_only
    def test_update_program_metadata(self, service):
        """Test updating program metadata."""
        program_id = self._upload_program(service)
        original = service.program(program_id)
        new_metadata = {
            "name": PROGRAM_PREFIX,
            "description": "test_update_program_metadata",
            "max_execution_time": original.max_execution_time + 100,
            "spec": {
                "return_values": {"type": "object", "description": "Some return value"}
            },
        }
        service.update_program(program_id=program_id, metadata=new_metadata)
        updated = service.program(program_id, refresh=True)
        self.assertEqual(new_metadata["name"], updated.name)
        self.assertEqual(new_metadata["description"], updated.description)
        self.assertEqual(new_metadata["max_execution_time"], updated.max_execution_time)
        self.assertEqual(new_metadata["spec"]["return_values"], updated.return_values)

    def _validate_program(self, program):
        """Validate a program."""
        self.assertTrue(program)
        self.assertTrue(program.name)
        self.assertTrue(program.program_id)
        self.assertTrue(program.description)
        self.assertTrue(program.max_execution_time)
        self.assertTrue(program.creation_date)
        self.assertTrue(program.update_date)

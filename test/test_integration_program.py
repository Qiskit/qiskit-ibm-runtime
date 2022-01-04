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

import copy
import unittest
import os
import uuid
from contextlib import suppress
import tempfile
from collections import defaultdict

from qiskit_ibm_runtime.exceptions import IBMNotAuthorizedError
from qiskit_ibm_runtime.runtime_program import RuntimeProgram
from qiskit_ibm_runtime.exceptions import (
    RuntimeProgramNotFound,
)

from .ibm_test_case import IBMTestCase
from .utils.decorators import requires_cloud_legacy_services, run_cloud_legacy_real
from .utils.templates import RUNTIME_PROGRAM, RUNTIME_PROGRAM_METADATA, PROGRAM_PREFIX


class TestIntegrationProgram(IBMTestCase):
    """Integration tests for runtime modules."""

    @classmethod
    @requires_cloud_legacy_services
    def setUpClass(cls, services):
        """Initial class level setup."""
        # pylint: disable=arguments-differ
        super().setUpClass()
        cls.services = services

    def setUp(self) -> None:
        """Test level setup."""
        super().setUp()
        self.to_delete = defaultdict(list)

    def tearDown(self) -> None:
        """Test level teardown."""
        super().tearDown()
        # Delete programs
        for service in self.services:
            for prog in self.to_delete[service.auth]:
                with suppress(Exception):
                    service.delete_program(prog)

    @run_cloud_legacy_real
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

    @run_cloud_legacy_real
    def test_list_programs_with_limit_skip(self, service):
        """Test listing programs with limit and skip."""
        for _ in range(4):
            self._upload_program(service)
        programs = service.programs(limit=3, refresh=True)
        all_ids = [prog.program_id for prog in programs]
        self.assertEqual(len(all_ids), 3)
        programs = service.programs(limit=2, skip=1)
        some_ids = [prog.program_id for prog in programs]
        self.assertEqual(len(some_ids), 2)
        self.assertNotIn(all_ids[0], some_ids)
        self.assertIn(all_ids[1], some_ids)
        self.assertIn(all_ids[2], some_ids)

    @run_cloud_legacy_real
    def test_list_program(self, service):
        """Test listing a single program."""
        program_id = self._upload_program(service)
        program = service.program(program_id)
        self.assertEqual(program_id, program.program_id)
        self._validate_program(program)

    @run_cloud_legacy_real
    def test_retrieve_program_data(self, service):
        """Test retrieving program data"""
        program_id = self._upload_program(service)
        program = service.program(program_id)
        self.assertEqual(RUNTIME_PROGRAM, program.data)
        self._validate_program(program)

    @run_cloud_legacy_real
    def test_retrieve_unauthorized_program_data(self, service):
        """Test retrieving program data when user is not the program author"""
        program = service.program("sample-program")
        self._validate_program(program)
        with self.assertRaises(IBMNotAuthorizedError):
            return program.data

    @run_cloud_legacy_real
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

    @run_cloud_legacy_real
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
    @run_cloud_legacy_real
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
    @run_cloud_legacy_real
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

    @run_cloud_legacy_real
    def test_delete_program(self, service):
        """Test deleting program."""
        program_id = self._upload_program(service)
        service.delete_program(program_id)
        with self.assertRaises(RuntimeProgramNotFound):
            service.program(program_id, refresh=True)

    @run_cloud_legacy_real
    def test_double_delete_program(self, service):
        """Test deleting a deleted program."""
        program_id = self._upload_program(service)
        service.delete_program(program_id)
        with self.assertRaises(RuntimeProgramNotFound):
            service.delete_program(program_id)

    @run_cloud_legacy_real
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

    @run_cloud_legacy_real
    def test_update_program_metadata(self, service):
        """Test updating program metadata."""
        program_id = self._upload_program(service)
        original = service.program(program_id)
        new_metadata = {
            "name": self._get_program_name(),
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

    def _upload_program(
        self,
        service,
        name=None,
        max_execution_time=300,
        data=None,
        is_public: bool = False,
    ):
        """Upload a new program."""
        name = name or self._get_program_name()
        data = data or RUNTIME_PROGRAM
        metadata = copy.deepcopy(RUNTIME_PROGRAM_METADATA)
        metadata["name"] = name
        metadata["max_execution_time"] = max_execution_time
        metadata["is_public"] = is_public
        program_id = service.upload_program(data=data, metadata=metadata)
        self.to_delete[service.auth].append(program_id)
        return program_id

    @classmethod
    def _get_program_name(cls):
        """Return a unique program name."""
        return PROGRAM_PREFIX + "_" + uuid.uuid4().hex

# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests CLI that saves user account to disk."""
from typing import List
import unittest
from unittest.mock import patch
from textwrap import dedent

from qiskit_ibm_runtime._cli import SaveAccountCLI, UserInput, Formatter

from qiskit_ibm_runtime.accounts.account import IBM_CLOUD_API_URL, IBM_QUANTUM_API_URL
from ..ibm_test_case import IBMTestCase


class MockIO:
    """Mock `input` and `getpass`"""

    # pylint: disable=missing-function-docstring

    def __init__(self, inputs: List[str]):
        self.inputs = inputs
        self.output = ""

    def mock_input(self, *args, **_kwargs):
        if args:
            self.mock_print(args[0])
        return self.inputs.pop(0)

    def mock_print(self, *args, **_kwargs):
        self.output += " ".join(args) + "\n"


class TestCLI(IBMTestCase):
    """Tests for the save-account CLI."""

    # pylint: disable=missing-class-docstring, missing-function-docstring

    def test_select_from_list(self):
        """Test the `UserInput.select_from_list` helper method"""
        self.maxDiff = 3000  # pylint: disable=invalid-name

        # Check a bunch of invalid inputs before entering a valid one
        mockio = MockIO(["", "0", "-1", "3.14", "9", " 3"])

        @patch("builtins.input", mockio.mock_input)
        @patch("builtins.print", mockio.mock_print)
        def run_test():
            choice = UserInput.select_from_list(["a", "b", "c", "d"], Formatter(color=False))
            self.assertEqual(choice, "c")

        run_test()
        self.assertEqual(mockio.inputs, [])
        self.assertEqual(
            mockio.output,
            dedent(
                """
              (1) a
              (2) b
              (3) c
              (4) d

            Enter a number 1-4 and press enter:•
            Did not understand input, trying again... (or type 'q' to quit)
            Enter a number 1-4 and press enter:•
            Did not understand input, trying again... (or type 'q' to quit)
            Enter a number 1-4 and press enter:•
            Did not understand input, trying again... (or type 'q' to quit)
            Enter a number 1-4 and press enter:•
            Did not understand input, trying again... (or type 'q' to quit)
            Enter a number 1-4 and press enter:•
            Did not understand input, trying again... (or type 'q' to quit)
            Enter a number 1-4 and press enter:•
            Selected c
            """.replace(
                    "•", " "
                )
            ),
        )

    def test_cli_multiple_instances_saved_account(self):
        """
        Full CLI: User has many instances and account saved.
        """
        token = "Password123"
        instances = ["my/instance/1", "my/instance/2", "my/instance/3"]
        selected_instance = 2  # == instances[1]

        class MockRuntimeService:
            def __init__(self, *_args, **_kwargs):
                pass

            def instances(self):
                return instances

        expected_saved_account = dedent(
            f"""
            {{
                "default": {{
                    "channel": "ibm_quantum",
                    "instance": "{instances[selected_instance-1]}",
                    "private_endpoint": false,
                    "token": "{token}",
                    "url": "{IBM_QUANTUM_API_URL}"
                }}
            }}
        """
        )

        existing_account = dedent(
            """
            {
                "default": {
                    "channel": "ibm_quantum",
                    "instance": "my/instance/0",
                    "private_endpoint": false,
                    "token": "super-secret-token",
                    "url": "https://auth.quantum-computing.ibm.com/api"
                }
            }
            """
        )

        mockio = MockIO(["1", token, str(selected_instance), "yes"])
        mock_open = unittest.mock.mock_open(read_data=existing_account)

        @patch("builtins.input", mockio.mock_input)
        @patch("builtins.open", mock_open)
        @patch("builtins.print", mockio.mock_print)
        @patch("os.path.isfile", lambda *args: True)
        @patch("qiskit_ibm_runtime._cli.getpass", mockio.mock_input)
        @patch("qiskit_ibm_runtime._cli.QiskitRuntimeService", MockRuntimeService)
        def run_cli():
            SaveAccountCLI(color=True).main()

        run_cli()
        self.assertEqual(mockio.inputs, [])

        written_output = "".join(call.args[0] for call in mock_open().write.mock_calls)
        self.assertEqual(written_output.strip(), expected_saved_account.strip())

    def test_cli_one_instance_no_saved_account(self):
        """
        Full CLI: user only has one instance and no account saved.
        """
        token = "QJjjbOxSfzZiskMZiyty"
        instance = "my/only/instance"

        class MockRuntimeService:
            def __init__(self, *_args, **_kwargs):
                pass

            def instances(self):
                return [instance]

        expected_saved_account = dedent(
            f"""
            {{
                "default": {{
                    "channel": "ibm_cloud",
                    "instance": "{instance}",
                    "private_endpoint": false,
                    "token": "{token}",
                    "url": "{IBM_CLOUD_API_URL}"
                }}
            }}
        """
        )

        mockio = MockIO(["2", token])
        mock_open = unittest.mock.mock_open(read_data="{}")

        @patch("builtins.input", mockio.mock_input)
        @patch("builtins.open", mock_open)
        @patch("builtins.print", mockio.mock_print)
        @patch("os.path.isfile", lambda *args: False)
        @patch("qiskit_ibm_runtime._cli.getpass", mockio.mock_input)
        @patch("qiskit_ibm_runtime._cli.QiskitRuntimeService", MockRuntimeService)
        def run_cli():
            SaveAccountCLI(color=True).main()

        run_cli()
        self.assertEqual(mockio.inputs, [])

        written_output = "".join(call.args[0] for call in mock_open().write.mock_calls)
        # The extra "{}" is runtime ensuring the file exists
        self.assertEqual(written_output.strip(), "{}" + expected_saved_account.strip())

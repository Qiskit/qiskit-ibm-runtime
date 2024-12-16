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

"""
The `save-account` command-line interface.

These classes and functions are not public.
"""

import argparse
import sys
from getpass import getpass
from typing import List, Literal, Callable, TypeVar

from ibm_cloud_sdk_core.api_exception import ApiException

from .qiskit_runtime_service import QiskitRuntimeService
from .exceptions import IBMNotAuthorizedError
from .api.exceptions import RequestsApiError
from .accounts.management import AccountManager, _DEFAULT_ACCOUNT_CONFIG_JSON_FILE
from .accounts.exceptions import AccountAlreadyExistsError

Channel = Literal["ibm_quantum", "ibm_cloud"]
T = TypeVar("T")


def entry_point() -> None:
    """
    This is the entry point for the `qiskit-ibm-runtime` command. At the
    moment, we only support one script (save-account), but we want to have a
    `qiskit-ibm-runtime` command so users can run `pipx run qiskit-ibm-runtime
    save-account`.
    """
    # Use argparse to create the --help feature
    parser = argparse.ArgumentParser(
        prog="qiskit-ibm-runtime",
        description="Commands for the Qiskit IBM Runtime Python package",
    )
    parser.add_subparsers(
        title="Commands",
        description="This package supports the following commands:",
        dest="script",
        required=True,
    ).add_parser(
        "save-account",
        description=(
            "An interactive command-line interface to save your Qiskit IBM "
            "Runtime account locally. This script is interactive-only."
        ),
        help="Interactive command-line interface to save your account locally.",
    ).add_argument(
        "--no-color", action="store_true", help="Hide ANSI escape codes in output"
    )
    args = parser.parse_args()
    use_color = not args.no_color
    if args.script == "save-account":
        try:
            SaveAccountCLI(color=use_color).main()
        except KeyboardInterrupt:
            sys.exit()


class Formatter:
    """Format using terminal escape codes"""

    # pylint: disable=missing-function-docstring
    #
    def __init__(self, color: bool):
        self.color = color

    @staticmethod
    def _skip_if_no_color(method):
        """Decorator to skip the method if self.color == False"""

        def new_method(self, s: str) -> str:
            if not self.color:
                return s
            return method(self, s)

        return new_method

    def box(self, lines: List[str]) -> str:
        """Print lines in a box using Unicode box-drawing characters"""
        width = max(len(line) for line in lines)
        box_lines = [
            "╭─" + "─" * width + "─╮",
            *(f"│ {self.bold(line.ljust(width))} │" for line in lines),
            "╰─" + "─" * width + "─╯",
        ]
        return "\n".join(box_lines)

    @_skip_if_no_color
    def bold(self, s: str) -> str:
        return f"\033[1m{s}\033[0m"

    @_skip_if_no_color
    def green(self, s: str) -> str:
        return f"\033[32m{s}\033[0m"

    @_skip_if_no_color
    def red(self, s: str) -> str:
        return f"\033[31m{s}\033[0m"

    @_skip_if_no_color
    def cyan(self, s: str) -> str:
        return f"\033[36m{s}\033[0m"

    @_skip_if_no_color
    def greenbold(self, s: str) -> str:
        return self.green(self.bold(s))


class SaveAccountCLI:
    """
    This class contains the save-account command and helper functions.
    """

    def __init__(self, color: bool):
        self.color = color
        self.fmt = Formatter(color=color)

    def main(self) -> None:
        """
        A CLI that guides users through getting their account information and
        saving it to disk.
        """
        print(self.fmt.box(["Qiskit IBM Runtime save account"]))
        channel = self.get_channel()
        token = self.get_token(channel)
        print("Verifying, this might take few seconds...")
        try:
            service = QiskitRuntimeService(channel=channel, token=token)
        except (ApiException, IBMNotAuthorizedError, RequestsApiError) as err:
            print(
                self.fmt.red(self.fmt.bold("\nError while authorizing with your token\n"))
                + self.fmt.red(err.message or "")
            )
            sys.exit(1)
        instance = self.get_instance(service)
        self.save_to_disk(
            {
                "channel": channel,
                "token": token,
                "instance": instance,
            }
        )

    def get_channel(self) -> Channel:
        """Ask user which channel to use"""
        print(self.fmt.bold("Select a channel"))
        return UserInput.select_from_list(["ibm_quantum", "ibm_cloud"], self.fmt)

    def get_token(self, channel: Channel) -> str:
        """Ask user for their token"""
        token_url = {
            "ibm_quantum": "https://quantum.ibm.com",
            "ibm_cloud": "https://cloud.ibm.com/iam/apikeys",
        }[channel]
        print(
            self.fmt.bold("\nPaste your API token")
            + f"\nYou can get this from {self.fmt.cyan(token_url)}."
            + "\nFor security, you might not see any feedback when typing."
        )
        return UserInput.token()

    def get_instance(self, service: QiskitRuntimeService) -> str:
        """
        Ask user which instance to use, or select automatically if only one
        is available.
        """
        instances = service.instances()
        if len(instances) == 1:
            instance = instances[0]
            print(f"Using instance {self.fmt.greenbold(instance)}")
            return instance
        print(self.fmt.bold("\nSelect a default instance"))
        return UserInput.select_from_list(instances, self.fmt)

    def save_to_disk(self, account: dict) -> None:
        """
        Save account details to disk, confirming if they'd like to overwrite if
        one exists already. Display a warning that token is stored in plain
        text.
        """
        try:
            AccountManager.save(**account)
        except AccountAlreadyExistsError:
            response = UserInput.input(
                message="\nDefault account already exists, would you like to overwrite it? (y/N):",
                is_valid=lambda response: response.strip().lower() in ["y", "yes", "n", "no", ""],
            )
            if response.strip().lower() in ["y", "yes"]:
                AccountManager.save(**account, overwrite=True)
            else:
                print("Account not saved.")
                return

        print(f"Account saved to {self.fmt.greenbold(_DEFAULT_ACCOUNT_CONFIG_JSON_FILE)}")
        print(
            self.fmt.box(
                [
                    "⚠️ Warning: your token is saved to disk in plain text.",
                    "If on a shared computer, make sure to revoke your token",
                    "by regenerating it in your account settings when finished.",
                ]
            )
        )


class UserInput:
    """
    Helper functions to get different types input from user.
    """

    @staticmethod
    def input(message: str, is_valid: Callable[[str], bool]) -> str:
        """
        Repeatedly ask user for input until they give us something that satisifies
        `is_valid`.
        """
        while True:
            response = input(message + " ").strip()
            if response in ["q", "quit"]:
                sys.exit()
            if is_valid(response):
                return response
            print("Did not understand input, trying again... (or type 'q' to quit)")

    @staticmethod
    def token() -> str:
        while True:
            token = getpass("Token: ").strip()
            if token != "":
                return token

    @staticmethod
    def select_from_list(options: List[T], formatter: Formatter) -> T:
        """
        Prompt user to select from a list of options by entering a number.
        """
        print()
        for index, option in enumerate(options):
            print(f"  ({index+1}) {option}")
        print()
        response = UserInput.input(
            message=f"Enter a number 1-{len(options)} and press enter:",
            is_valid=lambda response: response.isdigit()
            and int(response) in range(1, len(options) + 1),
        )
        choice = options[int(response) - 1]
        print(f"Selected {formatter.greenbold(str(choice))}")
        return choice

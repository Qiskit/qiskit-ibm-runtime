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
The `save-account` command-line interface. These classes and functions are not public.
"""

import argparse
import sys
from getpass import getpass
from typing import List, Literal, Callable

from ibm_cloud_sdk_core.api_exception import ApiException

from .qiskit_runtime_service import QiskitRuntimeService
from .exceptions import IBMNotAuthorizedError
from .api.exceptions import RequestsApiError
from .accounts.management import AccountManager, _DEFAULT_ACCOUNT_CONFIG_JSON_FILE
from .accounts.exceptions import AccountAlreadyExistsError

Channel = Literal["ibm_quantum", "ibm_cloud"]


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
        description="Scripts for the Qiskit IBM Runtime Python package",
    )
    subparsers = parser.add_subparsers(
        title="Scripts",
        description="This package supports the following scripts:",
        dest="script",
        required=True,
    )
    subparsers.add_parser(
        "save-account",
        description=(
            "An interactive command-line interface to save your Qiskit IBM "
            "Runtime account locally. This script is interactive-only and takes "
            "no arguments."
        ),
        help="Interactive command-line interface to save your account locally.",
    )
    args = parser.parse_args()
    if args.script == "save-account":
        try:
            SaveAccountCLI.main()
        except KeyboardInterrupt:
            sys.exit()


class SaveAccountCLI:
    """
    This class contains the save-account command and helper functions.
    """

    @classmethod
    def main(cls) -> None:
        """
        A CLI that guides users through getting their account information and
        saving it to disk.
        """
        cls.print_box(["Qiskit IBM Runtime save account"])
        channel = cls.get_channel()
        token = cls.get_token(channel)
        print("Verifying, this might take few seconds...")
        try:
            service = QiskitRuntimeService(channel=channel, token=token)
        except (ApiException, IBMNotAuthorizedError, RequestsApiError) as err:
            print(
                Format.red(Format.bold("\nError while authorizing with your token\n"))
                + Format.red(err.message)
            )
            sys.exit(1)
        instance = cls.get_instance(service)
        cls.save_to_disk(
            {
                "channel": channel,
                "token": token,
                "instance": instance,
            }
        )

    @classmethod
    def print_box(cls, lines: List[str]) -> None:
        """Print lines in a box using Unicode box-drawing characters"""
        width = max(len(line) for line in lines)
        box_lines = [
            "╭─" + "─" * width + "─╮",
            *(f"│ {Format.bold(line.ljust(width))} │" for line in lines),
            "╰─" + "─" * width + "─╯",
        ]
        print("\n".join(box_lines))

    @classmethod
    def get_channel(cls) -> Channel:
        """Ask user which channel to use"""
        print(Format.bold("Select a channel"))
        return select_from_list(["ibm_quantum", "ibm_cloud"])

    @classmethod
    def get_token(cls, channel: Channel) -> str:
        """Ask user for their token"""
        token_url = {
            "ibm_quantum": "https://quantum.ibm.com",
            "ibm_cloud": "https://cloud.ibm.com/iam/apikeys",
        }[channel]
        print(
            Format.bold("\nPaste your API token")
            + f"\nYou can get this from {Format.cyan(token_url)}."
            + "\nFor security, you might not see any feedback when typing."
        )
        while True:
            token = getpass("Token: ").strip()
            if token != "":
                return token

    @classmethod
    def get_instance(cls, service: QiskitRuntimeService) -> str:
        """
        Ask user which instance to use, or select automatically if only one
        is available.
        """
        instances = service.instances()
        if len(instances) == 1:
            instance = instances[0]
            print(f"Using instance {Format.greenbold(instance)}")
            return instance
        print(Format.bold("\nSelect a default instance"))
        return select_from_list(instances)

    @classmethod
    def save_to_disk(cls, account):
        """
        Save account details to disk, confirming if they'd like to overwrite if
        one exists already. Display a warning that token is stored in plain
        text.
        """
        try:
            AccountManager.save(**account)
        except AccountAlreadyExistsError:
            response = user_input(
                message="\nDefault account already exists, would you like to overwrite it? (y/N):",
                is_valid=lambda response: response.strip().lower() in ["y", "yes", "n", "no", ""],
            )
            if response.lower() in ["y", "yes"]:
                AccountManager.save(**account, overwrite=True)
            else:
                print("Account not saved.")
                return

        print(f"Account saved to {Format.greenbold(_DEFAULT_ACCOUNT_CONFIG_JSON_FILE)}")
        cls.print_box(
            [
                "⚠️ Warning: your token is saved to disk in plain text.",
                "If on a shared computer, make sure to revoke your token",
                "by regenerating it in your account settings when finished.",
            ]
        )


def user_input(message: str, is_valid: Callable[[str], bool]):
    """
    Repeatedly ask user for input until they give us something that satisifies
    `is_valid`.
    """
    while True:
        response = input(message + " ").strip()
        if response == "quit":
            sys.exit()
        if is_valid(response):
            return response
        print("Did not understand input, trying again... (type 'quit' to quit)")


def select_from_list(options: List[str]) -> str:
    """
    Prompt user to select from a list of options by entering a number.
    """
    print()
    for index, option in enumerate(options):
        print(f"  ({index+1}) {option}")
    print()
    response = user_input(
        message=f"Enter a number 1-{len(options)} and press enter:",
        is_valid=lambda response: response.isdigit()
        and int(response) in range(1, len(options) + 1),
    )
    choice = options[int(response) - 1]
    print(f"Selected {Format.greenbold(choice)}")
    return choice


class Format:
    """Format using terminal escape codes"""

    # pylint: disable=missing-function-docstring

    @classmethod
    def bold(cls, s: str) -> str:
        return f"\033[1m{s}\033[0m"

    @classmethod
    def green(cls, s: str) -> str:
        return f"\033[32m{s}\033[0m"

    @classmethod
    def red(cls, s: str) -> str:
        return f"\033[31m{s}\033[0m"

    @classmethod
    def cyan(cls, s: str) -> str:
        return f"\033[36m{s}\033[0m"

    @classmethod
    def greenbold(cls, s: str) -> str:
        return cls.green(cls.bold(s))

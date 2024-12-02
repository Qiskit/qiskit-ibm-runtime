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
# that they have been altered from the originals
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

SCRIPT_NAME = "Qiskit IBM Runtime save account"


def save_account() -> None:
    """
    A CLI that guides users through getting their account information and saving it to disk.
    """
    # Use argparse to create the --help feature
    parser = argparse.ArgumentParser(
        prog=SCRIPT_NAME,
        description=dedent(
            """
            An interactive command-line interface to save your Qiskit IBM 
            Runtime account locally. This script is interactive-only and takes 
            no arguments
            """
        ),
    )
    parser.parse_args()

    try:
        CLI.main()
    except KeyboardInterrupt:
        sys.exit()


class CLI:
    @classmethod
    def main(self) -> None:
        self.print_box([SCRIPT_NAME])
        channel = self.get_channel()
        token = self.get_token(channel)
        print("Verifying, this might take few seconds...")
        try:
            service = QiskitRuntimeService(channel=channel, token=token)
        except (ApiException, IBMNotAuthorizedError, RequestsApiError) as err:
            print(
                Format.red(Format.bold("\nError while authorizing with your token\n"))
                + Format.red(err.message)
            )
            sys.exit(1)
        instance = self.get_instance(service)
        self.save_account({
            "channel": channel,
            "token": token,
            "instance": instance,
        })

    @classmethod
    def print_box(self, lines: List[str]) -> None:
        width = max(len(line) for line in lines)
        box_lines = [
            "╭─" + "─"*width + "─╮",
            *(f"│ {Format.bold(line.ljust(width))} │" for line in lines),
            "╰─" + "─"*width + "─╯",
        ]
        print("\n".join(box_lines))

    @classmethod
    def get_channel(self) -> Channel:
        print(Format.bold("Select a channel"))
        return select_from_list(["ibm_quantum", "ibm_cloud"])

    @classmethod
    def get_token(self, channel: Channel) -> str:
        token_url = {
            "ibm_quantum": "https://quantum.ibm.com",
            "ibm_cloud": "https://cloud.ibm.com/iam/apikeys",
        }[channel]
        print(
            Format.bold(f"\nPaste your API token")
            + f"\nYou can get this from {Format.cyan(token_url)}."
            + "\nFor security, you might not see any feedback when typing."
        )
        while True:
            token = getpass("Token: ").strip()
            if token != "":
                return token
    
    @classmethod
    def get_instance(self, service: QiskitRuntimeService) -> str:
        instances = service.instances()
        if len(instances) == 1:
            instance = instances[0]
            print(f"Using instance {Format.greenbold(instance)}")
            return instance
        print(Format.bold("\nSelect a default instance"))
        return select_from_list(instances)
    
    @classmethod
    def save_account(self, account):
        try:
            AccountManager.save(**account)
        except AccountAlreadyExistsError:
            response = user_input(
                message="\nDefault account already exists, would you like to overwrite it? (y/N):",
                is_valid=lambda response: response.strip().lower() in ["y", "yes", "n", "no", ""]
            )
            if response in ["y", "yes"]:
                AccountManager.save(**account, overwrite=True)
            else:
                print("Account not saved.")
                return
        
        print(f"Account saved to {Format.greenbold(_DEFAULT_ACCOUNT_CONFIG_JSON_FILE)}")
        self.print_box([
            "⚠️ Warning: your token is saved to disk in plain text.",
            "If on a shared computer, make sure to revoke your token",
            "by regenerating it in your account settings when finished.",
        ])

def user_input(message: str, is_valid: Callable[[str], bool]):
    while True:
        response = input(message + " ").strip()
        if response == "quit":
            sys.exit()
        if is_valid(response):
            return response
        print("Did not understand input, trying again... (type 'quit' to quit)")

def select_from_list(options: List[str]) -> str:
    print()
    for index, option in enumerate(options):
        print(f"  ({index+1}) {option}")
    print()
    response = user_input(
        message=f"Enter a number 1-{len(options)} and press enter:",
        is_valid=lambda response: response.isdigit() and int(response) in range(1, len(options)+1)
    )
    choice = options[int(response)-1]
    print(f"Selected {Format.greenbold(choice)}")
    return choice

class Format:
    """Format using terminal escape codes"""
    @classmethod
    def bold(self, s: str) -> str:
        return f"\033[1m{s}\033[0m"
    @classmethod
    def green(self, s: str) -> str:
        return f"\033[32m{s}\033[0m"
    @classmethod
    def red(self, s: str) -> str:
        return f"\033[31m{s}\033[0m"
    @classmethod
    def cyan(self, s: str) -> str:
        return f"\033[36m{s}\033[0m"
    @classmethod
    def greenbold(self, s: str) -> str:
        return self.green(self.bold(s))
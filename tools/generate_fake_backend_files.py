#!/usr/bin/env python3
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
"""Fetch backend snapshots and generate fake backend package files.

This script connects to IBM Quantum Runtime, fetches the latest configuration and
properties for one or more backends, and writes the following files under:

``qiskit_ibm_runtime/fake_provider/backends/<backend_city>/``

- ``conf_<backend_city>.json``
- ``props_<backend_city>.json``
- ``__init__.py``
- ``fake_<backend_city>.py``

Usage examples:

    # Use the default saved account.
    python tools/generate_fake_backend_files.py -b ibm_boston

    # Fetch multiple backends in one run.
    python tools/generate_fake_backend_files.py -b ibm_berlin -b ibm_strasbourg

    # Use a named account and print progress logs.
    python tools/generate_fake_backend_files.py -b ibm_miami -a us-fleet -v
"""

import argparse
import json
import re
import sys
from pathlib import Path

from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime.accounts.exceptions import AccountsError
from qiskit_ibm_runtime.utils.backend_encoder import BackendEncoder

tools_dir = Path(__file__).parent
backends_dir = tools_dir.parent / "qiskit_ibm_runtime" / "fake_provider" / "backends"

parser = argparse.ArgumentParser(description="Retrieve latest config and properties from a backend")
parser.add_argument(
    "-b",
    "--backend",
    required=True,
    action="append",
    help="backend name (required), e.g. 'ibm_boston'. Can be used more than once.",
)
parser.add_argument(
    "-a",
    "--account",
    required=False,
    action="store",
    help="account name (optional), e.g. 'us-fleet'. If not provided, the default account \
                    will be used.",
)
parser.add_argument(
    "-v",
    "--verbose",
    required=False,
    action="store_true",
    help="print debug messages.",
)


COPYRIGHT_HEADER = """# This code is part of Qiskit.
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
"""


def _to_pascal_case(value: str) -> str:
    parts = re.split(r"[_\W]+", value)
    return "".join(part.capitalize() for part in parts if part)


def _build_init_file(city: str, class_name: str, n_qubits: int | str) -> str:
    city_title = city.capitalize()
    return (
        f"{COPYRIGHT_HEADER}\n"
        f'"""Fake {city_title} backend ({n_qubits} qubit)."""\n\n'
        f"from .fake_{city} import {class_name}\n"
    )


def _build_fake_backend_file(city: str, class_name: str, n_qubits: int | str) -> str:
    city_title = city.capitalize()
    return (
        f"{COPYRIGHT_HEADER}\n"
        f'"""Fake {city_title} device ({n_qubits} qubit)."""\n\n'
        "import os\n\n"
        "from qiskit_ibm_runtime.fake_provider import fake_backend\n\n\n"
        f"class {class_name}(fake_backend.FakeBackendV2):\n"
        f'    """A fake {n_qubits} qubit backend."""\n\n'
        "    dirname = os.path.dirname(__file__)\n"
        f'    conf_filename = "conf_{city}.json"\n'
        f'    props_filename = "props_{city}.json"\n'
        f'    backend_name = "fake_{city}"\n'
    )


def main(backend_list: list[str], account: str, verbose: bool) -> None:
    """Retrieves latest configuration and properties from a backend.

    The configuration and properties and then saved as valid JSON files in the backends directory.
    """
    if verbose:
        print("Initializing IBM service")

    try:
        service = QiskitRuntimeService(name=account) if account else QiskitRuntimeService()
    except AccountsError as e:
        print("Service initialization failed")
        print(e)
        sys.exit(1)

    for backend_name in backend_list:
        if verbose:
            print(f"Fetching backend '{backend_name}'")

        try:
            backend = service.backend(backend_name)
            backend.refresh()
        except Exception as e:
            print(f"Fetching '{backend_name}' has failed.")
            print(e)
            sys.exit(1)

        backend_city = backend_name.split("_")[-1]

        if verbose:
            print("Fetching properties")
        properties = backend.properties().to_dict()

        if verbose:
            print("Fetching configuration")
        configuration = backend.configuration().to_dict()
        configuration["backend_name"] = backend_name

        out_dir = backends_dir / backend_city
        Path.mkdir(out_dir, exist_ok=True)

        if not configuration:
            print("Script failed to fetch config")
            sys.exit(1)

        config_path = out_dir / f"conf_{backend_city}.json"

        if verbose:
            print("Saving configuration")

        with open(config_path, "w", encoding="utf-8") as fd:
            fd.write(json.dumps(configuration, cls=BackendEncoder))

        if not properties:
            print("Script failed to fetch properties")
            sys.exit(1)

        props_path = out_dir / f"props_{backend_city}.json"

        if verbose:
            print("Saving properties")

        with open(props_path, "w", encoding="utf-8") as fd:
            fd.write(json.dumps(properties, cls=BackendEncoder))

        n_qubits = configuration.get("n_qubits", "unknown")
        class_name = f"Fake{_to_pascal_case(backend_city)}"

        init_path = out_dir / "__init__.py"
        fake_backend_path = out_dir / f"fake_{backend_city}.py"

        if verbose:
            print("Saving backend Python files")

        with open(init_path, "w", encoding="utf-8") as fd:
            fd.write(_build_init_file(backend_city, class_name, n_qubits))

        with open(fake_backend_path, "w", encoding="utf-8") as fd:
            fd.write(_build_fake_backend_file(backend_city, class_name, n_qubits))

        if verbose:
            print(f"Backend '{backend_name}' done")


if __name__ == "__main__":
    args = parser.parse_args()
    main(args.backend, args.account, args.verbose)

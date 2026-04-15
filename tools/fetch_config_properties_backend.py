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
"""Retrieves latest configuration and properties from a backend."""

import argparse
import json
import sys
from pathlib import Path

from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime.accounts.exceptions import AccountNotFoundError
from qiskit_ibm_runtime.utils.backend_encoder import BackendEncoder

tools_dir = Path(__file__).parent
backends_dir = tools_dir.parent / "qiskit_ibm_runtime" / "fake_provider" / "backends"

parser = argparse.ArgumentParser(description="Retrieve latest config and properties from a backend")
parser.add_argument(
    "-b",
    "--backend",
    required=True,
    help="backend name (required), e.g. 'ibm_boston'",
)


def main(backend_name: str) -> None:
    """Retrieves latest configuration and properties from a backend.

    The configuration and properties and then saved as valid JSON files in the backends directory.
    """
    try:
        service = QiskitRuntimeService()
    except AccountNotFoundError:
        print("This script requires a saved IBM account")
        sys.exit(1)

    backend_city = backend_name.split("_")[-1]
    use_fractional_gates = False

    try:
        backend = service.backend(backend_name, use_fractional_gates=use_fractional_gates)
        properties = backend.properties(refresh=True).to_dict()
        configuration = backend.configuration().to_dict()
        configuration["backend_name"] = backend_name
    except Exception as e:
        print(f"Fetching {backend_name} has failed: {e}")
        sys.exit(1)

    out_dir = backends_dir / backend_city
    Path.mkdir(out_dir, exist_ok=True)

    if not configuration:
        print("Script failed to fetch config")
        sys.exit(1)

    config_path = out_dir / f"conf_{backend_city}.json"
    with open(config_path, "w", encoding="utf-8") as fd:
        fd.write(json.dumps(configuration, cls=BackendEncoder))

    if not properties:
        print("Script failed to fetch properties")
        sys.exit(1)

    props_path = out_dir / f"props_{backend_city}.json"
    with open(props_path, "w", encoding="utf-8") as fd:
        fd.write(json.dumps(properties, cls=BackendEncoder))


if __name__ == "__main__":
    args = parser.parse_args()
    main(args.backend)

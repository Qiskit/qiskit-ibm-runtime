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

This script connects to IBM Quantum Compute (formerly Qiskit Runtime), fetches the latest
configuration and properties for one or more backends, and writes the following files under:

``qiskit_ibm_runtime/fake_provider/backends/<backend_city>/``

- ``conf_<backend_city>.json``
- ``props_<backend_city>.json``

If the backend is new, i.e. its directory does not exist yet, the script also writes the following
files in the same directory:

- ``__init__.py``
- ``fake_<backend_city>.py``

registers the backend (in alphabetical position) in:

- ``qiskit_ibm_runtime/fake_provider/backends/__init__.py``
- ``qiskit_ibm_runtime/fake_provider/__init__.py`` (documentation list)
- ``qiskit_ibm_runtime/fake_provider/fake_provider.py``
- ``test/unit/fake_provider/test_fake_backends.py`` (``physical_qubits`` list)

and adds a ``feat`` release note under ``release-notes/unreleased/``.

If the backend directory already exists, a warning is printed and only the two JSON files are
overwritten, and an ``other`` release note about the refreshed data is added. The Python files and
the registration are left untouched.

Usage examples:

    # Use the default saved account.
    python tools/generate_fake_backend_files.py -b ibm_boston

    # Fetch multiple backends in one run.
    python tools/generate_fake_backend_files.py -b ibm_berlin -b ibm_strasbourg

    # Use a named account and print progress logs.
    python tools/generate_fake_backend_files.py -b ibm_miami -a us-fleet -v

    # Name the release note after the pull request number.
    python tools/generate_fake_backend_files.py -b ibm_chicago -p 3561
"""

import argparse
import json
import re
import sys
from pathlib import Path

from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime.accounts.exceptions import AccountsError
from qiskit_ibm_runtime.fake_provider.backend_encoder import BackendEncoder

tools_dir = Path(__file__).parent
repo_dir = tools_dir.parent
fake_provider_dir = repo_dir / "qiskit_ibm_runtime" / "fake_provider"
backends_dir = fake_provider_dir / "backends"
release_notes_dir = repo_dir / "release-notes" / "unreleased"
test_fake_backends_path = repo_dir / "test" / "unit" / "fake_provider" / "test_fake_backends.py"

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
    "-p",
    "--pr",
    required=False,
    action="store",
    help="pull request number (optional), used to name the release notes. If not \
                    provided, the release note file has to be renamed manually.",
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


def _build_fake_backend_file(
    city: str, class_name: str, n_qubits: int | str, physical_qubits: int | None
) -> str:
    city_title = city.capitalize()
    content = (
        f"{COPYRIGHT_HEADER}\n"
        f'"""Fake {city_title} device ({n_qubits} qubit)."""\n\n'
        "import os\n\n"
        "from ...fake_backend import FakeBackendV2\n\n\n"
        f"class {class_name}(FakeBackendV2):\n"
        f'    """A fake {n_qubits} qubit backend."""\n\n'
        "    dirname = os.path.dirname(__file__)\n"
        f'    conf_filename = "conf_{city}.json"\n'
        f'    props_filename = "props_{city}.json"\n'
        f'    backend_name = "fake_{city}"\n'
    )
    if physical_qubits is not None:
        content += f"    _physical_qubits = {physical_qubits}\n"
    return content


def _insert_sorted(
    path: Path,
    line_pattern: str,
    new_line: str,
    block_start: str | None = None,
    block_end: str | None = None,
) -> None:
    """Insert ``new_line`` into ``path``, next to the lines matching ``line_pattern``.

    The new line is placed before the first matching line whose name (the first capture group of
    ``line_pattern``) is alphabetically greater, or after the last matching line otherwise. Nothing
    is done if the line already exists.

    Args:
        path: File to modify.
        line_pattern: Regex matching the sorted lines. Its first group is the sorting key.
        new_line: The line to insert (without a trailing newline).
        block_start: If given, only lines after the first line containing this text are considered.
        block_end: If given, lines from the first line (after the block start) containing this
            text are not considered.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    if new_line in lines:
        return

    regex = re.compile(line_pattern)
    new_key = regex.match(new_line).group(1).lower()  # type: ignore[union-attr]

    in_block = block_start is None
    last_match = None
    insert_at = None
    for idx, line in enumerate(lines):
        if not in_block:
            in_block = block_start in line  # type: ignore[operator]
            continue
        if block_end is not None and block_end in line:
            break
        match = regex.match(line)
        if not match:
            continue
        last_match = idx
        if match.group(1).lower() > new_key:
            insert_at = idx
            break

    if insert_at is None:
        if last_match is None:
            raise RuntimeError(f"Could not find where to register '{new_line}' in {path}")
        insert_at = last_match + 1

    lines.insert(insert_at, new_line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _register_backend(city: str, class_name: str, physical_qubits: int | None) -> None:
    """Register a fake backend in the package, the documentation and the tests."""
    _insert_sorted(
        backends_dir / "__init__.py",
        r"^from \.(\w+) import \w+$",
        f"from .{city} import {class_name}",
    )
    _insert_sorted(
        fake_provider_dir / "__init__.py",
        r"^    (Fake\w+)$",
        f"    {class_name}",
        block_start="Fake V2 Backends",
        block_end='"""',
    )
    _insert_sorted(
        fake_provider_dir / "fake_provider.py",
        r"^            (Fake\w+)\(\),$",
        f"            {class_name}(),",
    )
    if physical_qubits is not None:
        _insert_sorted(
            test_fake_backends_path,
            r'^            "fake_(\w+)",$',
            f'            "fake_{city}",',
            block_start="backends_with_physical_qubits = [",
            block_end="]",
        )


def _write_release_note(class_names: list[str], pr: str | None, refreshed: bool) -> None:
    """Write a release note for added or refreshed fake backends.

    Args:
        class_names: Names of the fake backend classes.
        pr: Pull request number, used to name the release note file.
        refreshed: Whether the backends already existed and their data was refreshed (``other``
            note), as opposed to being newly added (``feat`` note).
    """
    names = [f"``{class_name}``" for class_name in class_names]
    if refreshed:
        kind = "other"
        if len(names) == 1:
            text = (
                f"The data of the fake backend {names[0]} has been updated to reflect the latest "
                "configuration and properties of the corresponding real backend.\n"
            )
        else:
            text = (
                f"The data of the fake backends {', '.join(names[:-1])} and {names[-1]} has been "
                "updated to reflect the latest configuration and properties of the corresponding "
                "real backends.\n"
            )
    else:
        kind = "feat"
        if len(names) == 1:
            text = f"A new fake backend, {names[0]}, has been added.\n"
        else:
            text = f"New fake backends, {', '.join(names[:-1])} and {names[-1]}, have been added.\n"

    fragment = f"{pr}.{kind}.rst" if pr else f"+{class_names[0].lower()}.{kind}.rst"
    release_notes_dir.mkdir(parents=True, exist_ok=True)
    (release_notes_dir / fragment).write_text(text, encoding="utf-8")

    print(f"Release note written to {release_notes_dir / fragment}")
    if not pr:
        print(
            "ACTION REQUIRED: no pull request number was given (--pr). Once the pull request is "
            f"created, rename the release note file to '<pr number>.{kind}.rst'."
        )


def main(backend_list: list[str], account: str, pr: str | None, verbose: bool) -> None:
    """Retrieves latest configuration and properties from a backend.

    The configuration and properties and then saved as valid JSON files in the backends directory.
    For new backends, the Python files are also written, the backend is registered in the package,
    and a release note is added. For existing backends, only a release note about the refreshed
    data is added.
    """
    new_backends: list[str] = []
    refreshed_backends: list[str] = []

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
        is_new = not out_dir.exists()
        if not is_new:
            print(
                f"WARNING: a fake backend for '{backend_name}' already exists in {out_dir}. "
                "Only its JSON files will be overwritten."
            )
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

        class_name = f"Fake{_to_pascal_case(backend_city)}"

        if not is_new:
            refreshed_backends.append(class_name)
            if verbose:
                print(f"Backend '{backend_name}' done")
            continue

        n_qubits = configuration.get("n_qubits", "unknown")
        physical_qubits = getattr(backend, "physical_qubits", None)
        if physical_qubits is None:
            print(
                f"WARNING: '{backend_name}' did not report physical_qubits. Skipping "
                "'_physical_qubits' in the fake backend class and the physical_qubits list in "
                "test_fake_backends.py. Add them manually if needed."
            )

        init_path = out_dir / "__init__.py"
        fake_backend_path = out_dir / f"fake_{backend_city}.py"

        if verbose:
            print("Saving backend Python files")

        with open(init_path, "w", encoding="utf-8") as fd:
            fd.write(_build_init_file(backend_city, class_name, n_qubits))

        with open(fake_backend_path, "w", encoding="utf-8") as fd:
            fd.write(_build_fake_backend_file(backend_city, class_name, n_qubits, physical_qubits))

        if verbose:
            print("Registering backend")
        _register_backend(backend_city, class_name, physical_qubits)

        new_backends.append(class_name)

        if verbose:
            print(f"Backend '{backend_name}' done")

    for class_names, refreshed in ((new_backends, False), (refreshed_backends, True)):
        if class_names:
            if verbose:
                print("Writing release note")
            _write_release_note(class_names, pr, refreshed)


if __name__ == "__main__":
    args = parser.parse_args()
    main(args.backend, args.account, args.pr, args.verbose)

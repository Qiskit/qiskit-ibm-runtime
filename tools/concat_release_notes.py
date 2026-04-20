# This code is part of Qiskit.
#
# (C) Copyright IBM 2024-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Script for concatenating release notes."""

from packaging import version
from pathlib import Path


def get_root_path() -> Path:
    """Return the root path of the repository."""
    return Path(__file__).resolve().parent.parent


def get_version_from_path(path: Path) -> str:
    """Return a version of the packaged, based on the file path."""
    # For unreleased.rst, use a high version number we'll never reach so that
    # unreleased always shows up as the newest entry.
    return "99.0.9" if path.stem == "unreleased" else path.stem


def sort_release_notes_paths(release_notes_paths: Path) -> list[Path]:
    """Sort the release notes by version."""
    return sorted(
        (fp for fp in release_notes_paths.iterdir() if fp.suffix == ".rst"),
        key=lambda x: version.parse(get_version_from_path(x)),
        reverse=True,
    )


def generate_header(output_file: Path) -> None:
    """Write the release note headers to a file."""
    output_file.write_text(
        "=======================================\n\
Qiskit Runtime IBM Client release notes\n\
=======================================\n\
\n\
.. towncrier release notes start\n",
        "utf-8",
    )


def concat_release_notes(output_file: Path, release_notes_paths: list[Path]) -> None:
    """Concatenate the release notes, producing an output file."""
    with output_file.open("a", encoding="utf-8") as file:
        for release_note in release_notes_paths:
            file.write(f"\n{release_note.read_text('utf-8')}")


def main() -> None:
    """Main entry point."""
    output_file = get_root_path() / "docs/release_notes.rst"
    release_notes_paths = sort_release_notes_paths(get_root_path() / "release-notes")
    generate_header(output_file)
    concat_release_notes(output_file, release_notes_paths)


if __name__ == "__main__":
    main()

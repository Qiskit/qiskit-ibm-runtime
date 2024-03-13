from packaging import version
from pathlib import Path
import os


def get_root_path():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_version_from_path(path):
    return str(path).split("/").pop().replace(".rst", "")


def sort_release_notes_paths(release_notes_paths):
    return sorted(
        release_notes_paths.iterdir(),
        key=lambda x: version.parse(get_version_from_path(x)),
        reverse=True,
    )


def generate_header(output_file):
    file = open(output_file, "w")
    file.write(
        "=======================================\n\
Qiskit Runtime IBM Client release notes\n\
=======================================\n\
\n\
.. towncrier release notes start\n"
    )
    file.close()


def concat_release_notes(output_file, release_notes_paths):
    file = open(output_file, "a")
    for release_note in release_notes_paths:
        file.write(f"\n{release_note.read_text()}")
    file.close()


def main():
    output_file = Path(f"{get_root_path()}/CHANGES.rst")
    release_notes_paths = sort_release_notes_paths(
        Path(f"{get_root_path()}/releasenotes/notes")
    )
    generate_header(output_file)
    concat_release_notes(output_file, release_notes_paths)


if __name__ == "__main__":
    main()

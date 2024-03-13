from packaging import version
from pathlib import Path, PurePosixPath


def get_root_path() -> Path:
    return PurePosixPath(Path(__file__).absolute()).parent.parent


def get_version_from_path(path: Path) -> str:
    return str(path).split("/").pop().replace(".rst", "")


def sort_release_notes_paths(release_notes_paths: list[Path]) -> list[Path]:
    return sorted(
        release_notes_paths.iterdir(),
        key=lambda x: version.parse(get_version_from_path(x)),
        reverse=True,
    )


def generate_header(output_file: Path) -> None:
    output_file.write_text(
        "=======================================\n\
Qiskit Runtime IBM Client release notes\n\
=======================================\n\
\n\
.. towncrier release notes start\n"
    )


def concat_release_notes(output_file: Path, release_notes_paths: list[Path]) -> None:
    with output_file.open("a") as file:
        for release_note in release_notes_paths:
            file.write(f"\n{release_note.read_text()}")


def main():
    output_file = Path(f"{get_root_path()}/docs/release_notes.rst")
    release_notes_paths = sort_release_notes_paths(
        Path(f"{get_root_path()}/releasenotes/notes")
    )
    generate_header(output_file)
    concat_release_notes(output_file, release_notes_paths)


if __name__ == "__main__":
    main()

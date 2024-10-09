from packaging import version
from pathlib import Path


def get_root_path() -> Path:
    return Path(__file__).resolve().parent.parent


def get_version_from_path(path: Path) -> str:
    # For unreleased.rst, use a high version number we'll never reach so that
    # unreleased always shows up as the newest entry.
    return "99.0.9" if path.stem == "unreleased" else path.stem


def sort_release_notes_paths(release_notes_paths: Path) -> list[Path]:
    return sorted(
        (fp for fp in release_notes_paths.iterdir() if fp.suffix == ".rst"),
        key=lambda x: version.parse(get_version_from_path(x)),
        reverse=True,
    )


def generate_header(output_file: Path) -> None:
    output_file.write_text(
        "=======================================\n\
Qiskit Runtime IBM Client release notes\n\
=======================================\n\
\n\
.. towncrier release notes start\n",
        "utf-8",
    )


def concat_release_notes(output_file: Path, release_notes_paths: list[Path]) -> None:
    with output_file.open("a", encoding="utf-8") as file:
        for release_note in release_notes_paths:
            file.write(f"\n{release_note.read_text('utf-8')}")


def main() -> None:
    output_file = get_root_path() / "docs/release_notes.rst"
    release_notes_paths = sort_release_notes_paths(get_root_path() / "release-notes")
    generate_header(output_file)
    concat_release_notes(output_file, release_notes_paths)


if __name__ == "__main__":
    main()

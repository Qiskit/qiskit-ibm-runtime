#!/usr/bin/env python3
# This code is part of Qiskit.
#
# (C) Copyright IBM 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Utility script to verify that all images have alt text"""

from pathlib import Path
import multiprocessing
import sys
import glob

# Dictionary to allowlist files that the checker will verify
ALLOWLIST_MISSING_ALT_TEXT = [
    "qiskit_ibm_runtime/fake_provider/__init__.py",
    "qiskit_ibm_runtime/transpiler/passes/scheduling/dynamical_decoupling.py",
    "qiskit_ibm_runtime/transpiler/passes/scheduling/__init__.py",
]


def is_image(line: str) -> bool:
    return line.strip().startswith((".. image:", ".. plot:"))


def validate_image(file_path: str) -> tuple[str, list[str]]:
    """Validate all the images of a single file"""

    if file_path in ALLOWLIST_MISSING_ALT_TEXT:
        return [file_path, []]

    invalid_images: list[str] = []

    lines = Path(file_path).read_text().splitlines()

    for line_index, line in enumerate(lines):
        if not is_image(line):
            continue

        options: list[str] = []
        options_line_index = line_index

        while options_line_index + 1 < len(lines):
            options_line_index += 1
            option_line = lines[options_line_index].strip()

            if not option_line.startswith(":"):
                break

            options.append(option_line)

        alt_exists = any(option.startswith(":alt:") for option in options)
        nofigs_exists = any(option.startswith(":nofigs:") for option in options)

        # Only `.. plot::`` directives without the `:nofigs:` option are required to have alt text.
        # Meanwhile, all `.. image::` directives need alt text and they don't have a `:nofigs:` option.
        if not alt_exists and not nofigs_exists:
            invalid_images.append(f"- Error in line {line_index + 1}: {line.strip()}")

    return (file_path, invalid_images)


def main() -> None:
    files = glob.glob("qiskit_ibm_runtime/**/*.py", recursive=True)

    with multiprocessing.Pool() as pool:
        results = pool.map(validate_image, files)

    failed_files = [x for x in results if len(x[1])]

    if not len(failed_files):
        print("✅ All images have alt text")
        sys.exit(0)

    print("💔 Some images are missing the alt text", file=sys.stderr)

    for filename, image_errors in failed_files:
        print(f"\nErrors found in {filename}:", file=sys.stderr)

        for image_error in image_errors:
            print(image_error, file=sys.stderr)

    print(
        "\nAlt text is crucial for making documentation accessible to all users. It should serve the same purpose as the images on the page, conveying the same meaning rather than describing visual characteristics. When an image contains words that are important to understanding the content, the alt text should include those words as well.",
        file=sys.stderr,
    )

    sys.exit(1)


if __name__ == "__main__":
    main()

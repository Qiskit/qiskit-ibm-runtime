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

# Dictionary to allowlist lines of code that the checker will not error
# Format: {"file_path": [list_of_line_numbers]}
ALLOWLIST_MISSING_ALT_TEXT = {
    "qiskit_ibm_runtime/fake_provider/__init__.py": [34, 55, 63],
    "qiskit_ibm_runtime/transpiler/passes/scheduling/dynamical_decoupling.py": [56, 88],
    "qiskit_ibm_runtime/transpiler/passes/scheduling/__init__.py": [
        51,
        102,
        137,
        152,
        176,
        207,
        226,
        240,
        256,
        274,
        294,
        313,
        328,
        342,
        363,
        382,
        406,
    ],
}


def is_image(line: str) -> bool:
    return line.strip().startswith((".. image:", ".. plot:"))


def in_allowlist(filename: str, line_num: str) -> bool:
    return line_num in ALLOWLIST_MISSING_ALT_TEXT.get(filename, [])


def validate_image(file_path: str) -> tuple[str, list[str]]:
    """Validate all the images of a single file"""
    invalid_images: list[str] = []

    lines = Path(file_path).read_text().splitlines()

    for line_number, line in enumerate(lines):
        if not is_image(line) or in_allowlist(file_path, line_number + 1):
            continue

        options: list[str] = []
        options_line_number = line_number

        while options_line_number + 1 < len(lines):
            options_line_number += 1
            option_line = lines[options_line_number].strip()

            if not option_line.startswith(":"):
                break

            options.append(option_line)

        alt_exists = any(option.startswith(":alt:") for option in options)
        nofig_exists = any(option.startswith(":nofig:") for option in options)

        # Only `.. plot::`` directives without the `:nofig:` option are required to have alt text.
        # Meanwhile, all `.. image::` directives need alt text and they don't have a `:nofig:` option.
        if not alt_exists and not nofig_exists:
            invalid_images.append(f"- Error in line {line_number + 1}: {line}\n")

    return (file_path, invalid_images)


def main() -> None:
    files = glob.glob("qiskit_ibm_runtime/**/*.py", recursive=True)

    with multiprocessing.Pool() as pool:
        results = pool.map(validate_image, files)

    failed_files = [x for x in results if len(x[1])]

    if not len(failed_files):
        print("✅ All images have alt text\n")
        sys.exit(0)

    print("💔 Some images are missing the alt text\n", file=sys.stderr)

    for filename, image_errors in failed_files:
        print(f"Errors found in {filename}:", file=sys.stderr)

        for image_error in image_errors:
            sys.stderr.write(image_error)

        print(
            "\nAlt text is crucial for making documentation accessible to all users. It should serve the same purpose as the images on the page, conveying the same meaning rather than describing visual characteristics. When an image contains words that are important to understanding the content, the alt text should include those words as well.",
            file=sys.stderr,
        )

    sys.exit(1)


if __name__ == "__main__":
    main()

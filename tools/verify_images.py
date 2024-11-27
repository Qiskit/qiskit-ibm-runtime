#!/usr/bin/env python3
# This code is part of Qiskit.
#
# (C) Copyright IBM 2020
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Utility script to verify that all images have alt text"""

from typing import NewType
import multiprocessing
import sys
import glob

# Dictionary to allowlist lines of code that the checker will not error
# # Format: {"file_path": [list_of_line_numbers]}
ALLOWLIST_MISSING_ALT_TEXT = {"qiskit_ibm_runtime/fake_provider/__init__.py": [34]}


def is_image(line) -> bool:
    return line.strip().startswith(".. image:")


def is_plot(line) -> bool:
    return line.strip().startswith(".. plot:")


def allowlist(filename, line_num) -> bool:
    return line_num in ALLOWLIST_MISSING_ALT_TEXT[filename]


Error = NewType("Error", tuple[int, str])


def validate_image(file_path) -> tuple[str, bool, list[Error]]:
    """Validate all the images of a single file"""
    invalid_images: list[Error] = []

    with open(file_path, encoding="utf8") as fd:
        lines = fd.readlines()

        for index, line in enumerate(lines):
            if (is_image(line) or is_plot(line)) and not allowlist(file_path, index + 1):
                options: list[str] = []
                option_idx = index

                while option_idx + 1 < len(lines):
                    option_idx += 1
                    option_line = lines[option_idx].strip()

                    if not option_line.startswith(":"):
                        break

                    options.append(option_line)

                alt_exists = any(option.startswith(":alt:") for option in options)
                nofig_exists = any(option.startswith(":nofig:") for option in options)

                # Only `.. plot::`` directives without the `:nofig:` option are required to have alt text.
                # All `.. image::` directives need alt text and they don't have a `:nofig:` option.
                if not alt_exists and not nofig_exists:
                    invalid_images.append(Error((index + 1, line)))

    return (file_path, len(invalid_images) == 0, invalid_images)


def main() -> None:
    files = glob.glob("qiskit_ibm_runtime/**/*.py", recursive=True)

    with multiprocessing.Pool() as pool:
        results = pool.map(validate_image, files)

    failed_files = list(filter(lambda x: x[1] is False, results))

    if len(failed_files):
        sys.stderr.write("💔 Some images are missing the alt text\n\n")

        for failed_file in failed_files:
            sys.stderr.write("Errors found in %s:\n" % failed_file[0])

            for image in failed_file[2]:
                sys.stderr.write("- Error in line %s: %s\n" % (image[0], image[1].strip()))

            sys.stderr.write("\n")

        sys.exit(1)

    sys.stdout.write("✅ All images have alt text\n")
    sys.exit(0)


if __name__ == "__main__":
    main()

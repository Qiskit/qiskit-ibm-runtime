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

"""Pytest configuration for tests."""

import os


def pytest_addoption(parser):
    """Add custom pytest options."""
    parser.addoption(
        "--both-samplers",
        action="store_true",
        help="Run sampler integration tests against both configured sampler implementations.",
    )


def pytest_configure(config):
    """Configure pytest-driven test behavior."""
    if config.getoption("both_samplers"):
        os.environ["QISKIT_IBM_TEST_BOTH_SAMPLER_IMPLEMENTATIONS"] = "1"
    else:
        os.environ.pop("QISKIT_IBM_TEST_BOTH_SAMPLER_IMPLEMENTATIONS", None)

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

"""Tests for SamplerV2 post-processors."""

from qiskit_ibm_runtime.executor_sampler.post_processors.registry import SAMPLER_POST_PROCESSORS


def test_available_post_processors():
    """Test the available post-processors."""
    assert "v0.1" in SAMPLER_POST_PROCESSORS

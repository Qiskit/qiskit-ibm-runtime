# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for Options class."""

from qiskit_ibm_runtime.options.primitive_options_model import (
    get_value_for_pub_and_param,
    Distribute,
)

from ..ibm_test_case import IBMTestCase


class TestDistribute(IBMTestCase):
    """Class for testing the distribution of option values."""

    def test_get_value_for_pub_and_param(self):
        pub_index = 1
        param_index = (2, 0)

        assert get_value_for_pub_and_param(pub_index, param_index, 6) == 6
        assert get_value_for_pub_and_param(pub_index, param_index, Distribute(5, 6, 7)) == 6
        assert get_value_for_pub_and_param(pub_index, param_index, [[4, 1], [5, 2], [7, 6]]) == 7
        assert (
            get_value_for_pub_and_param(
                pub_index, param_index, Distribute([[4, 1], [5, 2], [7, 6]], 1, [100, 110])
            )
            == 1
        )

        pub_index = 0
        assert get_value_for_pub_and_param(pub_index, param_index, 6) == 6
        assert get_value_for_pub_and_param(pub_index, param_index, Distribute(5, 6, 7)) == 5
        assert get_value_for_pub_and_param(pub_index, param_index, [[4, 1], [5, 2], [7, 6]]) == 7
        assert (
            get_value_for_pub_and_param(
                pub_index, param_index, Distribute([[4, 1], [5, 2], [7, 6]], 1, [100, 110])
            )
            == 7
        )

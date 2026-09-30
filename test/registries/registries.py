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

"""Registries that are shared among the test suite."""

from qiskit_ibm_runtime.fake_provider import FakeLimaV2

from .base import BaseRegistry
from .entities import Backend, Instance


class DefaultRegistry(BaseRegistry):
    """Registry with two instances, with one common backend and two unique backends.

    This registry contains:
    * instance ``a`` (free plan): with ``common_backend``, and ``unique_backend_a``
    * instance ``b`` (trial plan): with ``common_backend``, and ``unique_backend_b``
    """

    def __init__(self) -> None:
        super().__init__()

        self.add_instance(Instance("a"))
        self.add_instance(Instance("b", pricing_type="trial"))
        self.add_backend(Backend("common_backend"))
        self.add_backend(Backend("unique_backend_a"), "a")
        self.add_backend(Backend("unique_backend_b"), "b")


class OneInstanceNoBackendsRegistry(BaseRegistry):
    """Registry pre-loaded with a single instance ``a`` with no backends.

    This registry contains:
    * instance ``a`` (free plan): no backends.
    """

    def __init__(self) -> None:
        super().__init__()

        self.add_instance(Instance("a"))


class OneInstanceDryRunRegistry(BaseRegistry):
    """Registry pre-loaded with a single instance ``a`` with one backend that supports dry-run.

    This registry contains:
    * instance ``a`` (free plan): with ``ibm_foo``, and ``mock_foo`.
    """

    def __init__(self) -> None:
        super().__init__()

        self.add_instance(Instance("a"))
        self.add_backend(Backend.from_(FakeLimaV2, name="ibm_foo"), "a")
        self.add_backend(Backend.from_(FakeLimaV2, name="mock_foo"), "a")

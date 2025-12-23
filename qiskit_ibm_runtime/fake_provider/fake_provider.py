# This code is part of Qiskit.
#
# (C) Copyright IBM 2019, 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# pylint: disable=wildcard-import,unused-argument
# ruff: noqa: F405 undefined-local-with-import-star-usage

"""
Fake provider class that provides access to fake backends.
"""

from typing import Any
from qiskit.providers.exceptions import QiskitBackendNotFoundError

from .backends import *  # noqa: F403 undefined-local-with-import-star
from .fake_backend import FakeBackendV2


class FakeProviderForBackendV2:
    """Fake provider containing fake V2 backends.

    Only filtering backends by name is implemented. This class contains all fake V2 backends
    available in the :mod:`qiskit_ibm_runtime.fake_provider`.
    """

    def backend(self, name: str = None, **kwargs: Any) -> FakeBackendV2:
        """
        Filter backends in provider by name.
        """
        backend = self._backends[0]
        if name:
            filtered_backends = [backend for backend in self._backends if backend.name == name]
            if not filtered_backends:
                raise QiskitBackendNotFoundError()

            backend = filtered_backends[0]

        return backend

    def backends(self, name: str = None, **kwargs: Any) -> list[FakeBackendV2]:
        """Return all backends accessible via this account."""
        return self._backends

    def __init__(self) -> None:
        self._backends = [
            FakeAlgiers(),
            FakeAlmadenV2(),
            FakeArmonkV2(),
            FakeAthensV2(),
            FakeAuckland(),
            FakeBelemV2(),
            FakeBoeblingenV2(),
            FakeBogotaV2(),
            FakeBrisbane(),
            FakeBrooklynV2(),
            FakeBurlingtonV2(),
            FakeCairoV2(),
            FakeCambridgeV2(),
            FakeCasablancaV2(),
            FakeCusco(),
            FakeEssexV2(),
            FakeFez(),
            FakeFractionalBackend(),
            FakeGeneva(),
            FakeGuadalupeV2(),
            FakeHanoiV2(),
            FakeJakartaV2(),
            FakeJohannesburgV2(),
            FakeKawasaki(),
            FakeKolkataV2(),
            FakeKyiv(),
            FakeKyoto(),
            FakeLagosV2(),
            FakeLimaV2(),
            FakeLondonV2(),
            FakeManhattanV2(),
            FakeManilaV2(),
            FakeMelbourneV2(),
            FakeMarrakesh(),
            FakeMontrealV2(),
            FakeMumbaiV2(),
            FakeNairobiV2(),
            FakeNighthawk(),
            FakeOsaka(),
            FakeOslo(),
            FakeOurenseV2(),
            FakeParisV2(),
            FakePeekskill(),
            FakePerth(),
            FakePrague(),
            FakePoughkeepsieV2(),
            FakeQuebec(),
            FakeQuitoV2(),
            FakeRochesterV2(),
            FakeRomeV2(),
            FakeSantiagoV2(),
            FakeSherbrooke(),
            FakeSingaporeV2(),
            FakeSydneyV2(),
            FakeTorino(),
            FakeTorontoV2(),
            FakeValenciaV2(),
            FakeVigoV2(),
            FakeWashingtonV2(),
            FakeYorktownV2(),
        ]

        super().__init__()

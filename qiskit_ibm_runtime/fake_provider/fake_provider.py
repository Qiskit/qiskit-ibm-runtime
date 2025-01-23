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

"""
Fake provider class that provides access to fake backends.
"""

from typing import Any, List
from qiskit.providers.exceptions import QiskitBackendNotFoundError

from .backends import *
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

    def backends(self, name: str = None, **kwargs: Any) -> List[FakeBackendV2]:
        """Return all backends accessible via this account."""
        return self._backends

    def __init__(self) -> None:
        self._backends = [
            FakeAlgiers(),  # type: ignore
            FakeAlmadenV2(),  # type: ignore
            FakeArmonkV2(),  # type: ignore
            FakeAthensV2(),  # type: ignore
            FakeAuckland(),  # type: ignore
            FakeBelemV2(),  # type: ignore
            FakeBoeblingenV2(),  # type: ignore
            FakeBogotaV2(),  # type: ignore
            FakeBrisbane(),  # type: ignore
            FakeBrooklynV2(),  # type: ignore
            FakeBurlingtonV2(),  # type: ignore
            FakeCairoV2(),  # type: ignore
            FakeCambridgeV2(),  # type: ignore
            FakeCasablancaV2(),  # type: ignore
            FakeCusco(),  # type: ignore
            FakeEssexV2(),  # type: ignore
            FakeFez(),  # type: ignore
            FakeFractionalBackend(),  # type: ignore
            FakeGeneva(),  # type: ignore
            FakeGuadalupeV2(),  # type: ignore
            FakeHanoiV2(),  # type: ignore
            FakeJakartaV2(),  # type: ignore
            FakeJohannesburgV2(),  # type: ignore
            FakeKawasaki(),  # type: ignore
            FakeKolkataV2(),  # type: ignore
            FakeKyiv(),  # type: ignore
            FakeKyoto(),  # type: ignore
            FakeLagosV2(),  # type: ignore
            FakeLimaV2(),  # type: ignore
            FakeLondonV2(),  # type: ignore
            FakeManhattanV2(),  # type: ignore
            FakeManilaV2(),  # type: ignore
            FakeMelbourneV2(),  # type: ignore
            FakeMarrakesh(),  # type: ignore
            FakeMontrealV2(),  # type: ignore
            FakeMumbaiV2(),  # type: ignore
            FakeNairobiV2(),  # type: ignore
            FakeOsaka(),  # type: ignore
            FakeOslo(),  # type: ignore
            FakeOurenseV2(),  # type: ignore
            FakeParisV2(),  # type: ignore
            FakePeekskill(),  # type: ignore
            FakePerth(),  # type: ignore
            FakePrague(),  # type: ignore
            FakePoughkeepsieV2(),  # type: ignore
            FakeQuebec(),  # type: ignore
            FakeQuitoV2(),  # type: ignore
            FakeRochesterV2(),  # type: ignore
            FakeRomeV2(),  # type: ignore
            FakeSantiagoV2(),  # type: ignore
            FakeSherbrooke(),  # type: ignore
            FakeSingaporeV2(),  # type: ignore
            FakeSydneyV2(),  # type: ignore
            FakeTorino(),  # type: ignore
            FakeTorontoV2(),  # type: ignore
            FakeValenciaV2(),  # type: ignore
            FakeVigoV2(),  # type: ignore
            FakeWashingtonV2(),  # type: ignore
            FakeYorktownV2(),  # type: ignore
        ]

        super().__init__()

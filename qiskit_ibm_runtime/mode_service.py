from __future__ import annotations

import logging
from typing import TYPE_CHECKING, overload

from .ibm_backend import IBMBackend
from .utils.default_session import get_cm_session

if TYPE_CHECKING:
    from qiskit.providers.backend import BackendV2

    from .batch import Batch
    from .session import Session
    from .fake_provider.local_service import QiskitRuntimeLocalService
    from .qiskit_runtime_service import QiskitRuntimeService

logger = logging.getLogger(__name__)


@overload
def get_mode_service_backend(mode: None = None) -> tuple[None, QiskitRuntimeService, BackendV2]: ...


@overload
def get_mode_service_backend(
    mode: IBMBackend = ...,
) -> tuple[None, QiskitRuntimeService, BackendV2]: ...


@overload
def get_mode_service_backend(
    mode: Batch = ...,
) -> tuple[Batch, QiskitRuntimeService, BackendV2]: ...


@overload
def get_mode_service_backend(
    mode: Session = ...,
) -> tuple[Session, QiskitRuntimeService, BackendV2]: ...


@overload
def get_mode_service_backend(
    mode: BackendV2 = ...,
) -> tuple[None, QiskitRuntimeLocalService, BackendV2]: ...


def get_mode_service_backend(
    mode: BackendV2 | Session | Batch | None = None,
) -> tuple[
    Session | Batch | None,
    QiskitRuntimeService | QiskitRuntimeLocalService,
    BackendV2,
]:
    """A utility function that returns mode, service, and backend for a given execution mode.

    Args:
        mode: The execution mode used to make the primitive query. It can be

            * A :class:`Backend` if you are using job mode.
            * A :class:`Session` if you are using session execution mode.
            * A :class:`Batch` if you are using batch execution mode.
    """
    # Use runtime imports, to prevent `base_primitive.py` to depend on several core objects.

    from .fake_provider.local_service import QiskitRuntimeLocalService
    from .batch import Batch
    from .session import Session

    if isinstance(mode, (Session, Batch)):
        return mode, mode.service, mode._backend
    elif isinstance(mode, IBMBackend):
        if get_cm_session():
            logger.warning(
                "A backend was passed in as the mode but a session context manager "
                "is open so this job will run inside this session/batch "
                "instead of in job mode."
            )
            if get_cm_session()._backend != mode:
                raise ValueError(
                    "The backend passed in to the primitive is different from the session backend. "
                    "Please check which backend you intend to use or leave the mode parameter "
                    "empty to use the session backend."
                )
            return get_cm_session(), mode.service, mode
        return None, mode.service, mode
    elif isinstance(mode, BackendV2):
        return None, QiskitRuntimeLocalService(), mode
    elif mode is not None:
        raise ValueError("mode must be of type Backend, Session, Batch or None")
    elif get_cm_session():
        mode = get_cm_session()
        service = mode.service
        backend = mode._backend

        return mode, service, backend
    else:
        raise ValueError("A backend or session must be specified.")

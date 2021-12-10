# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Module for interfacing with an IBM Quantum Backend."""

import logging

from typing import List, Union, Optional, Any
from datetime import datetime as python_datetime

from qiskit.qobj.utils import MeasLevel, MeasReturnType
from qiskit.providers.backend import BackendV1 as Backend
from qiskit.providers.options import Options
from qiskit.providers.models import (
    BackendStatus,
    BackendProperties,
    PulseDefaults,
    GateConfig,
)
from qiskit.providers.models import QasmBackendConfiguration, PulseBackendConfiguration

# pylint: disable=unused-import, cyclic-import
from qiskit_ibm_runtime import ibm_runtime_service

from .api.clients import AccountClient, RuntimeClient
from .backendreservation import BackendReservation
from .credentials import Credentials
from .exceptions import IBMBackendApiProtocolError
from .utils.converters import utc_to_local_all, local_to_utc
from .utils.backend import decode_pulse_defaults, decode_backend_properties
from .utils.backend import convert_reservation_data

logger = logging.getLogger(__name__)


class IBMBackend(Backend):
    """Backend class interfacing with an IBM Quantum device.

    Note:

        * You should not instantiate the ``IBMBackend`` class directly. Instead, use
          the methods provided by an :class:`IBMRuntimeService` instance to retrieve and handle
          backends.

    Other methods return information about the backend. For example, the :meth:`status()` method
    returns a :class:`BackendStatus<qiskit.providers.models.BackendStatus>` instance.
    The instance contains the ``operational`` and ``pending_jobs`` attributes, which state whether
    the backend is operational and also the number of jobs in the server queue for the backend,
    respectively::

        status = backend.status()
        is_operational = status.operational
        jobs_in_queue = status.pending_jobs
    """

    id_warning_issued = False

    def __init__(
        self,
        configuration: Union[QasmBackendConfiguration, PulseBackendConfiguration],
        service: "ibm_runtime_service.IBMRuntimeService",
        credentials: Credentials,
        api_client: Union[AccountClient, RuntimeClient],
    ) -> None:
        """IBMBackend constructor.

        Args:
            configuration: Backend configuration.
            service: IBM Quantum account provider.
            credentials: IBM Quantum credentials.
            api_client: IBM Quantum client used to communicate with the server.
        """
        super().__init__(provider=service, configuration=configuration)

        self._api_client = api_client
        self._credentials = credentials
        self.hub = credentials.hub
        self.group = credentials.group
        self.project = credentials.project

        # Attributes used by caching functions.
        self._properties = None
        self._defaults = None

    @classmethod
    def _default_options(cls) -> Options:
        """Default runtime options."""
        return Options(
            shots=4000,
            memory=False,
            qubit_lo_freq=None,
            meas_lo_freq=None,
            schedule_los=None,
            meas_level=MeasLevel.CLASSIFIED,
            meas_return=MeasReturnType.AVERAGE,
            memory_slots=None,
            memory_slot_size=100,
            rep_time=None,
            rep_delay=None,
            init_qubits=True,
            use_measure_esp=None,
        )

    def properties(
        self, refresh: bool = False, datetime: Optional[python_datetime] = None
    ) -> Optional[BackendProperties]:
        """Return the backend properties, subject to optional filtering.

        This data describes qubits properties (such as T1 and T2),
        gates properties (such as gate length and error), and other general
        properties of the backend.

        The schema for backend properties can be found in
        `Qiskit/ibm-quantum-schemas
        <https://github.com/Qiskit/ibm-quantum-schemas/blob/main/schemas/backend_properties_schema.json>`_.

        Args:
            refresh: If ``True``, re-query the server for the backend properties.
                Otherwise, return a cached version.
            datetime: By specifying `datetime`, this function returns an instance
                of the :class:`BackendProperties<qiskit.providers.models.BackendProperties>`
                whose timestamp is closest to, but older than, the specified `datetime`.

        Returns:
            The backend properties or ``None`` if the backend properties are not
            currently available.

        Raises:
            TypeError: If an input argument is not of the correct type.
        """
        # pylint: disable=arguments-differ
        if not isinstance(refresh, bool):
            raise TypeError(
                "The 'refresh' argument needs to be a boolean. "
                "{} is of type {}".format(refresh, type(refresh))
            )
        if datetime and not isinstance(datetime, python_datetime):
            raise TypeError("'{}' is not of type 'datetime'.")

        if datetime:
            datetime = local_to_utc(datetime)

        if datetime or refresh or self._properties is None:
            api_properties = self._api_client.backend_properties(
                self.name(), datetime=datetime  # type: ignore
            )
            if not api_properties:
                return None
            decode_backend_properties(api_properties)
            api_properties = utc_to_local_all(api_properties)
            backend_properties = BackendProperties.from_dict(api_properties)
            if datetime:  # Don't cache result.
                return backend_properties
            self._properties = backend_properties
        return self._properties

    def status(self) -> BackendStatus:
        """Return the backend status.

        Note:
            If the returned :class:`~qiskit.providers.models.BackendStatus`
            instance has ``operational=True`` but ``status_msg="internal"``,
            then the backend is accepting jobs but not processing them.

        Returns:
            The status of the backend.

        Raises:
            IBMBackendApiProtocolError: If the status for the backend cannot be formatted properly.
        """
        api_status = self._api_client.backend_status(self.name())

        try:
            return BackendStatus.from_dict(api_status)
        except TypeError as ex:
            raise IBMBackendApiProtocolError(
                "Unexpected return value received from the server when "
                "getting backend status: {}".format(str(ex))
            ) from ex

    def defaults(self, refresh: bool = False) -> Optional[PulseDefaults]:
        """Return the pulse defaults for the backend.

        The schema for default pulse configuration can be found in
        `Qiskit/ibm-quantum-schemas
        <https://github.com/Qiskit/ibm-quantum-schemas/blob/main/schemas/default_pulse_configuration_schema.json>`_.

        Args:
            refresh: If ``True``, re-query the server for the backend pulse defaults.
                Otherwise, return a cached version.

        Returns:
            The backend pulse defaults or ``None`` if the backend does not support pulse.
        """
        if refresh or self._defaults is None:
            api_defaults = self._api_client.backend_pulse_defaults(self.name())
            if api_defaults:
                decode_pulse_defaults(api_defaults)
                self._defaults = PulseDefaults.from_dict(api_defaults)
            else:
                self._defaults = None

        return self._defaults

    def reservations(
        self,
        start_datetime: Optional[python_datetime] = None,
        end_datetime: Optional[python_datetime] = None,
    ) -> List[BackendReservation]:
        """Return backend reservations.

        If start_datetime and/or end_datetime is specified, reservations with
        time slots that overlap with the specified time window will be returned.

        Some of the reservation information is only available if you are the
        owner of the reservation.

        Args:
            start_datetime: Filter by the given start date/time, in local timezone.
            end_datetime: Filter by the given end date/time, in local timezone.

        Returns:
            A list of reservations that match the criteria.
        """
        start_datetime = local_to_utc(start_datetime) if start_datetime else None
        end_datetime = local_to_utc(end_datetime) if end_datetime else None
        raw_response = self._api_client.backend_reservations(  # type: ignore
            self.name(), start_datetime, end_datetime
        )
        return convert_reservation_data(raw_response, self.name())

    def configuration(
        self,
    ) -> Union[QasmBackendConfiguration, PulseBackendConfiguration]:
        """Return the backend configuration.

        Backend configuration contains fixed information about the backend, such
        as its name, number of qubits, basis gates, coupling map, quantum volume, etc.

        The schema for backend configuration can be found in
        `Qiskit/ibm-quantum-schemas
        <https://github.com/Qiskit/ibm-quantum-schemas/blob/main/schemas/backend_configuration_schema.json>`_.

        Returns:
            The configuration for the backend.
        """
        return self._configuration

    def __repr__(self) -> str:
        return "<{}('{}')>".format(self.__class__.__name__, self.name())

    def run(self, *args: Any, **kwargs: Any) -> None:
        """Not supported method"""
        # pylint: disable=arguments-differ
        raise RuntimeError(
            "IBMBackend.run() is not supported in the Qiskit Runtime environment."
        )


class IBMSimulator(IBMBackend):
    """Backend class interfacing with an IBM Quantum simulator."""

    @classmethod
    def _default_options(cls) -> Options:
        """Default runtime options."""
        options = super()._default_options()
        options.update_options(noise_model=None, seed_simulator=None)
        return options

    def properties(
        self, refresh: bool = False, datetime: Optional[python_datetime] = None
    ) -> None:
        """Return ``None``, simulators do not have backend properties."""
        return None


class IBMRetiredBackend(IBMBackend):
    """Backend class interfacing with an IBM Quantum device no longer available."""

    def __init__(
        self,
        configuration: Union[QasmBackendConfiguration, PulseBackendConfiguration],
        service: "ibm_runtime_service.IBMRuntimeService",
        credentials: Credentials,
        api_client: AccountClient,
    ) -> None:
        """IBMRetiredBackend constructor.

        Args:
            configuration: Backend configuration.
            service: IBM Quantum account provider.
            credentials: IBM Quantum credentials.
            api_client: IBM Quantum client used to communicate with the server.
        """
        super().__init__(configuration, service, credentials, api_client)
        self._status = BackendStatus(
            backend_name=self.name(),
            backend_version=self.configuration().backend_version,
            operational=False,
            pending_jobs=0,
            status_msg="This backend is no longer available.",
        )

    @classmethod
    def _default_options(cls) -> Options:
        """Default runtime options."""
        return Options()

    def properties(
        self, refresh: bool = False, datetime: Optional[python_datetime] = None
    ) -> None:
        """Return the backend properties."""
        return None

    def defaults(self, refresh: bool = False) -> None:
        """Return the pulse defaults for the backend."""
        return None

    def status(self) -> BackendStatus:
        """Return the backend status."""
        return self._status

    def reservations(
        self,
        start_datetime: Optional[python_datetime] = None,
        end_datetime: Optional[python_datetime] = None,
    ) -> List[BackendReservation]:
        return []

    @classmethod
    def from_name(
        cls,
        backend_name: str,
        service: "ibm_runtime_service.IBMRuntimeService",
        credentials: Credentials,
        api: AccountClient,
    ) -> "IBMRetiredBackend":
        """Return a retired backend from its name."""
        configuration = QasmBackendConfiguration(
            backend_name=backend_name,
            backend_version="0.0.0",
            n_qubits=1,
            basis_gates=[],
            simulator=False,
            local=False,
            conditional=False,
            open_pulse=False,
            memory=False,
            max_shots=1,
            gates=[GateConfig(name="TODO", parameters=[], qasm_def="TODO")],
            coupling_map=[[0, 1]],
        )
        return cls(configuration, service, credentials, api)

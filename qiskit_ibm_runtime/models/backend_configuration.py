# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2018.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


"""Backend Configuration Classes."""
import datetime
import copy
from typing import Dict, List, Any, TypeVar, Type

from qiskit.exceptions import QiskitError

GateConfigT = TypeVar("GateConfigT", bound="GateConfig")
UchannelLOT = TypeVar("UchannelLOT", bound="UchannelLO")  # pylint: disable=[invalid-name]
QasmBackendConfigurationT = TypeVar("QasmBackendConfigurationT", bound="QasmBackendConfiguration")


class GateConfig:
    """Class representing a Gate Configuration

    Attributes:
        name: the gate name as it will be referred to in OpenQASM.
        parameters: variable names for the gate parameters (if any).
        qasm_def: definition of this gate in terms of OpenQASM 2 primitives U
                  and CX.
    """

    def __init__(
        self,
        name: str,
        parameters: List[str],
        qasm_def: str,
        coupling_map: list = None,
        latency_map: list = None,
        conditional: bool = None,
        description: str = None,
    ):
        """Initialize a GateConfig object

        Args:
            name (str): the gate name as it will be referred to in OpenQASM.
            parameters (list): variable names for the gate parameters (if any)
                               as a list of strings.
            qasm_def (str): definition of this gate in terms of OpenQASM 2 primitives U and CX.
            coupling_map (list): An optional coupling map for the gate. In
                the form of a list of lists of integers representing the qubit
                groupings which are coupled by this gate.
            latency_map (list): An optional map of latency for the gate. In the
                the form of a list of lists of integers of either 0 or 1
                representing an array of dimension
                len(coupling_map) X n_registers that specifies the register
                latency (1: fast, 0: slow) conditional operations on the gate
            conditional (bool): Optionally specify whether this gate supports
                conditional operations (true/false). If this is not specified,
                then the gate inherits the conditional property of the backend.
            description (str): Description of the gate operation
        """

        self.name = name
        self.parameters = parameters
        self.qasm_def = qasm_def
        # coupling_map with length 0 is invalid
        if coupling_map:
            self.coupling_map = coupling_map
        # latency_map with length 0 is invalid
        if latency_map:
            self.latency_map = latency_map
        if conditional is not None:
            self.conditional = conditional
        if description is not None:
            self.description = description

    @classmethod
    def from_dict(cls: Type[GateConfigT], data: Dict[str, Any]) -> GateConfigT:
        """Create a new GateConfig object from a dictionary.

        Args:
            data (dict): A dictionary representing the GateConfig to create.
                         It will be in the same format as output by
                         :func:`to_dict`.

        Returns:
            GateConfig: The GateConfig from the input dictionary.
        """
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary format representation of the GateConfig.

        Returns:
            dict: The dictionary form of the GateConfig.
        """
        out_dict: Dict[str, Any] = {
            "name": self.name,
            "parameters": self.parameters,
            "qasm_def": self.qasm_def,
        }
        if hasattr(self, "coupling_map"):
            out_dict["coupling_map"] = self.coupling_map
        if hasattr(self, "latency_map"):
            out_dict["latency_map"] = self.latency_map
        if hasattr(self, "conditional"):
            out_dict["conditional"] = self.conditional
        if hasattr(self, "description"):
            out_dict["description"] = self.description
        return out_dict

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, GateConfig):
            if self.to_dict() == other.to_dict():
                return True
        return False

    def __repr__(self) -> str:
        out_str = f"GateConfig({self.name}, {self.parameters}, {self.qasm_def}"
        for i in ["coupling_map", "latency_map", "conditional", "description"]:
            if hasattr(self, i):
                out_str += ", " + repr(getattr(self, i))
        out_str += ")"
        return out_str


class UchannelLO:
    """Class representing a U Channel LO

    Attributes:
        q: Qubit that scale corresponds too.
        scale: Scale factor for qubit frequency.
    """

    def __init__(self, q: int, scale: complex) -> None:
        """Initialize a UchannelLOSchema object

        Args:
            q (int): Qubit that scale corresponds too. Must be >= 0.
            scale (complex): Scale factor for qubit frequency.

        Raises:
            QiskitError: If q is < 0
        """
        if q < 0:
            raise QiskitError("q must be >=0")
        self.q = q
        self.scale = scale

    @classmethod
    def from_dict(cls: Type[UchannelLOT], data: Dict[str, Any]) -> UchannelLOT:
        """Create a new UchannelLO object from a dictionary.

        Args:
            data (dict): A dictionary representing the UChannelLO to
                create. It will be in the same format as output by
                :func:`to_dict`.

        Returns:
            UchannelLO: The UchannelLO from the input dictionary.
        """
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary format representation of the UChannelLO.

        Returns:
            dict: The dictionary form of the UChannelLO.
        """
        out_dict: Dict[str, Any] = {
            "q": self.q,
            "scale": self.scale,
        }
        return out_dict

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, UchannelLO):
            if self.to_dict() == other.to_dict():
                return True
        return False

    def __repr__(self) -> str:
        return f"UchannelLO({self.q}, {self.scale})"


class QasmBackendConfiguration:
    """Class representing an OpenQASM 2.0 Backend Configuration.

    Attributes:
        backend_name: backend name.
        backend_version: backend version in the form X.Y.Z.
        n_qubits: number of qubits.
        basis_gates: list of basis gates names on the backend.
        gates: list of basis gates on the backend.
        local: backend is local or remote.
        simulator: backend is a simulator.
        conditional: backend supports conditional operations.
        open_pulse: backend supports open pulse.
        memory: backend supports memory.
    """

    _data: Dict[Any, Any] = {}

    def __init__(
        self,
        backend_name: str,
        backend_version: str,
        n_qubits: int,
        basis_gates: list,
        gates: list,
        local: bool,
        simulator: bool,
        conditional: bool,
        open_pulse: bool,
        memory: bool,
        coupling_map: list,
        meas_levels: List[int] = None,
        meas_kernels: List[str] = None,
        discriminators: List[str] = None,
        meas_map: list = None,
        supported_instructions: List[str] = None,
        dynamic_reprate_enabled: bool = False,
        rep_delay_range: List[float] = None,
        default_rep_delay: float = None,
        sample_name: str = None,
        n_registers: int = None,
        register_map: list = None,
        configurable: bool = None,
        credits_required: bool = None,
        online_date: datetime.datetime = None,
        display_name: str = None,
        description: str = None,
        tags: list = None,
        dt: float = None,
        dtm: float = None,
        processor_type: dict = None,
        parametric_pulses: list = None,
        **kwargs: Any,
    ):
        """Initialize a QasmBackendConfiguration Object

        Args:
            backend_name (str): The backend name
            backend_version (str): The backend version in the form X.Y.Z
            n_qubits (int): the number of qubits for the backend
            basis_gates (list): The list of strings for the basis gates of the
                backends
            gates (list): The list of GateConfig objects for the basis gates of
                the backend
            local (bool): True if the backend is local or False if remote
            simulator (bool): True if the backend is a simulator
            conditional (bool): True if the backend supports conditional
                operations
            open_pulse (bool): True if the backend supports OpenPulse
            memory (bool): True if the backend supports memory
            coupling_map (list): The coupling map for the device
            meas_levels: Supported measurement levels.
            meas_kernels: Supported measurement kernels.
            discriminators: Supported discriminators.
            meas_map (list): Grouping of measurement which are multiplexed
            supported_instructions (List[str]): Instructions supported by the backend.
            dynamic_reprate_enabled (bool): whether delay between programs can be set dynamically
                (ie via ``rep_delay``). Defaults to False.
            rep_delay_range (List[float]): 2d list defining supported range of repetition
                delays for backend in μs. First entry is lower end of the range, second entry is
                higher end of the range. Optional, but will be specified when
                ``dynamic_reprate_enabled=True``.
            default_rep_delay (float): Value of ``rep_delay`` if not specified by user and
                ``dynamic_reprate_enabled=True``.
            sample_name (str): Sample name for the backend
            n_registers (int): Number of register slots available for feedback
                (if conditional is True)
            register_map (list): An array of dimension n_qubits X
                n_registers that specifies whether a qubit can store a
                measurement in a certain register slot.
            configurable (bool): True if the backend is configurable, if the
                backend is a simulator
            credits_required (bool): True if backend requires credits to run a
                job.
            online_date (datetime.datetime): The date that the device went online
            display_name (str): Alternate name field for the backend
            description (str): A description for the backend
            tags (list): A list of string tags to describe the backend
            dt (float): Qubit drive channel timestep in nanoseconds.
            dtm (float): Measurement drive channel timestep in nanoseconds.
            processor_type (dict): Processor type for this backend. A dictionary of the
                form ``{"family": <str>, "revision": <str>, segment: <str>}`` such as
                ``{"family": "Canary", "revision": "1.0", segment: "A"}``.

                - family: Processor family of this backend.
                - revision: Revision version of this processor.
                - segment: Segment this processor belongs to within a larger chip.
            parametric_pulses (list): A list of pulse shapes which are supported on the backend.
                For example: ``['gaussian', 'constant']``

            **kwargs: optional fields
        """
        self._data = {}

        self.backend_name = backend_name
        self.backend_version = backend_version
        self.n_qubits = n_qubits
        self.basis_gates = basis_gates
        self.gates = gates
        self.local = local
        self.simulator = simulator
        self.conditional = conditional
        self.open_pulse = open_pulse
        self.memory = memory
        self.coupling_map = coupling_map
        self.meas_levels = meas_levels
        self.meas_kernels = meas_kernels
        self.discriminators = discriminators
        if meas_map is not None:
            self.meas_map = meas_map
        if supported_instructions:
            self.supported_instructions = supported_instructions

        self.dynamic_reprate_enabled = dynamic_reprate_enabled
        if rep_delay_range:
            self.rep_delay_range = [_rd * 1e-6 for _rd in rep_delay_range]  # convert to sec
        if default_rep_delay is not None:
            self.default_rep_delay = default_rep_delay * 1e-6  # convert to sec

        if sample_name is not None:
            self.sample_name = sample_name
        # n_registers must be >=1
        if n_registers:
            self.n_registers = 1
        # register_map must have at least 1 entry
        if register_map:
            self.register_map = register_map
        if configurable is not None:
            self.configurable = configurable
        if credits_required is not None:
            self.credits_required = credits_required
        if online_date is not None:
            self.online_date = online_date
        if display_name is not None:
            self.display_name = display_name
        if description is not None:
            self.description = description
        if tags is not None:
            self.tags = tags
        # Add pulse properties here because some backends do not
        # fit within the Qasm / Pulse backend partitioning in Qiskit
        if dt is not None:
            self.dt = dt * 1e-9
        if dtm is not None:
            self.dtm = dtm * 1e-9
        if processor_type is not None:
            self.processor_type = processor_type
        if parametric_pulses is not None:
            self.parametric_pulses = parametric_pulses

        # convert lo range from GHz to Hz
        if "qubit_lo_range" in kwargs:
            kwargs["qubit_lo_range"] = [
                [min_range * 1e9, max_range * 1e9]
                for (min_range, max_range) in kwargs["qubit_lo_range"]
            ]

        if "meas_lo_range" in kwargs:
            kwargs["meas_lo_range"] = [
                [min_range * 1e9, max_range * 1e9]
                for (min_range, max_range) in kwargs["meas_lo_range"]
            ]

        # convert rep_times from μs to sec
        if "rep_times" in kwargs:
            kwargs["rep_times"] = [_rt * 1e-6 for _rt in kwargs["rep_times"]]

        self._data.update(kwargs)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._data[name]
        except KeyError as ex:
            raise AttributeError(f"Attribute {name} is not defined") from ex

    @classmethod
    def from_dict(
        cls: Type[QasmBackendConfigurationT], data: Dict[str, Any]
    ) -> QasmBackendConfigurationT:
        """Create a new GateConfig object from a dictionary.

        Args:
            data (dict): A dictionary representing the GateConfig to create.
                         It will be in the same format as output by
                         :func:`to_dict`.
        Returns:
            GateConfig: The GateConfig from the input dictionary.
        """
        in_data: Dict[str, Any] = copy.copy(data)
        gates = [GateConfig.from_dict(x) for x in in_data.pop("gates")]
        in_data["gates"] = gates
        return cls(**in_data)

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary format representation of the GateConfig.

        Returns:
            dict: The dictionary form of the GateConfig.
        """
        out_dict: Dict[str, Any] = {
            "backend_name": self.backend_name,
            "backend_version": self.backend_version,
            "n_qubits": self.n_qubits,
            "basis_gates": self.basis_gates,
            "gates": [x.to_dict() for x in self.gates],
            "local": self.local,
            "simulator": self.simulator,
            "conditional": self.conditional,
            "open_pulse": self.open_pulse,
            "memory": self.memory,
            "coupling_map": self.coupling_map,
            "dynamic_reprate_enabled": self.dynamic_reprate_enabled,
            "meas_levels": self.meas_levels,
            "meas_kernels": self.meas_kernels,
            "discriminators": self.discriminators,
        }
        if hasattr(self, "meas_map"):
            out_dict["meas_map"] = self.meas_map

        if hasattr(self, "supported_instructions"):
            out_dict["supported_instructions"] = self.supported_instructions

        if hasattr(self, "rep_delay_range"):
            out_dict["rep_delay_range"] = [_rd * 1e6 for _rd in self.rep_delay_range]
        if hasattr(self, "default_rep_delay"):
            out_dict["default_rep_delay"] = self.default_rep_delay * 1e6

        for kwarg in [
            "sample_name",
            "n_registers",
            "register_map",
            "configurable",
            "credits_required",
            "online_date",
            "display_name",
            "description",
            "tags",
            "dt",
            "dtm",
            "processor_type",
            "parametric_pulses",
        ]:
            if hasattr(self, kwarg):
                out_dict[kwarg] = getattr(self, kwarg)

        out_dict.update(self._data)

        if "dt" in out_dict:
            out_dict["dt"] *= 1e9
        if "dtm" in out_dict:
            out_dict["dtm"] *= 1e9

        # Use GHz in dict
        if "qubit_lo_range" in out_dict:
            out_dict["qubit_lo_range"] = [
                [min_range * 1e-9, max_range * 1e-9]
                for (min_range, max_range) in out_dict["qubit_lo_range"]
            ]

        if "meas_lo_range" in out_dict:
            out_dict["meas_lo_range"] = [
                [min_range * 1e-9, max_range * 1e-9]
                for (min_range, max_range) in out_dict["meas_lo_range"]
            ]

        return out_dict

    @property
    def num_qubits(self) -> int:
        """Returns the number of qubits.

        In future, `n_qubits` should be replaced in favor of `num_qubits` for consistent use
        throughout Qiskit. Until this is properly refactored, this property serves as intermediate
        solution.
        """
        return self.n_qubits

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, QasmBackendConfiguration):
            if self.to_dict() == other.to_dict():
                return True
        return False

    def __contains__(self, item: str) -> bool:
        return item in self.__dict__


class BackendConfiguration(QasmBackendConfiguration):
    """Backwards compat shim representing an abstract backend configuration."""

    pass

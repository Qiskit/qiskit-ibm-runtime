# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""IBM configuration model."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from qiskit.circuit.parameter import Parameter

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GateConfig(BaseModel):
    """Schema of gate configuration"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    """QASM instruction name"""
    parameters: list[Parameter | float]
    """Gate parameters"""
    qasm_def: str | None = None
    """QASM representation"""
    coupling_map: list[tuple[int, ...]] = Field(default_factory=list)
    """Set of qubits this gate is applied to"""
    label: str | None = None
    """Unique identifier of this entry"""

    @field_validator("parameters", mode="before")
    @classmethod
    def _format_parameters(cls, params):
        if params is None:
            return []
        qk_params = []
        for param in params:
            try:
                qk_params.append(float(param))
            except ValueError:
                qk_params.append(Parameter(param))
        return qk_params


class ProcessorType(BaseModel):
    """Schema of processor type information"""

    family: str
    """Processor family of this backend"""
    revision: str
    """Revision version of this processor"""
    segment: str | None = None
    """Segment this processor belongs to within a larger chip"""

    @field_validator("revision", mode="before")
    @classmethod
    def _to_string(cls, value):
        return str(value)


class ChannelSpec(BaseModel):
    """Schema of hardware channel specification"""

    operates: dict[str, list[int]]
    """Hardware components that this channels act on"""
    purpose: str
    """Purpose of this channel"""
    type: Literal["drive", "measure", "control", "acquire"]
    """Qiskit Pulse channel type identifier"""


class TimingConstraints(BaseModel):
    """Schema of instruction timing constraints"""

    pulse_alignment: int = Field(ge=1)
    """Alignment interval of gate instructions"""
    acquire_alignment: int = Field(ge=1)
    """Alignment interval of acquisition trigger"""
    granularity: int = Field(ge=1)
    """granularity of pulse waveform"""
    min_length: int = Field(get=1)
    """Minimum pulse waveform samples"""


class IBMBackendConfiguration(BaseModel):
    """Schema of backend configuration"""

    backend_name: str
    """The backend name"""
    backend_version: str
    """The backend version in the form X.Y.Z"""
    n_qubits: int = Field(ge=1)
    """The number of qubits for the backend"""
    basis_gates: list[str]
    """The list of strings for the basis gates of the backends"""
    gates: list[GateConfig]
    """The list of GateConfig objects for the basis gates of the backend"""
    local: bool
    """True if the backend is local or False if remote"""
    simulator: bool
    """True if the backend is a simulator"""
    conditional: bool
    """True if the backend supports conditional operations"""
    open_pulse: bool
    """True if the backend supports Qiskit pulse gate feature"""
    memory: bool
    """True if the backend supports memory"""
    max_shots: int = Field(gt=0)
    """The maximum number of shots allowed on the backend"""
    coupling_map: list[list[int]]
    """The coupling map for the device"""
    dt: float = Field(ge=0)
    """Qubit drive channel timestep in nanoseconds"""
    dtm: float = Field(ge=0)
    """Measurement drive channel timestep in nanoseconds"""
    supported_instructions: list[str] = Field(default_factory=list)
    """Instructions supported by the backend"""
    dynamic_reprate_enabled: bool = False
    """Whether delay between programs can be set dynamically"""
    rep_delay_range: list[float] = Field(default_factory=list)
    """Range of idle time between circuits in units of microseconds"""
    default_rep_delay: float | None = None
    """Default value for idle time between circuits in units of microseconds"""
    rep_times: list[float] = Field(default_factory=list)
    """Available repetition rates of shots"""
    max_experiments: int | None = None
    """The maximum number of experiments per job"""
    sample_name: str | None = None
    """Sample name for the backend"""
    credits_required: bool | None = None
    """True if backend requires credits to run a job"""
    online_date: datetime | None = None
    """The date that the device went online"""
    description: str | None = None
    """A description for the backend"""
    processor_type: ProcessorType | None = None
    """Processor type for this backend"""
    parametric_pulses: list[str] = Field(default_factory=list)
    """A list of pulse shapes which are supported on the backend"""
    qubit_lo_range: list[tuple[float, float]] = Field(default_factory=list)
    """Range of measurement frequency for qubits."""
    meas_lo_range: list[tuple[float, float]] = Field(default_factory=list)
    """Range of measurement frequency for qubits."""
    meas_kernels: list[str] = Field(default_factory=list)
    """Supported measurement kernels"""
    discriminators: list[str] = Field(default_factory=list)
    """Supported discriminators"""
    acquisition_latency: list[float] = Field(default_factory=list)
    """Latency (in units of dt) to write a measurement result from qubit n into register slot m"""
    conditional_latency: list[float] = Field(default_factory=list)
    """Latency (in units of dt) to do a conditional operation on channel n from register slot m"""
    meas_map: list[list[int]] = Field(default_factory=list)
    """Grouping of measurement which are multiplexed"""
    channels: dict[str, ChannelSpec] = Field(default_factory=dict)
    """Information of each hardware channel"""
    uchannels_enabled: bool = False
    """True when control for u-channels are allowed"""
    n_uchannels: int | None = None
    """Number of u-channels"""
    u_channel_lo: list[list[dict]] = Field(default_factory=list)
    """U-channel relationship on device los"""
    meas_levels: list[int] = Field(default_factory=list)
    """Supported measurement levels"""
    hamiltonian: dict = Field(default_factory=dict)
    """Dictionary with fields characterizing the system hamiltonian"""
    supported_features: list[str] = Field(default_factory=list)
    """List of supported features."""
    timing_constraints: TimingConstraints | None = None
    """Constraints of instruction timing on hardware controller"""

    # TODO add more fields? Or remove fields that are never used practically?

    @field_validator("dt", "dtm", mode="before")
    @classmethod
    def _format_dts(cls, value):
        return _apply_prefix_recursive(value, 1e-9)

    @field_validator("qubit_lo_range", "meas_lo_range", mode="before")
    @classmethod
    def _format_los(cls, value):
        return _apply_prefix_recursive(value, 1e9)

    @field_validator(
        "rep_delay_range",
        "default_rep_delay",
        "default_rep_delay",
        "rep_times",
        mode="before",
    )
    @classmethod
    def _format_reptimes(cls, value):
        return _apply_prefix_recursive(value, 1e-6)

    @field_validator("u_channel_lo", mode="before")
    @classmethod
    def _format_u_channel_lo(cls, value):
        if value is None:
            return None
        for uchannel_lo in value:
            for lo_spec in uchannel_lo:
                scale = lo_spec["scale"]
                if not isinstance(scale, complex):
                    try:
                        lo_spec["scale"] = complex(*scale)
                    except TypeError:
                        raise TypeError(f"{scale} is not in a valid complex number format.")
        return value

    @property
    def num_qubits(self) -> int:
        """Alias of n_qubits"""
        return self.n_qubits


def _apply_prefix_recursive(value: Any, prefix: float):
    """Helper function to apply prefix recursively."""
    try:
        return prefix * float(value)
    except TypeError:
        return [_apply_prefix_recursive(v, prefix) for v in value]

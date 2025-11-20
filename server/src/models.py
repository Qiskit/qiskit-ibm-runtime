"""
Pydantic models for Qiskit Runtime Backend API.

This module defines all request and response models for the backend endpoints,
based on the IBM Qiskit Runtime REST API specification (IBM-API-Version: 2025-05-01).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Base Models - Reusable components
# ============================================================================

class Nduv(BaseModel):
    """
    Name-Date-Unit-Value model for backend properties.

    Represents a measurement or property with its metadata.
    """
    date: datetime = Field(..., description="Timestamp when the property was measured")
    name: str = Field(..., description="Name of the property (e.g., 'T1', 'T2', 'frequency')")
    unit: str = Field(..., description="Unit of measurement (e.g., 'us', 'GHz')")
    value: float = Field(..., description="Measured value")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "date": "2024-11-20T10:46:00Z",
            "name": "T1",
            "unit": "us",
            "value": 125.3
        }
    })


class ProcessorType(BaseModel):
    """Processor type information."""
    family: str = Field(..., description="Processor family (e.g., 'Canary', 'Falcon', 'Hummingbird')")
    revision: float = Field(..., description="Processor revision number")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "family": "Canary",
            "revision": 1.2
        }
    })


class UchannelLO(BaseModel):
    """
    U-channel local oscillator configuration.

    Used for calibration of control pulses.
    """
    q: int = Field(..., description="Qubit index")
    scale: List[float] = Field(
        ...,
        description="Complex scale factor as [real, imaginary] pair",
        min_length=2,
        max_length=2
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "q": 0,
            "scale": [1.0, 0.0]
        }
    })


# ============================================================================
# Gate Configuration Models
# ============================================================================

class GateConfig(BaseModel):
    """
    Gate configuration details.

    Defines a quantum gate with its properties and constraints.
    """
    name: str = Field(..., description="Gate name (e.g., 'cx', 'sx', 'rz')")
    parameters: List[str] = Field(
        default_factory=list,
        description="List of gate parameter names"
    )
    qasm_def: Optional[str] = Field(
        None,
        description="OpenQASM definition of the gate"
    )
    coupling_map: Optional[List[List[int]]] = Field(
        None,
        description="Qubit pairs this gate operates on"
    )
    latency_map: Optional[List[List[int]]] = Field(
        None,
        description="Latency information for gate operations"
    )
    conditional: bool = Field(
        default=False,
        description="Whether the gate supports conditional execution"
    )
    description: Optional[str] = Field(
        None,
        description="Human-readable gate description"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "cx",
            "parameters": [],
            "qasm_def": "gate cx q1,q2 { CX q1,q2; }",
            "coupling_map": [[0, 1], [1, 0]],
            "conditional": True,
            "description": "CNOT gate"
        }
    })


class GateProperties(BaseModel):
    """
    Runtime properties of a gate.

    Contains calibration data and performance metrics for a specific gate.
    """
    qubits: List[int] = Field(..., description="Qubit indices this gate operates on")
    gate: str = Field(..., description="Gate name")
    parameters: List[Nduv] = Field(
        default_factory=list,
        description="Gate parameters like error rate, gate time, etc."
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "qubits": [0, 1],
            "gate": "cx",
            "parameters": [
                {
                    "date": "2024-11-20T10:46:00Z",
                    "name": "gate_error",
                    "unit": "",
                    "value": 0.0043
                },
                {
                    "date": "2024-11-20T10:46:00Z",
                    "name": "gate_length",
                    "unit": "ns",
                    "value": 467.0
                }
            ]
        }
    })


# ============================================================================
# Backend Configuration Models
# ============================================================================

class BackendConfiguration(BaseModel):
    """
    Complete backend configuration.

    Describes the quantum backend's capabilities, topology, and specifications.
    This corresponds to GET /v1/backends/{id}/configuration response.
    """
    # Basic identification
    backend_name: str = Field(..., description="Unique backend identifier")
    backend_version: str = Field(..., description="Backend version string")

    # Quantum system properties
    n_qubits: int = Field(..., description="Number of qubits in the system")
    basis_gates: List[str] = Field(..., description="List of supported basis gates")
    gates: List[GateConfig] = Field(
        default_factory=list,
        description="Detailed gate configurations"
    )

    # Device characteristics
    local: bool = Field(default=False, description="Whether backend is local")
    simulator: bool = Field(default=False, description="Whether backend is a simulator")
    conditional: bool = Field(default=False, description="Supports conditional operations")
    open_pulse: bool = Field(default=False, description="Supports OpenPulse")
    memory: bool = Field(default=False, description="Supports memory slots")
    max_shots: int = Field(default=8192, description="Maximum shots per job")
    max_experiments: int = Field(default=1, description="Maximum experiments per job")

    # Topology and connectivity
    coupling_map: Optional[List[List[int]]] = Field(
        None,
        description="Qubit connectivity graph as edge list"
    )
    supported_instructions: Optional[List[str]] = Field(
        None,
        description="List of supported quantum instructions"
    )
    dynamic_reprate_enabled: bool = Field(
        default=False,
        description="Dynamic repetition rate enabled"
    )
    rep_delay_range: Optional[List[float]] = Field(
        None,
        description="Min and max repetition delay in microseconds"
    )
    default_rep_delay: Optional[float] = Field(
        None,
        description="Default repetition delay in microseconds"
    )

    # Measurement capabilities
    meas_map: Optional[List[List[int]]] = Field(
        None,
        description="Grouping of qubits that must be measured together"
    )

    # Processor information
    processor_type: Optional[ProcessorType] = Field(
        None,
        description="Processor type and revision"
    )

    # Pulse-level properties (for OpenPulse backends)
    dt: Optional[float] = Field(
        None,
        description="System time resolution in seconds"
    )
    dtm: Optional[float] = Field(
        None,
        description="Measurement time resolution in seconds"
    )
    parametric_pulses: List[str] = Field(
        default_factory=list,
        description="Supported parametric pulse shapes"
    )

    # Channel information
    n_registers: Optional[int] = Field(None, description="Number of registers")
    n_uchannels: int = Field(default=0, description="Number of U channels")
    u_channel_lo: List[List[UchannelLO]] = Field(
        default_factory=list,
        description="U-channel local oscillator configurations"
    )

    # Timing constraints
    qubit_lo_range: Optional[List[List[float]]] = Field(
        None,
        description="Qubit frequency ranges in GHz"
    )
    meas_lo_range: Optional[List[List[float]]] = Field(
        None,
        description="Measurement frequency ranges in GHz"
    )

    # Additional features
    acquire_alignment: Optional[int] = Field(
        None,
        description="Acquisition alignment constraint"
    )
    pulse_alignment: Optional[int] = Field(
        None,
        description="Pulse alignment constraint"
    )
    meas_kernels: Optional[List[str]] = Field(
        None,
        description="Supported measurement discrimination kernels"
    )
    discriminators: Optional[List[str]] = Field(
        None,
        description="Supported measurement discriminators"
    )

    # Performance metrics
    quantum_volume: Optional[int] = Field(
        None,
        description="Quantum volume metric"
    )
    clops_h: Optional[float] = Field(
        None,
        description="Circuit Layer Operations Per Second (CLOPS) metric"
    )

    # Runtime features
    supported_features: List[str] = Field(
        default_factory=list,
        description="List of supported runtime features"
    )

    # Multi-chip architecture
    multi_meas_enabled: bool = Field(
        default=False,
        description="Multiple measurement enabled"
    )

    # Input constraints
    timing_constraints: Optional[Dict[str, Any]] = Field(
        None,
        description="Timing constraints for pulse scheduling"
    )

    # Online date
    online_date: Optional[datetime] = Field(
        None,
        description="Date when backend came online"
    )

    # Additional metadata
    credits_required: bool = Field(
        default=True,
        description="Whether credits are required to use this backend"
    )
    sample_name: Optional[str] = Field(None, description="Sample name")
    description: Optional[str] = Field(None, description="Backend description")

    # Allow extra fields for forward compatibility
    model_config = ConfigDict(extra='allow')


# ============================================================================
# Backend Properties Models
# ============================================================================

class BackendProperties(BaseModel):
    """
    Backend calibration properties.

    Contains time-stamped calibration data for qubits and gates.
    This corresponds to GET /v1/backends/{id}/properties response.
    """
    backend_name: str = Field(..., description="Backend identifier")
    backend_version: str = Field(..., description="Backend version")
    last_update_date: datetime = Field(
        ...,
        description="Timestamp of last calibration update"
    )
    qubits: List[List[Nduv]] = Field(
        ...,
        description="Per-qubit properties (T1, T2, frequency, readout error, etc.)"
    )
    gates: List[GateProperties] = Field(
        ...,
        description="Per-gate properties (error rates, gate times, etc.)"
    )
    general: List[Nduv] = Field(
        default_factory=list,
        description="General backend-level properties"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "backend_name": "ibmq_armonk",
            "backend_version": "2.4.3",
            "last_update_date": "2024-11-20T10:46:00Z",
            "qubits": [
                [
                    {"date": "2024-11-20T10:46:00Z", "name": "T1", "unit": "us", "value": 125.3},
                    {"date": "2024-11-20T10:46:00Z", "name": "T2", "unit": "us", "value": 89.2},
                    {"date": "2024-11-20T10:46:00Z", "name": "frequency", "unit": "GHz", "value": 4.971}
                ]
            ],
            "gates": [],
            "general": []
        }
    })


# ============================================================================
# Backend Status Models
# ============================================================================

class BackendStatus(BaseModel):
    """
    Real-time backend status.

    Provides current operational status and queue information.
    This corresponds to GET /v1/backends/{id}/status response.
    """
    backend_name: str = Field(..., description="Backend identifier")
    backend_version: str = Field(..., description="Backend version")
    operational: bool = Field(
        ...,
        description="Whether the backend is operational",
        alias="state"
    )
    status_msg: str = Field(
        ...,
        description="Human-readable status message",
        alias="status"
    )
    pending_jobs: int = Field(
        ...,
        description="Number of jobs in queue",
        alias="length_queue"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "backend_name": "ibmq_armonk",
                "backend_version": "2.4.3",
                "state": True,
                "status": "operational",
                "length_queue": 5
            }
        }
    )


# ============================================================================
# Backend Defaults Models (Pulse Calibrations)
# ============================================================================

class Command(BaseModel):
    """Pulse command definition."""
    name: str = Field(..., description="Command name")
    qubits: Optional[List[int]] = Field(None, description="Target qubits")
    sequence: Optional[List[Any]] = Field(None, description="Pulse sequence")

    model_config = ConfigDict(extra='allow')


class BackendDefaults(BaseModel):
    """
    Default pulse calibrations and command definitions.

    Contains pulse-level calibration data for OpenPulse backends.
    This corresponds to GET /v1/backends/{id}/defaults response.

    Note: Simulator backends may not support this endpoint.
    """
    qubit_freq_est: List[float] = Field(
        ...,
        description="Estimated qubit frequencies in GHz"
    )
    meas_freq_est: List[float] = Field(
        ...,
        description="Estimated measurement frequencies in GHz"
    )
    buffer: int = Field(..., description="Buffer time in dt units")
    pulse_library: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Library of pulse waveforms"
    )
    cmd_def: List[Command] = Field(
        default_factory=list,
        description="Command definitions mapping gates to pulses"
    )

    model_config = ConfigDict(extra='allow')


# ============================================================================
# Backend List Response Models
# ============================================================================

class BackendDevice(BaseModel):
    """
    Backend summary in list response.

    Lightweight backend information for list endpoint.
    """
    backend_name: str = Field(..., description="Backend identifier")
    backend_version: str = Field(..., description="Backend version")
    operational: bool = Field(..., description="Operational status")
    simulator: bool = Field(default=False, description="Is simulator")
    n_qubits: int = Field(..., description="Number of qubits")
    processor_type: Optional[ProcessorType] = Field(None, description="Processor type")

    # Optional performance metrics
    quantum_volume: Optional[int] = Field(None, description="Quantum volume")
    clops_h: Optional[float] = Field(None, description="CLOPS metric")

    # Queue information (only if fields=wait_time_seconds requested)
    queue_length: Optional[int] = Field(None, description="Current queue length")
    wait_time_seconds: Optional[float] = Field(
        None,
        description="Estimated wait time in seconds"
    )

    # Performance metrics
    performance_metrics: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional performance metrics"
    )

    model_config = ConfigDict(extra='allow')


class BackendsResponse(BaseModel):
    """
    Response for GET /v1/backends.

    Returns list of all backends accessible to the service instance.
    """
    devices: List[BackendDevice] = Field(
        ...,
        description="List of available backends"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "devices": [
                {
                    "backend_name": "ibmq_armonk",
                    "backend_version": "2.4.3",
                    "operational": True,
                    "simulator": False,
                    "n_qubits": 1,
                    "processor_type": {"family": "Canary", "revision": 1.2},
                    "queue_length": 5
                }
            ]
        }
    })


# ============================================================================
# Error Response Models
# ============================================================================

class ErrorDetail(BaseModel):
    """Detailed error information."""
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Standard error response."""
    errors: List[ErrorDetail] = Field(..., description="List of errors")
    trace: Optional[str] = Field(None, description="Error trace ID")
    status_code: int = Field(..., description="HTTP status code")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "errors": [
                {
                    "message": "Backend not found",
                    "code": "BACKEND_NOT_FOUND"
                }
            ],
            "trace": "abc123",
            "status_code": 404
        }
    })

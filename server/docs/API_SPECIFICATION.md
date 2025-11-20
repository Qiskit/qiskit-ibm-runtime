# Qiskit Runtime Backend API Specification

Complete specification for the Qiskit Runtime Backend API server.

**API Version:** 2025-05-01
**Base URL:** `/v1`
**Protocol:** HTTPS
**Content-Type:** `application/json`

## Table of Contents

- [Authentication](#authentication)
- [Headers](#headers)
- [Endpoints](#endpoints)
  - [List Backends](#list-backends)
  - [Get Backend Configuration](#get-backend-configuration)
  - [Get Backend Defaults](#get-backend-defaults)
  - [Get Backend Properties](#get-backend-properties)
  - [Get Backend Status](#get-backend-status)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Examples](#examples)

---

## Authentication

All backend endpoints require authentication using IBM Cloud IAM (Identity and Access Management).

**Required IAM Action:** `quantum-computing.device.read`

### Authentication Headers

```
Authorization: Bearer {IAM_TOKEN}
Service-CRN: {SERVICE_INSTANCE_CRN}
IBM-API-Version: 2025-05-01
```

### Obtaining Credentials

1. **IAM Token**: Obtain from IBM Cloud IAM service
2. **Service CRN**: Your Qiskit Runtime service instance CRN
   - Format: `crn:v1:bluemix:public:quantum-computing:{region}:a/{account_id}:{instance_id}::`

---

## Headers

### Required Headers

| Header | Type | Description | Example |
|--------|------|-------------|---------|
| `Authorization` | string | Bearer token for authentication | `Bearer eyJhbGc...` |
| `Service-CRN` | string | IBM Cloud service instance CRN | `crn:v1:bluemix:...` |
| `IBM-API-Version` | string | API version | `2025-05-01` |

### Supported API Versions

- `2025-05-01` (latest)
- `2025-01-01`
- `2024-01-01`

---

## Endpoints

### List Backends

List all backends available to your service instance.

**Endpoint:** `GET /v1/backends`

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `fields` | string | No | Comma-separated list of additional fields (e.g., `wait_time_seconds`) |

#### Response

**Status:** 200 OK

**Body:**
```json
{
  "devices": [
    {
      "backend_name": "ibm_brisbane",
      "backend_version": "1.0.0",
      "operational": true,
      "simulator": false,
      "n_qubits": 127,
      "processor_type": {
        "family": "Eagle",
        "revision": 1.0
      },
      "quantum_volume": 128,
      "clops_h": 2500.0,
      "queue_length": 15,
      "wait_time_seconds": 120.5,
      "performance_metrics": {
        "median_t1": 125.0,
        "median_t2": 89.0
      }
    }
  ]
}
```

#### Field Details

**Basic Fields (always returned):**
- `backend_name`: Unique identifier
- `backend_version`: Version string
- `operational`: Current operational status
- `simulator`: Whether it's a simulator
- `n_qubits`: Number of qubits
- `processor_type`: Processor family and revision

**Optional Fields (when `fields=wait_time_seconds`):**
- `wait_time_seconds`: Estimated queue wait time
- `queue_length`: Current queue size

#### Error Responses

- `400 Bad Request`: Invalid API version
- `401 Unauthorized`: Invalid or missing authentication
- `403 Forbidden`: Insufficient permissions

---

### Get Backend Configuration

Get complete configuration of a specific backend.

**Endpoint:** `GET /v1/backends/{id}/configuration`

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Backend identifier (e.g., `ibm_brisbane`) |

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `calibration_id` | string | No | Specific calibration ID to retrieve |

#### Response

**Status:** 200 OK

**Body:**
```json
{
  "backend_name": "ibm_brisbane",
  "backend_version": "1.0.0",
  "n_qubits": 127,
  "basis_gates": ["id", "rz", "sx", "x", "cx", "reset"],
  "gates": [
    {
      "name": "cx",
      "parameters": [],
      "qasm_def": "gate cx q1,q2 { CX q1,q2; }",
      "coupling_map": [[0, 1], [1, 0], [1, 2]],
      "conditional": true,
      "description": "CNOT gate"
    }
  ],
  "local": false,
  "simulator": false,
  "conditional": true,
  "open_pulse": true,
  "memory": true,
  "max_shots": 100000,
  "max_experiments": 300,
  "coupling_map": [[0, 1], [1, 2], [2, 3]],
  "dynamic_reprate_enabled": true,
  "rep_delay_range": [0.0, 500.0],
  "default_rep_delay": 250.0,
  "processor_type": {
    "family": "Eagle",
    "revision": 1.0
  },
  "dt": 0.2222e-9,
  "dtm": 0.2222e-9,
  "parametric_pulses": ["gaussian", "gaussian_square", "drag"],
  "u_channel_lo": [
    [
      {"q": 0, "scale": [1.0, 0.0]},
      {"q": 1, "scale": [1.0, 0.0]}
    ]
  ],
  "meas_map": [[0, 1, 2], [3, 4, 5]],
  "quantum_volume": 128,
  "clops_h": 2500.0,
  "supported_features": ["qasm3", "pulse_gates", "dynamic_circuits"],
  "online_date": "2023-12-01T00:00:00Z"
}
```

#### Key Configuration Fields

**Quantum System:**
- `n_qubits`: Number of qubits
- `basis_gates`: Supported gate set
- `gates`: Detailed gate definitions
- `coupling_map`: Qubit connectivity

**Capabilities:**
- `simulator`: Is simulator
- `conditional`: Supports conditional operations
- `open_pulse`: Supports OpenPulse
- `memory`: Supports classical memory
- `supported_features`: List of advanced features

**Timing:**
- `dt`: System time resolution (seconds)
- `rep_delay_range`: Repetition delay range (μs)
- `default_rep_delay`: Default repetition delay (μs)

**Performance:**
- `quantum_volume`: Quantum volume metric
- `clops_h`: Circuit Layer Operations Per Second

#### Error Responses

- `404 Not Found`: Backend doesn't exist
- `400 Bad Request`: Invalid calibration_id

---

### Get Backend Defaults

Get default pulse calibrations for OpenPulse backends.

**Endpoint:** `GET /v1/backends/{id}/defaults`

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Backend identifier |

#### Response

**Status:** 200 OK

**Body:**
```json
{
  "qubit_freq_est": [4.971, 4.823, 5.102],
  "meas_freq_est": [6.523, 6.789, 6.456],
  "buffer": 10,
  "pulse_library": [
    {
      "name": "gaussian_pulse",
      "samples": [[0.0, 0.0], [0.1, 0.0], [0.5, 0.0]]
    }
  ],
  "cmd_def": [
    {
      "name": "x",
      "qubits": [0],
      "sequence": [...]
    }
  ]
}
```

#### Field Details

- `qubit_freq_est`: Estimated qubit frequencies (GHz)
- `meas_freq_est`: Estimated measurement frequencies (GHz)
- `buffer`: Buffer time in dt units
- `pulse_library`: Pulse waveform definitions
- `cmd_def`: Gate-to-pulse mappings

#### Notes

- **Not supported by simulators** - will return 404
- Only available for OpenPulse-enabled backends
- Required for pulse-level programming

#### Error Responses

- `404 Not Found`: Backend doesn't exist or doesn't support defaults
- `501 Not Implemented`: Backend is a simulator

---

### Get Backend Properties

Get calibration properties for qubits and gates.

**Endpoint:** `GET /v1/backends/{id}/properties`

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Backend identifier |

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `calibration_id` | string | No | Specific calibration ID |
| `updated_before` | datetime | No | Get properties before this timestamp (ISO 8601) |

#### Response

**Status:** 200 OK

**Body:**
```json
{
  "backend_name": "ibm_brisbane",
  "backend_version": "1.0.0",
  "last_update_date": "2025-11-20T10:46:00Z",
  "qubits": [
    [
      {
        "date": "2025-11-20T10:46:00Z",
        "name": "T1",
        "unit": "us",
        "value": 125.3
      },
      {
        "date": "2025-11-20T10:46:00Z",
        "name": "T2",
        "unit": "us",
        "value": 89.2
      },
      {
        "date": "2025-11-20T10:46:00Z",
        "name": "frequency",
        "unit": "GHz",
        "value": 4.971
      },
      {
        "date": "2025-11-20T10:46:00Z",
        "name": "readout_error",
        "unit": "",
        "value": 0.0123
      },
      {
        "date": "2025-11-20T10:46:00Z",
        "name": "prob_meas0_prep1",
        "unit": "",
        "value": 0.0089
      },
      {
        "date": "2025-11-20T10:46:00Z",
        "name": "prob_meas1_prep0",
        "unit": "",
        "value": 0.0156
      }
    ]
  ],
  "gates": [
    {
      "qubits": [0, 1],
      "gate": "cx",
      "parameters": [
        {
          "date": "2025-11-20T10:46:00Z",
          "name": "gate_error",
          "unit": "",
          "value": 0.0043
        },
        {
          "date": "2025-11-20T10:46:00Z",
          "name": "gate_length",
          "unit": "ns",
          "value": 467.0
        }
      ]
    }
  ],
  "general": []
}
```

#### Property Types

**Qubit Properties:**
- `T1`: Relaxation time (μs)
- `T2`: Dephasing time (μs)
- `frequency`: Qubit frequency (GHz)
- `readout_error`: Measurement error rate
- `prob_meas0_prep1`: P(measure 0 | prepared 1)
- `prob_meas1_prep0`: P(measure 1 | prepared 0)

**Gate Properties:**
- `gate_error`: Gate error rate
- `gate_length`: Gate duration (ns)

#### Error Responses

- `404 Not Found`: Backend doesn't exist
- `400 Bad Request`: Invalid datetime format

---

### Get Backend Status

Get real-time operational status.

**Endpoint:** `GET /v1/backends/{id}/status`

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Backend identifier |

#### Response

**Status:** 200 OK

**Body:**
```json
{
  "backend_name": "ibm_brisbane",
  "backend_version": "1.0.0",
  "state": true,
  "status": "operational",
  "length_queue": 15
}
```

#### Field Details

- `backend_name`: Backend identifier
- `backend_version`: Version string
- `state`: Operational state (true/false)
- `status`: Status message ("operational", "maintenance", "down")
- `length_queue`: Number of jobs in queue

#### Status Values

- `"operational"`: Backend is running normally
- `"maintenance"`: Scheduled maintenance
- `"down"`: Backend unavailable

#### Error Responses

- `404 Not Found`: Backend doesn't exist

---

## Data Models

### Core Models

#### BackendConfiguration

Complete backend configuration including:
- Quantum system properties (qubits, gates, topology)
- Capabilities (OpenPulse, conditional, memory)
- Timing constraints (dt, rep_delay)
- Performance metrics (quantum_volume, CLOPS)
- Processor information

See `src/models.py:BackendConfiguration` for complete schema.

#### BackendProperties

Time-stamped calibration data:
- Per-qubit properties (T1, T2, frequency, readout_error)
- Per-gate properties (gate_error, gate_length)
- Measurement timestamp

See `src/models.py:BackendProperties` for complete schema.

#### BackendStatus

Real-time status:
- Operational state
- Queue information
- Status message

See `src/models.py:BackendStatus` for complete schema.

#### BackendDefaults

Pulse-level calibrations:
- Qubit/measurement frequencies
- Pulse library
- Gate-to-pulse command definitions

See `src/models.py:BackendDefaults` for complete schema.

### Nested Models

#### ProcessorType
```python
{
  "family": str,      # e.g., "Eagle", "Falcon", "Hummingbird"
  "revision": float   # e.g., 1.0, 1.2
}
```

#### GateConfig
```python
{
  "name": str,
  "parameters": List[str],
  "qasm_def": Optional[str],
  "coupling_map": Optional[List[List[int]]],
  "conditional": bool,
  "description": Optional[str]
}
```

#### Nduv (Name-Date-Unit-Value)
```python
{
  "date": datetime,
  "name": str,
  "unit": str,
  "value": float
}
```

---

## Error Handling

### Error Response Format

All errors return:

```json
{
  "errors": [
    {
      "message": "Error description",
      "code": "ERROR_CODE"
    }
  ],
  "trace": "trace-id",
  "status_code": 404
}
```

### HTTP Status Codes

| Code | Description | When It Occurs |
|------|-------------|----------------|
| 200 | OK | Successful request |
| 400 | Bad Request | Invalid parameters or API version |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Backend doesn't exist |
| 500 | Internal Server Error | Server error |
| 501 | Not Implemented | Feature not supported |

### Common Error Codes

- `BACKEND_NOT_FOUND`: Backend ID doesn't exist
- `INVALID_API_VERSION`: Unsupported API version
- `INVALID_CALIBRATION_ID`: Calibration not found
- `AUTHENTICATION_FAILED`: Invalid token
- `INSUFFICIENT_PERMISSIONS`: IAM action not authorized

---

## Examples

### Example 1: List All Backends

```bash
curl -X GET "https://api.quantum.ibm.com/v1/backends" \
  -H "Authorization: Bearer ${IAM_TOKEN}" \
  -H "Service-CRN: ${SERVICE_CRN}" \
  -H "IBM-API-Version: 2025-05-01"
```

Response:
```json
{
  "devices": [
    {
      "backend_name": "ibm_brisbane",
      "backend_version": "1.0.0",
      "operational": true,
      "simulator": false,
      "n_qubits": 127,
      "processor_type": {
        "family": "Eagle",
        "revision": 1.0
      }
    }
  ]
}
```

### Example 2: Get Backend Configuration

```bash
curl -X GET "https://api.quantum.ibm.com/v1/backends/ibm_brisbane/configuration" \
  -H "Authorization: Bearer ${IAM_TOKEN}" \
  -H "Service-CRN: ${SERVICE_CRN}" \
  -H "IBM-API-Version: 2025-05-01"
```

### Example 3: Get Backend Properties with Calibration ID

```bash
curl -X GET "https://api.quantum.ibm.com/v1/backends/ibm_brisbane/properties?calibration_id=abc123" \
  -H "Authorization: Bearer ${IAM_TOKEN}" \
  -H "Service-CRN: ${SERVICE_CRN}" \
  -H "IBM-API-Version: 2025-05-01"
```

### Example 4: Get Backend Status

```bash
curl -X GET "https://api.quantum.ibm.com/v1/backends/ibm_brisbane/status" \
  -H "Authorization: Bearer ${IAM_TOKEN}" \
  -H "Service-CRN: ${SERVICE_CRN}" \
  -H "IBM-API-Version: 2025-05-01"
```

Response:
```json
{
  "backend_name": "ibm_brisbane",
  "backend_version": "1.0.0",
  "state": true,
  "status": "operational",
  "length_queue": 15
}
```

### Example 5: List Backends with Wait Time

```bash
curl -X GET "https://api.quantum.ibm.com/v1/backends?fields=wait_time_seconds" \
  -H "Authorization: Bearer ${IAM_TOKEN}" \
  -H "Service-CRN: ${SERVICE_CRN}" \
  -H "IBM-API-Version: 2025-05-01"
```

---

## Implementation Notes

### Calibration Versioning

Backends are calibrated regularly. Each calibration has a unique ID:
- Use `calibration_id` to retrieve specific calibration data
- Without `calibration_id`, returns latest calibration
- Historical data available via `updated_before` parameter

### Caching Recommendations

Properties and configuration change infrequently:
- Cache configuration data (rarely changes)
- Cache properties with TTL of ~5 minutes
- Status should not be cached (real-time data)

### Rate Limiting

Not specified in API documentation. Implement sensible defaults:
- Authenticated: 100 req/min per user
- Burst: 20 req/10sec

### Regional Endpoints

Support for EU region:
- EU-DE: `eu-de.quantum.cloud.ibm.com`
- US: `quantum.cloud.ibm.com`

### Audit Events

All endpoints generate audit events:
- Event type: `quantum-computing.device.read`
- Includes: User, backend_id, timestamp, result

---

## Type Reference

For complete type definitions, see:
- `server/src/models.py` - Pydantic models
- `server/src/main.py` - FastAPI endpoints

For client-side types, see:
- `qiskit_ibm_runtime/models/` - Client data models
- `qiskit_ibm_runtime/api/` - API client implementation

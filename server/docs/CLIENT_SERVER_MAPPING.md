# Client-Server API Mapping

This document maps the Qiskit Runtime client implementation to the server API endpoints.

## Overview

The client code is located in `qiskit_ibm_runtime/` and makes HTTP requests to the backend API. This document shows how client methods correspond to server endpoints.

## Client API Methods → Server Endpoints

### Backend Listing

**Client Method:**
```python
# File: qiskit_ibm_runtime/api/clients/runtime.py
def list_backends(self) -> List[Dict[str, Any]]:
    """Return IBM backends available for this service instance."""
    return self._api.backends()["devices"]
```

**REST Call:**
```python
# File: qiskit_ibm_runtime/api/rest/runtime.py
def backends(self, timeout: Optional[float] = None) -> Dict[str, Any]:
    url = self.get_url("backends")  # → "/backends"
    return self.session.get(url, timeout=timeout, headers=self._HEADER_JSON_ACCEPT).json()
```

**Server Endpoint:**
```
GET /v1/backends
→ Returns: BackendsResponse
```

---

### Backend Configuration

**Client Method:**
```python
# File: qiskit_ibm_runtime/api/clients/runtime.py
def backend_configuration(
    self, backend_name: str, refresh: bool = False, calibration_id: Optional[str] = None
) -> Dict[str, Any]:
    """Return the configuration of the IBM backend."""
    return self._api.backend(backend_name).configuration(calibration_id=calibration_id)
```

**REST Call:**
```python
# File: qiskit_ibm_runtime/api/rest/cloud_backend.py
def configuration(self, calibration_id: Optional[str] = None) -> Dict[str, Any]:
    url = self.get_url("configuration")  # → "/backends/{backend_name}/configuration"
    params = {"calibration_id": calibration_id} if calibration_id else {}
    return self.session.get(url, params=params).json()
```

**Server Endpoint:**
```
GET /v1/backends/{id}/configuration?calibration_id={calibration_id}
→ Returns: BackendConfiguration
```

**Data Transformation:**
```python
# File: qiskit_ibm_runtime/utils/backend_decoder.py
def configuration_from_server_data(raw_config: Dict) -> QasmBackendConfiguration:
    """Convert raw server JSON to QasmBackendConfiguration object."""
```

---

### Backend Properties

**Client Method:**
```python
# File: qiskit_ibm_runtime/api/clients/runtime.py
def backend_properties(
    self, backend_name: str, datetime: Optional[python_datetime] = None,
    calibration_id: Optional[str] = None
) -> Dict[str, Any]:
    """Return the properties of the IBM backend."""
    return self._api.backend(backend_name).properties(datetime=datetime, calibration_id=calibration_id)
```

**REST Call:**
```python
# File: qiskit_ibm_runtime/api/rest/cloud_backend.py
def properties(
    self, datetime: Optional[python_datetime] = None,
    calibration_id: Optional[str] = None
) -> Dict[str, Any]:
    url = self.get_url("properties")  # → "/backends/{backend_name}/properties"
    params = {}
    if datetime:
        params["updated_before"] = datetime.isoformat()
    if calibration_id:
        params["calibration_id"] = calibration_id
    return self.session.get(url, params=params).json()
```

**Server Endpoint:**
```
GET /v1/backends/{id}/properties?calibration_id={id}&updated_before={datetime}
→ Returns: BackendProperties
```

**Data Transformation:**
```python
# File: qiskit_ibm_runtime/utils/backend_decoder.py
def properties_from_server_data(properties: Dict) -> BackendProperties:
    """Convert raw server JSON to BackendProperties object."""
```

---

### Backend Status

**Client Method:**
```python
# File: qiskit_ibm_runtime/api/clients/runtime.py
def backend_status(self, backend_name: str) -> Dict[str, Any]:
    """Return the status of the IBM backend."""
    return self._api.backend(backend_name).status()
```

**REST Call:**
```python
# File: qiskit_ibm_runtime/api/rest/cloud_backend.py
def status(self) -> Dict[str, Any]:
    url = self.get_url("status")  # → "/backends/{backend_name}/status"
    return self.session.get(url).json()
```

**Server Endpoint:**
```
GET /v1/backends/{id}/status
→ Returns: BackendStatus
```

**Data Model:**
```python
# File: qiskit_ibm_runtime/models/backend_status.py
class BackendStatus:
    backend_name: str
    backend_version: str
    operational: bool       # from "state" field
    pending_jobs: int       # from "length_queue" field
    status_msg: str         # from "status" field
```

---

### Backend Defaults

**Note:** Not directly exposed in the main runtime client, but available through the REST adapter.

**REST Call:**
```python
# File: qiskit_ibm_runtime/api/rest/cloud_backend.py
# (Would need to add this method)
def defaults(self) -> Dict[str, Any]:
    url = self.get_url("defaults")  # → "/backends/{backend_name}/defaults"
    return self.session.get(url).json()
```

**Server Endpoint:**
```
GET /v1/backends/{id}/defaults
→ Returns: BackendDefaults
```

---

## Data Model Mapping

### Client Models → Server Models

| Client Model | File | Server Model | Mapping Notes |
|-------------|------|--------------|---------------|
| `QasmBackendConfiguration` | `models/backend_configuration.py` | `BackendConfiguration` | Direct mapping |
| `BackendProperties` | `models/backend_properties.py` | `BackendProperties` | Direct mapping |
| `BackendStatus` | `models/backend_status.py` | `BackendStatus` | Field name aliases:<br>`state` → `operational`<br>`length_queue` → `pending_jobs`<br>`status` → `status_msg` |
| `GateConfig` | `models/backend_configuration.py` | `GateConfig` | Direct mapping |
| `GateProperties` | `models/backend_properties.py` | `GateProperties` | Direct mapping |
| `Nduv` | `models/backend_properties.py` | `Nduv` | Direct mapping |
| `UchannelLO` | `models/backend_configuration.py` | `UchannelLO` | Complex number as `[real, imag]` |
| N/A | N/A | `BackendDefaults` | New model for defaults endpoint |
| N/A | N/A | `BackendsResponse` | Wrapper for list response |
| N/A | N/A | `BackendDevice` | Summary for list items |

---

## Field Name Differences

### BackendStatus

**Client → Server:**
- `state` (bool) → `operational` (bool)
- `length_queue` (int) → `pending_jobs` (int)
- `status` (str) → `status_msg` (str)

The server Pydantic model uses `alias` to support both names:
```python
class BackendStatus(BaseModel):
    operational: bool = Field(..., alias="state")
    status_msg: str = Field(..., alias="status")
    pending_jobs: int = Field(..., alias="length_queue")
```

### Complex Numbers

**Client Format:**
```python
u_channel_lo = [[{"q": 0, "scale": [1.0, 0.0]}]]  # [real, imag]
```

**Encoding/Decoding:**
```python
# File: qiskit_ibm_runtime/utils/backend_encoder.py
class BackendEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, complex):
            return [obj.real, obj.imag]

# File: qiskit_ibm_runtime/utils/backend_decoder.py
def decode_backend_configuration(config):
    for u_channel in config.get("u_channel_lo", []):
        for u_lo_config in u_channel:
            if "scale" in u_lo_config and isinstance(u_lo_config["scale"], list):
                u_lo_config["scale"] = complex(
                    u_lo_config["scale"][0],
                    u_lo_config["scale"][1]
                )
```

---

## HTTP Request Flow

### Typical Request Sequence

1. **Client creates request:**
   ```python
   client = RuntimeClient(...)
   config = client.backend_configuration("ibm_brisbane")
   ```

2. **REST adapter builds URL:**
   ```python
   # CloudBackend.__init__ sets base URL
   base_url = "/backends/ibm_brisbane"
   # configuration() appends path
   url = base_url + "/configuration"
   # Final: "/backends/ibm_brisbane/configuration"
   ```

3. **Session adds headers:**
   ```python
   headers = {
       "Authorization": f"Bearer {token}",
       "Service-CRN": service_crn,
       "Accept": "application/json"
   }
   ```

4. **Server receives:**
   ```
   GET /v1/backends/ibm_brisbane/configuration
   Headers:
     Authorization: Bearer ...
     Service-CRN: crn:...
     IBM-API-Version: 2025-05-01
   ```

5. **Server responds:**
   ```json
   {
     "backend_name": "ibm_brisbane",
     "n_qubits": 127,
     ...
   }
   ```

6. **Client decodes response:**
   ```python
   # backend_decoder.py transforms JSON to model
   config_obj = configuration_from_server_data(response_json)
   # Returns QasmBackendConfiguration instance
   ```

---

## Authentication Flow

### Client Side

```python
# File: qiskit_ibm_runtime/api/rest/base.py
class RestAdapterBase:
    def __init__(self, session: RetrySession, ...):
        self.session = session  # Has auth token

# File: qiskit_ibm_runtime/api/session.py
class RetrySession(FuturesSession):
    def __init__(self, auth, ...):
        self._auth = auth  # CloudAuth or similar
```

### Server Side

```python
# File: server/src/main.py
async def verify_authorization(
    authorization: str = Header(...),
    service_crn: str = Header(..., alias="Service-CRN")
):
    # Validates Bearer token format
    # In real implementation: validate IAM token
    # Check service instance permissions
```

---

## URL Structure

### Client URL Construction

```python
# Base URL from service
base_url = "https://quantum.cloud.ibm.com"

# Runtime adapter adds prefix
runtime = Runtime(session, "/v1")

# Backend endpoints
backends_url = base_url + "/v1" + "/backends"
# → "https://quantum.cloud.ibm.com/v1/backends"

backend_url = base_url + "/v1" + f"/backends/{backend_name}"
# → "https://quantum.cloud.ibm.com/v1/backends/ibm_brisbane"

config_url = backend_url + "/configuration"
# → "https://quantum.cloud.ibm.com/v1/backends/ibm_brisbane/configuration"
```

### Server URL Routes

```python
@app.get("/v1/backends")                         # List
@app.get("/v1/backends/{backend_id}/configuration")  # Config
@app.get("/v1/backends/{backend_id}/defaults")       # Defaults
@app.get("/v1/backends/{backend_id}/properties")     # Properties
@app.get("/v1/backends/{backend_id}/status")         # Status
```

---

## Query Parameters

### Configuration Endpoint

**Client:**
```python
params = {"calibration_id": calibration_id} if calibration_id else {}
response = session.get(url, params=params)
```

**Server:**
```python
calibration_id: Optional[str] = Query(None, description="...")
```

### Properties Endpoint

**Client:**
```python
params = {}
if datetime:
    params["updated_before"] = datetime.isoformat()
if calibration_id:
    params["calibration_id"] = calibration_id
response = session.get(url, params=params)
```

**Server:**
```python
calibration_id: Optional[str] = Query(None, ...)
updated_before: Optional[datetime] = Query(None, ...)
```

---

## Response Transformations

### Example: Backend Status

**Server JSON Response:**
```json
{
  "backend_name": "ibm_brisbane",
  "backend_version": "1.0.0",
  "state": true,
  "status": "operational",
  "length_queue": 15
}
```

**Client Model (after deserialization):**
```python
BackendStatus(
    backend_name="ibm_brisbane",
    backend_version="1.0.0",
    operational=True,        # from "state"
    status_msg="operational", # from "status"
    pending_jobs=15          # from "length_queue"
)
```

**Conversion:**
```python
# File: qiskit_ibm_runtime/models/backend_status.py
@classmethod
def from_dict(cls, data: Dict) -> "BackendStatus":
    return cls(
        backend_name=data["backend_name"],
        backend_version=data["backend_version"],
        operational=data["state"],
        pending_jobs=data["length_queue"],
        status_msg=data["status"]
    )
```

---

## Implementation Checklist

When implementing server endpoints, ensure:

### 1. URL Paths Match Client Expectations
- [ ] `/v1/backends` (not `/backends`)
- [ ] `/v1/backends/{id}/...` (not `/backends/{id}`)
- [ ] Path parameter names match client usage

### 2. Field Names Match or Have Aliases
- [ ] `BackendStatus` uses correct field names or aliases
- [ ] Complex numbers as `[real, imag]` arrays
- [ ] Datetime in ISO 8601 format

### 3. Query Parameters Supported
- [ ] `calibration_id` for configuration and properties
- [ ] `updated_before` for properties (datetime)
- [ ] `fields` for backends list

### 4. Headers Required
- [ ] `Authorization: Bearer {token}`
- [ ] `Service-CRN: {crn}`
- [ ] `IBM-API-Version: {version}`

### 5. Error Responses
- [ ] 404 for backend not found
- [ ] 400 for invalid parameters
- [ ] 401 for auth failures
- [ ] Proper error JSON structure

### 6. Data Validation
- [ ] All required fields present
- [ ] Types match Pydantic models
- [ ] Arrays have correct structure
- [ ] Nested objects validated

---

## Testing Strategy

### Unit Tests

Test each endpoint independently:
```python
# Test backend list
response = client.get("/v1/backends", headers=auth_headers)
assert response.status_code == 200
assert "devices" in response.json()

# Test backend configuration
response = client.get(
    "/v1/backends/ibm_brisbane/configuration",
    headers=auth_headers
)
assert response.status_code == 200
config = response.json()
assert config["backend_name"] == "ibm_brisbane"
assert "n_qubits" in config
```

### Integration Tests

Test with actual client:
```python
# Using real qiskit_ibm_runtime client
from qiskit_ibm_runtime import QiskitRuntimeService

# Point to mock server
service = QiskitRuntimeService(url="http://localhost:8000")

# Test methods
backends = service.backends()
backend = service.backend("ibm_brisbane")
config = backend.configuration()
properties = backend.properties()
status = backend.status()
```

### Contract Tests

Ensure server responses match client expectations:
```python
# Validate response schema
from pydantic import ValidationError

response_json = server.get_backend_configuration("ibm_brisbane")
try:
    BackendConfiguration(**response_json)  # Should not raise
except ValidationError as e:
    print(f"Schema mismatch: {e}")
```

---

## Summary

**Key Takeaways:**

1. **5 Main Endpoints:** list, configuration, defaults, properties, status
2. **Direct Model Mapping:** Most models map 1:1 between client and server
3. **Field Name Aliases:** Use Pydantic `alias` for `BackendStatus` field names
4. **Complex Number Encoding:** Always as `[real, imag]` arrays
5. **Query Parameters:** Support `calibration_id`, `updated_before`, `fields`
6. **Authentication:** Require Bearer token, Service-CRN, and API version headers

For implementation details, see:
- Client code: `qiskit_ibm_runtime/api/`
- Server code: `server/src/`
- Models: `server/src/models.py`
- API docs: `server/docs/API_SPECIFICATION.md`

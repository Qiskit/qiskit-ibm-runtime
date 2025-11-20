# Development Guide

Guide for implementing the Qiskit Runtime Backend API server.

## Quick Start

### 1. Setup Development Environment

```bash
cd server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the Server

```bash
# Development mode with auto-reload
python -m src.main

# Or using uvicorn directly
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Access Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

---

## Architecture Overview

```
server/
├── src/
│   ├── __init__.py
│   ├── main.py          # FastAPI app & endpoints
│   ├── models.py        # Pydantic models
│   ├── database.py      # Database layer (to implement)
│   ├── auth.py          # Authentication logic (to implement)
│   └── services/
│       └── backend_service.py  # Business logic (to implement)
├── tests/
│   ├── test_endpoints.py
│   ├── test_models.py
│   └── fixtures/        # Test data
└── docs/
    ├── API_SPECIFICATION.md
    └── CLIENT_SERVER_MAPPING.md
```

---

## Implementation Steps

### Phase 1: Mock Data Layer

Create a simple in-memory data store for testing.

**Create `src/database.py`:**

```python
"""Mock database for backend data."""

from typing import Dict, List, Optional
from datetime import datetime
from .models import (
    BackendConfiguration,
    BackendProperties,
    BackendStatus,
    BackendDefaults,
    BackendDevice,
)

class MockDatabase:
    """In-memory mock database."""

    def __init__(self):
        self._backends: Dict[str, BackendConfiguration] = {}
        self._properties: Dict[str, BackendProperties] = {}
        self._status: Dict[str, BackendStatus] = {}
        self._defaults: Dict[str, BackendDefaults] = {}
        self._load_sample_data()

    def _load_sample_data(self):
        """Load sample backend data."""
        # TODO: Load from JSON files or generate mock data
        pass

    def list_backends(self, fields: Optional[str] = None) -> List[BackendDevice]:
        """List all backends."""
        # Convert configurations to device summaries
        devices = []
        for backend_id, config in self._backends.items():
            device = BackendDevice(
                backend_name=config.backend_name,
                backend_version=config.backend_version,
                operational=self._status[backend_id].operational,
                simulator=config.simulator,
                n_qubits=config.n_qubits,
                processor_type=config.processor_type,
                quantum_volume=config.quantum_volume,
                clops_h=config.clops_h,
            )

            # Add optional fields
            if fields and "wait_time_seconds" in fields:
                device.queue_length = self._status[backend_id].pending_jobs
                device.wait_time_seconds = self._calculate_wait_time(backend_id)

            devices.append(device)

        return devices

    def get_backend_configuration(
        self,
        backend_id: str,
        calibration_id: Optional[str] = None
    ) -> Optional[BackendConfiguration]:
        """Get backend configuration."""
        # TODO: Handle calibration_id
        return self._backends.get(backend_id)

    def get_backend_properties(
        self,
        backend_id: str,
        calibration_id: Optional[str] = None,
        updated_before: Optional[datetime] = None
    ) -> Optional[BackendProperties]:
        """Get backend properties."""
        # TODO: Handle calibration_id and updated_before
        return self._properties.get(backend_id)

    def get_backend_status(self, backend_id: str) -> Optional[BackendStatus]:
        """Get backend status."""
        return self._status.get(backend_id)

    def get_backend_defaults(self, backend_id: str) -> Optional[BackendDefaults]:
        """Get backend defaults."""
        # Simulators don't have defaults
        config = self._backends.get(backend_id)
        if config and config.simulator:
            return None
        return self._defaults.get(backend_id)

    def _calculate_wait_time(self, backend_id: str) -> float:
        """Calculate estimated wait time."""
        # Simple calculation: queue_length * average_job_time
        status = self._status.get(backend_id)
        if not status:
            return 0.0
        return status.pending_jobs * 120.0  # Assume 2 min per job


# Global database instance
db = MockDatabase()
```

### Phase 2: Implement Endpoints

Update `src/main.py` to use the database:

```python
from .database import db

@app.get("/v1/backends", response_model=BackendsResponse)
async def list_backends(
    fields: Optional[str] = Query(None, ...),
    api_version: str = Depends(verify_api_version),
    auth: dict = Depends(verify_authorization),
) -> BackendsResponse:
    """List all available backends."""
    devices = db.list_backends(fields=fields)
    return BackendsResponse(devices=devices)

@app.get("/v1/backends/{backend_id}/configuration", response_model=BackendConfiguration)
async def get_backend_configuration(
    backend_id: str = Path(..., alias="id"),
    calibration_id: Optional[str] = Query(None, ...),
    api_version: str = Depends(verify_api_version),
    auth: dict = Depends(verify_authorization),
) -> BackendConfiguration:
    """Get backend configuration."""
    config = db.get_backend_configuration(backend_id, calibration_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Backend '{backend_id}' not found")
    return config

# Implement other endpoints similarly...
```

### Phase 3: Add Authentication

**Create `src/auth.py`:**

```python
"""Authentication and authorization."""

from typing import Dict
from fastapi import HTTPException
import jwt  # PyJWT library

class IAMValidator:
    """Validates IBM Cloud IAM tokens."""

    def __init__(self, public_key: str):
        self.public_key = public_key

    def validate_token(self, token: str) -> Dict:
        """Validate IAM token."""
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"]
            )
            return payload
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid token: {str(e)}"
            )

    def check_permission(
        self,
        token_payload: Dict,
        service_crn: str,
        action: str
    ) -> bool:
        """Check if token has required IAM action."""
        # TODO: Implement IAM action checking
        # Check if token has 'quantum-computing.device.read' for service_crn
        return True


# Update verify_authorization dependency
iam_validator = IAMValidator(public_key="...")  # Load from config

async def verify_authorization(
    authorization: str = Header(...),
    service_crn: str = Header(..., alias="Service-CRN")
) -> dict:
    """Verify authorization."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.replace("Bearer ", "")
    payload = iam_validator.validate_token(token)

    # Check IAM action
    if not iam_validator.check_permission(payload, service_crn, "quantum-computing.device.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return {"token_payload": payload, "service_crn": service_crn}
```

### Phase 4: Add Real Database

Replace mock database with PostgreSQL/MongoDB:

```python
"""Real database implementation."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Or use MongoDB
from motor.motor_asyncio import AsyncIOMotorClient

class BackendDatabase:
    """Production database."""

    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)
        self.Session = sessionmaker(bind=self.engine)

    async def list_backends(self, fields: Optional[str] = None):
        """List backends from database."""
        # Implement SQL queries
        pass
```

---

## Data Generation

### Creating Sample Backend Data

**Create `scripts/generate_sample_data.py`:**

```python
"""Generate sample backend data for testing."""

import json
from datetime import datetime, timedelta
from pathlib import Path

def generate_backend_configuration(backend_name: str, n_qubits: int):
    """Generate sample configuration."""
    return {
        "backend_name": backend_name,
        "backend_version": "1.0.0",
        "n_qubits": n_qubits,
        "basis_gates": ["id", "rz", "sx", "x", "cx", "reset"],
        "gates": [
            {
                "name": "cx",
                "parameters": [],
                "qasm_def": "gate cx q1,q2 { CX q1,q2; }",
                "coupling_map": [[i, i+1] for i in range(n_qubits-1)],
                "conditional": True
            }
        ],
        "simulator": False,
        "local": False,
        "conditional": True,
        "open_pulse": True,
        "memory": True,
        "max_shots": 100000,
        "coupling_map": [[i, i+1] for i in range(n_qubits-1)],
        "processor_type": {
            "family": "Eagle",
            "revision": 1.0
        },
        "dt": 0.2222e-9,
        "online_date": datetime.utcnow().isoformat()
    }

def generate_backend_properties(backend_name: str, n_qubits: int):
    """Generate sample properties."""
    qubits = []
    for i in range(n_qubits):
        qubit_props = [
            {
                "date": datetime.utcnow().isoformat(),
                "name": "T1",
                "unit": "us",
                "value": 100 + i * 10
            },
            {
                "date": datetime.utcnow().isoformat(),
                "name": "T2",
                "unit": "us",
                "value": 80 + i * 5
            }
        ]
        qubits.append(qubit_props)

    return {
        "backend_name": backend_name,
        "backend_version": "1.0.0",
        "last_update_date": datetime.utcnow().isoformat(),
        "qubits": qubits,
        "gates": [],
        "general": []
    }

def generate_backend_status(backend_name: str):
    """Generate sample status."""
    return {
        "backend_name": backend_name,
        "backend_version": "1.0.0",
        "state": True,
        "status": "operational",
        "length_queue": 5
    }

if __name__ == "__main__":
    backends = [
        ("ibm_brisbane", 127),
        ("ibm_kyoto", 127),
        ("ibm_osaka", 127),
    ]

    output_dir = Path("server/data")
    output_dir.mkdir(exist_ok=True)

    for backend_name, n_qubits in backends:
        config = generate_backend_configuration(backend_name, n_qubits)
        properties = generate_backend_properties(backend_name, n_qubits)
        status = generate_backend_status(backend_name)

        with open(output_dir / f"{backend_name}_config.json", "w") as f:
            json.dump(config, f, indent=2)

        with open(output_dir / f"{backend_name}_properties.json", "w") as f:
            json.dump(properties, f, indent=2)

        with open(output_dir / f"{backend_name}_status.json", "w") as f:
            json.dump(status, f, indent=2)

    print(f"Generated data for {len(backends)} backends")
```

Run:
```bash
python scripts/generate_sample_data.py
```

---

## Testing

### Unit Tests

**Create `tests/test_endpoints.py`:**

```python
"""Test API endpoints."""

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_check():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_list_backends_no_auth():
    """Test list backends without auth."""
    response = client.get("/v1/backends")
    assert response.status_code == 422  # Missing headers

def test_list_backends_with_auth():
    """Test list backends with auth."""
    headers = {
        "Authorization": "Bearer test-token",
        "Service-CRN": "crn:test",
        "IBM-API-Version": "2025-05-01"
    }
    response = client.get("/v1/backends", headers=headers)
    assert response.status_code in [200, 501]  # 200 when implemented

def test_backend_configuration():
    """Test get backend configuration."""
    headers = {
        "Authorization": "Bearer test-token",
        "Service-CRN": "crn:test",
        "IBM-API-Version": "2025-05-01"
    }
    response = client.get(
        "/v1/backends/ibm_brisbane/configuration",
        headers=headers
    )
    assert response.status_code in [200, 404, 501]
```

Run tests:
```bash
pytest tests/ -v
```

---

## Configuration Management

### Environment Variables

**Create `.env`:**

```bash
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Database
DATABASE_URL=postgresql://user:pass@localhost/qiskit_runtime

# Authentication
IAM_PUBLIC_KEY_URL=https://iam.cloud.ibm.com/identity/keys
JWT_ALGORITHM=RS256

# Logging
LOG_LEVEL=INFO
```

**Create `src/config.py`:**

```python
"""Configuration management."""

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings."""

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    database_url: str

    iam_public_key_url: str
    jwt_algorithm: str = "RS256"

    log_level: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Deployment

### Docker

**Create `Dockerfile`:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Create `docker-compose.yml`:**

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db/qiskit
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=qiskit
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Build and run:
```bash
docker-compose up --build
```

---

## Logging and Monitoring

### Add Logging

```python
import logging
from src.config import settings

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# In endpoints
@app.get("/v1/backends")
async def list_backends(...):
    logger.info("Listing backends", extra={"user": auth["token_payload"]["sub"]})
    # ...
```

### Add Metrics

```python
from prometheus_client import Counter, Histogram
from starlette_prometheus import metrics, PrometheusMiddleware

app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", metrics)

# Custom metrics
backend_requests = Counter(
    'backend_requests_total',
    'Total backend requests',
    ['method', 'endpoint']
)

@app.get("/v1/backends")
async def list_backends(...):
    backend_requests.labels(method='GET', endpoint='/backends').inc()
    # ...
```

---

## Performance Optimization

### Caching

```python
from functools import lru_cache
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

# Initialize cache
@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")

# Cache responses
@app.get("/v1/backends/{backend_id}/configuration")
@cache(expire=300)  # Cache for 5 minutes
async def get_backend_configuration(...):
    # ...
```

### Database Optimization

```python
# Add indexes
CREATE INDEX idx_backend_name ON backends(backend_name);
CREATE INDEX idx_calibration_date ON calibrations(backend_id, created_at);

# Use connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=0
)
```

---

## Next Steps

1. **Implement Mock Database** with sample data
2. **Complete All Endpoints** (remove 501 responses)
3. **Add Authentication** validation
4. **Write Tests** for all endpoints
5. **Add Real Database** (PostgreSQL/MongoDB)
6. **Deploy** to staging environment
7. **Performance Test** with load testing tools
8. **Documentation** - keep API docs updated

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [IBM Cloud IAM](https://cloud.ibm.com/docs/account?topic=account-iamoverview)
- [Qiskit Runtime Docs](https://quantum.ibm.com/docs)

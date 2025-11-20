# Qiskit Runtime Backend API Server

A FastAPI-based mock server implementing the IBM Qiskit Runtime Backend API endpoints.

## Overview

This server provides a mock implementation of the Qiskit Runtime Backend API as specified in the [IBM Quantum Cloud API documentation](https://quantum.cloud.ibm.com/docs/en/api/qiskit-runtime-rest/tags/backends).

**API Version:** 2025-05-01

## Features

- Full type annotations using Pydantic models
- OpenAPI/Swagger documentation
- Authentication middleware
- API versioning support
- Comprehensive docstrings

## Project Structure

```
server/
├── src/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # FastAPI application and endpoints
│   └── models.py            # Pydantic data models
├── docs/
│   └── API_SPECIFICATION.md # Detailed API specifications
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server

### Development Mode

```bash
cd server
python -m src.main
```

Or using uvicorn directly:
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The server will be available at:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Production Mode

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Backend Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/backends` | List all available backends |
| GET | `/v1/backends/{id}/configuration` | Get backend configuration |
| GET | `/v1/backends/{id}/defaults` | Get default pulse calibrations |
| GET | `/v1/backends/{id}/properties` | Get backend properties |
| GET | `/v1/backends/{id}/status` | Get backend operational status |

### System Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check |

## Authentication

All backend endpoints require the following headers:

- `Authorization: Bearer YOUR-TOKEN`
- `Service-CRN: YOUR-SERVICE-CRN`
- `IBM-API-Version: 2025-05-01`

Example request:
```bash
curl -X GET "http://localhost:8000/v1/backends" \
  -H "Authorization: Bearer your-token-here" \
  -H "Service-CRN: crn:v1:bluemix:public:quantum-computing:..." \
  -H "IBM-API-Version: 2025-05-01"
```

## Data Models

The server uses Pydantic models for request/response validation. Key models include:

- `BackendsResponse` - List of backends
- `BackendConfiguration` - Complete backend configuration
- `BackendProperties` - Calibration properties
- `BackendStatus` - Operational status
- `BackendDefaults` - Pulse calibrations

See `src/models.py` for complete model definitions.

## Development

### Type Checking

```bash
mypy src/
```

### Code Formatting

```bash
black src/
ruff check src/
```

### Testing

```bash
pytest
```

## Implementation Status

This is a **mock/specification server**. All endpoints currently return:
- HTTP 501 (Not Implemented)

The purpose is to define the API interface, types, and documentation structure.

To implement actual functionality:
1. Replace the `raise HTTPException(status_code=501, ...)` with real logic
2. Add database/storage layer for backend data
3. Implement authentication validation
4. Add caching for frequently accessed data

## Documentation

See `docs/API_SPECIFICATION.md` for detailed API specifications, including:
- Complete endpoint documentation
- Request/response schemas
- Authentication flows
- Error handling
- Examples

## Related Resources

- [Qiskit Runtime Documentation](https://quantum.ibm.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## License

This mock server is for development and testing purposes.

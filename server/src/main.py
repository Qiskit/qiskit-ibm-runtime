"""
FastAPI Backend Server for Qiskit Runtime API.

This module implements the Qiskit Runtime Backend API endpoints as specified in:
https://quantum.cloud.ibm.com/docs/en/api/qiskit-runtime-rest/tags/backends

API Version: 2025-05-01 (IBM-API-Version header)

Endpoints:
- GET  /v1/backends                        - List all backends
- GET  /v1/backends/{id}/configuration     - Get backend configuration
- GET  /v1/backends/{id}/defaults          - Get default pulse calibrations
- GET  /v1/backends/{id}/properties        - Get backend properties
- GET  /v1/backends/{id}/status            - Get backend status
"""

from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Header, HTTPException, Query, Path, Depends
from fastapi.responses import JSONResponse

from .models import (
    BackendsResponse,
    BackendConfiguration,
    BackendDefaults,
    BackendProperties,
    BackendStatus,
    ErrorResponse,
    ErrorDetail,
)


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Qiskit Runtime Backend API",
    description="Mock server for IBM Qiskit Runtime Backend API",
    version="2025-05-01",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============================================================================
# Dependencies for Authentication and Headers
# ============================================================================

async def verify_api_version(
    ibm_api_version: str = Header(
        ...,
        alias="IBM-API-Version",
        description="API version (e.g., '2025-05-01')"
    )
) -> str:
    """
    Verify IBM-API-Version header is present.

    Args:
        ibm_api_version: IBM API version from header

    Returns:
        The API version string

    Raises:
        HTTPException: If API version is not supported
    """
    supported_versions = ["2024-01-01", "2025-01-01", "2025-05-01"]
    if ibm_api_version not in supported_versions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported API version. Supported versions: {supported_versions}"
        )
    return ibm_api_version


async def verify_authorization(
    authorization: str = Header(
        ...,
        description="Bearer token for authentication"
    ),
    service_crn: str = Header(
        ...,
        alias="Service-CRN",
        description="IBM Cloud service instance CRN"
    )
) -> dict:
    """
    Verify authorization headers.

    Args:
        authorization: Bearer token
        service_crn: Service instance CRN

    Returns:
        Dictionary with auth info

    Raises:
        HTTPException: If authentication fails
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )

    # In a real implementation, validate the token and CRN here
    # For mock purposes, we just verify they're present

    return {
        "token": authorization.replace("Bearer ", ""),
        "service_crn": service_crn
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Custom error response handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            errors=[ErrorDetail(message=str(exc.detail), code=None)],
            trace=None,
            status_code=exc.status_code
        ).model_dump()
    )


# ============================================================================
# Backend Endpoints
# ============================================================================

@app.get(
    "/v1/backends",
    response_model=BackendsResponse,
    tags=["backends"],
    summary="List Your Backends",
    description="""
    Returns a list of all the backends your service instance has access to.

    Required IAM action: quantum-computing.device.read

    The response includes basic backend information. Use the `fields` query parameter
    to request additional computed fields like wait_time_seconds.
    """
)
async def list_backends(
    fields: Optional[str] = Query(
        None,
        description="Comma-separated list of additional fields (e.g., 'wait_time_seconds')"
    ),
    api_version: str = Depends(verify_api_version),
    auth: dict = Depends(verify_authorization),
) -> BackendsResponse:
    """
    List all available backends.

    Args:
        fields: Optional comma-separated list of additional fields to include
        api_version: IBM API version from header
        auth: Authentication information

    Returns:
        BackendsResponse with list of available backends

    Implementation notes:
        - Returns all backends accessible to the authenticated service instance
        - If fields includes 'wait_time_seconds', computes estimated wait time
        - Generates audit event: quantum-computing.device.read
    """
    # TODO: Implement actual backend listing logic
    # This is a mock response for demonstration
    raise HTTPException(
        status_code=501,
        detail="Endpoint not yet implemented. This is a mock specification."
    )


@app.get(
    "/v1/backends/{backend_id}/configuration",
    response_model=BackendConfiguration,
    tags=["backends"],
    summary="Get Backend Configuration",
    description="""
    Returns the complete configuration of a specific backend.

    Required IAM action: quantum-computing.device.read

    The configuration includes quantum system properties, gate definitions,
    topology, timing constraints, and supported features.
    """
)
async def get_backend_configuration(
    backend_id: str = Path(
        ...,
        description="Backend identifier (e.g., 'ibmq_armonk')",
        alias="id"
    ),
    calibration_id: Optional[str] = Query(
        None,
        description="Optional calibration ID to get configuration for specific calibration"
    ),
    api_version: str = Depends(verify_api_version),
    auth: dict = Depends(verify_authorization),
) -> BackendConfiguration:
    """
    Get backend configuration.

    Args:
        backend_id: Unique backend identifier
        calibration_id: Optional specific calibration ID
        api_version: IBM API version from header
        auth: Authentication information

    Returns:
        BackendConfiguration with complete backend specs

    Raises:
        HTTPException: 404 if backend not found

    Implementation notes:
        - If calibration_id provided, returns config for that calibration
        - Otherwise returns latest configuration
        - Includes gate definitions, coupling map, processor type, etc.
        - Generates audit event: quantum-computing.device.read
    """
    # TODO: Implement backend configuration retrieval
    raise HTTPException(
        status_code=501,
        detail="Endpoint not yet implemented. This is a mock specification."
    )


@app.get(
    "/v1/backends/{backend_id}/defaults",
    response_model=BackendDefaults,
    tags=["backends"],
    summary="Get Backend Default Settings",
    description="""
    Returns default pulse-level calibrations and command definitions.

    Required IAM action: quantum-computing.device.read

    Note: Simulator backends may not support this endpoint and will return 404.
    """
)
async def get_backend_defaults(
    backend_id: str = Path(
        ...,
        description="Backend identifier",
        alias="id"
    ),
    api_version: str = Depends(verify_api_version),
    auth: dict = Depends(verify_authorization),
) -> BackendDefaults:
    """
    Get default pulse calibrations.

    Args:
        backend_id: Unique backend identifier
        api_version: IBM API version from header
        auth: Authentication information

    Returns:
        BackendDefaults with pulse calibrations and command definitions

    Raises:
        HTTPException: 404 if backend not found or doesn't support defaults

    Implementation notes:
        - Only available for OpenPulse-enabled backends
        - Simulators typically do not support this endpoint
        - Returns qubit/measurement frequencies, pulse library, and gate->pulse mappings
        - Generates audit event: quantum-computing.device.read
    """
    # TODO: Implement defaults retrieval
    raise HTTPException(
        status_code=501,
        detail="Endpoint not yet implemented. This is a mock specification."
    )


@app.get(
    "/v1/backends/{backend_id}/properties",
    response_model=BackendProperties,
    tags=["backends"],
    summary="Get Backend Properties",
    description="""
    Returns calibration properties for qubits and gates.

    Required IAM action: quantum-computing.device.read

    Properties include T1, T2, readout errors, gate errors, gate times,
    and other time-stamped calibration data.
    """
)
async def get_backend_properties(
    backend_id: str = Path(
        ...,
        description="Backend identifier",
        alias="id"
    ),
    calibration_id: Optional[str] = Query(
        None,
        description="Optional calibration ID to get properties for specific calibration"
    ),
    updated_before: Optional[datetime] = Query(
        None,
        description="Get properties from before this timestamp (ISO 8601 format)"
    ),
    api_version: str = Depends(verify_api_version),
    auth: dict = Depends(verify_authorization),
) -> BackendProperties:
    """
    Get backend calibration properties.

    Args:
        backend_id: Unique backend identifier
        calibration_id: Optional specific calibration ID
        updated_before: Optional datetime to get historical properties
        api_version: IBM API version from header
        auth: Authentication information

    Returns:
        BackendProperties with calibration data

    Raises:
        HTTPException: 404 if backend not found

    Implementation notes:
        - Returns time-stamped calibration measurements
        - If updated_before specified, returns properties from that time
        - If calibration_id specified, returns that specific calibration
        - Includes per-qubit properties (T1, T2, frequency, readout_error)
        - Includes per-gate properties (gate_error, gate_length)
        - Generates audit event: quantum-computing.device.read
    """
    # TODO: Implement properties retrieval
    raise HTTPException(
        status_code=501,
        detail="Endpoint not yet implemented. This is a mock specification."
    )


@app.get(
    "/v1/backends/{backend_id}/status",
    response_model=BackendStatus,
    tags=["backends"],
    summary="Get Backend Status",
    description="""
    Returns real-time operational status of a backend.

    Required IAM action: quantum-computing.device.read

    Status includes whether the backend is operational and queue information.
    """
)
async def get_backend_status(
    backend_id: str = Path(
        ...,
        description="Backend identifier",
        alias="id"
    ),
    api_version: str = Depends(verify_api_version),
    auth: dict = Depends(verify_authorization),
) -> BackendStatus:
    """
    Get backend operational status.

    Args:
        backend_id: Unique backend identifier
        api_version: IBM API version from header
        auth: Authentication information

    Returns:
        BackendStatus with operational status and queue info

    Raises:
        HTTPException: 404 if backend not found

    Implementation notes:
        - Returns real-time status (operational/down/maintenance)
        - Includes current queue length (pending_jobs)
        - Status is updated frequently (near real-time)
        - Generates audit event: quantum-computing.device.read
    """
    # TODO: Implement status retrieval
    raise HTTPException(
        status_code=501,
        detail="Endpoint not yet implemented. This is a mock specification."
    )


# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get(
    "/health",
    tags=["system"],
    summary="Health Check",
    description="Simple health check endpoint to verify server is running"
)
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        Dictionary with status information
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2025-05-01"
    }


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get(
    "/",
    tags=["system"],
    summary="API Information",
    description="Root endpoint with API information"
)
async def root() -> dict:
    """
    Root endpoint with API information.

    Returns:
        Dictionary with API metadata
    """
    return {
        "name": "Qiskit Runtime Backend API",
        "version": "2025-05-01",
        "documentation": "/docs",
        "endpoints": {
            "backends": "/v1/backends",
            "health": "/health"
        }
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

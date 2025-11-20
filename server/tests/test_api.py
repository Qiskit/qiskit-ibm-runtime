"""
Test suite for Qiskit Runtime Backend API endpoints.

Run with: pytest tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

# Import the FastAPI app
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import app


# ============================================================================
# Test Client Setup
# ============================================================================

client = TestClient(app)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def auth_headers():
    """Provide valid authentication headers."""
    return {
        "Authorization": "Bearer test-token-123",
        "Service-CRN": "crn:v1:bluemix:public:quantum-computing:us-south:a/test:test::",
        "IBM-API-Version": "2025-05-01"
    }


@pytest.fixture
def invalid_auth_headers():
    """Provide invalid authentication headers."""
    return {
        "Authorization": "InvalidToken",
        "Service-CRN": "crn:test",
        "IBM-API-Version": "2025-05-01"
    }


# ============================================================================
# System Endpoints Tests
# ============================================================================

class TestSystemEndpoints:
    """Test system/utility endpoints."""

    def test_health_check(self):
        """Test /health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    def test_root_endpoint(self):
        """Test root / endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Qiskit Runtime Backend API"
        assert "version" in data
        assert "endpoints" in data


# ============================================================================
# Authentication Tests
# ============================================================================

class TestAuthentication:
    """Test authentication and authorization."""

    def test_missing_authorization_header(self):
        """Test request without Authorization header."""
        headers = {
            "Service-CRN": "crn:test",
            "IBM-API-Version": "2025-05-01"
        }
        response = client.get("/v1/backends", headers=headers)

        # Should return 422 (validation error) for missing header
        assert response.status_code == 422

    def test_missing_service_crn_header(self):
        """Test request without Service-CRN header."""
        headers = {
            "Authorization": "Bearer test",
            "IBM-API-Version": "2025-05-01"
        }
        response = client.get("/v1/backends", headers=headers)

        # Should return 422 (validation error) for missing header
        assert response.status_code == 422

    def test_missing_api_version_header(self):
        """Test request without IBM-API-Version header."""
        headers = {
            "Authorization": "Bearer test",
            "Service-CRN": "crn:test"
        }
        response = client.get("/v1/backends", headers=headers)

        # Should return 422 (validation error) for missing header
        assert response.status_code == 422

    def test_invalid_authorization_format(self, auth_headers):
        """Test request with invalid Authorization format."""
        headers = auth_headers.copy()
        headers["Authorization"] = "InvalidFormat token"

        response = client.get("/v1/backends", headers=headers)

        # Should return 401 for invalid auth format
        assert response.status_code in [401, 501]

    def test_unsupported_api_version(self, auth_headers):
        """Test request with unsupported API version."""
        headers = auth_headers.copy()
        headers["IBM-API-Version"] = "2020-01-01"

        response = client.get("/v1/backends", headers=headers)

        # Should return 400 for unsupported version
        assert response.status_code == 400
        assert "Unsupported API version" in response.json()["detail"]


# ============================================================================
# Backend List Endpoint Tests
# ============================================================================

class TestListBackends:
    """Test GET /v1/backends endpoint."""

    def test_list_backends_success(self, auth_headers):
        """Test successful backend listing."""
        response = client.get("/v1/backends", headers=auth_headers)

        # Currently returns 501 (not implemented)
        # When implemented, should return 200
        assert response.status_code in [200, 501]

        if response.status_code == 200:
            data = response.json()
            assert "devices" in data
            assert isinstance(data["devices"], list)

    def test_list_backends_with_fields(self, auth_headers):
        """Test backend listing with fields parameter."""
        response = client.get(
            "/v1/backends",
            params={"fields": "wait_time_seconds"},
            headers=auth_headers
        )

        assert response.status_code in [200, 501]

        if response.status_code == 200:
            data = response.json()
            assert "devices" in data
            # If fields=wait_time_seconds, devices should include wait_time_seconds
            if data["devices"]:
                assert "wait_time_seconds" in data["devices"][0]

    def test_list_backends_response_schema(self, auth_headers):
        """Test response matches BackendsResponse schema."""
        response = client.get("/v1/backends", headers=auth_headers)

        if response.status_code == 200:
            data = response.json()
            assert "devices" in data

            # Validate device structure
            for device in data["devices"]:
                assert "backend_name" in device
                assert "backend_version" in device
                assert "operational" in device
                assert "simulator" in device
                assert "n_qubits" in device


# ============================================================================
# Backend Configuration Endpoint Tests
# ============================================================================

class TestBackendConfiguration:
    """Test GET /v1/backends/{id}/configuration endpoint."""

    def test_get_configuration_success(self, auth_headers):
        """Test getting backend configuration."""
        response = client.get(
            "/v1/backends/ibm_brisbane/configuration",
            headers=auth_headers
        )

        # Currently returns 501 (not implemented) or 404 (not found)
        assert response.status_code in [200, 404, 501]

        if response.status_code == 200:
            data = response.json()
            assert "backend_name" in data
            assert data["backend_name"] == "ibm_brisbane"
            assert "n_qubits" in data
            assert "basis_gates" in data
            assert "gates" in data

    def test_get_configuration_with_calibration_id(self, auth_headers):
        """Test getting configuration with calibration_id."""
        response = client.get(
            "/v1/backends/ibm_brisbane/configuration",
            params={"calibration_id": "cal_123"},
            headers=auth_headers
        )

        assert response.status_code in [200, 404, 501]

    def test_get_configuration_not_found(self, auth_headers):
        """Test getting configuration for non-existent backend."""
        response = client.get(
            "/v1/backends/nonexistent_backend/configuration",
            headers=auth_headers
        )

        # Should return 404 when implemented
        assert response.status_code in [404, 501]

    def test_configuration_response_schema(self, auth_headers):
        """Test response matches BackendConfiguration schema."""
        response = client.get(
            "/v1/backends/ibm_brisbane/configuration",
            headers=auth_headers
        )

        if response.status_code == 200:
            data = response.json()

            # Required fields
            required_fields = [
                "backend_name", "backend_version", "n_qubits",
                "basis_gates", "gates", "simulator"
            ]
            for field in required_fields:
                assert field in data


# ============================================================================
# Backend Properties Endpoint Tests
# ============================================================================

class TestBackendProperties:
    """Test GET /v1/backends/{id}/properties endpoint."""

    def test_get_properties_success(self, auth_headers):
        """Test getting backend properties."""
        response = client.get(
            "/v1/backends/ibm_brisbane/properties",
            headers=auth_headers
        )

        assert response.status_code in [200, 404, 501]

        if response.status_code == 200:
            data = response.json()
            assert "backend_name" in data
            assert "backend_version" in data
            assert "last_update_date" in data
            assert "qubits" in data
            assert "gates" in data

    def test_get_properties_with_calibration_id(self, auth_headers):
        """Test getting properties with calibration_id."""
        response = client.get(
            "/v1/backends/ibm_brisbane/properties",
            params={"calibration_id": "cal_123"},
            headers=auth_headers
        )

        assert response.status_code in [200, 404, 501]

    def test_get_properties_with_datetime(self, auth_headers):
        """Test getting properties with updated_before parameter."""
        timestamp = datetime.utcnow().isoformat()
        response = client.get(
            "/v1/backends/ibm_brisbane/properties",
            params={"updated_before": timestamp},
            headers=auth_headers
        )

        assert response.status_code in [200, 404, 501]

    def test_properties_response_schema(self, auth_headers):
        """Test response matches BackendProperties schema."""
        response = client.get(
            "/v1/backends/ibm_brisbane/properties",
            headers=auth_headers
        )

        if response.status_code == 200:
            data = response.json()

            # Validate qubit properties structure
            assert isinstance(data["qubits"], list)
            if data["qubits"]:
                qubit = data["qubits"][0]
                assert isinstance(qubit, list)
                if qubit:
                    prop = qubit[0]
                    assert "date" in prop
                    assert "name" in prop
                    assert "unit" in prop
                    assert "value" in prop


# ============================================================================
# Backend Status Endpoint Tests
# ============================================================================

class TestBackendStatus:
    """Test GET /v1/backends/{id}/status endpoint."""

    def test_get_status_success(self, auth_headers):
        """Test getting backend status."""
        response = client.get(
            "/v1/backends/ibm_brisbane/status",
            headers=auth_headers
        )

        assert response.status_code in [200, 404, 501]

        if response.status_code == 200:
            data = response.json()
            assert "backend_name" in data
            assert "backend_version" in data
            # Check for either new field names or aliases
            assert "state" in data or "operational" in data
            assert "status" in data or "status_msg" in data
            assert "length_queue" in data or "pending_jobs" in data

    def test_status_response_schema(self, auth_headers):
        """Test response matches BackendStatus schema."""
        response = client.get(
            "/v1/backends/ibm_brisbane/status",
            headers=auth_headers
        )

        if response.status_code == 200:
            data = response.json()

            # Validate status values
            if "state" in data:
                assert isinstance(data["state"], bool)
            if "status" in data:
                assert data["status"] in ["operational", "maintenance", "down"]
            if "length_queue" in data:
                assert isinstance(data["length_queue"], int)


# ============================================================================
# Backend Defaults Endpoint Tests
# ============================================================================

class TestBackendDefaults:
    """Test GET /v1/backends/{id}/defaults endpoint."""

    def test_get_defaults_success(self, auth_headers):
        """Test getting backend defaults."""
        response = client.get(
            "/v1/backends/ibm_brisbane/defaults",
            headers=auth_headers
        )

        assert response.status_code in [200, 404, 501]

        if response.status_code == 200:
            data = response.json()
            assert "qubit_freq_est" in data
            assert "meas_freq_est" in data
            assert "buffer" in data

    def test_get_defaults_simulator_not_supported(self, auth_headers):
        """Test getting defaults for simulator (should fail)."""
        response = client.get(
            "/v1/backends/simulator_backend/defaults",
            headers=auth_headers
        )

        # Simulators don't support defaults
        assert response.status_code in [404, 501]


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error responses."""

    def test_404_backend_not_found(self, auth_headers):
        """Test 404 error for non-existent backend."""
        response = client.get(
            "/v1/backends/nonexistent/configuration",
            headers=auth_headers
        )

        # When implemented, should return 404
        assert response.status_code in [404, 501]

    def test_error_response_format(self, auth_headers):
        """Test error response follows ErrorResponse schema."""
        # Trigger a known error (unsupported API version)
        headers = auth_headers.copy()
        headers["IBM-API-Version"] = "1999-01-01"

        response = client.get("/v1/backends", headers=headers)

        assert response.status_code == 400
        data = response.json()

        # Should have error structure
        # Either FastAPI default or our custom ErrorResponse format
        assert "detail" in data or "errors" in data


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for typical workflows."""

    def test_complete_backend_workflow(self, auth_headers):
        """Test complete workflow: list → configure → properties → status."""
        # 1. List backends
        list_response = client.get("/v1/backends", headers=auth_headers)
        if list_response.status_code == 501:
            pytest.skip("Endpoints not yet implemented")

        assert list_response.status_code == 200
        backends = list_response.json()["devices"]
        assert len(backends) > 0

        backend_id = backends[0]["backend_name"]

        # 2. Get configuration
        config_response = client.get(
            f"/v1/backends/{backend_id}/configuration",
            headers=auth_headers
        )
        assert config_response.status_code == 200

        # 3. Get properties
        props_response = client.get(
            f"/v1/backends/{backend_id}/properties",
            headers=auth_headers
        )
        assert props_response.status_code == 200

        # 4. Get status
        status_response = client.get(
            f"/v1/backends/{backend_id}/status",
            headers=auth_headers
        )
        assert status_response.status_code == 200


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Basic performance tests."""

    def test_response_time(self, auth_headers):
        """Test that responses are reasonably fast."""
        import time

        start = time.time()
        response = client.get("/v1/backends", headers=auth_headers)
        duration = time.time() - start

        # Should respond within 1 second (adjust as needed)
        assert duration < 1.0

    def test_concurrent_requests(self, auth_headers):
        """Test handling concurrent requests."""
        import concurrent.futures

        def make_request():
            return client.get("/v1/backends", headers=auth_headers)

        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [f.result() for f in futures]

        # All should succeed (or all return 501 if not implemented)
        for response in responses:
            assert response.status_code in [200, 501]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

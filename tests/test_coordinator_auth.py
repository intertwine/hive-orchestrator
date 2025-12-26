"""Tests for CoordinatorClient authentication."""

import os
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from src.coordinator import app
from src.coordinator_client import CoordinatorClient, get_coordinator_client


# ============================================================================
# Authentication Tests
# ============================================================================


class TestCoordinatorClientAuthentication:
    """Test CoordinatorClient authentication functionality."""

    def test_client_initialization_with_api_key_parameter(self):
        """Test that client accepts and stores API key parameter."""
        client = CoordinatorClient(
            base_url="http://localhost:8080", api_key="test-key-123"
        )
        assert client.api_key == "test-key-123"
        assert client.base_url == "http://localhost:8080"

    def test_client_initialization_with_env_var(self):
        """Test that client reads API key from environment variable."""
        with patch.dict(os.environ, {"HIVE_API_KEY": "env-key-456"}, clear=False):
            client = CoordinatorClient(base_url="http://localhost:8080")
            assert client.api_key == "env-key-456"

    def test_client_initialization_parameter_overrides_env(self):
        """Test that explicit parameter overrides environment variable."""
        with patch.dict(os.environ, {"HIVE_API_KEY": "env-key-456"}, clear=False):
            client = CoordinatorClient(
                base_url="http://localhost:8080", api_key="param-key-789"
            )
            assert client.api_key == "param-key-789"

    def test_client_initialization_no_api_key(self):
        """Test that client works without API key (for unauthenticated servers)."""
        with patch.dict(os.environ, {}, clear=False):
            # Remove HIVE_API_KEY if it exists
            os.environ.pop("HIVE_API_KEY", None)
            client = CoordinatorClient(base_url="http://localhost:8080")
            assert client.api_key is None

    @patch("src.coordinator_client.requests.request")
    def test_request_includes_auth_header_when_api_key_set(self, mock_request):
        """Test that requests include Authorization header when API key is set."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_request.return_value = mock_response

        client = CoordinatorClient(
            base_url="http://localhost:8080", api_key="test-key-123"
        )
        client._request("GET", "/health")

        # Verify the request was made with Authorization header
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert "headers" in call_args.kwargs
        assert call_args.kwargs["headers"]["Authorization"] == "Bearer test-key-123"

    @patch("src.coordinator_client.requests.request")
    def test_request_no_auth_header_when_api_key_not_set(self, mock_request):
        """Test that requests don't include Authorization header when no API key."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_request.return_value = mock_response

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HIVE_API_KEY", None)
            client = CoordinatorClient(base_url="http://localhost:8080")
            client._request("GET", "/health")

            # Verify the request was made with empty headers
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert "headers" in call_args.kwargs
            assert call_args.kwargs["headers"] == {}

    def test_get_coordinator_client_with_env_vars(self):
        """Test get_coordinator_client helper function with environment variables."""
        with patch.dict(
            os.environ,
            {"COORDINATOR_URL": "http://coordinator:8080", "HIVE_API_KEY": "helper-key-123"},
            clear=False,
        ):
            client = get_coordinator_client()
            assert client is not None
            assert client.base_url == "http://coordinator:8080"
            assert client.api_key == "helper-key-123"

    def test_get_coordinator_client_no_url(self):
        """Test get_coordinator_client returns None when URL not configured."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("COORDINATOR_URL", None)
            client = get_coordinator_client()
            assert client is None


class TestCoordinatorClientWithAuthServer:
    """Test CoordinatorClient against a real FastAPI server with authentication enabled."""

    @pytest.fixture
    def auth_client(self):
        """Create a test client for the FastAPI app with auth enabled."""
        # Enable authentication for these tests
        with patch.dict(
            "os.environ",
            {"HIVE_REQUIRE_AUTH": "true", "HIVE_API_KEY": "test-secret-key-12345"},
            clear=False,
        ):
            # Need to reload the module to pick up the new env vars
            import src.coordinator as coordinator_module

            original_require_auth = coordinator_module.REQUIRE_AUTH
            original_api_key = coordinator_module.HIVE_API_KEY
            coordinator_module.REQUIRE_AUTH = True
            coordinator_module.HIVE_API_KEY = "test-secret-key-12345"
            try:
                yield TestClient(app)
            finally:
                coordinator_module.REQUIRE_AUTH = original_require_auth
                coordinator_module.HIVE_API_KEY = original_api_key

    @pytest.fixture(autouse=True)
    def clear_store(self):
        """Clear the reservation store before each test."""
        from src.coordinator import store

        store.claims.clear()
        store.claims_by_id.clear()
        yield
        store.claims.clear()
        store.claims_by_id.clear()

    def test_unauthenticated_request_fails_with_401(self, auth_client):
        """Test that requests without auth header fail with 401."""
        response = auth_client.post(
            "/claim", json={"project_id": "test-project", "agent_name": "test-agent"}
        )
        assert response.status_code == 401
        data = response.json()
        assert "Authentication required" in data["detail"]

    def test_authenticated_request_succeeds(self, auth_client):
        """Test that requests with valid auth header succeed."""
        response = auth_client.post(
            "/claim",
            json={"project_id": "test-project", "agent_name": "test-agent"},
            headers={"Authorization": "Bearer test-secret-key-12345"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["project_id"] == "test-project"

    def test_invalid_api_key_fails_with_401(self, auth_client):
        """Test that requests with invalid API key fail with 401."""
        response = auth_client.post(
            "/claim",
            json={"project_id": "test-project", "agent_name": "test-agent"},
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert response.status_code == 401
        data = response.json()
        assert "Invalid API key" in data["detail"]

    def test_malformed_auth_header_fails(self, auth_client):
        """Test that requests with malformed auth header fail."""
        # Missing "Bearer" prefix
        response = auth_client.post(
            "/claim",
            json={"project_id": "test-project", "agent_name": "test-agent"},
            headers={"Authorization": "test-secret-key-12345"},
        )
        assert response.status_code == 401

    def test_all_protected_endpoints_require_auth(self, auth_client):
        """Test that all claim/release/extend endpoints require authentication."""
        # Test /claim
        response = auth_client.post(
            "/claim", json={"project_id": "test", "agent_name": "agent"}
        )
        assert response.status_code == 401

        # Test /release/{project_id}
        response = auth_client.delete("/release/test")
        assert response.status_code == 401

        # Test /release/claim/{claim_id}
        response = auth_client.delete("/release/claim/test-id")
        assert response.status_code == 401

        # Test /extend/{project_id}
        response = auth_client.post("/extend/test")
        assert response.status_code == 401

    def test_health_endpoint_does_not_require_auth(self, auth_client):
        """Test that /health endpoint works without authentication."""
        response = auth_client.get("/health")
        assert response.status_code == 200

    def test_status_endpoint_does_not_require_auth(self, auth_client):
        """Test that /status endpoint works without authentication."""
        response = auth_client.get("/status/test-project")
        assert response.status_code == 200

    def test_reservations_endpoint_does_not_require_auth(self, auth_client):
        """Test that /reservations endpoint works without authentication."""
        response = auth_client.get("/reservations")
        assert response.status_code == 200


class TestCoordinatorClientIntegrationWithAuth:
    """Integration tests for CoordinatorClient with authentication."""

    @pytest.fixture
    def auth_server(self):
        """Start a test server with authentication enabled."""
        with patch.dict(
            "os.environ",
            {"HIVE_REQUIRE_AUTH": "true", "HIVE_API_KEY": "integration-key-789"},
            clear=False,
        ):
            import src.coordinator as coordinator_module

            original_require_auth = coordinator_module.REQUIRE_AUTH
            original_api_key = coordinator_module.HIVE_API_KEY
            coordinator_module.REQUIRE_AUTH = True
            coordinator_module.HIVE_API_KEY = "integration-key-789"

            # Create a test client that acts as the server
            test_client = TestClient(app)

            # Patch requests.request to use the test client
            def mock_request(method, url, json=None, params=None, headers=None, timeout=None):
                endpoint = url.replace("http://test-server", "")
                response = test_client.request(
                    method, endpoint, json=json, params=params, headers=headers
                )
                return response

            with patch("src.coordinator_client.requests.request", side_effect=mock_request):
                yield test_client

            coordinator_module.REQUIRE_AUTH = original_require_auth
            coordinator_module.HIVE_API_KEY = original_api_key

    @pytest.fixture(autouse=True)
    def clear_store(self):
        """Clear the reservation store before each test."""
        from src.coordinator import store

        store.claims.clear()
        store.claims_by_id.clear()
        yield
        store.claims.clear()
        store.claims_by_id.clear()

    def test_client_with_api_key_succeeds(self, auth_server):
        """Test that client with API key can successfully claim projects."""
        client = CoordinatorClient(
            base_url="http://test-server", api_key="integration-key-789"
        )
        result = client.claim("my-project", "test-agent")

        assert result.success is True
        assert result.project_id == "my-project"
        assert result.claim_id is not None

    def test_client_without_api_key_fails(self, auth_server):
        """Test that client without API key fails when server requires auth."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HIVE_API_KEY", None)
            client = CoordinatorClient(base_url="http://test-server")

            # Should fail because no API key is provided
            result = client.claim("my-project", "test-agent")
            assert result.success is False

    def test_client_with_wrong_api_key_fails(self, auth_server):
        """Test that client with wrong API key fails."""
        client = CoordinatorClient(base_url="http://test-server", api_key="wrong-key")

        # Should fail because API key is invalid
        result = client.claim("my-project", "test-agent")
        assert result.success is False

    def test_full_workflow_with_authentication(self, auth_server):
        """Test complete claim/extend/release workflow with authentication."""
        client = CoordinatorClient(
            base_url="http://test-server", api_key="integration-key-789"
        )

        # 1. Claim a project
        claim_result = client.claim("workflow-test", "authenticated-agent")
        assert claim_result.success is True
        claim_id = claim_result.claim_id

        # 2. Get status
        status = client.get_status("workflow-test")
        assert status.is_claimed is True
        assert status.agent_name == "authenticated-agent"

        # 3. Extend the claim
        extended = client.extend("workflow-test", ttl_seconds=7200)
        assert extended is True

        # 4. Release the claim
        released = client.release("workflow-test")
        assert released is True

        # 5. Verify released
        status = client.get_status("workflow-test")
        assert status.is_claimed is False

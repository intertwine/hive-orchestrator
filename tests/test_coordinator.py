"""Tests for the Agent Hive Coordinator server and client."""

from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from src.coordinator import app, store, Claim, ReservationStore
from src.coordinator_client import (
    CoordinatorClient,
    CoordinatorUnavailable,
    ClaimConflict,
    get_coordinator_client,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_store():
    """Clear the reservation store before each test."""
    store.claims.clear()
    store.claims_by_id.clear()
    yield
    store.claims.clear()
    store.claims_by_id.clear()


@pytest.fixture
def sample_claim():
    """Create a sample claim for testing."""
    now = datetime.utcnow()
    return Claim(
        claim_id="test-claim-123",
        project_id="test-project",
        agent_name="claude-3.5-sonnet",
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )


@pytest.fixture
def expired_claim():
    """Create an expired claim for testing."""
    now = datetime.utcnow()
    return Claim(
        claim_id="expired-claim-456",
        project_id="expired-project",
        agent_name="old-agent",
        created_at=now - timedelta(hours=2),
        expires_at=now - timedelta(hours=1),
    )


# ============================================================================
# ReservationStore Tests
# ============================================================================


class TestReservationStore:
    """Test the ReservationStore class."""

    def test_add_and_get_claim(self, sample_claim):
        """Test adding and retrieving a claim."""
        test_store = ReservationStore()
        test_store.add_claim(sample_claim)

        retrieved = test_store.get_claim(sample_claim.project_id)
        assert retrieved is not None
        assert retrieved.claim_id == sample_claim.claim_id
        assert retrieved.agent_name == sample_claim.agent_name

    def test_get_claim_removes_expired(self, expired_claim):
        """Test that expired claims are automatically removed."""
        test_store = ReservationStore()
        test_store.add_claim(expired_claim)

        retrieved = test_store.get_claim(expired_claim.project_id)
        assert retrieved is None
        assert expired_claim.project_id not in test_store.claims

    def test_remove_claim(self, sample_claim):
        """Test removing a claim."""
        test_store = ReservationStore()
        test_store.add_claim(sample_claim)

        removed = test_store.remove_claim(sample_claim.project_id)
        assert removed is not None
        assert removed.claim_id == sample_claim.claim_id
        assert sample_claim.project_id not in test_store.claims

    def test_remove_nonexistent_claim(self):
        """Test removing a claim that doesn't exist."""
        test_store = ReservationStore()
        removed = test_store.remove_claim("nonexistent")
        assert removed is None

    def test_remove_claim_by_id(self, sample_claim):
        """Test removing a claim by claim_id."""
        test_store = ReservationStore()
        test_store.add_claim(sample_claim)

        removed = test_store.remove_claim_by_id(sample_claim.claim_id)
        assert removed is not None
        assert removed.project_id == sample_claim.project_id

    def test_get_all_active_claims(self, sample_claim, expired_claim):
        """Test getting all active (non-expired) claims."""
        test_store = ReservationStore()
        test_store.add_claim(sample_claim)
        test_store.add_claim(expired_claim)

        active = test_store.get_all_active_claims()
        assert len(active) == 1
        assert sample_claim.project_id in active
        assert expired_claim.project_id not in active

    def test_cleanup_expired(self, sample_claim, expired_claim):
        """Test cleanup of expired claims."""
        test_store = ReservationStore()
        test_store.add_claim(sample_claim)
        test_store.add_claim(expired_claim)

        removed_count = test_store.cleanup_expired()
        assert removed_count == 1
        assert sample_claim.project_id in test_store.claims
        assert expired_claim.project_id not in test_store.claims


class TestClaim:
    """Test the Claim dataclass."""

    def test_is_expired_false(self, sample_claim):
        """Test that active claim is not expired."""
        assert not sample_claim.is_expired()

    def test_is_expired_true(self, expired_claim):
        """Test that expired claim is detected."""
        assert expired_claim.is_expired()

    def test_to_dict(self, sample_claim):
        """Test claim serialization to dict."""
        result = sample_claim.to_dict()
        assert result["claim_id"] == sample_claim.claim_id
        assert result["project_id"] == sample_claim.project_id
        assert result["agent_name"] == sample_claim.agent_name
        assert "created_at" in result
        assert "expires_at" in result


# ============================================================================
# API Endpoint Tests
# ============================================================================


class TestHealthEndpoint:
    """Test the /health endpoint."""

    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "active_claims" in data
        assert "uptime_seconds" in data


class TestClaimEndpoint:
    """Test the /claim endpoint."""

    def test_claim_project_success(self, client):
        """Test successfully claiming a project."""
        response = client.post(
            "/claim",
            json={"project_id": "my-project", "agent_name": "claude-opus", "ttl_seconds": 3600},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["project_id"] == "my-project"
        assert data["agent_name"] == "claude-opus"
        assert "claim_id" in data
        assert "expires_at" in data

    def test_claim_project_conflict(self, client):
        """Test claiming an already claimed project."""
        # First claim
        client.post("/claim", json={"project_id": "my-project", "agent_name": "claude-opus"})

        # Second claim should fail
        response = client.post(
            "/claim", json={"project_id": "my-project", "agent_name": "grok-beta"}
        )

        assert response.status_code == 409
        data = response.json()
        assert data["success"] is False
        assert data["error"] == "Project already claimed"
        assert data["current_owner"] == "claude-opus"

    def test_claim_project_force_override(self, client):
        """Test force claiming an already claimed project."""
        # First claim
        client.post("/claim", json={"project_id": "my-project", "agent_name": "claude-opus"})

        # Force claim should succeed
        response = client.post(
            "/claim?force=true", json={"project_id": "my-project", "agent_name": "grok-beta"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["agent_name"] == "grok-beta"

    def test_claim_project_default_ttl(self, client):
        """Test that default TTL is used when not specified."""
        response = client.post(
            "/claim", json={"project_id": "my-project", "agent_name": "claude-opus"}
        )

        assert response.status_code == 200
        # Claim should be stored with default TTL

    def test_claim_project_custom_ttl(self, client):
        """Test claiming with custom TTL."""
        response = client.post(
            "/claim",
            json={"project_id": "my-project", "agent_name": "claude-opus", "ttl_seconds": 7200},
        )

        assert response.status_code == 200


class TestReleaseEndpoint:
    """Test the /release endpoints."""

    def test_release_project_success(self, client):
        """Test releasing a claimed project."""
        # Claim first
        client.post("/claim", json={"project_id": "my-project", "agent_name": "claude-opus"})

        # Release
        response = client.delete("/release/my-project")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["project_id"] == "my-project"

    def test_release_nonexistent_project(self, client):
        """Test releasing a project that wasn't claimed."""
        response = client.delete("/release/nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_release_by_claim_id_success(self, client):
        """Test releasing by claim_id."""
        # Claim first
        claim_response = client.post(
            "/claim", json={"project_id": "my-project", "agent_name": "claude-opus"}
        )
        claim_id = claim_response.json()["claim_id"]

        # Release by claim_id
        response = client.delete(f"/release/claim/{claim_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_release_by_invalid_claim_id(self, client):
        """Test releasing with invalid claim_id."""
        response = client.delete("/release/claim/invalid-id")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False


class TestStatusEndpoint:
    """Test the /status endpoint."""

    def test_status_unclaimed_project(self, client):
        """Test status of unclaimed project."""
        response = client.get("/status/my-project")
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == "my-project"
        assert data["is_claimed"] is False
        assert data["claim"] is None

    def test_status_claimed_project(self, client):
        """Test status of claimed project."""
        # Claim first
        client.post("/claim", json={"project_id": "my-project", "agent_name": "claude-opus"})

        response = client.get("/status/my-project")
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == "my-project"
        assert data["is_claimed"] is True
        assert data["claim"]["agent_name"] == "claude-opus"


class TestReservationsEndpoint:
    """Test the /reservations endpoint."""

    def test_get_empty_reservations(self, client):
        """Test getting reservations when none exist."""
        response = client.get("/reservations")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["reservations"] == []

    def test_get_reservations_with_claims(self, client):
        """Test getting reservations with active claims."""
        # Create some claims
        client.post("/claim", json={"project_id": "project-1", "agent_name": "claude-opus"})
        client.post("/claim", json={"project_id": "project-2", "agent_name": "grok-beta"})

        response = client.get("/reservations")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["reservations"]) == 2


class TestExtendEndpoint:
    """Test the /extend endpoint."""

    def test_extend_claim_success(self, client):
        """Test extending a claim."""
        # Claim first
        client.post("/claim", json={"project_id": "my-project", "agent_name": "claude-opus"})

        response = client.post("/extend/my-project?ttl_seconds=7200")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "new_expires_at" in data

    def test_extend_nonexistent_claim(self, client):
        """Test extending a claim that doesn't exist."""
        response = client.post("/extend/nonexistent")
        assert response.status_code == 404


# ============================================================================
# Coordinator Client Tests
# ============================================================================


class TestCoordinatorClient:
    """Test the CoordinatorClient class."""

    def test_client_initialization_default(self):
        """Test client initialization with defaults."""
        client = CoordinatorClient()
        assert client.base_url == "http://localhost:8080"
        assert client.timeout == 5.0

    def test_client_initialization_custom(self):
        """Test client initialization with custom values."""
        client = CoordinatorClient(base_url="http://custom:9000", timeout=10.0, retry_count=3)
        assert client.base_url == "http://custom:9000"
        assert client.timeout == 10.0
        assert client.retry_count == 3

    def test_client_initialization_from_env(self, monkeypatch):
        """Test client initialization from environment variable."""
        monkeypatch.setenv("COORDINATOR_URL", "http://env-url:8080")
        client = CoordinatorClient()
        assert client.base_url == "http://env-url:8080"

    @patch("src.coordinator_client.requests.get")
    def test_is_available_success(self, mock_get):
        """Test availability check when server is up."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        client = CoordinatorClient()
        assert client.is_available() is True

    @patch("src.coordinator_client.requests.get")
    def test_is_available_failure(self, mock_get):
        """Test availability check when server is down."""
        from requests.exceptions import ConnectionError

        mock_get.side_effect = ConnectionError()

        client = CoordinatorClient()
        assert client.is_available() is False

    @patch("src.coordinator_client.requests.request")
    def test_claim_success(self, mock_request):
        """Test successful claim via client."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "claim_id": "abc123",
            "project_id": "my-project",
            "agent_name": "claude-opus",
            "expires_at": "2025-01-01T12:00:00Z",
        }
        mock_request.return_value = mock_response

        client = CoordinatorClient()
        result = client.claim("my-project", "claude-opus")

        assert result.success is True
        assert result.claim_id == "abc123"
        assert result.project_id == "my-project"

    @patch("src.coordinator_client.requests.request")
    def test_claim_conflict(self, mock_request):
        """Test claim conflict via client."""
        mock_response = MagicMock()
        mock_response.status_code = 409
        mock_response.json.return_value = {
            "success": False,
            "error": "Project already claimed",
            "current_owner": "grok-beta",
            "expires_at": "2025-01-01T12:00:00Z",
        }
        mock_request.return_value = mock_response

        client = CoordinatorClient()

        with pytest.raises(ClaimConflict) as exc_info:
            client.claim("my-project", "claude-opus")

        assert exc_info.value.current_owner == "grok-beta"

    @patch("src.coordinator_client.requests.request")
    def test_try_claim_conflict_no_exception(self, mock_request):
        """Test try_claim returns result instead of raising exception."""
        mock_response = MagicMock()
        mock_response.status_code = 409
        mock_response.json.return_value = {
            "success": False,
            "error": "Project already claimed",
            "current_owner": "grok-beta",
            "expires_at": "2025-01-01T12:00:00Z",
        }
        mock_request.return_value = mock_response

        client = CoordinatorClient()
        result = client.try_claim("my-project", "claude-opus")

        assert result.success is False
        assert result.current_owner == "grok-beta"

    @patch("src.coordinator_client.requests.request")
    def test_release_success(self, mock_request):
        """Test releasing a claim via client."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_request.return_value = mock_response

        client = CoordinatorClient()
        result = client.release("my-project")

        assert result is True

    @patch("src.coordinator_client.requests.request")
    def test_get_status(self, mock_request):
        """Test getting claim status via client."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "project_id": "my-project",
            "is_claimed": True,
            "claim": {
                "claim_id": "abc123",
                "agent_name": "claude-opus",
                "created_at": "2025-01-01T10:00:00Z",
                "expires_at": "2025-01-01T11:00:00Z",
            },
        }
        mock_request.return_value = mock_response

        client = CoordinatorClient()
        status = client.get_status("my-project")

        assert status.is_claimed is True
        assert status.agent_name == "claude-opus"

    @patch("src.coordinator_client.requests.request")
    def test_coordinator_unavailable(self, mock_request):
        """Test handling of unavailable coordinator."""
        from requests.exceptions import ConnectionError

        mock_request.side_effect = ConnectionError()

        client = CoordinatorClient(retry_count=0)

        with pytest.raises(CoordinatorUnavailable):
            client.claim("my-project", "claude-opus")


class TestGetCoordinatorClient:
    """Test the get_coordinator_client helper function."""

    def test_returns_none_without_env(self, monkeypatch):
        """Test that None is returned when COORDINATOR_URL not set."""
        monkeypatch.delenv("COORDINATOR_URL", raising=False)
        result = get_coordinator_client()
        assert result is None

    def test_returns_client_with_env(self, monkeypatch):
        """Test that client is returned when COORDINATOR_URL is set."""
        monkeypatch.setenv("COORDINATOR_URL", "http://localhost:8080")
        result = get_coordinator_client()
        assert result is not None
        assert isinstance(result, CoordinatorClient)


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for coordinator workflow."""

    def test_full_claim_workflow(self, client):
        """Test complete claim-work-release workflow."""
        # 1. Claim project
        claim_response = client.post(
            "/claim", json={"project_id": "integration-test", "agent_name": "test-agent"}
        )
        assert claim_response.status_code == 200
        assert "claim_id" in claim_response.json()

        # 2. Verify status
        status_response = client.get("/status/integration-test")
        assert status_response.json()["is_claimed"] is True

        # 3. Try to claim from another agent (should fail)
        conflict_response = client.post(
            "/claim", json={"project_id": "integration-test", "agent_name": "other-agent"}
        )
        assert conflict_response.status_code == 409

        # 4. Extend the claim
        extend_response = client.post("/extend/integration-test?ttl_seconds=7200")
        assert extend_response.status_code == 200

        # 5. Release the project
        release_response = client.delete("/release/integration-test")
        assert release_response.json()["success"] is True

        # 6. Verify released
        status_response = client.get("/status/integration-test")
        assert status_response.json()["is_claimed"] is False

        # 7. Another agent can now claim
        new_claim_response = client.post(
            "/claim", json={"project_id": "integration-test", "agent_name": "other-agent"}
        )
        assert new_claim_response.status_code == 200

    def test_multiple_projects_workflow(self, client):
        """Test managing multiple project claims."""
        projects = ["project-a", "project-b", "project-c"]
        agents = ["agent-1", "agent-2", "agent-3"]

        # Claim each project with different agent
        for project, agent in zip(projects, agents):
            response = client.post("/claim", json={"project_id": project, "agent_name": agent})
            assert response.status_code == 200

        # Verify all reservations
        response = client.get("/reservations")
        data = response.json()
        assert data["count"] == 3

        # Release one project
        client.delete("/release/project-b")

        # Verify count decreased
        response = client.get("/reservations")
        assert response.json()["count"] == 2

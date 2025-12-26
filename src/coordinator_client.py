#!/usr/bin/env python3
"""
Coordinator Client - Client library for Agent Hive Coordinator.

This module provides a client for interacting with the coordination server,
with graceful fallback to git-only mode when the coordinator is unavailable.
"""

import os
from typing import Dict, Optional, Any
from dataclasses import dataclass
import requests


class CoordinatorUnavailable(Exception):
    """Exception raised when the coordinator server is unavailable."""


class ClaimConflict(Exception):
    """Exception raised when a project is already claimed by another agent."""

    def __init__(self, message: str, current_owner: str, expires_at: str):
        super().__init__(message)
        self.current_owner = current_owner
        self.expires_at = expires_at


@dataclass
class ClaimResult:
    """Result of a claim operation."""

    success: bool
    claim_id: Optional[str] = None
    project_id: Optional[str] = None
    agent_name: Optional[str] = None
    expires_at: Optional[str] = None
    error: Optional[str] = None
    current_owner: Optional[str] = None


@dataclass
class ClaimStatus:
    """Status of a project claim."""

    project_id: str
    is_claimed: bool
    claim_id: Optional[str] = None
    agent_name: Optional[str] = None
    created_at: Optional[str] = None
    expires_at: Optional[str] = None


class CoordinatorClient:
    """
    Client for the Agent Hive Coordinator server.

    Provides methods to claim, release, and query project reservations
    with automatic handling of network errors and graceful degradation.
    """

    def __init__(
        self, base_url: str = None, api_key: str = None, timeout: float = 5.0, retry_count: int = 1
    ):
        """
        Initialize the coordinator client.

        Args:
            base_url: Base URL of the coordinator server.
                     If None, reads from COORDINATOR_URL env var.
            api_key: API key for authentication.
                    If None, reads from HIVE_API_KEY env var.
            timeout: Request timeout in seconds.
            retry_count: Number of retries for failed requests.
        """
        self.base_url = base_url or os.getenv("COORDINATOR_URL", "http://localhost:8080")
        self.base_url = self.base_url.rstrip("/")
        self.api_key = api_key or os.getenv("HIVE_API_KEY")
        self.timeout = timeout
        self.retry_count = retry_count
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        """
        Check if the coordinator server is available.

        Returns:
            True if server responds to health check, False otherwise.
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            self._available = response.status_code == 200
            return self._available
        except requests.RequestException:
            self._available = False
            return False

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
    ) -> requests.Response:
        """
        Make a request to the coordinator server.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path
            json_data: JSON body data
            params: Query parameters

        Returns:
            Response object

        Raises:
            CoordinatorUnavailable: If the server cannot be reached
        """
        url = f"{self.base_url}{endpoint}"

        # Build headers with authentication if API key is available
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        for attempt in range(self.retry_count + 1):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    json=json_data,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )
                self._available = True
                return response
            except requests.RequestException as e:
                if attempt == self.retry_count:
                    self._available = False
                    raise CoordinatorUnavailable(
                        f"Coordinator server unavailable at {self.base_url}: {e}"
                    ) from e

        # Should not reach here, but satisfy type checker
        raise CoordinatorUnavailable(f"Failed to reach coordinator at {self.base_url}")

    def claim(
        self, project_id: str, agent_name: str, ttl_seconds: int = 3600, force: bool = False
    ) -> ClaimResult:
        """
        Claim a project for an agent.

        Args:
            project_id: The project ID to claim
            agent_name: The agent name claiming the project
            ttl_seconds: Time-to-live for the claim in seconds
            force: If True, override existing claims (admin use)

        Returns:
            ClaimResult with claim details or error information

        Raises:
            CoordinatorUnavailable: If the server cannot be reached
            ClaimConflict: If the project is already claimed (and not forcing)
        """
        response = self._request(
            method="POST",
            endpoint="/claim",
            json_data={
                "project_id": project_id,
                "agent_name": agent_name,
                "ttl_seconds": ttl_seconds,
            },
            params={"force": str(force).lower()} if force else None,
        )

        data = response.json()

        if response.status_code == 200:
            return ClaimResult(
                success=True,
                claim_id=data.get("claim_id"),
                project_id=data.get("project_id"),
                agent_name=data.get("agent_name"),
                expires_at=data.get("expires_at"),
            )

        if response.status_code == 409:
            raise ClaimConflict(
                message=data.get("error", "Project already claimed"),
                current_owner=data.get("current_owner", "unknown"),
                expires_at=data.get("expires_at", "unknown"),
            )

        return ClaimResult(success=False, error=data.get("error", f"HTTP {response.status_code}"))

    def release(self, project_id: str) -> bool:
        """
        Release a project claim.

        Args:
            project_id: The project ID to release

        Returns:
            True if released successfully, False if no claim existed

        Raises:
            CoordinatorUnavailable: If the server cannot be reached
        """
        response = self._request(method="DELETE", endpoint=f"/release/{project_id}")

        data = response.json()
        return data.get("success", False)

    def release_by_claim_id(self, claim_id: str) -> bool:
        """
        Release a project claim by claim ID.

        Args:
            claim_id: The claim ID to release

        Returns:
            True if released successfully, False if no claim existed

        Raises:
            CoordinatorUnavailable: If the server cannot be reached
        """
        response = self._request(method="DELETE", endpoint=f"/release/claim/{claim_id}")

        data = response.json()
        return data.get("success", False)

    def get_status(self, project_id: str) -> ClaimStatus:
        """
        Get the claim status of a project.

        Args:
            project_id: The project ID to check

        Returns:
            ClaimStatus with claim information

        Raises:
            CoordinatorUnavailable: If the server cannot be reached
        """
        response = self._request(method="GET", endpoint=f"/status/{project_id}")

        data = response.json()
        claim = data.get("claim")

        return ClaimStatus(
            project_id=data.get("project_id", project_id),
            is_claimed=data.get("is_claimed", False),
            claim_id=claim.get("claim_id") if claim else None,
            agent_name=claim.get("agent_name") if claim else None,
            created_at=claim.get("created_at") if claim else None,
            expires_at=claim.get("expires_at") if claim else None,
        )

    def get_all_reservations(self) -> Dict[str, Any]:
        """
        Get all active reservations.

        Returns:
            Dictionary with count and list of reservations

        Raises:
            CoordinatorUnavailable: If the server cannot be reached
        """
        response = self._request(method="GET", endpoint="/reservations")

        return response.json()

    def extend(self, project_id: str, ttl_seconds: int = 3600) -> bool:
        """
        Extend an existing claim's TTL.

        Args:
            project_id: The project ID to extend
            ttl_seconds: New TTL in seconds

        Returns:
            True if extended successfully, False otherwise

        Raises:
            CoordinatorUnavailable: If the server cannot be reached
        """
        response = self._request(
            method="POST", endpoint=f"/extend/{project_id}", params={"ttl_seconds": ttl_seconds}
        )

        if response.status_code == 200:
            return True
        return False

    def try_claim(self, project_id: str, agent_name: str, ttl_seconds: int = 3600) -> ClaimResult:
        """
        Try to claim a project, returning result without raising ClaimConflict.

        This is a convenience method that catches ClaimConflict and returns
        a result object instead, useful for callers that want to handle
        conflicts without exception handling.

        Args:
            project_id: The project ID to claim
            agent_name: The agent name claiming the project
            ttl_seconds: Time-to-live for the claim in seconds

        Returns:
            ClaimResult with success=True if claimed, or error info if not

        Raises:
            CoordinatorUnavailable: If the server cannot be reached
        """
        try:
            return self.claim(project_id, agent_name, ttl_seconds)
        except ClaimConflict as e:
            return ClaimResult(
                success=False, project_id=project_id, error=str(e), current_owner=e.current_owner
            )


def get_coordinator_client() -> Optional[CoordinatorClient]:
    """
    Get a coordinator client if configured.

    Returns:
        CoordinatorClient if COORDINATOR_URL is set, None otherwise.
    """
    url = os.getenv("COORDINATOR_URL")
    if url:
        api_key = os.getenv("HIVE_API_KEY")
        return CoordinatorClient(base_url=url, api_key=api_key)
    return None

#!/usr/bin/env python3
"""
Agent Hive Coordinator - Real-time Reservation Server

This module provides an optional real-time coordination layer for Agent Hive,
preventing multiple agents from claiming the same project simultaneously.

Inspired by beads' Agent Mail concept, this coordinator enables faster conflict
resolution than git-only coordination while remaining fully optional.

Security Note: This server now requires API key authentication via the
HIVE_API_KEY environment variable. Set this to a secure random value.
"""

import os
import uuid
import asyncio
import hmac
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# Configuration
DEFAULT_TTL_SECONDS = 3600  # 1 hour default claim TTL
MAX_TTL_SECONDS = 86400  # 24 hours maximum TTL

# Security configuration
HIVE_API_KEY = os.getenv("HIVE_API_KEY")
REQUIRE_AUTH = os.getenv("HIVE_REQUIRE_AUTH", "true").lower() == "true"

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> bool:
    """
    Verify the API key provided in the Authorization header.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        credentials: HTTP Bearer credentials from the request

    Returns:
        True if authentication passes

    Raises:
        HTTPException: If authentication fails
    """
    # Only allow unauthenticated access if BOTH auth is disabled AND no key is configured
    if (not REQUIRE_AUTH) and (not HIVE_API_KEY):
        return True

    # If auth is required but no API key is configured, fail securely
    if not HIVE_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: HIVE_API_KEY not set but authentication is required",
        )

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide Bearer token in Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(credentials.credentials.encode(), HIVE_API_KEY.encode()):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True


@dataclass
class Claim:
    """Represents a project claim/reservation."""

    claim_id: str
    project_id: str
    agent_name: str
    created_at: datetime
    expires_at: datetime

    def is_expired(self) -> bool:
        """Check if the claim has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert claim to dictionary."""
        return {
            "claim_id": self.claim_id,
            "project_id": self.project_id,
            "agent_name": self.agent_name,
            "created_at": self.created_at.isoformat() + "Z",
            "expires_at": self.expires_at.isoformat() + "Z",
        }


@dataclass
class ReservationStore:
    """In-memory store for project reservations."""

    claims: Dict[str, Claim] = field(default_factory=dict)  # project_id -> Claim
    claims_by_id: Dict[str, str] = field(default_factory=dict)  # claim_id -> project_id

    def get_claim(self, project_id: str) -> Optional[Claim]:
        """Get active claim for a project, removing if expired."""
        claim = self.claims.get(project_id)
        if claim and claim.is_expired():
            self._remove_claim(project_id)
            return None
        return claim

    def add_claim(self, claim: Claim) -> None:
        """Add a new claim."""
        self.claims[claim.project_id] = claim
        self.claims_by_id[claim.claim_id] = claim.project_id

    def _remove_claim(self, project_id: str) -> Optional[Claim]:
        """Internal method to remove a claim."""
        claim = self.claims.pop(project_id, None)
        if claim:
            self.claims_by_id.pop(claim.claim_id, None)
        return claim

    def remove_claim(self, project_id: str) -> Optional[Claim]:
        """Remove and return a claim."""
        return self._remove_claim(project_id)

    def remove_claim_by_id(self, claim_id: str) -> Optional[Claim]:
        """Remove a claim by its claim_id."""
        project_id = self.claims_by_id.get(claim_id)
        if project_id:
            return self._remove_claim(project_id)
        return None

    def get_all_active_claims(self) -> Dict[str, Claim]:
        """Get all non-expired claims."""
        # Clean up expired claims first
        expired = [pid for pid, claim in self.claims.items() if claim.is_expired()]
        for pid in expired:
            self._remove_claim(pid)
        return dict(self.claims)

    def cleanup_expired(self) -> int:
        """Remove all expired claims. Returns count of removed claims."""
        expired = [pid for pid, claim in self.claims.items() if claim.is_expired()]
        for pid in expired:
            self._remove_claim(pid)
        return len(expired)


# Global reservation store
store = ReservationStore()


# Pydantic models for request/response validation
class ClaimRequest(BaseModel):
    """Request model for claiming a project."""

    project_id: str = Field(..., description="The project ID to claim")
    agent_name: str = Field(..., description="The agent name claiming the project")
    ttl_seconds: int = Field(
        default=DEFAULT_TTL_SECONDS,
        ge=60,
        le=MAX_TTL_SECONDS,
        description=f"Time-to-live in seconds (60-{MAX_TTL_SECONDS})",
    )


class ClaimResponse(BaseModel):
    """Response model for successful claim."""

    success: bool = True
    claim_id: str
    project_id: str
    agent_name: str
    expires_at: str


class ConflictResponse(BaseModel):
    """Response model for claim conflict."""

    success: bool = False
    error: str
    current_owner: str
    claimed_at: str
    expires_at: str


class StatusResponse(BaseModel):
    """Response model for status check."""

    project_id: str
    is_claimed: bool
    claim: Optional[Dict[str, Any]] = None


class ReservationsResponse(BaseModel):
    """Response model for all reservations."""

    count: int
    reservations: list


class ReleaseResponse(BaseModel):
    """Response model for release operation."""

    success: bool
    project_id: Optional[str] = None
    message: str


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    active_claims: int
    uptime_seconds: float


# Track server start time
server_start_time: Optional[datetime] = None


async def cleanup_task():
    """Background task to periodically clean up expired claims."""
    while True:
        await asyncio.sleep(60)  # Run every minute
        removed = store.cleanup_expired()
        if removed > 0:
            print(f"Cleaned up {removed} expired claim(s)")


@asynccontextmanager
async def lifespan(app: FastAPI):  # pylint: disable=unused-argument,redefined-outer-name
    """Application lifespan handler for startup/shutdown tasks."""
    global server_start_time  # pylint: disable=global-statement
    server_start_time = datetime.now(timezone.utc)

    # Start background cleanup task
    task = asyncio.create_task(cleanup_task())
    print("Coordinator server started")

    yield

    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    print("Coordinator server stopped")


# Create FastAPI app
app = FastAPI(
    title="Agent Hive Coordinator",
    description="Real-time reservation server for agent coordination",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    uptime = 0.0
    if server_start_time:
        uptime = (datetime.now(timezone.utc) - server_start_time).total_seconds()

    return HealthResponse(
        status="healthy", active_claims=len(store.get_all_active_claims()), uptime_seconds=uptime
    )


@app.post(
    "/claim",
    response_model=ClaimResponse,
    responses={409: {"model": ConflictResponse}},
    dependencies=[Depends(verify_api_key)],
)
async def claim_project(request: ClaimRequest):
    """
    Claim a project for an agent.

    Requires authentication via Bearer token in Authorization header.
    Returns 409 Conflict if the project is already claimed by another agent.
    """
    existing_claim = store.get_claim(request.project_id)

    if existing_claim:
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "error": "Project already claimed",
                "current_owner": existing_claim.agent_name,
                "claimed_at": existing_claim.created_at.isoformat() + "Z",
                "expires_at": existing_claim.expires_at.isoformat() + "Z",
            },
        )

    # Create new claim
    now = datetime.now(timezone.utc)
    claim = Claim(
        claim_id=str(uuid.uuid4()),
        project_id=request.project_id,
        agent_name=request.agent_name,
        created_at=now,
        expires_at=now + timedelta(seconds=request.ttl_seconds),
    )

    store.add_claim(claim)

    return ClaimResponse(
        success=True,
        claim_id=claim.claim_id,
        project_id=claim.project_id,
        agent_name=claim.agent_name,
        expires_at=claim.expires_at.isoformat() + "Z",
    )


@app.delete(
    "/release/{project_id}",
    response_model=ReleaseResponse,
    dependencies=[Depends(verify_api_key)],
)
async def release_project(project_id: str):
    """Release a project claim by project_id. Requires authentication."""
    claim = store.remove_claim(project_id)

    if claim:
        return ReleaseResponse(
            success=True, project_id=project_id, message=f"Project '{project_id}' released"
        )

    return ReleaseResponse(
        success=False,
        project_id=project_id,
        message=f"No active claim found for project '{project_id}'",
    )


@app.delete(
    "/release/claim/{claim_id}",
    response_model=ReleaseResponse,
    dependencies=[Depends(verify_api_key)],
)
async def release_by_claim_id(claim_id: str):
    """Release a project claim by claim_id. Requires authentication."""
    claim = store.remove_claim_by_id(claim_id)

    if claim:
        return ReleaseResponse(
            success=True, project_id=claim.project_id, message=f"Claim '{claim_id}' released"
        )

    return ReleaseResponse(success=False, message=f"No claim found with id '{claim_id}'")


@app.get("/status/{project_id}", response_model=StatusResponse)
async def get_status(project_id: str):
    """Check the claim status of a project."""
    claim = store.get_claim(project_id)

    return StatusResponse(
        project_id=project_id,
        is_claimed=claim is not None,
        claim=claim.to_dict() if claim else None,
    )


@app.get("/reservations", response_model=ReservationsResponse)
async def get_reservations():
    """Get all active reservations."""
    claims = store.get_all_active_claims()

    return ReservationsResponse(
        count=len(claims), reservations=[claim.to_dict() for claim in claims.values()]
    )


@app.post("/extend/{project_id}", dependencies=[Depends(verify_api_key)])
async def extend_claim(project_id: str, ttl_seconds: int = Query(default=DEFAULT_TTL_SECONDS)):
    """Extend an existing claim's TTL. Requires authentication."""
    claim = store.get_claim(project_id)

    if not claim:
        raise HTTPException(
            status_code=404, detail=f"No active claim found for project '{project_id}'"
        )

    # Extend the expiration
    new_expires = datetime.now(timezone.utc) + timedelta(seconds=min(ttl_seconds, MAX_TTL_SECONDS))
    claim.expires_at = new_expires

    return {
        "success": True,
        "project_id": project_id,
        "new_expires_at": claim.expires_at.isoformat() + "Z",
    }


def main():
    """Run the coordinator server."""
    # Default to localhost for security (prevents external access)
    # Set COORDINATOR_HOST=0.0.0.0 to allow external connections
    host = os.getenv("COORDINATOR_HOST", "127.0.0.1")
    port = int(os.getenv("COORDINATOR_PORT", "8080"))

    # Security warning if binding to all interfaces
    if host == "0.0.0.0":
        if not HIVE_API_KEY:
            print("WARNING: Binding to all interfaces without HIVE_API_KEY set!")
            print("         Set HIVE_API_KEY environment variable for security.")
        if not REQUIRE_AUTH:
            print("WARNING: Authentication is disabled (HIVE_REQUIRE_AUTH=false)!")

    print(f"Starting Agent Hive Coordinator on {host}:{port}")
    print(f"Authentication: {'required' if REQUIRE_AUTH and HIVE_API_KEY else 'disabled'}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()

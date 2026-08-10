"""
MACI Custom Exception Hierarchy.

All exceptions inherit from MACIError so they can be caught uniformly
in FastAPI exception handlers. Each has an HTTP status code and a
machine-readable error code for the frontend.
"""

from fastapi import HTTPException, status


class MACIError(HTTPException):
    """Base exception for all MACI-specific errors."""

    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "An unexpected error occurred.",
        error_code: str = "INTERNAL_ERROR",
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code


# ── Auth Errors ──────────────────────────────────────────────────────

class InvalidCredentialsError(MACIError):
    def __init__(self, detail: str = "Invalid email or password.", error_code: str = "INVALID_CREDENTIALS"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code=error_code,
        )


class TokenExpiredError(MACIError):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            error_code="TOKEN_EXPIRED",
        )


class TokenInvalidError(MACIError):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed token.",
            error_code="TOKEN_INVALID",
        )


class DuplicateEmailError(MACIError):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
            error_code="DUPLICATE_EMAIL",
        )


# ── Resource Errors ──────────────────────────────────────────────────

class NotFoundError(MACIError):
    def __init__(self, resource: str = "Resource", identifier: str = ""):
        detail = f"{resource} not found."
        if identifier:
            detail = f"{resource} '{identifier}' not found."
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="NOT_FOUND",
        )


class ForbiddenError(MACIError):
    def __init__(self, detail: str = "You do not have access to this resource."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="FORBIDDEN",
        )


# ── Trip Errors ──────────────────────────────────────────────────────

class TripStateError(MACIError):
    """Raised when an action is invalid for the trip's current state."""

    def __init__(self, current_state: str, expected_states: list[str], action: str = ""):
        msg = f"Trip is in '{current_state}' state."
        if expected_states:
            msg += f" Expected one of: {expected_states}."
        if action:
            msg = f"Cannot {action}: {msg}"
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=msg,
            error_code="INVALID_TRIP_STATE",
        )


class IntakeClosedError(MACIError):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_410_GONE,
            detail="The intake period for this trip has closed.",
            error_code="INTAKE_CLOSED",
        )


class IntakeTokenInvalidError(MACIError):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired intake link.",
            error_code="INVALID_INTAKE_TOKEN",
        )


# ── Negotiation Errors ───────────────────────────────────────────────

class NegotiationExhaustedError(MACIError):
    """Raised when max negotiation rounds are exceeded without consensus."""

    def __init__(self, rounds: int):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to reach consensus after {rounds} negotiation rounds.",
            error_code="NEGOTIATION_EXHAUSTED",
        )


class NoViableFlightsError(MACIError):
    def __init__(self, cluster_key: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No viable flights found for cluster '{cluster_key}'.",
            error_code="NO_VIABLE_FLIGHTS",
        )


# ── Provider Errors ──────────────────────────────────────────────────

class FlightProviderError(MACIError):
    def __init__(self, provider: str, detail: str = "Flight provider request failed."):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"[{provider}] {detail}",
            error_code="PROVIDER_ERROR",
        )

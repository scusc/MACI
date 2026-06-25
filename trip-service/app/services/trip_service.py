"""
Trip Service — handles trip CRUD and lifecycle management.
"""

import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from maci_core.core.exceptions import NotFoundError, ForbiddenError, TripStateError
from maci_core.models.trip import Trip, TripStatus
from maci_core.models.traveler import Traveler
from maci_core.schemas.trip import TripCreateRequest, TripUpdateRequest, TripResponse, TripListResponse


async def create_trip(
    db: AsyncSession, org_id: uuid.UUID, request: TripCreateRequest
) -> TripResponse:
    """Create a new trip for an organization."""
    trip = Trip(
        org_id=org_id,
        title=request.title,
        description=request.description,
        destination_city=request.destination_city,
        destination_iata=request.destination_iata.upper(),
        arrival_date=request.arrival_date,
        return_date=request.return_date,
        max_arrival_spread_minutes=request.max_arrival_spread_minutes,
        friction_weight_cents=request.friction_weight_cents,
        max_travelers=request.max_travelers,
        intake_deadline=request.intake_deadline,
    )
    db.add(trip)
    await db.flush()

    return _trip_to_response(trip, traveler_count=0)


async def get_trip(
    db: AsyncSession, trip_id: uuid.UUID, org_id: uuid.UUID
) -> TripResponse:
    """Get a single trip by ID, scoped to the organization."""
    trip = await _get_trip_or_404(db, trip_id)
    _verify_ownership(trip, org_id)

    # Get traveler count
    count_stmt = select(func.count()).select_from(Traveler).where(Traveler.trip_id == trip_id)
    result = await db.execute(count_stmt)
    traveler_count = result.scalar_one()

    return _trip_to_response(trip, traveler_count=traveler_count)


async def list_trips(
    db: AsyncSession, org_id: uuid.UUID, offset: int = 0, limit: int = 50
) -> TripListResponse:
    """List all trips for an organization, ordered by creation date (newest first)."""
    # Get trips
    stmt = (
        select(Trip)
        .where(Trip.org_id == org_id)
        .order_by(Trip.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    trips = list(result.scalars().all())

    # Get total count
    count_stmt = select(func.count()).select_from(Trip).where(Trip.org_id == org_id)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Get traveler counts per trip (batch query to avoid N+1)
    trip_ids = [t.id for t in trips]
    if trip_ids:
        traveler_counts_stmt = (
            select(Traveler.trip_id, func.count().label("count"))
            .where(Traveler.trip_id.in_(trip_ids))
            .group_by(Traveler.trip_id)
        )
        traveler_result = await db.execute(traveler_counts_stmt)
        counts_map = {row.trip_id: row.count for row in traveler_result}
    else:
        counts_map = {}

    trip_responses = [
        _trip_to_response(trip, traveler_count=counts_map.get(trip.id, 0))
        for trip in trips
    ]

    return TripListResponse(trips=trip_responses, total=total)


async def update_trip(
    db: AsyncSession, trip_id: uuid.UUID, org_id: uuid.UUID, request: TripUpdateRequest
) -> TripResponse:
    """Update a trip. Only allowed in DRAFT or INTAKE_OPEN state."""
    trip = await _get_trip_or_404(db, trip_id)
    _verify_ownership(trip, org_id)

    if trip.status not in [TripStatus.DRAFT, TripStatus.INTAKE_OPEN]:
        raise TripStateError(
            current_state=trip.status,
            expected_states=[TripStatus.DRAFT, TripStatus.INTAKE_OPEN],
            action="update trip",
        )

    # Apply only the fields that were provided
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "destination_iata" and value:
            value = value.upper()
        setattr(trip, field, value)

    await db.flush()

    count_stmt = select(func.count()).select_from(Traveler).where(Traveler.trip_id == trip_id)
    result = await db.execute(count_stmt)
    traveler_count = result.scalar_one()

    return _trip_to_response(trip, traveler_count=traveler_count)


async def open_intake(
    db: AsyncSession, trip_id: uuid.UUID, org_id: uuid.UUID
) -> TripResponse:
    """Transition trip from DRAFT to INTAKE_OPEN (share the intake link)."""
    trip = await _get_trip_or_404(db, trip_id)
    _verify_ownership(trip, org_id)

    if trip.status != TripStatus.DRAFT:
        raise TripStateError(
            current_state=trip.status,
            expected_states=[TripStatus.DRAFT],
            action="open intake",
        )

    trip.status = TripStatus.INTAKE_OPEN
    await db.flush()

    return _trip_to_response(trip, traveler_count=0)


async def delete_trip(
    db: AsyncSession, trip_id: uuid.UUID, org_id: uuid.UUID
) -> None:
    """Delete a trip. Only allowed in DRAFT state."""
    trip = await _get_trip_or_404(db, trip_id)
    _verify_ownership(trip, org_id)

    if trip.status != TripStatus.DRAFT:
        raise TripStateError(
            current_state=trip.status,
            expected_states=[TripStatus.DRAFT],
            action="delete trip",
        )

    await db.delete(trip)
    await db.flush()


# ── Internal Helpers ─────────────────────────────────────────────────

async def _get_trip_or_404(db: AsyncSession, trip_id: uuid.UUID) -> Trip:
    """Fetch a trip by ID or raise NotFoundError."""
    stmt = select(Trip).where(Trip.id == trip_id)
    result = await db.execute(stmt)
    trip = result.scalar_one_or_none()
    if trip is None:
        raise NotFoundError("Trip", str(trip_id))
    return trip


def _verify_ownership(trip: Trip, org_id: uuid.UUID) -> None:
    """Verify the trip belongs to the organization."""
    if trip.org_id != org_id:
        raise ForbiddenError("You do not have access to this trip.")


def _trip_to_response(trip: Trip, traveler_count: int = 0) -> TripResponse:
    """Convert a Trip ORM model to a TripResponse schema."""
    return TripResponse(
        id=trip.id,
        org_id=trip.org_id,
        title=trip.title,
        description=trip.description,
        destination_city=trip.destination_city,
        destination_iata=trip.destination_iata,
        arrival_date=trip.arrival_date,
        return_date=trip.return_date,
        max_arrival_spread_minutes=trip.max_arrival_spread_minutes,
        friction_weight_cents=trip.friction_weight_cents,
        status=trip.status,
        intake_token=trip.intake_token,
        intake_deadline=trip.intake_deadline,
        max_travelers=trip.max_travelers,
        traveler_count=traveler_count,
        created_at=trip.created_at,
        updated_at=trip.updated_at,
    )

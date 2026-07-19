from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.models.models import User
from maci_core.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from maci_core.schemas.auth import (
    RallyRegisterRequest, LoginRequest, RallyAuthResponse, 
    TokenResponse, RallyUserResponse
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RallyAuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RallyRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user in Rally (e.g., an Organizer)."""
    # Check if user exists
    result = await db.execute(select(User).where(User.email == body.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        if existing_user.password_hash:
            raise HTTPException(status_code=400, detail="User already registered.")
        else:
            # User was created lazily via an invite. Update their profile with a password.
            existing_user.password_hash = hash_password(body.password)
            if body.display_name:
                existing_user.display_name = body.display_name
            if body.phone:
                existing_user.phone = body.phone
            user = existing_user
    else:
        # Create a brand new user
        user = User(
            email=body.email,
            password_hash=hash_password(body.password),
            display_name=body.display_name,
            phone=body.phone
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    # Generate JWT Tokens (org_id is user_id for Rally)
    access_token = create_access_token(org_id=user.id, email=user.email)
    refresh_token = create_refresh_token(org_id=user.id, email=user.email)

    return RallyAuthResponse(
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=900  # Default 15 mins
        ),
        user=RallyUserResponse.model_validate(user)
    )


@router.post("/login", response_model=RallyAuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email and password."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Generate JWT Tokens
    access_token = create_access_token(org_id=user.id, email=user.email)
    refresh_token = create_refresh_token(org_id=user.id, email=user.email)

    return RallyAuthResponse(
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=900
        ),
        user=RallyUserResponse.model_validate(user)
    )

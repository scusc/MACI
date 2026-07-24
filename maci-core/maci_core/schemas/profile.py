from pydantic import BaseModel, Field
from typing import Optional

class PsychometricQuizSubmit(BaseModel):
    # 1-10 Scales
    social_battery: int = Field(..., ge=1, le=10, description="1=Introvert, 10=Extrovert")
    budget_tolerance: int = Field(..., ge=1, le=10, description="1=Shoestring, 10=Luxury")
    pacing: int = Field(..., ge=1, le=10, description="1=Relaxed, 10=Packed")
    spontaneity: int = Field(..., ge=1, le=10, description="1=Rigid, 10=Spontaneous")
    conflict_style: int = Field(..., ge=1, le=10, description="1=Avoidant, 10=Direct")
    
    # Structured Bio
    travel_ethos: str = Field(..., max_length=500)
    dealbreakers: str = Field(..., max_length=500)

class PsychometricProfileResponse(BaseModel):
    social_battery: int
    budget_tolerance: int
    pacing: int
    spontaneity: int
    conflict_style: int
    structured_bio: dict
    profile_completeness_score: float

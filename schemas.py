"""
Database Schemas for Competitions Service

Each Pydantic model represents a MongoDB collection. Collection name is the
lowercased class name. These schemas are used for validation throughout the
backend.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

class Organizer(BaseModel):
    name: str = Field(..., description="Organizer display name")
    email: EmailStr = Field(..., description="Primary contact email")
    organization: Optional[str] = Field(None, description="Organization name")
    is_active: bool = Field(True, description="Whether organizer account is active")

class Event(BaseModel):
    organizer_id: str = Field(..., description="ID of the organizer who created this event")
    title: str = Field(..., description="Public event title")
    description: Optional[str] = Field(None, description="Event details")
    location: Optional[str] = Field(None, description="Venue or online link")
    start_at: Optional[datetime] = Field(None, description="Event start datetime (UTC)")
    end_at: Optional[datetime] = Field(None, description="Event end datetime (UTC)")
    capacity: Optional[int] = Field(None, ge=1, description="Max participants allowed")
    is_published: bool = Field(False, description="Whether event is visible to public")

class Participant(BaseModel):
    name: str = Field(..., description="Participant full name")
    email: EmailStr = Field(..., description="Participant email")

class Registration(BaseModel):
    event_id: str = Field(..., description="Event ID")
    participant_name: str = Field(..., description="Name provided at registration")
    participant_email: EmailStr = Field(..., description="Email provided at registration")
    status: str = Field("pending", description="Registration status: pending|confirmed|cancelled")
    confirmation_code: Optional[str] = Field(None, description="Generated confirmation code after processing")

class Job(BaseModel):
    type: str = Field(..., description="Job type, e.g., post_registration")
    payload: dict = Field(default_factory=dict, description="Arbitrary payload for job processing")
    status: str = Field("pending", description="pending|processing|done|failed")
    error: Optional[str] = None

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class RideStatus(str, Enum):
    PENDING = "PENDING"
    MATCHED = "MATCHED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class TripStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

# User Schemas
class UserBase(BaseModel):
    name: str
    email: str

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: str
    rating: float

    class Config:
        from_attributes = True

# Ride Request Schemas
class RideRequestCreate(BaseModel):
    user_id: str
    pickup_lat: float
    pickup_lon: float
    dropoff_lat: float
    dropoff_lon: float
    seats_needed: int = 1
    luggage_count: int = 0
    pickup_time_window_start: datetime
    pickup_time_window_end: datetime

class RideRequestResponse(RideRequestCreate):
    id: str
    status: RideStatus
    request_time: datetime
    trip_id: Optional[str] = None
    estimated_fare: Optional[float] = None

    class Config:
        from_attributes = True

# Trip Schemas
class TripBase(BaseModel):
    vehicle_id: str
    start_time: datetime
    origin_lat: float
    origin_lon: float
    destination_lat: float
    destination_lon: float

class TripResponse(TripBase):
    id: str
    status: TripStatus
    current_seat_load: int
    current_luggage_load: int

    class Config:
        from_attributes = True

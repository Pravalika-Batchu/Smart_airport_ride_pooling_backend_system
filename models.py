from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from database import Base
import datetime
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    rating = Column(Float, default=5.0)

class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(String, primary_key=True, default=generate_uuid)
    driver_name = Column(String)
    capacity_seats = Column(Integer, default=4)
    capacity_luggage = Column(Integer, default=4)
    license_plate = Column(String, unique=True)
    status = Column(String, default="AVAILABLE") # AVAILABLE, BUSY

class Trip(Base):
    __tablename__ = "trips"
    id = Column(String, primary_key=True, default=generate_uuid)
    vehicle_id = Column(String, ForeignKey("vehicles.id"))
    status = Column(String, default="SCHEDULED") # SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED
    
    current_seat_load = Column(Integer, default=0)
    current_luggage_load = Column(Integer, default=0)
    
    # Route info - Simplified as start/end generic for now, but in reality would have waypoints
    origin_lat = Column(Float)
    origin_lon = Column(Float)
    destination_lat = Column(Float)
    destination_lon = Column(Float)
    
    start_time = Column(DateTime)
    
    driver = relationship("Vehicle")
    orders = relationship("RideRequest", back_populates="trip")

class RideRequest(Base):
    __tablename__ = "ride_requests"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    trip_id = Column(String, ForeignKey("trips.id"), nullable=True)
    
    pickup_lat = Column(Float)
    pickup_lon = Column(Float)
    dropoff_lat = Column(Float)
    dropoff_lon = Column(Float)
    
    seats_needed = Column(Integer, default=1)
    luggage_count = Column(Integer, default=0)
    
    request_time = Column(DateTime, default=datetime.datetime.utcnow)
    pickup_time_window_start = Column(DateTime)
    pickup_time_window_end = Column(DateTime)
    
    status = Column(String, default="PENDING") # PENDING, MATCHED, COMPLETED, CANCELLED
    
    estimated_fare = Column(Float, nullable=True)

    trip = relationship("Trip", back_populates="orders")
    user = relationship("User")

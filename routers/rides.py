from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
import datetime

from database import get_db
from models import RideRequest, Trip, User, Vehicle
from schemas import RideRequestCreate, RideRequestResponse, TripResponse, UserCreate, TripStatus
from matching_engine import MatchingEngine

router = APIRouter(prefix="/rides", tags=["rides"])

@router.post("/request", response_model=RideRequestResponse)
async def create_ride_request(request: RideRequestCreate, db: AsyncSession = Depends(get_db)):
    # 1. Create the request object (Draft state)
    db_request = RideRequest(
        id=str(uuid.uuid4()),
        user_id=request.user_id,
        pickup_lat=request.pickup_lat,
        pickup_lon=request.pickup_lon,
        dropoff_lat=request.dropoff_lat,
        dropoff_lon=request.dropoff_lon,
        seats_needed=request.seats_needed,
        luggage_count=request.luggage_count,
        pickup_time_window_start=request.pickup_time_window_start,
        pickup_time_window_end=request.pickup_time_window_end,
        status="PENDING"
    )
    
    # Calculate initial estimate (assuming solo for now, update if shared later in complex flows)
    # We need a matcher instance to calc distance/price
    matcher = MatchingEngine(db)
    dist = matcher.calculate_distance(request.pickup_lat, request.pickup_lon, request.dropoff_lat, request.dropoff_lon)
    price = matcher.calculate_price(dist, is_shared=False, total_passengers=1) # Initial quote
    db_request.estimated_fare = price
    
    db.add(db_request)
    await db.commit()
    await db.refresh(db_request)
    
    # 2. Try to match
    
    match_found = False
    retry_count = 0
    
    while not match_found and retry_count < 3:
        matched_trip = await matcher.find_match(db_request)
        
        if matched_trip:
            # Try atomic booking
            success = await matcher.attempt_booking(db_request, matched_trip)
            if success:
                db_request.trip_id = matched_trip.id
                db_request.status = "MATCHED"
                match_found = True
            else:
                retry_count += 1 # Trip filled up while we were looking, retry
        else:
            break # No existing trips match, move to new trip creation

    if match_found:
        db.add(db_request)
        await db.commit()
    else:
        # Create new trip logic (Simplified for assignment: no race condition handling for vehicle allocation here)
        # In prod: use SELECT FOR UPDATE on Vehicle table or atomic update status
        new_trip = await matcher.create_new_trip(db_request)
        if new_trip:
            db_request.trip_id = new_trip.id
            db_request.status = "MATCHED"
            db.add(db_request)
            await db.commit()
        else:
            # No vehicles available, keep as PENDING
            pass
            
    await db.refresh(db_request)
    return db_request

@router.get("/{request_id}", response_model=RideRequestResponse)
async def get_ride_status(request_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RideRequest).where(RideRequest.id == request_id))
    ride = result.scalar_one_or_none()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride request not found")
    return ride

@router.post("/seed")
async def seed_data(db: AsyncSession = Depends(get_db)):
    """Helper to seed some vehicles and users"""
    try:
        # Check if data exists
        result = await db.execute(select(User).where(User.email == "test@example.com"))
        if result.scalar_one_or_none():
             return {"message": "Data already seeded"}
    
        # Create a vehicle
        v = Vehicle(id=str(uuid.uuid4()), driver_name="John Doe", license_plate="ABC-123", status="AVAILABLE")
        v2 = Vehicle(id=str(uuid.uuid4()), driver_name="Jane Smith", license_plate="XYZ-789", status="AVAILABLE")
        
        # Create a user
        u = User(id=str(uuid.uuid4()), name="Test User", email="test@example.com")
        
        db.add_all([v, v2, u])
        await db.commit()
        return {"message": "Seeded generic data"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to seed data: {str(e)}")

@router.post("/{request_id}/cancel", response_model=RideRequestResponse)
async def cancel_ride_request(request_id: str, db: AsyncSession = Depends(get_db)):
    # 1. Fetch request
    result = await db.execute(select(RideRequest).where(RideRequest.id == request_id))
    ride = result.scalar_one_or_none()
    
    if not ride:
        raise HTTPException(status_code=404, detail="Ride request not found")
        
    if ride.status in ["COMPLETED", "CANCELLED"]:
        raise HTTPException(status_code=400, detail="Ride cannot be cancelled in current state")
        
    # 2. Logic to free up space if matched
    if ride.status == "MATCHED" and ride.trip_id:
        trip_result = await db.execute(select(Trip).where(Trip.id == ride.trip_id))
        trip = trip_result.scalar_one_or_none()
        
        if trip:
            # Atomic decrement (or just standard decrement inside transaction)
            trip.current_seat_load -= ride.seats_needed
            trip.current_luggage_load -= ride.luggage_count
            db.add(trip)
            
    
    # 3. Update status
    ride.status = "CANCELLED"
    db.add(ride)
    await db.commit()
    await db.refresh(ride)
    
    return ride

async def create_new_trip(self, request: RideRequest) -> Trip:
    # Find an available vehicle
    stmt = select(Vehicle).where(Vehicle.status == "AVAILABLE").limit(1)
    result = await self.db.execute(stmt)
    vehicle = result.scalar_one_or_none()
        
    if not vehicle:
        return None # No vehicles available
            
    # Create Trip
    new_trip = Trip(
        id=str(uuid.uuid4()),
        vehicle_id=vehicle.id,
        status="SCHEDULED",
        current_seat_load=request.seats_needed,
        current_luggage_load=request.luggage_count,
        origin_lat=request.pickup_lat,
        origin_lon=request.pickup_lon,
        destination_lat=request.dropoff_lat,
        destination_lon=request.dropoff_lon,
        start_time=request.pickup_time_window_start
    )
        
    # Mark vehicle as BUSY
    vehicle.status = "BUSY"
    self.db.add(vehicle)
    self.db.add(new_trip)
    await self.db.commit()
    await self.db.refresh(new_trip)
        
    return new_trip

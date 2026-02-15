import uuid
import math
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from models import Trip, RideRequest, Vehicle

class MatchingEngine:
    """
    Core engine responsible for grouping ride requests into safe, efficient trips.
    Implements a Greedy Heuristic approach with spatial clustering.
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.MAX_DETOUR_KM = 2.0  # Configurable threshold for max deviation
        self.MAX_WAIT_TIME_MINS = 15

    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculates Haversine distance between two coordinates in kilometers.
        """
        if not all([lat1, lon1, lat2, lon2]):
            return 0.0
            
        R = 6371  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) * math.sin(dlon / 2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c

    async def find_match(self, request: RideRequest) -> Optional[Trip]:
        """
        Attempts to find an existing Trip that can accommodate the new request.
        
        Matching Strategy:
        1. **Capacity Check**: Filter active trips with available seats and luggage space.
        2. **Spatial Clustering**: Check if Trip origin/destination is within acceptable range (5km) of request.
           This serves as a proxy for "Directionality" in this implementation.
        3. **Detour Minimization**: Select the trip that minimizes additional travel time (approximated by distance).
        """
        
        # 1. Fetch active trips with physical capacity
        # We assume standard vehicle capacity (4 pax) for this implementation, 
        # but this could be dynamic based on Vehicle properties.
        stmt = select(Trip).where(
            Trip.status.in_(["SCHEDULED", "IN_PROGRESS"]),
            Trip.current_seat_load + request.seats_needed <= 4,
            Trip.current_luggage_load + request.luggage_count <= 4
        )
        
        result = await self.db.execute(stmt)
        candidate_trips = result.scalars().all()
        
        best_trip = None
        min_detour = float('inf')
        
        for trip in candidate_trips:
            # 2. Check Spatial Constraint (Clustering)
            # We calculate a 'proximity score' based on how close the pickup/dropoff points are.
            origin_dist = self.calculate_distance(request.pickup_lat, request.pickup_lon, trip.origin_lat, trip.origin_lon)
            dest_dist = self.calculate_distance(request.dropoff_lat, request.dropoff_lon, trip.destination_lat, trip.destination_lon)
            
            total_proximity_score = origin_dist + dest_dist
            
            # Simple heuristic: If the new passenger is within 5km of the current trip's path, it's a candidate.
            if total_proximity_score < 5.0: 
                if total_proximity_score < min_detour:
                    min_detour = total_proximity_score
                    best_trip = trip
        
        return best_trip

    async def attempt_booking(self, request: RideRequest, trip: Trip) -> bool:
        """
        Executes a safe booking using an Atomic Update (Optimistic Locking).
        Ensures we don't overbook a trip even under high concurrency.
        
        Returns:
            bool: True if booking was successful, False if capacity was lost during processing.
        """
        stmt = update(Trip).where(
            Trip.id == trip.id,
            Trip.current_seat_load + request.seats_needed <= 4, 
            Trip.current_luggage_load + request.luggage_count <= 4
        ).values(
            current_seat_load=Trip.current_seat_load + request.seats_needed,
            current_luggage_load=Trip.current_luggage_load + request.luggage_count
        )
        
        result = await self.db.execute(stmt)
        if result.rowcount == 0:
            return False # Race condition: Failed to update
            
        await self.db.commit()
        return True

    def calculate_price(self, distance_km: float, is_shared: bool, total_passengers: int) -> float:
        """
        Computes dynamic pricing based on distance and sharing.
        Formula: (Base + Rate*Dist) * (1 - Discount)
        """
        base_rate = 2.0
        base_fare = 10.0
        
        price = base_fare + (distance_km * base_rate)
        
        if is_shared and total_passengers > 1:
            # incentivize pooling with a discount
            discount_factor = 0.10 * (total_passengers - 1)
            discount_factor = min(discount_factor, 0.50) # Cap at 50%
            price = price * (1 - discount_factor)
            
        return round(price, 2)

    async def create_new_trip(self, request: RideRequest) -> Optional[Trip]:
        """
        Allocates a new Vehicle and creates a Trip.
        """
        # 1. Find an available vehicle
        stmt = select(Vehicle).where(Vehicle.status == "AVAILABLE").limit(1)
        result = await self.db.execute(stmt)
        vehicle = result.scalar_one_or_none()
        
        if not vehicle:
            return None # Resource exhaustion
            
        # 2. Create the Trip record
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
        
        # 3. Mark vehicle as BUSY to prevent double allocation
        vehicle.status = "BUSY"
        self.db.add(vehicle)
        self.db.add(new_trip)
        await self.db.commit()
        await self.db.refresh(new_trip)
        
        return new_trip
 
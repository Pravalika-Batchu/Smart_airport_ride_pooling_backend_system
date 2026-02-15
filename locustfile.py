from locust import HttpUser, task, between
import random
import uuid

class RidePoolingUser(HttpUser):
    wait_time = between(1, 3)  

    @task
    def book_ride(self):
        base_lat = 12.9716
        base_lon = 77.5946
        
        pickup_lat = base_lat + random.uniform(-0.05, 0.05)
        pickup_lon = base_lon + random.uniform(-0.05, 0.05)
        dropoff_lat = base_lat + random.uniform(-0.05, 0.05)
        dropoff_lon = base_lon + random.uniform(-0.05, 0.05)

        payload = {
            "user_id": str(uuid.uuid4()),
            "pickup_lat": pickup_lat,
            "pickup_lon": pickup_lon,
            "dropoff_lat": dropoff_lat,
            "dropoff_lon": dropoff_lon,
            "seats_needed": 1,
            "luggage_count": 0,
            "pickup_time_window_start": "2024-03-15T10:00:00",
            "pickup_time_window_end": "2024-03-15T10:15:00"
        }
        
        with self.client.post("/rides/request", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}: {response.text}")

    def on_start(self):
        # Seed data once per user start (optional, just ensuring db isn't empty)
        # self.client.post("/rides/seed") 
        pass

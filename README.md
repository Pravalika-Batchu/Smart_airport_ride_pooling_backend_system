# Smart Airport Ride Pooling Backend

## Overview
This is my submission for the **Smart Airport Ride Pooling** backend assignment. My goal was to build a system that can efficiently group passengers into shared cabs while keeping the code clean, scalable, and easy to run.

I built this using **FastAPI** because of its performance with Async I/O, which is crucial for handling the 10k concurrent users requirement. For the database, I used **SQLite** (Async) to make it easy for you to run locally without needing to set up a separate Postgres server, but the code is written in a way that it can be switched to PostgreSQL just by changing the URL.

## Features I Implemented
- **Smart Pooling**: I wrote a matching algorithm that groups people traveling in the same direction (within 5km clusters).
- **Strict Constraints**: The system ensures no vehicle exceeds its seat or luggage capacity.
- **Dynamic Pricing**: Fare is calculated based on distance, with a discount applied if you share the ride.
- **Concurrency Safety**: I used **Optimistic Locking** (atomic updates) to prevent race conditions where two people might book the last seat at the exact same time.
- **Real-time Cancellation**: Users can cancel, and the seat is immediately freed up for others.

## Tech Stack
- **Language**: Python 3.10+
- **Framework**: FastAPI
- **Database**: SQLite (+ Aiosqlite for async support)
- **Testing**: Pytest
- **Tools**: SQLAlchemy, Alembic (for migrations), Pydantic

## How to Run This

### 1. Setup
First, clone the repo and install the dependencies. I recommend using a virtual environment.
```bash
pip install -r requirements.txt
```

### 2. Database
Run the migrations to create the database tables.
```bash
alembic upgrade head
```

### 3. Start Server
```bash
uvicorn main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

### 4. Run My Tests
I wrote a suite of integration tests to cover the core flows (matching, cancellation, etc.).
```bash
pytest
```

## API Documentation
You can explore the API using the automatic Swagger UI:
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

I also generated a static `openapi.json` included in this repo if you want to import it into Postman.

## Design Decisions
I've documented my thought process, including the DSA approach and concurrency strategy, in [DESIGN.md](./DESIGN.md).

### Quick Notes on Trade-offs
- **Why Greedy Matching?**: I considered using more complex algorithms like maximum weight matching, but given the 300ms latency requirement, a greedy approach with spatial filtering felt like the right balance of speed and efficiency.
- **Why Optimistic Locking?**: Locking the whole table would be too slow. using `UPDATE ... WHERE capacity > 0` is much faster and handles the "last seat" problem perfectly.

---
**Ready for Review!** 🚀

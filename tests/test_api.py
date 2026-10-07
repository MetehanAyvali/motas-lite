import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
from fastapi.testclient import TestClient
from app.main import app, Base, engine

client = TestClient(app)

def setup_module():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

def test_health():
    assert client.get("/health").json() == {"status": "ok"}

def _trip(v, d, s, e):
    return client.post("/trips", json={"vehicle_id": v, "driver_id": d, "start": s, "end": e})

def test_trip_rules():
    v = client.post("/vehicles", json={"plate": "44 AB 123"}).json()["id"]
    old = client.post("/vehicles", json={"plate": "44 CD 456", "km": 20000}).json()["id"]
    d = client.post("/drivers", json={"name": "Ali"}).json()["id"]
    
    assert _trip(v, d, "2026-01-01T08:00:00", "2026-01-01T09:00:00").status_code == 201
    assert _trip(v, d, "2026-01-01T08:30:00", "2026-01-01T09:30:00").status_code == 409 # çakışma
    assert _trip(old, d, "2026-01-01T12:00:00", "2026-01-01T13:00:00").status_code == 409 # bakım


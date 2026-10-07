import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import ForeignKey, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
MAINTENANCE_INTERVAL_KM = 10_000

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(unique=True)
    km: Mapped[int] = mapped_column(default=0)
    last_service_km: Mapped[int] = mapped_column(default=0)


class Driver(Base):
    __tablename__ = "drivers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]


class Trip(Base):
    __tablename__ = "trips"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"))
    start: Mapped[datetime]
    end: Mapped[datetime]


class VehicleIn(BaseModel):
    plate: str
    km: int = 0
    last_service_km: int = 0


class DriverIn(BaseModel):
    name: str


class TripIn(BaseModel):
    vehicle_id: int
    driver_id: int
    start: datetime
    end: datetime


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="MOTAŞ-lite Filo Yönetimi", lifespan=lifespan)


def get_db():
    with SessionLocal() as db:
        yield db


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}


@app.post("/vehicles", status_code=201)
def create_vehicle(v: VehicleIn, db: Session = Depends(get_db)):
    if db.scalar(select(Vehicle).where(Vehicle.plate == v.plate)):
        raise HTTPException(409, "Bu plaka zaten kayıtlı")
    obj = Vehicle(**v.model_dump())
    db.add(obj)
    db.commit()
    return {"id": obj.id, **v.model_dump()}


@app.get("/vehicles")
def list_vehicles(db: Session = Depends(get_db)):
    return [
        {
            "id": x.id, "plate": x.plate, "km": x.km,
            "maintenance_due": x.km - x.last_service_km >= MAINTENANCE_INTERVAL_KM,
        }
        for x in db.scalars(select(Vehicle))
    ]


@app.post("/drivers", status_code=201)
def create_driver(d: DriverIn, db: Session = Depends(get_db)):
    obj = Driver(name=d.name)
    db.add(obj)
    db.commit()
    return {"id": obj.id, "name": obj.name}


@app.post("/trips", status_code=201)
def create_trip(t: TripIn, db: Session = Depends(get_db)):
    if t.end <= t.start:
        raise HTTPException(422, "Bitiş, başlangıçtan sonra olmalı")
    vehicle = db.get(Vehicle, t.vehicle_id)
    if not vehicle or not db.get(Driver, t.driver_id):
        raise HTTPException(404, "Araç veya sürücü bulunamadı")
    # İş kuralı 1: bakımı gelen araca sefer atanmaz
    if vehicle.km - vehicle.last_service_km >= MAINTENANCE_INTERVAL_KM:
        raise HTTPException(409, "Araç bakım zamanı gelmiş, sefer atanamaz")
    # İş kuralı 2: aynı sürücü/araç çakışan iki sefere atanamaz
    overlap = db.scalar(
        select(Trip).where(
            (Trip.start < t.end) & (Trip.end > t.start)
            & ((Trip.driver_id == t.driver_id) | (Trip.vehicle_id == t.vehicle_id))
        )
    )
    if overlap:
        raise HTTPException(409, "Sürücü veya araç bu saatte başka bir seferde")
    obj = Trip(**t.model_dump())
    db.add(obj)
    db.commit()
    return {"id": obj.id}

from sqlalchemy import Column, Integer, Float, String
from .db import Base

class Route(Base):
    __tablename__ = "routes"
    id = Column(Integer, primary_key=True, index=True)
    start_lat = Column(Float, nullable=False)
    start_lng = Column(Float, nullable=False)
    end_lat = Column(Float, nullable=False)
    end_lng = Column(Float, nullable=False)
    depart_time = Column(String, nullable=False)
    max_detour_km = Column(Float, default=2.0)
    status = Column(String, default="active")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    pickup_lat = Column(Float, nullable=False)
    pickup_lng = Column(Float, nullable=False)
    drop_lat = Column(Float, nullable=False)
    drop_lng = Column(Float, nullable=False)
    ready_from = Column(String, nullable=False)
    due_by = Column(String, nullable=False)
    payout = Column(Float, default=3.0)
    priority = Column(Integer, default=0)
    status = Column(String, default="open")

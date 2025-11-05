from pydantic import BaseModel, Field

class CreateRoute(BaseModel):
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    depart_time: str
    max_detour_km: float = Field(2.0, ge=0)

class RouteOut(BaseModel):
    id: int
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    depart_time: str
    max_detour_km: float
    status: str
    class Config:
        from_attributes = True

class CreateOrder(BaseModel):
    pickup_lat: float
    pickup_lng: float
    drop_lat: float
    drop_lng: float
    ready_from: str
    due_by: str
    payout: float = 3.0
    priority: int = 0

class OrderOut(BaseModel):
    id: int
    pickup_lat: float
    pickup_lng: float
    drop_lat: float
    drop_lng: float
    ready_from: str
    due_by: str
    payout: float
    priority: int
    status: str
    class Config:
        from_attributes = True

class MatchOut(BaseModel):
    order: OrderOut
    added_km: float
    added_min: float
    score: float

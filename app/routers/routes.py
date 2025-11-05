from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db, Base, engine
from .. import models, schemas
Base.metadata.create_all(bind=engine)
router = APIRouter()

@router.post("", response_model=schemas.RouteOut)
def create_route(payload: schemas.CreateRoute, db: Session = Depends(get_db)):
    r = models.Route(**payload.model_dump(), status="active")
    db.add(r); db.commit(); db.refresh(r); return r

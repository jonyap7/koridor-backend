from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db, Base, engine
from .. import models, schemas
Base.metadata.create_all(bind=engine)
router = APIRouter()

@router.post("", response_model=schemas.OrderOut)
def create_order(p: schemas.CreateOrder, db: Session = Depends(get_db)):
    o = models.Order(**p.model_dump(), status="open")
    db.add(o); db.commit(); db.refresh(o); return o

@router.get("", response_model=list[schemas.OrderOut])
def list_orders(db: Session = Depends(get_db)):
    return db.query(models.Order).filter(models.Order.status=="open").all()

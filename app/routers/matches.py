from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db, Base, engine
from .. import models, schemas
from ..utils import marginal_cost_km, estimate_minutes
Base.metadata.create_all(bind=engine)
router = APIRouter()

@router.get("/{route_id}/matches", response_model=list[schemas.MatchOut])
def get_matches(route_id:int, db:Session=Depends(get_db)):
    route=db.query(models.Route).filter(models.Route.id==route_id, models.Route.status=="active").first()
    if not route: raise HTTPException(404,"Route not found")
    start=(route.start_lat, route.start_lng); end=(route.end_lat, route.end_lng)
    out=[]
    for o in db.query(models.Order).filter(models.Order.status=="open").all():
        added=marginal_cost_km(start,(o.pickup_lat,o.pickup_lng),(o.drop_lat,o.drop_lng),end)
        if added<=route.max_detour_km:
            mins=estimate_minutes(added)
            score=1/(added+1)+o.payout*0.1+o.priority*0.2
            out.append(
                schemas.MatchOut(order=schemas.OrderOut.model_validate(o), added_km=round(added,2), added_min=round(mins,1), score=round(score,3))
            )
    return sorted(out, key=lambda x: x.score, reverse=True)

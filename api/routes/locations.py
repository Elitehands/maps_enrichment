from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from api.db import get_session
from api.models import Location, Company

router = APIRouter()

@router.get("/api/locations", response_class=JSONResponse)
def list_locations(db = Depends(get_session)):
    stmt = select(Location, Company).join(Company, Company.id == Location.company_id)
    rows = db.execute(stmt).all()
    collection = {"type": "FeatureCollection", "features": []}
    for loc, comp in rows:
        if loc.latitude is None or loc.longitude is None:
            continue
        collection["features"].append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [loc.longitude, loc.latitude]
            },
            "properties": {
                "id": loc.id,
                "id": loc.id,
                "company": comp.name,
                "entity_type": loc.entity_type,
                "country": loc.country,
                "state": loc.state,
                "state_code": loc.state_code,
                "county": loc.county,
                "postcode": loc.postcode,
                "duns_number": loc.duns_number,
                "source": loc.source,
                "source_ref": loc.source_ref
            }
        })
    return collection
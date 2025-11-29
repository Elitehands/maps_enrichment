from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from api.db import get_session
from api.models import Feature
from geoalchemy2.shape import to_shape

router = APIRouter()

@router.get("/api/geodata", response_class=JSONResponse)
async def read_geodata(db = Depends(get_session)):
    features = db.execute(select(Feature)).scalars().all()
    collection = {"type": "FeatureCollection", "features": []}
    for f in features:
        geom = to_shape(f.geometry)
        collection["features"].append({
            "type": "Feature",
            "geometry": geom.__geo_interface__,
            "properties": {
                "id": f.id,
                "location_id": f.location_id,
                "osm_id": f.osm_id,
                "osm_type": f.osm_type,
                "address": f.address,
                "data_source": f.data_source
            }
        })
    return collection

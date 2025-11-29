from sqlalchemy import select
from shapely.geometry import shape, box
from geoalchemy2.shape import from_shape
from api.models import Company, Location, Feature

def get_or_create_company(db, name: str):
    stmt = select(Company).where(Company.name == name)
    obj = db.execute(stmt).scalar_one_or_none()
    if obj:
        return obj
    obj = Company(name=name)
    db.add(obj)
    db.flush()
    return obj

def get_or_create_location(db, company_id: int, lat: float | None, lon: float | None, **kw):
    """Create a location unless an identical (company + lat/lon) one exists.
    Additional metadata passed via **kw (entity_type, country, duns_number, state,...)."""
    if lat is not None and lon is not None:
        stmt = select(Location).where(
            Location.company_id == company_id,
            Location.latitude == lat,
            Location.longitude == lon
        )
        existing = db.execute(stmt).scalar_one_or_none()
        if existing:
            return existing
    obj = Location(company_id=company_id, latitude=lat, longitude=lon, **kw)
    db.add(obj)
    db.flush()
    return obj

def insert_feature(db, location_id: int, feature_dict: dict, data_source: str):
    geom_geojson = feature_dict.get("geometry")
    if not geom_geojson:
        return
    shp = shape(geom_geojson)
    geom = from_shape(shp, srid=4326)
    minx, miny, maxx, maxy = shp.bounds
    bbox_geom = from_shape(box(minx, miny, maxx, maxy), srid=4326)
    props = feature_dict.get("properties", {})
    f = Feature(
        location_id=location_id,
        osm_id=props.get("osm_id"),
        osm_type=props.get("osm_type"),
        address=props.get("address") or props.get("display_name"),
        geometry=geom,
        bbox=bbox_geom,
        data_source=data_source
    )
    db.add(f)

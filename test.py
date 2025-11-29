import os
from pprint import pprint

# Optional: speed up by bypassing external geocoding / Overpass
os.environ.setdefault("FAST_TEST", "1")

from fastapi.testclient import TestClient
from api import main
from sqlalchemy import select, func
from api.db import get_session
from api.models import Company, Location, Feature
from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon

# Monkeypatch seed functions if FAST_TEST enabled
if os.getenv("FAST_TEST") == "1":
    def _fake_csv():
        return [{
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[0,0],[0,1],[1,1],[1,0],[0,0]]]},
            "properties": {
                "company_name": "TestCo",
                "entity_type": "Factory",
                "country": "United Kingdom",
                "country_code": "GB"
            }
        }]
    def _fake_us(_filter: str):
        return []
    main.load_geodata_csv = _fake_csv
    main.get_us_locations = _fake_us

client = TestClient(main.app)

# Deterministic manual seed (independent of lifespan) if empty
def manual_seed():
    db = get_session()
    try:
        loc_count = db.execute(select(func.count()).select_from(Location)).scalar()
        if loc_count == 0:
            company = Company(name="DemoCo")
            db.add(company); db.flush()
            loc = Location(
                company_id=company.id,
                entity_type="Demo",
                country="United Kingdom",
                country_code="GB",
                latitude=51.5,
                longitude=-0.12,
                source="test",
                source_ref="demo1"
            )
            db.add(loc); db.flush()
            try:
                poly = Polygon([(-0.13,51.49),(-0.13,51.51),(-0.11,51.51),(-0.11,51.49),(-0.13,51.49)])
                feat = Feature(
                    location_id=loc.id,
                    osm_id=None,
                    osm_type=None,
                    address="Demo Area",
                    geometry=from_shape(poly, srid=4326),
                    bbox=from_shape(poly.envelope, srid=4326),
                    data_source="test"
                )
                db.add(feat)
            except Exception as e:
                print("Feature seed skipped (likely PostGIS missing):", e)
            db.commit()
    finally:
        db.close()

manual_seed()

def check_locations():
    r = client.get("/api/locations")
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "FeatureCollection"
    if data["features"]:
        f = data["features"][0]
        assert f["geometry"]["type"] == "Point"
        assert "company" in f["properties"]
    return data

def check_features():
    r = client.get("/api/geodata")
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "FeatureCollection"
    if data["features"]:
        f = data["features"][0]
        assert "geometry" in f
        assert "properties" in f
    return data

if __name__ == "__main__":
    locs = check_locations()
    feats = check_features()
    print("Locations sample:")
    pprint(locs["features"][:1])
    print("Features sample:")
    pprint(feats["features"][:1])
    print("OK")
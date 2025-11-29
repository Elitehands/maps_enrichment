import pycountry
import api.geocode.geocode_utils as osm
import time
import os
import json

# All imports with api.* are added for production purposes as imports fail without it
from fastapi import FastAPI
from api.routes.geodata import router as polygon_router
from api.routes.locations import router as locations_router
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from api.config import GEODATA_PATH, LOCATIONS_PATH_EXCEL, LOCATIONS_PATH_CSV, CORP_CSV_PATH
from api.db import get_session
from api.models import Base
from api.crud import get_or_create_company, get_or_create_location, insert_feature
from sqlalchemy import select, func, text
from api.loaders.corp_csv import load_clean_dataframe, iter_location_rows


async def load_geodata_excel():
    if not os.path.exists(GEODATA_PATH):
        output = {}
        df = osm.get_filtered_dataset(LOCATIONS_PATH_EXCEL, "`P1L_Counrty` == 'UK'", 'excel')
        if df is not None:
            for _, rows in df.iterrows():
                plus_code = rows['GOOGLE LOC'].split(' ')[0]
                post_code = rows['P1L_Postcode']
                lat_lon = osm.plus_code_decoder(plus_code, post_code)
                time.sleep(2) # avoid rate limiting
                if type(lat_lon) is tuple:
                    lat, lon = lat_lon
                    data = osm.overpass_fetch_nearest_feature(lat, lon)
                    time.sleep(1) # avoid rate limiting
                    if type(data) is osm.GeoData:
                        # Seed data with company-specific info to properties
                        data.properties.company_name = rows['P1L_Name']
                        data.properties.entity_type = rows.fillna('')["P1L_Type"]
                        data.properties.country = rows['P1L_Counrty']
                        # Create feature collection
                        output['type'] = "FeatureCollection"
                        if 'features' not in output:
                            output['features'] = []
                        output['features'].append(data.model_dump())
            with open(GEODATA_PATH, "w") as geocode:
                json.dump(output, geocode, indent=4)
                print(f"Successfully dumped JSON data to {GEODATA_PATH}")

async def load_geodata_csv():
    output = []
    df = osm.get_filtered_dataset(LOCATIONS_PATH_CSV, "`Country/Region` == 'United Kingdom'", 'csv')
    if df is not None:
        for _, rows in df.iterrows():
            lon = rows["Longitude"]
            lat = rows["Latitude"]
            data = osm.geocode_nominatim_boundary(lat, lon)
            time.sleep(1) # avoid rate limiting
            if type(data) is osm.GeoData:
                # Seed data with company-specific info to properties
                data.properties.company_name = rows['Company Name'].capitalize()
                data.properties.entity_type = rows["Entity Type"].capitalize()
                # Create feature collection
                output.append(data.model_dump())
    return output

async def get_us_locations(filter: str):
    us_states = [sub.code for sub in pycountry.subdivisions if sub.country_code == "US"] # type: ignore
    output = []
    for state in us_states:
        data = osm.overpass_get_locations(state, filter)
        if type(data) is list:
            for feature in data:
                output.append(feature.model_dump())
    return output

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_session()
    Base.metadata.create_all(bind=db.get_bind())

    # Ensure new columns exist (idempotent, simple check)
    existing_cols = {row[0] for row in db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='locations'"))}
    alter_parts = []
    for col_def in [
        ("duns_number", "TEXT"),
        ("state", "TEXT"),
        ("state_code", "TEXT"),
        ("county", "TEXT"),
        ("postcode", "TEXT")
    ]:
        if col_def[0] not in existing_cols:
            alter_parts.append(f"ADD COLUMN {col_def[0]} {col_def[1]}")
    if alter_parts:
        db.execute(text(f"ALTER TABLE locations {', '.join(alter_parts)}"))
        db.commit()

    # Seed corporate locations if empty and file available
    location_count = db.execute(select(func.count()).select_from(Base.metadata.tables['locations'])).scalar()
    if location_count == 0 and CORP_CSV_PATH.exists():
        try:
            corp_df = load_clean_dataframe(CORP_CSV_PATH)
            for row in iter_location_rows(corp_df):
                company = get_or_create_company(db, row["company_name"] or "Unknown")
                lat = row.get("latitude")
                lon = row.get("longitude")
                get_or_create_location(
                    db,
                    company.id,
                    float(lat) if lat is not None else None,
                    float(lon) if lon is not None else None,
                    entity_type=row.get("entity_type"),
                    country=row.get("country"),
                    country_code=row.get("state_code"),
                    postcode=row.get("postcode"),
                    plus_code=None,
                    duns_number=row.get("duns_number"),
                    state=row.get("state"),
                    state_code=row.get("state_code"),
                    county=row.get("county"),
                    source=row.get("source"),
                    source_ref=row.get("source_ref")
                )
            db.commit()
            print("Seeded corporate locations from CSV")
        except Exception as e:
            print(f"Corporate CSV seeding failed: {e}")

    # Seed features if none exist (retains original behavior)
    feature_count = db.execute(select(func.count()).select_from(Base.metadata.tables['features'])).scalar()
    if feature_count == 0:
        csv_data = await load_geodata_csv()
        overpass_data = await get_us_locations("^(Nestl(e[\u0301]?|é)( |$).*|Purina$|Nespresso$)")

        for feature in csv_data:
            props = feature.get("properties", {})
            company = get_or_create_company(db, props.get("company_name") or "Unknown")
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates", [None, None])
            lon = coords[0] if isinstance(coords, list) else None
            lat = coords[1] if isinstance(coords, list) else None
            loc = get_or_create_location(
                db,
                company.id,
                lat,
                lon,
                entity_type=props.get("entity_type"),
                country=props.get("country"),
                country_code=props.get("country_code"),
                postcode=props.get("postcode"),
                plus_code=props.get("plus_code"),
                source="uk_csv",
                source_ref=props.get("source_ref")
            )
            insert_feature(db, loc.id, feature, data_source="nominatim")

        for feature in overpass_data:
            props = feature.get("properties", {})
            company = get_or_create_company(db, props.get("company_name") or "Unknown")
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates", [None, None])
            lon = coords[0] if isinstance(coords, list) else None
            lat = coords[1] if isinstance(coords, list) else None
            loc = get_or_create_location(
                db,
                company.id,
                lat,
                lon,
                entity_type=props.get("entity_type"),
                country=props.get("country"),
                country_code=props.get("country_code"),
                postcode=props.get("postcode"),
                plus_code=props.get("plus_code"),
                source="overpass_us",
                source_ref=str(props.get("osm_id"))
            )
            insert_feature(db, loc.id, feature, data_source="overpass")

        db.commit()
        output = {"type": "FeatureCollection", "features": csv_data + overpass_data}
        with open(GEODATA_PATH, "w") as geocode:
            json.dump(output, geocode, indent=4)

    yield
    db.close()

app = FastAPI(lifespan=lifespan)

# Configure CORS to allow requests from frontend
# origins = [
#     "http://localhost:5173",  
#     "http://127.0.0.1:5173",  
# ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         
    allow_credentials=True,        
    allow_methods=["*"],           
    allow_headers=["*"],           
)

app.include_router(polygon_router)
app.include_router(locations_router)

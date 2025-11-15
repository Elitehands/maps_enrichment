import api.geocode.geocode_utils as osm
import time
import os
import json

from fastapi import FastAPI
from api.routes.geodata import router as polygon_router
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from api.config import  GEODATA_PATH, LOCATIONS_PATH_EXCEL, LOCATIONS_PATH_CSV


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
    if not os.path.exists(GEODATA_PATH):
        output = {}
        df = osm.get_filtered_dataset(LOCATIONS_PATH_CSV, "`Country/Region` == 'United Kingdom'", 'csv')
        if df is not None:
            for _, rows in df.iterrows():
                lon = rows["Longitude"]
                lat = rows["Latitude"]
                data = osm.geocode_nominatim_boundary(lat, lon)
                time.sleep(1) # avoid rate limiting
                if type(data) is osm.GeoData:
                    # Seed data with company-specific info to properties
                    data.properties.company_name = rows['Company Name']
                    data.properties.entity_type = rows["Entity Type"]
                    # Create feature collection
                    output['type'] = "FeatureCollection"
                    if 'features' not in output:
                        output['features'] = []
                    output['features'].append(data.model_dump())
            with open(GEODATA_PATH, "w") as geocode:
                json.dump(output, geocode, indent=4)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await load_geodata_csv()
    yield


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

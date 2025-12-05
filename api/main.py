import os
import json

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from api.lifecycle import *
from api.config import GEODATA_PATH
from api.routes.geodata import router as polygon_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.exists(GEODATA_PATH):
        output = {
        "type": "FeatureCollection",
        "features": []
        }
        
        features = output["features"]
        
        for lifecycle_fn in [poc_sheets_with_metadata, find_nestle_us_locations]:
            features.extend(lifecycle_fn())

        with open("out/geodata.json", "w") as geocode:
            json.dump(output, geocode, indent=4)
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

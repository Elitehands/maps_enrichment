import json
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from config import GEODATA_PATH

async def load_geodata():
    try:
        with open(GEODATA_PATH, "r") as geodata:
            data = json.load(geodata)
        return data
    except FileNotFoundError:
        raise Exception(f"File {GEODATA_PATH} not found.")
    except json.JSONDecodeError:
        raise Exception(f"Failed to decode JSON from {GEODATA_PATH}.")


router = APIRouter()


@router.get("/api/geodata", response_class=JSONResponse)
async def read_geodata():
    data = await load_geodata()
    return data

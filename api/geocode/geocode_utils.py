import pandas as pd
import requests as fetch
from pydantic import BaseModel
from pathlib import Path
from typing import Literal
from openlocationcode import openlocationcode as olc
from shapely import MultiPolygon
from shapely.geometry import Point, Polygon

NOMINATIM_REVERSE_GEOCODING_URL = "https://nominatim.openstreetmap.org/reverse"
UNITED_KINGDOM_POSTCODES_API_URL = "https://api.postcodes.io/postcodes/"
OVERPASS_API_URL = "https://overpass.openstreetmap.fr/api/interpreter"


class RuntimeInfo(BaseModel):
    message: str


class GeoData(BaseModel):
    type: str = "Feature"
    geometry: Geometry
    bbox: list[float]|None = None
    properties: Properties


class Geometry(BaseModel):
    type: str
    coordinates: list[list[list[float]] |list[list[list[float]]]]


class Properties(BaseModel):
    osm_id: int | None = None
    osm_type: str | None = None
    company_name: str | None = None
    entity_type: str | None = None
    address: str | None = None
    country_code: str | None = None
    country: str | None = None


# Decorator to print out any custom messages returned by functions durring runtime
def logger(f):
    def get_runtime_info(*args):
        data = f(*args)
        if type(data) is RuntimeInfo:
            print(data.message)
        else:
            return data

    return get_runtime_info


@logger
def overpass_fetch_nearest_feature(lat: float, lon: float, radius: int = 30) -> GeoData | RuntimeInfo:
    query = f"""
                [out:json];
                (
                    way["building"](around:{radius},{lat},{lon});
                    relation["building"](around:{radius},{lat},{lon});
                    way["landuse"~"industrial|commercial"](around:{radius},{lat},{lon});
                    relation["landuse"~"industrial|commercial"](around:{radius},{lat},{lon});
                );
                out geom;
            """
    try:
        # Create point object to test if within returned geometries
        point = Point(lon, lat)  # Longitude before latitude for shapely don't forget!
        response = fetch.get(OVERPASS_API_URL, params={"data": query}, timeout=25)
        response.raise_for_status()
        data = response.json()

        if data:
            for el in data["elements"]:
                geom = None
                coords = []
                # Single polygon (way)
                if el["type"] == "way":
                    coords = [[p["lon"], p["lat"]] for p in el["geometry"]]
                    if coords[0] != coords[-1]:
                        coords.append(coords[0])  # close polygon if necessary
                    geom = Polygon(coords)

                # Multipolygon (relation)
                if el["type"] == "relation":
                    member_polygons = []
                    for member in el.get("members", []):
                        if member["type"] != "way" or "geometry" not in member:
                            continue
                        member_coords = [
                            [p["lon"], p["lat"]] for p in member["geometry"]
                        ]
                        if member_coords[0] != member_coords[-1]:
                            member_coords.append(member_coords[0])
                        member_polygons.append(Polygon(member_coords))
                        coords.append(member_coords)
                    if member_polygons:
                        geom = MultiPolygon(member_polygons)
                        geom.contains(point)

                if geom and coords:
                #  Check if point is within the geometry
                    if geom.contains(point):
                        props = Properties(osm_id=el.get("id", ""))
                        print(f'Feature Type: {geom.geom_type}, OSM ID: {el.get("id", "")}')
                        return GeoData(properties=props, geometry=Geometry(type=geom.geom_type, coordinates=[coords]))
                
                continue
    except Exception as e:
        return RuntimeInfo(message=f"An error has occured: {e}")
    return RuntimeInfo(message=f"No data was found within the specified radius. Current radius: {radius} meters.")


# If a short code is passed, it will only decode it correctly if it is in the UK.
@logger
def plus_code_decoder(code: str, post_code: str = "") -> tuple[float, float] | RuntimeInfo:
    match code:
        case code if olc.isFull(code):
            lat, lon = olc.decode(code).latitudeCenter, olc.decode(code).longitudeCenter
            return lat, lon
        case code if olc.isShort(code):
            # Need to get the area info from postcode API to decode short codes
            if not post_code:
                return RuntimeInfo(message="Postcode required for short plus codes.")

            r = fetch.get(f"{UNITED_KINGDOM_POSTCODES_API_URL}{post_code}", timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == 200:
                    result = data.get("result", {})
                    lat = result.get("latitude", 0)
                    lon = result.get("longitude", 0)
                    full_code = olc.recoverNearest(code, lat, lon)
                    lat, lon = (
                        olc.decode(full_code).latitudeCenter,
                        olc.decode(full_code).longitudeCenter,
                    )
                    return lat, lon
                else:
                    return RuntimeInfo(message="Postcode API returned no result.")
            else:
                return RuntimeInfo(message=f"Postcode API request failed. Status code: {r.status_code}")
        case _:
            return RuntimeInfo(message=f"Invalid plus code format. Received: {code}")


def get_filtered_dataset(file: Path | str, filter: str, file_type: Literal["csv", "excel"]) -> pd.DataFrame | None:
    match file_type:
        case "csv":
            try:
                df = pd.read_csv(file)
                df = df.query(filter)
                cols = ["Longitude", "Latitude", "Company Name"]
                for col in cols:
                    df[col] = df[col].str.strip(" '")
                return df
            except Exception as e:
                print("An error occured:", e)
        case "excel":
            try:
                df = pd.read_excel(file)
                df = df.query(filter)
                return df
            except Exception as e:
                print("An error occured:", e)


@logger
def geocode_nominatim_boundary(lat: float, lon: float) -> GeoData | RuntimeInfo:
    options = {
        "params": {
            "lat": lat,
            "lon": lon,
            "format": "geojson",
            "polygon_geojson": 1,
            "zoom": 18,
            "accept-language": "en",
        },
        "timeout": 5,
        "headers": {"User-Agent": "Nestle-Location-Intelligence-POC/1.0"},
    }
    try:
        r = fetch.get(NOMINATIM_REVERSE_GEOCODING_URL, **options)
        # Raise exception if HTTP request fails
        r.raise_for_status()
        data = r.json()

        if data:
            result = data.get("features", [None])[0]

            # Only proceed where there is any data to be processed
            if not result:
                raise ValueError("Error: No values found in data.")

            geometry = result.get("geometry", {})
            bbox = result.get("bbox", {})

            properties = result.get("properties", {})

            display_name = properties.get("display_name", "")
            address = properties.get("address", {})
            osm_id = properties.get("osm_id", "")
            osm_type = properties.get("osm_type", "")

            country = address.get("country", "")
            country_code = address.get("country_code", "")

            props = Properties(
                osm_id=osm_id,
                osm_type=osm_type,
                address=display_name,
                country_code=country_code,
                country=country,
            )

            # Only use polygon data and no converting bbox to polygon, yet...
            if not geometry.get("type") == "Polygon":
                message = RuntimeInfo(message=f"Dropped:{geometry['type']}")
                return message

            return GeoData(geometry=Geometry(**geometry), bbox=bbox, properties=props)

    except Exception as e:
        RuntimeInfo(message=f"An error has occured: , {e}")

    return RuntimeInfo(message="No Operation Performed.")



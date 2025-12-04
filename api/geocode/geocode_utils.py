import pandas as pd
import pycountry
import requests as fetch
from pydantic import BaseModel
from pathlib import Path
from typing import List, Literal, Union
from openlocationcode import openlocationcode as olc
from shapely import MultiPolygon
from shapely.geometry import Point, Polygon

# Constants
NOMINATIM_REVERSE_GEOCODING_URL = "https://nominatim.openstreetmap.org/reverse"
UNITED_KINGDOM_POSTCODES_API_URL = "https://api.postcodes.io/postcodes/"
OVERPASS_API_URL = "https://overpass.private.coffee/api/interpreter"


# Types
class Geometry(BaseModel):
    type: str
    coordinates: Union[List[List[List[float]]], List[List[List[List[float]]]]]

class Properties(BaseModel):
    osm_id: int | None = None
    osm_type: str | None = None
    company_name: str | None = None
    entity_type: str | None = None
    address: str | None = None
    country_code: str | None = None
    country: str | None = None


class GeoData(BaseModel):
    type: str = "Feature"
    geometry: Geometry
    bbox: list[float] | None = None
    properties: Properties


def overpass_fetch_nearest_feature(lat: float, lon: float, radius: int = 30) -> GeoData | None:
    query = f"""
                [out:json];
            (
                way(around:{radius},{lat},{lon})[!"highway"][!"natural"][!"waterway"][!"amenity"];
                relation(around:{radius},{lat},{lon})[!"highway"][!"natural"][!"waterway"][!"amenity"];
            );
                out geom;
            """
    try:
        # Create point object to test if within returned geometries
        point = Point(lon, lat)  # Longitude before latitude for shapely don't forget!
        response = fetch.get(OVERPASS_API_URL, params={"data": query}, timeout=150)
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
                        props = Properties(osm_id=el.get("id", ""), osm_type=el.get("type", ""))
                        print(f'Feature Type: {geom.geom_type}, OSM ID: {el.get("id", "")}')
                        return GeoData(properties=props, geometry=Geometry(type=geom.geom_type, coordinates=[coords]))
                
                continue
    except Exception as e:
        print(f"An error has occured: {e}")
        return None
    print(f"No data was found within the specified radius. Current radius: {radius} meters.")
    return None

# If a short code is passed, it will only decode it correctly if it is in the UK.
def plus_code_decoder(code: str, post_code: str = "") -> tuple[float, float] | None:
    match code:
        case code if olc.isFull(code):
            lat, lon = olc.decode(code).latitudeCenter, olc.decode(code).longitudeCenter
            return lat, lon
        case code if olc.isShort(code):
            # Need to get the area info from postcode API to decode short codes
            if not post_code:
                print("Postcode required for short plus codes.")
                return None

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
                    print("Postcode API returned no result.")
                    return None 
            else:
                print(f"Postcode API request failed. Status code: {r.status_code}")
                return None
        case _:
            print(f"Invalid plus code format. Received: {code}")
            return None 

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

def geocode_nominatim_boundary(lat: float, lon: float) -> GeoData | None:
    options = {
        "params": {
            "lat": lat,
            "lon": lon,
            "format": "geojson",
            "polygon_geojson": 1,
            "zoom": 18,
            "accept-language": "en",
        },
        "timeout": 25,
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

            address = properties.get("address", {})
            osm_id = properties.get("osm_id", "")
            osm_type = properties.get("osm_type", "")

            country = address.get("country", "")
            country_code = address.get("country_code", "")

            keys = [
                    "city",
                    "town",
                    "village",
                    "hamlet",
                    "suburb",
                    "borough",
                    "county"  
                    ]
            
            display_name = f'{country}' # fallback 
            for key in keys:
                if key in address:
                    display_name = f'{address[key]}, {country}'
        
            props = Properties(
                osm_id=osm_id,
                osm_type=osm_type,
                address=display_name,
                country_code=country_code,
                country=country,
            )

            # Only use polygon data and no converting bbox to polygon, yet...
            if not geometry.get("type") == "Polygon":
                message =message=f"Dropped:{geometry['type']}"
                print(message)
                return

            return GeoData(geometry=Geometry(**geometry), bbox=bbox, properties=props)
        
    except Exception as e:
        print(f"An error has occured: , {e}")

    print("No operation performed")

def overpass_get_locations(country_code: str, regex: str, timeout: int = 1200) -> list[GeoData] | None:
    query = """
            [out:json][timeout:{timeout}];
            area["ISO3166-2"="{country_code}"]->.searchArea;
            (
            way["brand"~"{name}"]["highway"!~"."](area.searchArea);
            way["name"~"{name}"]["highway"!~"."](area.searchArea);
            relation["brand"~"{name}"]["highway"!~"."](area.searchArea);
            relation["name"~"{name}"]["highway"!~"."](area.searchArea);
            );
            out geom;
            """
    query = query.format(timeout=timeout, country_code=country_code, name=regex)
    
    header = {"User-Agent": "Nestle-Location-Intelligence-POC/1.0"}
    try:
        print(f"Searching {country_code}")
        response = fetch.post(OVERPASS_API_URL, data={"data":query}, headers=header)
        response.raise_for_status()
        print(f'Status Code:{response.status_code}')
        
        if "application/json" not in response.headers.get("Content-Type", ""):
            print("Non JSON response received\n")  
            return
        
        data = response.json()
        features = []
        count = 0
        if data:
            for el in data["elements"]:
                coords = []
                geom_type = None
                # Single polygon (way)
                if el["type"] == "way":
                    geom_type = 'Polygon'
                    coords = [[p["lon"], p["lat"]] for p in el["geometry"]]
                    if coords[0] != coords[-1]:
                        coords.append(coords[0])  # close polygon if necessary

                # Multiple Polygons (relations)
                if el["type"] == "relation":
                    geom_type = 'MultiPolygon'
                    member_polygons = []
                    for member in el.get("members", []):
                        if member["type"] != "way" or "geometry" not in member:
                            continue
                        member_coords = [[p["lon"], p["lat"]] for p in member["geometry"]]
                        if member_coords[0] != member_coords[-1]:
                            member_coords.append(member_coords[0])
                        member_polygons.append(member_coords) 
                    coords = member_polygons  
                    
                if geom_type and coords:                
                        tags = el.get("tags", {})
                        
                        company_name = tags.get('name') or tags.get('brand', '')
                        country = c.name if (c:= pycountry.countries.get(alpha_2=country_code.split("-")[0])) else ""                
                        city = c.name if (c:= pycountry.subdivisions.get(code=country_code)) else '' # type: ignore
                        
                        address = f'{city}, {country}'
                        
                        props = Properties(
                            osm_id=el.get("id", ""),
                            company_name=company_name,
                            entity_type='Branch', # Tag all as branch as placeholder in the absence of better data
                            country_code=country_code.split('-')[0],
                            country=country,
                            address=address
                            )
                        print(f'Feature Type: {geom_type}, OSM ID: {el.get("id", "")}')
                        geodata = GeoData(properties=props, geometry=Geometry(type=geom_type, coordinates=[coords]))
                        features.append(geodata)
                        count += 1
        print(f'Found: {count}')
        return features
    except Exception as e:
        print(f"An error has occured: {e}")

def google_plus_code_decoder(pluscode:str, api_key:str):
    try:
        response = fetch.get(f"https://maps.googleapis.com/maps/api/geocode/json?address={pluscode}&key={api_key}")
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [None])
        if not results:
            raise ValueError("No results returned")
        
        geometry = results[0].get("geometry", {})
        location = geometry.get("location", {})
        
        return [location["lat"], location["lng"]]
    except Exception as e:
        print(e)

def google_geocode_area_text(area_text:str, api_key:str):
    try:
        response = fetch.get(f"https://maps.googleapis.com/maps/api/geocode/json?address={area_text}&key={api_key}")
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [None])
        if not results:
            raise ValueError("No results returned")
        
        geometry = results[0].get("geometry", {})
        location = geometry.get("location", {})
        
        return [location["lat"], location["lng"]]
    except Exception as e:
        print(e)

def google_geocode_region_from_coords(lat: int, lon:int, api_key:str):
    try: 
        data = fetch.get(f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={api_key}")
        data.raise_for_status()
        data = data.json()
        results = data.get("results", [])

        city_address = None
        country_address = None
        country_short = None

        for r in results:
            types = r.get("types", [])
            
            if "locality" in types:
                city_address = r["formatted_address"]

            if "country" in types:
                country_address = r["formatted_address"]
                # extract the short country code (e.g. "GB", "US")
                for comp in r["address_components"]:
                    if "country" in comp["types"]:
                        country_short = comp["short_name"]
                        break

        return [city_address, country_address, country_short]
    except Exception as e:  
        print(e)
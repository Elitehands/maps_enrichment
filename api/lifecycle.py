# Create a custom lifecycle function for any data set you're working with
import time
import json
import pandas as pd
from api.utils import safe
from openlocationcode import openlocationcode as olc
from api.geocode.geocode_utils import GeoData, google_geocode_region_from_coords, google_geocode_area_text, overpass_fetch_nearest_feature
from api.config import GOOGLE_API_KEY, DATA_WITH_METADATA

def poc_sheets_with_metadata():
    output = {
        "type": "FeatureCollection",
        "features": []
    }

    expected_cols = [
        "LEGAL ENTITY NAME",
        "P1L_Usage",
        "GOOGLE LOC",
        "FINANCIAL",
        "PHYSICAL",
        "CLIMATE",
        "CLIMATE",
        "NATURE",
        "SUPPLY CHAIN DISRUPTION",
        "GLOBAL ULTIMATE 50+",
    ]

    file_location = DATA_WITH_METADATA
    df = pd.read_excel(file_location, sheet_name="POC_DATA_DISPLAY", usecols=expected_cols)
    
    # Use only rows with plus code data
    df = df.dropna(subset=["GOOGLE LOC"])

    for _, row in df.iterrows():
        plus_code_with_address = row["GOOGLE LOC"]
        [plus_code_no_address, *area_text] = plus_code_with_address.split(" ",1)
        area_text = area_text[0] if area_text else ''
    
        if olc.isValid(plus_code_no_address) is False or area_text == '':
            continue        
        
        nearest_location = google_geocode_area_text(area_text, GOOGLE_API_KEY)
        if nearest_location:
            [lat, lon] = nearest_location
            
            # Decode short plus code to full
            full_plus_code = olc.recoverNearest(plus_code_no_address, lat, lon)
            
            points = olc.decode(full_plus_code)
            lat, lon = points.latitudeCenter, points.longitudeCenter 

            data = overpass_fetch_nearest_feature(lat, lon)

            features = output.get("features", [])
            if data:
                data = data.model_dump()
                # Seed with company info
                exclude_list = ["GOOGLE LOC"]
                company_info = [metadata for metadata in expected_cols if metadata not in exclude_list]

                properties = data["properties"]

                # Seed address data
                [city, country, country_code] = google_geocode_region_from_coords(lat, lon, GOOGLE_API_KEY) or ("", "", "")
                properties["address"] = city
                properties["country"] = country
                properties["country_code"] = country_code
                
                # Programmatically add the rest of the properties
                for tag in company_info:
                    prop_name = "_".join(tag.lower().split(" "))
                    
                    # These attributes already exist in Properties
                    if tag == "LEGAL ENTITY NAME":
                        # Check if value is NaN and provide fallback
                        properties['company_name'] = safe(row[tag],"Nestlé")
                        continue   
                    if tag == "P1L_Usage":
                        properties['entity_type'] = safe(row[tag],"Branch")
                        continue
                    properties[prop_name] = safe(row[tag],"Not Available")
                features.append(data)
        time.sleep(1)
    with open("out/geodata.json", "w") as geocode:
        json.dump(output, geocode, indent=4)
    
__all__ = ["poc_sheets_with_metadata"]
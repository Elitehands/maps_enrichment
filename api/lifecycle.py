# Create a custom lifecycle function for any data set you're working with
import time
import pycountry
import pandas as pd
from api.utils import safe
from openlocationcode import openlocationcode as olc
from api.geocode.geocode_utils import geocode_nominatim_boundary, get_filtered_dataset, google_geocode_region_from_coords, google_geocode_area_text, overpass_fetch_nearest_feature, overpass_get_locations, plus_code_decoder
from api.config import GOOGLE_API_KEY, DATA_WITH_METADATA, LOCATIONS_PATH_CSV, LOCATIONS_PATH_EXCEL

def poc_sheets_with_metadata() -> list[dict]:
    output = []
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
                output.append(data)
        time.sleep(1)
    return output

def find_nestle_us_locations() -> list[dict]:
    output = []
    us_states = [sub.code for sub in pycountry.subdivisions if sub.country_code == "US"]  # type: ignore
    for state in us_states:
        overpass_data = overpass_get_locations(state, "^(Nestl(e[\u0301]?|é)( |$).*|Purina$|Nespresso$)")
        if overpass_data is not None:
            output.extend(item.model_dump() for item in overpass_data)
            time.sleep(1)

    return output

def load_geodata_excel():
    output = []
    df = get_filtered_dataset(LOCATIONS_PATH_EXCEL, "`P1L_Counrty` == 'UK'", 'excel')
    if df is not None:
        for _, rows in df.iterrows():
            plus_code = rows['GOOGLE LOC'].split(' ')[0]
            post_code = rows['P1L_Postcode']
            lat_lon = plus_code_decoder(plus_code, post_code)
            time.sleep(2) # avoid rate limiting
            if type(lat_lon) is tuple:
                lat, lon = lat_lon
                data = overpass_fetch_nearest_feature(lat, lon)
                time.sleep(1) # avoid rate limiting
                if data:
                    # Seed data with company-specific info to properties
                    data.properties.company_name = rows['P1L_Name']
                    data.properties.entity_type = rows.fillna('')["P1L_Type"]
                    data.properties.country = rows['P1L_Counrty']
                    # Create feature collection
                    output.append(data.model_dump())
    return output

def load_geodata_csv():
    output = []
    df = get_filtered_dataset(LOCATIONS_PATH_CSV, "`Country/Region` == 'United Kingdom'", 'csv')
    if df is not None:
        for _, rows in df.iterrows():
            lon = rows["Longitude"]
            lat = rows["Latitude"]
            data = geocode_nominatim_boundary(lat, lon)
            time.sleep(1) # avoid rate limiting
            if data:
                # Seed data with company-specific info to properties
                data.properties.company_name = rows['Company Name'].capitalize()
                data.properties.entity_type = rows["Entity Type"].capitalize()
                # Create feature collection
                output.append(data.model_dump())
    return output

__all__ = ["poc_sheets_with_metadata", "find_nestle_us_locations", "load_geodata_csv", "load_geodata_excel"]
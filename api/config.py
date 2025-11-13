from pathlib import Path
import os
from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
GEODATA_PATH = BASE_DIR / os.getenv("GEODATA_PATH", "out/geodata.json")
LOCATIONS_PATH_CSV = BASE_DIR / os.getenv("LOCATIONS_CSV_PATH", "data/locations.csv")
LOCATIONS_PATH_EXCEL = BASE_DIR / os.getenv("LOCATIONS_EXCEL_PATH", "data/locations.ods")
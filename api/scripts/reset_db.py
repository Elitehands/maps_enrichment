import os
import sys
# Add parent dir to path so we can import api
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from api.config import DATABASE_URL
from dotenv import load_dotenv

load_dotenv()

def reset_database():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set")
        return

    engine = create_engine(url)
    
    # 1. Drop old tables (Order matters due to foreign keys)
    drop_sql = """
    DROP TABLE IF EXISTS features CASCADE;
    DROP TABLE IF EXISTS company_locations CASCADE;
    DROP TABLE IF EXISTS locations CASCADE;
    DROP TABLE IF EXISTS companies CASCADE;
    """
    
    # 2. Create new schema
    create_sql = """
    CREATE EXTENSION IF NOT EXISTS postgis;

    CREATE TABLE IF NOT EXISTS companies (
      id   SERIAL PRIMARY KEY,
      name TEXT UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS locations (
      id SERIAL PRIMARY KEY,
      country_code TEXT,
      country      TEXT,
      postcode  TEXT,
      plus_code TEXT,
      latitude  DOUBLE PRECISION,
      longitude DOUBLE PRECISION,
      created_at TIMESTAMP DEFAULT NOW(),
      updated_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS company_locations (
      id SERIAL PRIMARY KEY,
      company_id  INT NOT NULL REFERENCES companies(id),
      location_id INT NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
      entity_type TEXT,
      source      TEXT,
      source_ref  TEXT,
      created_at TIMESTAMP DEFAULT NOW(),
      updated_at TIMESTAMP DEFAULT NOW()
    );

    CREATE UNIQUE INDEX IF NOT EXISTS uniq_company_location
    ON company_locations (company_id, location_id, source);

    CREATE TABLE IF NOT EXISTS features (
      id SERIAL PRIMARY KEY,
      location_id INT NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
      osm_id   BIGINT,
      osm_type TEXT,
      address  TEXT,
      geometry GEOMETRY(GEOMETRY, 4326),
      bbox     GEOMETRY(POLYGON, 4326),
      data_source TEXT,
      fetched_at  TIMESTAMP DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_features_geom ON features USING GIST (geometry);
    """

    with engine.begin() as conn:
        print("Dropping old tables...")
        conn.execute(text(drop_sql))
        print("Creating new schema...")
        conn.execute(text(create_sql))
        print("Database reset complete.")

if __name__ == "__main__":
    reset_database()

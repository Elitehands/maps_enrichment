# Database Schema – Companies, Locations and Features

## Purpose

This system takes a list of company locations from internal data (CSV/Excel), enriches each physical place with polygon boundaries from OpenStreetMap, and exposes the result as map-ready GeoJSON for the frontend.

To support this, we use four tables:

- `companies` – who is operating there
- `locations` – where the place is
- `company_locations` – which company is at which place (many-to-many)
- `features` – what shape/boundary OpenStreetMap gives us for that place

---

## High-level relationships

- One **company** can have many **locations** (offices, branches, factories).
- One **location** (a building) can host many **companies**.
- We model this with a **many-to-many** relationship using `company_locations`.
- Each **location** can have one or more **features** over time (polygon geometries from OSM).

In words:

- `companies` ←→ `company_locations` ←→ `locations` ←→ `features`

---

## Schema (SQL)

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Companies: one row per unique company / brand
CREATE TABLE IF NOT EXISTS companies (
  id   SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL
);

-- 2. Locations: one row per physical place (no company info here)
CREATE TABLE IF NOT EXISTS locations (
  id SERIAL PRIMARY KEY,

  country_code TEXT,          -- e.g. "GB", "US"
  country      TEXT,          -- e.g. "United Kingdom"

  postcode  TEXT,
  plus_code TEXT,

  latitude  DOUBLE PRECISION,
  longitude DOUBLE PRECISION,

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- 3. Company_locations: many-to-many link between companies and locations
CREATE TABLE IF NOT EXISTS company_locations (
  id SERIAL PRIMARY KEY,

  company_id  INT NOT NULL REFERENCES companies(id),
  location_id INT NOT NULL REFERENCES locations(id) ON DELETE CASCADE,

  entity_type TEXT,          -- Branch, Factory, Office, HQ, etc.
  source      TEXT,          -- "uk_csv", "uk_excel", "overpass_us", etc.
  source_ref  TEXT,          -- row id / filename / internal ref

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_company_location
ON company_locations (company_id, location_id, source);

-- 4. Features: polygons / multipolygons from OpenStreetMap
CREATE TABLE IF NOT EXISTS features (
  id SERIAL PRIMARY KEY,

  location_id INT NOT NULL REFERENCES locations(id) ON DELETE CASCADE,

  osm_id   BIGINT,   -- OSM object id
  osm_type TEXT,     -- "way" or "relation"
  address  TEXT,     -- label from OSM

  geometry GEOMETRY(GEOMETRY, 4326),  -- Polygon or MultiPolygon
  bbox     GEOMETRY(POLYGON, 4326),   -- optional bounding box

  data_source TEXT,          -- "nominatim" or "overpass"
  fetched_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_features_geom
ON features
USING GIST (geometry);

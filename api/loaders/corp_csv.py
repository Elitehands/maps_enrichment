import pandas as pd
from pathlib import Path
from typing import Iterable, Dict, Any
from api.config import CORP_CSV_PATH

EXPECTED_LAT = "Latitude"
EXPECTED_LON = "Longitude"

RENAME_MAP = {
    "Company Name": "company_name",
    "Entity Type": "entity_type",
    "Country/Region": "country",
    "Postal Code": "postcode",
    "D-U-N-S® Number": "duns_number",
    "State Or Province": "state",
    "State Or Province Abbreviation": "state_code",
    "County": "county",
}

def load_clean_dataframe(path: Path | str = CORP_CSV_PATH) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Corporate CSV not found: {path}")
    df = pd.read_csv(path, dtype=str)
    # Trim whitespace for all object columns
    df = df.apply(lambda s: s.str.strip() if s.dtype == "object" else s)
    # Rename columns for internal consistency
    df = df.rename(columns=RENAME_MAP)
    # Clean lat/lon stray apostrophes
    for col in [EXPECTED_LAT, EXPECTED_LON]:
        if col in df.columns:
            df[col] = (
                df[col]
                .str.replace("'", "", regex=False)
                .str.replace("`", "", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # Drop rows without coordinates
    df = df.dropna(subset=[EXPECTED_LAT, EXPECTED_LON])
    return df

def iter_location_rows(df: pd.DataFrame) -> Iterable[Dict[str, Any]]:
    for _, r in df.iterrows():
        yield {
            "company_name": r.get("company_name"),
            "entity_type": r.get("entity_type"),
            "country": r.get("country"),
            "postcode": r.get("postcode"),
            "duns_number": r.get("duns_number"),
            "state": r.get("state"),
            "state_code": r.get("state_code"),
            "county": r.get("county"),
            "latitude": r.get(EXPECTED_LAT),
            "longitude": r.get(EXPECTED_LON),
            "source": "corp_csv",
            "source_ref": r.get("Order"),  # original row order/identifier
        }

__all__ = ["load_clean_dataframe", "iter_location_rows"]

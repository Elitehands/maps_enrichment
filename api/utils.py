import pandas as pd

def safe(value, fallback=""):
    if value is None or pd.isna(value) or value == "":
        return fallback
    return value
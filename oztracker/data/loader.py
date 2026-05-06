"""
Load Opportunity Zone tract lists for OZ 1.0 and OZ 2.0.
"""
import os
import requests
import pandas as pd
from pathlib import Path

from oztracker.data.schema import (
    OZTract, OZ1_MFI_THRESHOLD, OZ1_POVERTY_THRESHOLD,
    OZ2_MFI_THRESHOLD, OZ2_POVERTY_THRESHOLD, OZ2_POVERTY_MFI_THRESHOLD,
)

CACHE_DIR = Path.home() / ".oztracker" / "cache"

# OZ 1.0 designated tracts — IRS Notice 2018-48
OZ1_URL = (
    "https://www.cdfifund.gov/sites/cdfi/files/2018-06/"
    "QOZ_Tracts_List_Formatted_July2018.xlsx"
)

# OZ 2.0 eligible tracts — Rev. Proc. 2026-14
OZ2_URL = (
    "https://home.treasury.gov/system/files/136/"
    "Eligible-LICs-for-Nomination-as-2027-QOZs.xlsx"
)


def get_cache_dir() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def load_oz1_tracts(force: bool = False) -> set:
    """
    Load the set of OZ 1.0 designated census tract FIPS codes.
    Returns set of 11-digit FIPS codes from IRS Notice 2018-48.
    Falls back to sample data if download fails.
    """
    path = get_cache_dir() / "oz1_tracts.xlsx"

    if not path.exists() or force:
        try:
            print("Downloading OZ 1.0 tract list...")
            r = requests.get(OZ1_URL, timeout=60)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"Saved to {path}")
        except Exception as e:
            print(f"OZ 1.0 download failed: {e}. Using sample data.")
            return _sample_oz1_tracts()

    try:
        df = pd.read_excel(path, dtype=str)
        df.columns = df.columns.str.strip().str.upper()
        for col in ["GEOID", "CENSUS_TRACT", "TRACT_ID", "TRACT"]:
            if col in df.columns:
                tracts = set(df[col].str.strip().str.zfill(11).tolist())
                print(f"OZ 1.0: {len(tracts):,} designated tracts loaded")
                return tracts
    except Exception as e:
        print(f"Parse error: {e}. Using sample data.")

    return _sample_oz1_tracts()


def load_oz2_eligible_tracts(force: bool = False) -> pd.DataFrame:
    """
    Load OZ 2.0 eligible tracts with economic data.
    Returns DataFrame with tract_id, poverty_rate, ami_ratio, is_rural.
    """
    path = get_cache_dir() / "oz2_eligible.xlsx"

    if not path.exists() or force:
        try:
            print("Downloading OZ 2.0 eligible tract list...")
            r = requests.get(OZ2_URL, timeout=60)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"Saved to {path}")
        except Exception as e:
            print(f"OZ 2.0 download failed: {e}. Using sample data.")
            return _sample_oz2_dataframe()

    try:
        df = pd.read_excel(path, dtype=str)
        df.columns = df.columns.str.strip().str.upper()
        print(f"OZ 2.0 eligible tracts loaded: {len(df):,}")
        return df
    except Exception as e:
        print(f"Parse error: {e}. Using sample data.")
        return _sample_oz2_dataframe()


def check_oz2_eligibility(
    poverty_rate: float,
    ami_ratio: float,
) -> bool:
    """
    Check if a tract meets OZ 2.0 eligibility criteria.
    OZ 2.0 requires STRICTER criteria than OZ 1.0:
    - MFI < 70% of state/metro AMI, OR
    - Poverty rate >= 20% AND MFI <= 125% of state/metro AMI
    """
    low_mfi = ami_ratio < OZ2_MFI_THRESHOLD
    poverty_and_mfi = (
        poverty_rate >= OZ2_POVERTY_THRESHOLD and
        ami_ratio <= OZ2_POVERTY_MFI_THRESHOLD
    )
    return low_mfi or poverty_and_mfi


def check_oz1_eligibility(
    poverty_rate: float,
    ami_ratio: float,
) -> bool:
    """
    Check if a tract meets OZ 1.0 eligibility criteria.
    - Poverty rate >= 20%, OR
    - MFI <= 80% of state/metro AMI
    """
    return (poverty_rate >= OZ1_POVERTY_THRESHOLD or
            ami_ratio <= OZ1_MFI_THRESHOLD)


def _sample_oz1_tracts() -> set:
    """Known OZ 1.0 tracts for testing."""
    return {
        "17031840100", "17031839100", "26163518300",
        "36061015900", "13121010400", "48113010900",
        "26163520100", "36061019100",
    }


def _sample_oz2_dataframe() -> pd.DataFrame:
    """Sample OZ 2.0 eligible tract data for testing."""
    return pd.DataFrame([
        {"tract_id": "17031840100", "state": "17", "poverty_rate": 0.38,
         "ami_ratio": 0.55, "is_rural": False},
        {"tract_id": "17031839100", "state": "17", "poverty_rate": 0.42,
         "ami_ratio": 0.48, "is_rural": False},
        {"tract_id": "26163518300", "state": "26", "poverty_rate": 0.45,
         "ami_ratio": 0.45, "is_rural": False},
        {"tract_id": "36061015900", "state": "36", "poverty_rate": 0.35,
         "ami_ratio": 0.60, "is_rural": False},
        {"tract_id": "13121010400", "state": "13", "poverty_rate": 0.29,
         "ami_ratio": 0.68, "is_rural": False},
        {"tract_id": "17019000100", "state": "17", "poverty_rate": 0.22,
         "ami_ratio": 0.65, "is_rural": True},
        {"tract_id": "26001010100", "state": "26", "poverty_rate": 0.25,
         "ami_ratio": 0.62, "is_rural": True},
    ])

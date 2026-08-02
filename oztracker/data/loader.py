"""
Load Opportunity Zone tract lists for OZ 1.0 and OZ 2.0.

STATUS (0.2.0): both upstream URLs below return HTTP 404 (verified 2026-07-30).
Every loader in this module therefore raises OZDownloadError in practice. That
is deliberate: through 0.1.0 these functions silently returned an 8-row
hardcoded sample on any failure, which made ``is_designated()`` answer a
confident, wrong ``False`` for 99.91% of real designated tracts.

Restoration is deferred for a DIFFERENT reason per checker (see the README):
OZ 1.0 is blocked on the census-tract vintage question (a 2010-basis
designation list vs. current-vintage caller GEOIDs), pending nmtc-mapper 0.5.0.
OZ 2.0 is NOT blocked on vintage — Rev. Proc. 2026-14 §3.01(1) derives the
eligible list from the 2020-2024 ACS 5-Year and 2020 DECIA data sets, i.e.
2020-basis, and its Appendix is live (verified 2026-08-02: HTTP 200, 25,332
rows). OZ 2.0 is deferred purely on scope: 0.2.0 adds no data paths.

Sample data still exists but is reachable ONLY through the explicitly named
``load_sample_oz1_tracts()`` / ``load_sample_oz2_dataframe()`` entry points, or
``OZ1Checker.from_sample()`` / ``OZ2Checker.from_sample()``.
"""
import os
import requests
import pandas as pd
from pathlib import Path

from oztracker.exceptions import OZTrackerError, OZDownloadError, OZParseError
from oztracker.data.schema import (
    OZ1_MFI_THRESHOLD, OZ1_POVERTY_THRESHOLD,
    OZ2_MFI_THRESHOLD, OZ2_POVERTY_THRESHOLD, OZ2_POVERTY_MFI_THRESHOLD,
)

CACHE_DIR = Path.home() / ".oztracker" / "cache"

# OZ 1.0 designated tracts — IRS Notice 2018-48
# KNOWN DEAD: HTTP 404 as of 2026-07-30 (cdfifund.gov root returns 200, so the
# document itself is gone, not the host). Not repointed in 0.2.0 by decision.
OZ1_URL = (
    "https://www.cdfifund.gov/sites/cdfi/files/2018-06/"
    "QOZ_Tracts_List_Formatted_July2018.xlsx"
)

# OZ 2.0 eligible tracts — Rev. Proc. 2026-14
# KNOWN DEAD: HTTP 404 as of 2026-07-30.
OZ2_URL = (
    "https://home.treasury.gov/system/files/136/"
    "Eligible-LICs-for-Nomination-as-2027-QOZs.xlsx"
)


def get_cache_dir() -> Path:
    """Return the cache directory, creating it if needed.

    A filesystem failure here (read-only home, permission denied, ENOSPC)
    happens BEFORE any download handler exists, so without this wrapper a bare
    ``PermissionError`` / ``OSError`` would escape ``load_oz1_tracts()`` past a
    caller's ``except OZTrackerError``. Wrapped and chained so the load path
    raises only typed errors.
    """
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OZDownloadError(
            f"Cannot create the oz-tracker cache directory {CACHE_DIR}: "
            f"{type(e).__name__}: {e}"
        ) from e
    return CACHE_DIR


def _discard(tmp: Path) -> None:
    """Best-effort removal of the ``.part`` temp during error handling.

    Deliberately swallows OSError: this runs inside ``except`` blocks that are
    already raising a typed OZDownloadError, and on a failing filesystem the
    unlink itself can raise — which would replace the typed error with a raw
    OSError and put an untyped exception back on the load path. A leftover
    ``.part`` is harmless; nothing ever reads it.
    """
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass


def _download_to_cache(url: str, path: Path, label: str) -> None:
    """Stream `url` to `path` atomically, or raise OZDownloadError.

    Writes to a sibling ``.part`` file and renames on success, so a mid-stream
    failure can never leave a truncated file at the final cache path — a
    poisoned cache would make every later run parse-fail (or worse, parse
    partially) with no indication why.

    The rename is what guarantees that, not the ``unlink`` cleanup below:
    ``KeyboardInterrupt`` and ``SystemExit`` are deliberately NOT caught here
    (see exceptions.py), so on Ctrl-C mid-download no handler runs at all and
    the only thing left behind is the ``.part`` file. The final cache path is
    never written to except by ``Path.replace``, which is atomic on POSIX.
    """
    tmp = path.with_suffix(path.suffix + ".part")
    try:
        print(f"Downloading {label} tract list...")
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        tmp.replace(path)
        print(f"Saved to {path}")
    except requests.exceptions.HTTPError as e:
        _discard(tmp)
        status = getattr(e.response, "status_code", None)
        if status == 404:
            reason = (
                "not found (404) — this URL is known-dead as of 2026-07-30 and "
                "has not been repointed in 0.2.0; see the oz-tracker README"
            )
        elif status == 403:
            reason = "access blocked (403 Forbidden)"
        else:
            reason = f"HTTP {status}"
        raise OZDownloadError(
            f"Failed to download {label} tract list from {url}: {reason}"
        ) from e
    except requests.exceptions.RequestException as e:
        _discard(tmp)
        raise OZDownloadError(
            f"Failed to download {label} tract list from {url}: "
            f"connection/DNS/timeout error ({type(e).__name__}: {e})"
        ) from e
    except OSError as e:
        # Filesystem failure while writing the .part file or renaming it into
        # place (ENOSPC, EACCES, read-only mount). Must be listed AFTER the
        # requests clauses: RequestException subclasses OSError, so an earlier
        # position here would swallow every transport error.
        _discard(tmp)
        raise OZDownloadError(
            f"Failed to write {label} tract list to {tmp}: "
            f"{type(e).__name__}: {e}"
        ) from e


def load_oz1_tracts(force: bool = False) -> set:
    """
    Load the set of OZ 1.0 designated census tract FIPS codes (IRS Notice
    2018-48, 8,764 tracts on 2010 tract boundaries).

    Raises OZDownloadError / OZParseError on any failure. NEVER falls back to
    sample data — for offline demos and tests use ``load_sample_oz1_tracts()``
    or ``OZ1Checker.from_sample()``.

    NOTE: OZ1_URL currently 404s, so this function raises OZDownloadError on
    every call against a cold cache. That is the intended 0.2.0 behavior.
    """
    path = get_cache_dir() / "oz1_tracts.xlsx"

    if not path.exists() or force:
        _download_to_cache(OZ1_URL, path, "OZ 1.0")

    try:
        df = pd.read_excel(path, dtype=str)
        df.columns = df.columns.str.strip().str.upper()
    except OZTrackerError:
        raise
    except Exception as e:
        raise OZParseError(
            f"Failed to parse OZ 1.0 tract file {path}: {type(e).__name__}: {e}"
        ) from e

    for col in ["GEOID", "CENSUS_TRACT", "TRACT_ID", "TRACT"]:
        if col in df.columns:
            tracts = set(df[col].dropna().str.strip().str.zfill(11).tolist())
            print(f"OZ 1.0: {len(tracts):,} designated tracts loaded")
            return tracts

    # Parsed, but no recognizable tract column — fail loud rather than degrade
    # to the 8-row sample set.
    raise OZParseError(
        f"OZ 1.0 tract file {path} parsed but no tract column was found "
        f"(looked for GEOID / CENSUS_TRACT / TRACT_ID / TRACT; got "
        f"{list(df.columns)[:10]})."
    )


def load_oz2_eligible_tracts(force: bool = False) -> pd.DataFrame:
    """
    Load OZ 2.0 eligible tracts with economic data.
    Returns a DataFrame with tract_id, poverty_rate, ami_ratio, is_rural.

    Raises OZDownloadError / OZParseError on any failure. NEVER falls back to
    sample data — use ``load_sample_oz2_dataframe()`` or
    ``OZ2Checker.from_sample()``.

    KNOWN LIMITATION (not fixed in 0.2.0, deliberately): this function
    uppercases the downloaded frame's column names while ``OZ2Checker._process``
    reads lowercase ``tract_id``, so even a successful download would yield an
    empty eligibility set. Repairing that is bundled with the deferred OZ data
    restoration rather than fixed blind against a file nobody can currently
    fetch. With the tri-state return added in 0.2.0 the consequence is an
    honest "not determined", not a fabricated negative.
    """
    path = get_cache_dir() / "oz2_eligible.xlsx"

    if not path.exists() or force:
        _download_to_cache(OZ2_URL, path, "OZ 2.0")

    try:
        df = pd.read_excel(path, dtype=str)
        df.columns = df.columns.str.strip().str.upper()
    except OZTrackerError:
        raise
    except Exception as e:
        raise OZParseError(
            f"Failed to parse OZ 2.0 eligible tract file {path}: "
            f"{type(e).__name__}: {e}"
        ) from e

    print(f"OZ 2.0 eligible tracts loaded: {len(df):,}")
    return df


def check_oz2_eligibility(
    poverty_rate: float,
    ami_ratio: float,
) -> bool:
    """
    Check if a tract meets OZ 2.0 eligibility criteria.
    OZ 2.0 requires STRICTER criteria than OZ 1.0:
    - MFI < 70% of state/metro AMI, OR
    - Poverty rate >= 20% AND MFI <= 125% of state/metro AMI

    This is a pure threshold calculation on values the CALLER supplies; it
    performs no lookup and so cannot fabricate anything.
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

    Pure threshold calculation on caller-supplied values; no lookup.
    """
    return (poverty_rate >= OZ1_POVERTY_THRESHOLD or
            ami_ratio <= OZ1_MFI_THRESHOLD)


def load_sample_oz1_tracts() -> set:
    """Return the 8-tract synthetic OZ 1.0 demo set — EXPLICIT opt-in only.

    WARNING: this is demo data, not the designation list. The real universe is
    8,764 tracts; this is 8, and several of its GEOIDs (e.g. "26163518300",
    "48113010900", "26163520100") are not present in either the 2010 or the
    current census-tract universe — they are invented. It is NEVER valid for a
    real OZ designation answer.

    Through 0.1.0 this set was substituted silently whenever a download or
    parse failed, which is exactly how the package came to answer "not
    designated" for 99.91% of designated tracts. That path is gone. Reach it
    only through this function or ``OZ1Checker.from_sample()``, which stamps
    ``data_source == "sample"``.
    """
    return {
        "17031840100", "17031839100", "26163518300",
        "36061015900", "13121010400", "48113010900",
        "26163520100", "36061019100",
    }


def load_sample_oz2_dataframe() -> pd.DataFrame:
    """Return the 7-row synthetic OZ 2.0 demo frame — EXPLICIT opt-in only.

    WARNING: demo data with invented economic values and, in several rows,
    invented GEOIDs ("26163518300", "17019000100", "26001010100"). Never valid
    for a real OZ 2.0 eligibility answer. Stamped ``data_source == "sample"``
    when reached via ``OZ2Checker.from_sample()``.
    """
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


# Backwards-compatible private aliases: 0.1.0 shipped these names and external
# code may import them. They are NOT reachable from any failure path.
_sample_oz1_tracts = load_sample_oz1_tracts
_sample_oz2_dataframe = load_sample_oz2_dataframe

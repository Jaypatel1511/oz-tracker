import pytest
from oztracker.data.schema import OZInvestment
from oztracker.eligibility.oz1 import OZ1Checker
from oztracker.eligibility.oz2 import OZ2Checker
from oztracker.portfolio.tracker import OZPortfolio


# ── Verified-real census tracts, for tests that must NOT use sample GEOIDs ────
#
# Classified against ~/recon-2026-07-30/geo/universes.pkl using the CORRECTED
# detector (gazetteer2024 ∪ rel2020 = "real now"), not the 2020 universe alone —
# the latter false-positives all 884 Connecticut tracts (RECON_2026-07-30 §B-0).
# None of these appear in the built-in sample sets, which is the point: they are
# real tracts the sample cannot answer for.
REAL_TRACTS_NOT_IN_SAMPLE = [
    "17031838200",  # Cook County, IL
    "12086003100",  # Miami-Dade County, FL
    "42101037300",  # Philadelphia County, PA
    "26163517200",  # Wayne County, MI
    "53033010001",  # King County, WA
]

# Structurally impossible GEOID (11 nines) — not a tract in any vintage.
NOT_A_GEOID = "99999999999"


@pytest.fixture
def oz1_checker():
    """A checker on the EXPLICIT sample set.

    Through 0.1.0 this fixture monkeypatched ``oztracker.data.loader``, which
    did not even work — ``oz1.py`` binds the loader name at import time, so the
    patch was a no-op and every test made a live network call that 404'd and
    silently landed on the sample fallback. The tests passed only because the
    fabrication path existed. ``from_sample()`` gives real isolation.
    """
    return OZ1Checker.from_sample()


@pytest.fixture
def oz2_checker():
    return OZ2Checker.from_sample()


@pytest.fixture
def sample_investment():
    return OZInvestment(
        id="INV001",
        investor_name="Jay Patel",
        fund_name="Midwest OZ Fund I",
        fund_type="qof",
        oz_version="oz2",
        tract_id="17031840100",
        investment_type="real_estate",
        capital_gain_invested=500_000,
        investment_date="2027-03-15",
        fmv_at_investment=500_000,
        current_fmv=650_000,
        state="IL",
        is_rural=False,
    )


@pytest.fixture
def rural_investment():
    return OZInvestment(
        id="INV002",
        investor_name="Jay Patel",
        fund_name="Rural QORF I",
        fund_type="qorf",
        oz_version="oz2",
        tract_id="17019000100",
        investment_type="real_estate",
        capital_gain_invested=1_000_000,
        investment_date="2027-06-01",
        fmv_at_investment=1_000_000,
        current_fmv=1_300_000,
        state="IL",
        is_rural=True,
    )


@pytest.fixture
def sample_portfolio(sample_investment, rural_investment):
    p = OZPortfolio(name="Test Portfolio")
    p.add(sample_investment)
    p.add(rural_investment)
    return p

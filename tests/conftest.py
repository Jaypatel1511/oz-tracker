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


# ── Fixture dates are deliberately far from today ────────────────────────────
#
# These were 2027-03-15 and 2027-06-01, and the suite depended on 2027 being in
# the FUTURE: test_portfolio.py's refusal test asserts the portfolio cannot
# total, which is only true while the investment dates have not yet passed.
# Verified by pinning ``oztracker.benefits.qof.datetime.today()``: 94 passed at
# a simulated 2027-04-01, and 1 failed from 2027-06-02 onward. A build that is
# knowingly scheduled to go red is not shippable.
#
# 2099 is far enough that nothing here depends on when the suite runs, matching
# what tests/test_holding_period.py already does with 2015 / 2099 and for the
# same reason. Tests that need a specific holding period pass an explicit
# exit_date offset from FUTURE_* below rather than leaning on the wall clock.
FUTURE_INVESTMENT_DATE       = "2099-03-15"   # sample_investment
FUTURE_RURAL_INVESTMENT_DATE = "2099-06-01"   # rural_investment

# Exit dates for tests that pin a step-up / exclusion TIER. Named for the tier
# they select, not for an exact anniversary, and each sits clear of its
# threshold by ~6 months on purpose.
#
# calculate_benefits() measures holding_years as days / 365.25, so an exact
# calendar anniversary is not reliably >= the integer tier: 2099-03-15 to
# 2104-03-15 spans 1826 days = 4.9993 years and misses the 5-year step-up,
# because 2100 is a century year and not a leap year. Naming the tier and
# leaving margin keeps these tests about the tier boundary in the calculator
# rather than about the Gregorian calendar.
FUTURE_EXIT_UNDER_5YR       = "2102-03-15"   # ~3.0y  -> no step-up
FUTURE_EXIT_OVER_5YR        = "2104-09-15"   # ~5.5y  -> step-up, no exclusion
FUTURE_EXIT_OVER_10YR       = "2109-09-15"   # ~10.5y -> appreciation excluded
FUTURE_RURAL_EXIT_OVER_5YR  = "2104-12-01"   # ~5.5y after the rural date


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
        investment_date=FUTURE_INVESTMENT_DATE,
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
        investment_date=FUTURE_RURAL_INVESTMENT_DATE,
        fmv_at_investment=1_000_000,
        current_fmv=1_300_000,
        state="IL",
        is_rural=True,
    )


@pytest.fixture
def realized_investment():
    """A future-dated investment that carries its OWN ``exit_date``.

    No fixture anywhere set this field before — every ``exit_date=`` in tests/
    was the ``calculate_benefits`` parameter — which is exactly why a 94-test
    suite could not see that the field was never read, and that a
    fully-specified investment was being refused with "exit_date was not
    supplied". The blind spot was in the fixtures, so the cover goes here.
    """
    return OZInvestment(
        id="INV003",
        investor_name="Jay Patel",
        fund_name="Realized OZ Fund",
        fund_type="qof",
        oz_version="oz2",
        tract_id="17031840100",
        investment_type="real_estate",
        capital_gain_invested=750_000,
        investment_date=FUTURE_INVESTMENT_DATE,
        fmv_at_investment=750_000,
        current_fmv=1_125_000,
        exit_date=FUTURE_EXIT_OVER_10YR,
        state="IL",
        is_rural=False,
    )


@pytest.fixture
def sample_portfolio(sample_investment, rural_investment):
    """Two future-dated members, NEITHER carrying an exit_date — so the whole
    portfolio is undeterminable, permanently."""
    p = OZPortfolio(name="Test Portfolio")
    p.add(sample_investment)
    p.add(rural_investment)
    return p


@pytest.fixture
def mixed_portfolio(sample_investment, rural_investment, realized_investment):
    """One determinable member (via its exit_date field) and two not.

    Exercises the covered/excluded partition with a fixture that carries the
    field, which is the combination F1 left untested.
    """
    p = OZPortfolio(name="Mixed Portfolio")
    p.add(realized_investment)
    p.add(sample_investment)
    p.add(rural_investment)
    return p

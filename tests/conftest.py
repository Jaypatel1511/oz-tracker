import pytest
from oztracker.data.schema import OZInvestment
from oztracker.eligibility.oz1 import OZ1Checker
from oztracker.eligibility.oz2 import OZ2Checker
from oztracker.portfolio.tracker import OZPortfolio


@pytest.fixture
def oz1_checker(monkeypatch):
    monkeypatch.setattr(
        "oztracker.data.loader.load_oz1_tracts",
        lambda force=False: {
            "17031840100", "17031839100", "26163518300",
            "36061015900", "13121010400", "48113010900",
        }
    )
    return OZ1Checker()


@pytest.fixture
def oz2_checker(monkeypatch):
    monkeypatch.setattr(
        "oztracker.data.loader.load_oz2_eligible_tracts",
        lambda force=False: __import__(
            'oztracker.data.loader', fromlist=['_sample_oz2_dataframe']
        )._sample_oz2_dataframe()
    )
    return OZ2Checker()


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

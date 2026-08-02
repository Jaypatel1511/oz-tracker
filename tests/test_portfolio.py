import pytest
import pandas as pd
from oztracker.portfolio.tracker import OZPortfolio
from oztracker.data.schema import OZInvestment
from oztracker.exceptions import OZCalculationError


def test_portfolio_count(sample_portfolio):
    assert sample_portfolio.count() == 2


def test_total_invested(sample_portfolio):
    assert sample_portfolio.total_invested == pytest.approx(1_500_000)


def test_oz2_invested(sample_portfolio):
    assert sample_portfolio.oz2_invested == pytest.approx(1_500_000)


def test_rural_invested(sample_portfolio, rural_investment):
    assert sample_portfolio.rural_invested == pytest.approx(
        rural_investment.capital_gain_invested
    )


def test_duplicate_raises(sample_portfolio, sample_investment):
    with pytest.raises(ValueError, match="already exists"):
        sample_portfolio.add(sample_investment)


def test_remove(sample_portfolio, sample_investment):
    sample_portfolio.remove(sample_investment.id)
    assert sample_portfolio.count() == 1


def test_filter_rural(sample_portfolio):
    rural = sample_portfolio.filter_rural()
    assert len(rural) == 1
    assert rural[0].is_rural == True


def test_filter_fund_type(sample_portfolio):
    qorf = sample_portfolio.filter_fund_type("qorf")
    assert len(qorf) == 1


def test_total_tax_benefits_refuses_the_future_dated_fixture(sample_portfolio):
    """This test used to read ``assert isinstance(benefits, float)`` and passed.

    Both fixture investments are dated 2027 — in the future — and no exit_date
    is supplied, so every figure it was type-checking was computed from a
    NEGATIVE holding period. It asserted the type of a fabricated number and
    certified it green. The contract now is that the portfolio refuses.
    """
    with pytest.raises(OZCalculationError) as exc:
        sample_portfolio.total_tax_benefits()
    assert "no determinable holding period" in str(exc.value)


def test_total_tax_benefits_returns_float_when_determinable():
    """The float path, on a portfolio whose holding periods actually exist."""
    p = OZPortfolio(name="Determinable")
    p.add(OZInvestment(
        id="D1", investor_name="Jay Patel", fund_name="Past Fund",
        fund_type="qof", oz_version="oz2", tract_id="17031840100",
        investment_type="real_estate", capital_gain_invested=500_000,
        investment_date="2015-01-15", fmv_at_investment=500_000,
        current_fmv=750_000, state="IL", is_rural=False,
    ))
    benefits = p.total_tax_benefits()
    assert isinstance(benefits, float)
    assert benefits > 0


def test_to_dataframe(sample_portfolio):
    df = sample_portfolio.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "capital_gain" in df.columns


def test_summary_runs(sample_portfolio):
    sample_portfolio.summary()

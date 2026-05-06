import pytest
import pandas as pd
from oztracker.portfolio.tracker import OZPortfolio


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


def test_total_tax_benefits_returns_float(sample_portfolio):
    benefits = sample_portfolio.total_tax_benefits()
    assert isinstance(benefits, float)


def test_to_dataframe(sample_portfolio):
    df = sample_portfolio.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "capital_gain" in df.columns


def test_summary_runs(sample_portfolio):
    sample_portfolio.summary()

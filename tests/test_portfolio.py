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

    Both fixture investments are future-dated and neither supplies an exit_date
    — as an argument or as a field — so every figure it was type-checking was
    computed from a NEGATIVE holding period. It asserted the type of a
    fabricated number and certified it green. The contract now is that the
    portfolio refuses.

    The fixture dates moved from 2027 to 2099 so this stays true regardless of
    when the suite runs; at 2027 it was scheduled to go red on 2027-06-02.
    """
    with pytest.raises(OZCalculationError) as exc:
        sample_portfolio.total_tax_benefits()
    assert "no determinable holding period" in str(exc.value)


# ── The exit_date FIELD, at the shared-fixture layer ─────────────────────────

def test_investment_carrying_its_own_exit_date_is_determinable(
        realized_investment):
    """A fully-specified investment is not undeterminable.

    Before this fix ``realized_investment`` — future-dated but carrying its own
    exit_date — was refused with "exit_date was not supplied", a statement
    about the caller's input that was simply false.
    """
    p = OZPortfolio(name="Realized")
    p.add(realized_investment)
    assert p.undeterminable_benefits() == []
    assert p.total_tax_benefits() > 0


def test_mixed_portfolio_partitions_on_the_field(mixed_portfolio):
    """Covered/excluded still partitions correctly when determinability comes
    from the field rather than from a past investment date."""
    undeterminable = mixed_portfolio.undeterminable_benefits()
    assert [inv.id for inv, _ in undeterminable] == ["INV001", "INV002"]


def test_mixed_portfolio_summary_is_partial_not_empty(mixed_portfolio, capsys):
    """Knock-on: honouring the field changes which members are determinable,
    which changes what summary() renders. This portfolio was 3-of-3 excluded
    before and is 1-of-3 covered now."""
    mixed_portfolio.summary()
    out = capsys.readouterr().out

    assert "covers 1 of 3 investments" in out
    assert "Benefit (covered subset):" in out
    assert "No benefit figure can be computed" not in out
    assert "INV003" not in out, "the determinable member must not be listed as excluded"


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

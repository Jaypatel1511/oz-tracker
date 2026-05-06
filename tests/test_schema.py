import pytest
from oztracker.data.schema import OZInvestment, FUND_TYPES, INVESTMENT_TYPES


def test_investment_created(sample_investment):
    assert sample_investment.capital_gain_invested == 500_000
    assert sample_investment.fund_type == "qof"
    assert sample_investment.oz_version == "oz2"


def test_invalid_fund_type_raises():
    with pytest.raises(ValueError, match="fund_type"):
        OZInvestment(
            id="X", investor_name="X", fund_name="X",
            fund_type="invalid", oz_version="oz2",
            tract_id="17031840100", investment_type="real_estate",
            capital_gain_invested=100_000,
            investment_date="2027-01-01",
            fmv_at_investment=100_000,
        )


def test_invalid_oz_version_raises():
    with pytest.raises(ValueError, match="oz_version"):
        OZInvestment(
            id="X", investor_name="X", fund_name="X",
            fund_type="qof", oz_version="oz3",
            tract_id="17031840100", investment_type="real_estate",
            capital_gain_invested=100_000,
            investment_date="2027-01-01",
            fmv_at_investment=100_000,
        )


def test_negative_amount_raises():
    with pytest.raises(ValueError, match="positive"):
        OZInvestment(
            id="X", investor_name="X", fund_name="X",
            fund_type="qof", oz_version="oz2",
            tract_id="17031840100", investment_type="real_estate",
            capital_gain_invested=-100_000,
            investment_date="2027-01-01",
            fmv_at_investment=100_000,
        )


def test_amount_mm(sample_investment):
    assert sample_investment.amount_mm == pytest.approx(0.5)


def test_rural_investment_properties(rural_investment):
    assert rural_investment.is_rural == True
    assert rural_investment.fund_type == "qorf"

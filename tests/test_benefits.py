"""Benefit-tier tests over the shared conftest fixtures.

Exit dates come from the FUTURE_EXIT_* constants rather than literals: they are
offsets from the fixture investment dates, and both moved to 2099 so that no
test here depends on when the suite runs (see conftest.py for why).
"""
import pytest
from oztracker.benefits.qof import calculate_benefits, compare_scenarios
from oztracker.data.schema import QOFBenefits

from tests.conftest import (
    FUTURE_EXIT_UNDER_5YR, FUTURE_EXIT_OVER_5YR,
    FUTURE_EXIT_OVER_10YR, FUTURE_RURAL_EXIT_OVER_5YR,
)


def test_benefits_returns_object(sample_investment):
    result = calculate_benefits(sample_investment, current_fmv=650_000,
                                exit_date=FUTURE_EXIT_OVER_10YR)
    assert isinstance(result, QOFBenefits)


def test_10yr_exclusion_applies(sample_investment):
    result = calculate_benefits(sample_investment, current_fmv=650_000,
                                exit_date=FUTURE_EXIT_OVER_10YR)
    assert result.excluded_appreciation > 0


def test_no_exclusion_before_10yr(sample_investment):
    result = calculate_benefits(sample_investment, current_fmv=650_000,
                                exit_date=FUTURE_EXIT_UNDER_5YR)
    assert result.excluded_appreciation == 0


def test_rural_higher_stepup(sample_investment, rural_investment):
    std = calculate_benefits(sample_investment, current_fmv=650_000,
                             exit_date=FUTURE_RURAL_EXIT_OVER_5YR)
    rural = calculate_benefits(rural_investment, current_fmv=1_300_000,
                               exit_date=FUTURE_RURAL_EXIT_OVER_5YR)
    assert rural.stepup_pct > std.stepup_pct


def test_5yr_stepup_oz2(sample_investment):
    result = calculate_benefits(sample_investment, current_fmv=650_000,
                                exit_date=FUTURE_EXIT_OVER_5YR)
    assert result.stepup_pct == pytest.approx(0.10)


def test_rural_5yr_stepup_30pct(rural_investment):
    result = calculate_benefits(rural_investment, current_fmv=1_300_000,
                                exit_date=FUTURE_RURAL_EXIT_OVER_5YR)
    assert result.stepup_pct == pytest.approx(0.30)


def test_summary_runs(sample_investment):
    result = calculate_benefits(sample_investment, current_fmv=650_000,
                                exit_date=FUTURE_EXIT_OVER_10YR)
    result.summary()


def test_compare_scenarios():
    result = compare_scenarios(
        capital_gain=500_000,
        investment_date="2027-01-01",
        current_fmv=700_000,
        exit_date="2037-01-01",
    )
    assert "oz1_benefit" in result
    assert "oz2_rural_benefit" in result
    assert result["oz2_rural_benefit"] >= result["oz2_benefit"]

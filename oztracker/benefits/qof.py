"""
QOF (Qualified Opportunity Fund) tax benefit calculator.
Handles both OZ 1.0 and OZ 2.0 benefit structures.
"""
from datetime import datetime
from oztracker.data.schema import (
    OZInvestment, QOFBenefits,
    OZ1_5YR_STEPUP_PCT, OZ1_7YR_STEPUP_PCT,
    OZ2_5YR_STEPUP_PCT, OZ2_DEFERRAL_YEARS,
    RURAL_STEPUP_PCT, STANDARD_STEPUP_PCT,
    OZ2_MAX_STEPUP_HOLD,
)


def calculate_benefits(
    investment: OZInvestment,
    current_fmv: float = None,
    exit_date: str = None,
    tax_rate: float = 0.238,
) -> QOFBenefits:
    """
    Calculate tax benefits for a QOF investment.

    Handles:
    - OZ 1.0: deferral through 12/31/2026, 5/7-year step-ups, 10-year exclusion
    - OZ 2.0: rolling 5-year deferral, 10% step-up (30% rural), 10-year exclusion
    - Rural QORF: enhanced 30% step-up benefit

    Args:
        investment:  OZInvestment instance
        current_fmv: Current fair market value of QOF interest
        exit_date:   Assumed exit date for calculation (default: today)
        tax_rate:    Assumed capital gains tax rate (default: 23.8%)

    Returns:
        QOFBenefits with full tax benefit breakdown
    """
    fmv = current_fmv or investment.current_fmv or investment.fmv_at_investment

    inv_date = datetime.strptime(investment.investment_date, "%Y-%m-%d")
    exit_dt = (datetime.strptime(exit_date, "%Y-%m-%d")
               if exit_date else datetime.today())

    holding_years = (exit_dt - inv_date).days / 365.25

    # ── Determine step-up percentage ─────────────────────────────────────────
    if investment.oz_version == "oz1":
        if holding_years >= 7:
            stepup_pct = OZ1_7YR_STEPUP_PCT
        elif holding_years >= 5:
            stepup_pct = OZ1_5YR_STEPUP_PCT
        else:
            stepup_pct = 0.0
    else:  # oz2
        if investment.is_rural or investment.fund_type == "qorf":
            stepup_pct = RURAL_STEPUP_PCT if holding_years >= 5 else 0.0
        else:
            stepup_pct = OZ2_5YR_STEPUP_PCT if holding_years >= 5 else 0.0

    # ── Deferred gain ─────────────────────────────────────────────────────────
    deferred_gain = investment.capital_gain_invested
    stepup_amount = deferred_gain * stepup_pct
    taxable_deferred = deferred_gain - stepup_amount
    deferred_tax_savings = taxable_deferred * tax_rate * (
        holding_years / (investment.capital_gain_invested / deferred_gain)
    ) if deferred_gain > 0 else 0

    # Simplified: tax savings = step-up * tax rate + time value of deferral
    time_value_factor = min(holding_years, 5) / 5
    deferred_tax_savings = (
        stepup_amount * tax_rate +
        taxable_deferred * tax_rate * 0.05 * time_value_factor
    )

    # ── Post-investment appreciation exclusion ────────────────────────────────
    appreciation = max(fmv - investment.fmv_at_investment, 0)
    excluded_appreciation = appreciation if holding_years >= 10 else 0.0

    # ── Total benefit ─────────────────────────────────────────────────────────
    total_benefit = deferred_tax_savings + excluded_appreciation * tax_rate

    # ── Effective tax rate on original gain ───────────────────────────────────
    effective_rate = max(
        (deferred_gain * tax_rate - total_benefit) / deferred_gain, 0
    )

    return QOFBenefits(
        investment=investment,
        holding_years=round(holding_years, 2),
        deferred_gain=deferred_gain,
        stepup_amount=round(stepup_amount, 0),
        stepup_pct=stepup_pct,
        deferred_tax_savings=round(deferred_tax_savings, 0),
        excluded_appreciation=round(excluded_appreciation, 0),
        total_tax_benefit=round(total_benefit, 0),
        effective_tax_rate=round(effective_rate, 4),
        tax_rate_assumed=tax_rate,
    )


def compare_scenarios(
    capital_gain: float,
    investment_date: str,
    current_fmv: float,
    exit_date: str = None,
    tax_rate: float = 0.238,
) -> dict:
    """
    Compare tax outcomes across four scenarios:
    1. No OZ investment (pay tax immediately)
    2. OZ 1.0 QOF (standard)
    3. OZ 2.0 QOF (standard)
    4. OZ 2.0 Rural QORF (enhanced)
    """
    import uuid

    def make_inv(oz_version, fund_type, is_rural):
        return OZInvestment(
            id=str(uuid.uuid4())[:8],
            investor_name="Investor",
            fund_name=f"{oz_version.upper()} {'Rural' if is_rural else 'Standard'} Fund",
            fund_type=fund_type,
            oz_version=oz_version,
            tract_id="17031840100",
            investment_type="real_estate",
            capital_gain_invested=capital_gain,
            investment_date=investment_date,
            fmv_at_investment=capital_gain,
            current_fmv=current_fmv,
            is_rural=is_rural,
        )

    no_oz_tax = capital_gain * tax_rate
    oz1 = calculate_benefits(make_inv("oz1", "qof", False),
                             current_fmv, exit_date, tax_rate)
    oz2 = calculate_benefits(make_inv("oz2", "qof", False),
                             current_fmv, exit_date, tax_rate)
    oz2_rural = calculate_benefits(make_inv("oz2", "qorf", True),
                                   current_fmv, exit_date, tax_rate)

    print(f"\nOZ Scenario Comparison — ${capital_gain:,.0f} Capital Gain")
    print("=" * 60)
    print(f"  No OZ Investment:     Tax = ${no_oz_tax:,.0f} (rate: {tax_rate*100:.1f}%)")
    print(f"  OZ 1.0 Standard:      Tax benefit = ${oz1.total_tax_benefit:,.0f}")
    print(f"  OZ 2.0 Standard:      Tax benefit = ${oz2.total_tax_benefit:,.0f}")
    print(f"  OZ 2.0 Rural QORF:    Tax benefit = ${oz2_rural.total_tax_benefit:,.0f}")
    print(f"  Best strategy:        "
          f"{'Rural QORF' if oz2_rural.total_tax_benefit >= oz2.total_tax_benefit else 'OZ 2.0 Standard'}")
    print()

    return {
        "no_oz_tax": no_oz_tax,
        "oz1_benefit": oz1.total_tax_benefit,
        "oz2_benefit": oz2.total_tax_benefit,
        "oz2_rural_benefit": oz2_rural.total_tax_benefit,
        "oz1_details": oz1,
        "oz2_details": oz2,
        "oz2_rural_details": oz2_rural,
    }

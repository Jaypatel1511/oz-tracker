# oz-tracker 🏘️

**Opportunity Zone investment tracker for OZ 1.0 and OZ 2.0.**

Check eligibility, calculate QOF tax benefits, analyze rural QORF enhanced incentives,
and track a portfolio of Qualified Opportunity Fund investments — built for the
One Big Beautiful Bill Act (2025) permanent OZ program.

---

## Why oz-tracker?

The One Big Beautiful Bill Act made Opportunity Zones permanent with decennial
redesignation cycles. OZ 2.0 brings stricter eligibility, enhanced rural benefits,
and new reporting requirements. No open source Python library existed to handle
both OZ 1.0 and OZ 2.0 mechanics — until now.

---

## Installation

    pip install oz-tracker

---

## Quickstart

    from oztracker import OZ1Checker, OZ2Checker, OZInvestment
    from oztracker import calculate_benefits, compare_scenarios, OZPortfolio

    # Check OZ 1.0 eligibility (current map through 2028)
    oz1 = OZ1Checker()
    print(oz1.is_designated("17031840100"))   # True

    # Check OZ 2.0 eligibility (2027 designations)
    oz2 = OZ2Checker()
    print(oz2.is_eligible("17031840100"))     # True
    print(oz2.is_rural("17019000100"))        # True

    # Compare OZ 1.0 vs 2.0 tract overlap
    oz2.compare_oz1_oz2(oz1.designated_tracts)

    # Calculate QOF tax benefits
    inv = OZInvestment(
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
        current_fmv=750_000,
        state="IL",
        is_rural=False,
    )

    benefits = calculate_benefits(inv, exit_date="2037-03-15")
    benefits.summary()

    # Compare all scenarios
    compare_scenarios(
        capital_gain=500_000,
        investment_date="2027-01-01",
        current_fmv=700_000,
        exit_date="2037-01-01",
    )

    # Portfolio tracking
    p = OZPortfolio(name="Family OZ Portfolio")
    p.add(inv)
    p.summary()

---

## OZ 2.0 Key Changes (One Big Beautiful Bill Act 2025)

- Program made permanent — decennial redesignation every 10 years
- Stricter eligibility — MFI threshold tightened from 80% to 70% of AMI
- Contiguous tract rule eliminated — fewer eligible tracts in 2027
- Rural QORF enhanced benefits — 30% basis step-up vs 10% standard
- Rolling 5-year deferral — no more 2026 deadline
- New reporting requirements — annual IRS Form 8996 disclosures

---

## Eligibility Rules

OZ 1.0 (current map, through 2028):
- Poverty rate >= 20%, OR
- MFI <= 80% of state/metro AMI

OZ 2.0 (2027 designations):
- MFI < 70% of state/metro AMI, OR
- Poverty rate >= 20% AND MFI <= 125% of state/metro AMI

---

## Tax Benefits Modeled

- OZ 1.0: deferral through 12/31/2026, 5-year 10% step-up, 7-year 15% step-up
- OZ 2.0: rolling 5-year deferral, 5-year 10% step-up
- Rural QORF: 5-year 30% step-up (triple standard benefit)
- 10-year exclusion: post-investment appreciation excluded from tax

---

## Running Tests

    PYTHONPATH=. pytest tests/ -v

37 tests across all modules.

---

## Who This Is For

- Investors evaluating OZ 1.0 vs OZ 2.0 strategy
- Real estate developers screening project locations for eligibility
- Fund managers tracking QOF and QORF portfolios
- Tax advisors modeling capital gains deferral scenarios
- Community development practitioners preparing for 2027 redesignation

---

## License

MIT 2026 Jaypatel1511

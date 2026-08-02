"""
Core dataclasses and constants for Opportunity Zone tracking.
Based on OZ 1.0 (Tax Cuts and Jobs Act 2017) and
OZ 2.0 (One Big Beautiful Bill Act 2025).
"""
from dataclasses import dataclass, field
from typing import Optional


# ── OZ 2.0 Eligibility Thresholds (effective 2027) ───────────────────────────
# Source: Rev. Proc. 2026-14, April 6, 2026
OZ2_MFI_THRESHOLD           = 0.70   # MFI < 70% of state/metro AMI
OZ2_POVERTY_THRESHOLD       = 0.20   # Poverty rate >= 20%
OZ2_POVERTY_MFI_THRESHOLD   = 1.25   # AND MFI <= 125% of state/metro AMI

# ── OZ 1.0 Eligibility Thresholds (effective through 2028) ───────────────────
OZ1_MFI_THRESHOLD           = 0.80   # MFI <= 80% of state/metro AMI
OZ1_POVERTY_THRESHOLD       = 0.20   # Poverty rate >= 20%

# ── Rural QORF Enhanced Benefits ─────────────────────────────────────────────
RURAL_STEPUP_PCT            = 0.30   # 30% basis step-up (vs 10% standard)
STANDARD_STEPUP_PCT         = 0.10   # 10% basis step-up
RURAL_SUBSTANTIAL_IMPROVE   = 0.50   # 50% improvement test (vs 100%)
STANDARD_SUBSTANTIAL_IMPROVE = 1.00  # 100% improvement test

# ── OZ 1.0 Tax Benefit Parameters ────────────────────────────────────────────
OZ1_DEFERRAL_DEADLINE       = "2026-12-31"
OZ1_MAP_EXPIRY              = "2028-12-31"
OZ1_5YR_STEPUP_PCT          = 0.10
OZ1_7YR_STEPUP_PCT          = 0.15
OZ1_MIN_HOLD_TAX_FREE       = 10     # years

# ── OZ 2.0 Tax Benefit Parameters ────────────────────────────────────────────
OZ2_EFFECTIVE_DATE          = "2027-01-01"
OZ2_5YR_STEPUP_PCT          = 0.10
OZ2_DEFERRAL_YEARS          = 5      # rolling 5-year deferral
OZ2_MAX_STEPUP_HOLD         = 30     # years (capped at 30)

# ── Investment Types ──────────────────────────────────────────────────────────
INVESTMENT_TYPES = {
    "real_estate":      "Real estate development or improvement",
    "operating_business": "Operating business investment",
    "mixed_use":        "Mixed-use development",
    "infrastructure":   "Infrastructure project",
    "rural":            "Rural qualified opportunity fund investment",
}

# ── Fund Types ────────────────────────────────────────────────────────────────
FUND_TYPES = {
    "qof":   "Qualified Opportunity Fund (standard)",
    "qorf":  "Qualified Opportunity Rural Fund (enhanced rural benefits)",
}

# ── OZ Program Versions ───────────────────────────────────────────────────────
OZ_VERSIONS = {
    "oz1": "OZ 1.0 — Tax Cuts and Jobs Act 2017 (expires 2028)",
    "oz2": "OZ 2.0 — One Big Beautiful Bill Act 2025 (effective 2027, permanent)",
}


@dataclass
class OZTract:
    """Represents a single Opportunity Zone census tract.

    The eligibility fields are tri-state (``True`` / ``None``), matching the
    ``OZ1Checker.is_designated`` / ``OZ2Checker.is_eligible`` contract. They
    default to ``None`` — "not confirmed" — and NOT to ``False``.

    This changed in 0.2.0. Through 0.1.0 both defaulted to ``bool`` ``False``,
    so an ``OZTract`` constructed without eligibility data asserted a confident
    negative it had no basis for: the same fabricated negative this release
    exists to remove, in a public exported type. Callers must branch on
    ``is True`` / ``is None``, never on truthiness.
    """
    tract_id: str                      # 11-digit FIPS code
    state: str
    oz_version: str                    # "oz1", "oz2", or "both"
    is_rural: bool = False
    is_oz1_eligible: Optional[bool] = None
    is_oz2_eligible: Optional[bool] = None
    poverty_rate: Optional[float] = None
    ami_ratio: Optional[float] = None
    oz1_expires: str = "2028-12-31"
    oz2_effective: str = "2027-01-01"

    @property
    def is_active(self) -> Optional[bool]:
        """Tri-state, forwarding ``is_oz1_eligible`` unchanged.

        ``True`` = confirmed designated under OZ 1.0. ``None`` = not confirmed,
        which is the default and is NOT a negative finding. ``False`` only if a
        caller explicitly assigned it, in which case it is the caller's own
        assertion and is passed through rather than reinterpreted.
        """
        return self.is_oz1_eligible

    @property
    def enhanced_rural_benefits(self) -> Optional[bool]:
        """Tri-state: ``True`` if the tract is rural AND confirmed OZ 2.0
        eligible; ``False`` if it is definitely not rural; ``None`` if rural but
        OZ 2.0 eligibility is unconfirmed.

        The ``and`` below already produces exactly that — ``False and None`` is
        ``False`` (a real fact: a non-rural tract gets no rural benefit
        regardless), ``True and None`` is ``None``. Only the annotation needed
        widening once ``is_oz2_eligible`` became tri-state.
        """
        return self.is_rural and self.is_oz2_eligible


@dataclass
class OZInvestment:
    """
    Represents a single investment in a Qualified Opportunity Fund.
    Tracks holding period, tax benefits, and exit scenarios.
    """
    id: str
    investor_name: str
    fund_name: str
    fund_type: str                     # "qof" or "qorf"
    oz_version: str                    # "oz1" or "oz2"
    tract_id: str
    investment_type: str
    capital_gain_invested: float       # original capital gain reinvested
    investment_date: str               # e.g. "2024-06-15"
    fmv_at_investment: float           # FMV of QOF interest at investment
    current_fmv: Optional[float] = None
    exit_date: Optional[str] = None
    state: str = ""
    is_rural: bool = False
    notes: Optional[str] = None

    def __post_init__(self):
        if self.capital_gain_invested <= 0:
            raise ValueError("capital_gain_invested must be positive")
        if self.fund_type not in FUND_TYPES:
            raise ValueError(
                f"fund_type must be one of {list(FUND_TYPES.keys())}"
            )
        if self.oz_version not in OZ_VERSIONS:
            raise ValueError(
                f"oz_version must be one of {list(OZ_VERSIONS.keys())}"
            )
        if self.investment_type not in INVESTMENT_TYPES:
            raise ValueError(
                f"investment_type must be one of {list(INVESTMENT_TYPES.keys())}"
            )

    @property
    def amount_mm(self) -> float:
        return self.capital_gain_invested / 1_000_000

    def __repr__(self):
        return (
            f"OZInvestment(id='{self.id}', fund='{self.fund_name}', "
            f"amount=${self.amount_mm:.2f}MM, "
            f"version='{self.oz_version}', rural={self.is_rural})"
        )


@dataclass
class QOFBenefits:
    """Tax benefit calculation result for a QOF investment."""
    investment: OZInvestment
    holding_years: float
    deferred_gain: float
    stepup_amount: float
    stepup_pct: float
    deferred_tax_savings: float        # at assumed tax rate
    excluded_appreciation: float       # post-investment gain excluded
    total_tax_benefit: float
    effective_tax_rate: float
    tax_rate_assumed: float = 0.238    # 23.8% (20% cap gains + 3.8% NIIT)

    def summary(self) -> None:
        print(f"\nQOF Tax Benefit Summary — {self.investment.fund_name}")
        print("=" * 55)
        print(f"  Investor:              {self.investment.investor_name}")
        print(f"  Fund Type:             {self.investment.fund_type.upper()}")
        print(f"  OZ Version:            {self.investment.oz_version.upper()}")
        print(f"  Rural Benefits:        {'Yes' if self.investment.is_rural else 'No'}")
        print(f"  Capital Gain Invested: ${self.investment.capital_gain_invested:,.0f}")
        print(f"  Holding Period:        {self.holding_years:.1f} years")
        print(f"\n  Deferred Gain:         ${self.deferred_gain:,.0f}")
        print(f"  Step-Up Amount:        ${self.stepup_amount:,.0f} ({self.stepup_pct*100:.0f}%)")
        print(f"  Deferred Tax Savings:  ${self.deferred_tax_savings:,.0f}")
        print(f"  Excluded Appreciation: ${self.excluded_appreciation:,.0f}")
        print(f"  ── Total Tax Benefit:  ${self.total_tax_benefit:,.0f}")
        print(f"  ── Effective Tax Rate: {self.effective_tax_rate*100:.1f}%")
        print()

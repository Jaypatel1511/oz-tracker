"""Holding-period determinability (added after the stage-3 audit).

`calculate_benefits()` defaults exit_date to today, and that default was
unguarded: an investment dated in the FUTURE produced a negative holding period
that flowed into every downstream figure. The README's own 2027 example
returned holding_years -0.62 and total_tax_benefit -$733, and
OZPortfolio.summary() printed "Total Tax Benefit: $-0.00MM / -0.1%".

The contract these pin:

  * an undeterminable holding period RAISES OZCalculationError — it is not
    clamped to zero, because a confident $0.00 for a question with no answer is
    the same fabrication class as a confident False for a tract nobody looked
    up, and a caller cannot distinguish it from a genuine zero-benefit result;
  * a portfolio TOTAL refuses rather than silently omitting members, because a
    bare float cannot carry "this covers 2 of your 3 investments";
  * summary(), which CAN carry the caveat, reports the covered subset as
    explicitly partial and names every excluded investment.

Dates here are deliberately far from today (2015 / 2099) so nothing depends on
when the suite runs.
"""
import pytest

from oztracker import (
    OZInvestment, OZPortfolio, calculate_benefits,
    OZCalculationError, OZTrackerError,
)

FAR_FUTURE = "2099-06-01"   # always after today
LONG_PAST = "2015-01-15"    # always before today


def _inv(inv_id="INV1", date=LONG_PAST, amount=500_000, name="Test Fund"):
    return OZInvestment(
        id=inv_id, investor_name="Jay Patel", fund_name=name,
        fund_type="qof", oz_version="oz2", tract_id="17031840100",
        investment_type="real_estate", capital_gain_invested=amount,
        investment_date=date, fmv_at_investment=amount,
        current_fmv=amount * 1.5, state="IL", is_rural=False,
    )


# ── Individual path ──────────────────────────────────────────────────────────

def test_future_investment_without_exit_date_raises():
    """The exact shape of the original bug."""
    with pytest.raises(OZCalculationError):
        calculate_benefits(_inv(date=FAR_FUTURE))


def test_it_raises_rather_than_returning_any_figure():
    """The mutation this is aimed at: clamping the holding period to zero.

    A clamp returns a QOFBenefits whose numbers all look like real results —
    holding_years 0.0, total_tax_benefit 0.0 — for a question that has no
    answer. Asserting "raises" is what makes the clamp fail; asserting
    "total == 0" would PASS against the clamp and is exactly the toothless
    shape this suite is meant to avoid.
    """
    with pytest.raises(OZCalculationError):
        result = calculate_benefits(_inv(date=FAR_FUTURE))
        pytest.fail(
            f"returned {result.total_tax_benefit!r} "
            f"(holding_years={result.holding_years!r}) instead of raising — a "
            f"clamped or negative figure for an investment not yet made"
        )


def test_error_names_the_investment_and_both_dates():
    with pytest.raises(OZCalculationError) as exc:
        calculate_benefits(_inv(inv_id="P002", date=FAR_FUTURE,
                                name="Rural Illinois QORF"))
    msg = str(exc.value)
    assert "P002" in msg
    assert "Rural Illinois QORF" in msg
    assert "2099-06-01" in msg, "the error must name the investment date"
    assert "exit_date" in msg, "the error must say which input would fix it"


def test_error_is_catchable_at_the_package_base():
    with pytest.raises(OZTrackerError):
        calculate_benefits(_inv(date=FAR_FUTURE))


def test_explicit_exit_date_before_investment_date_also_raises():
    """Not only the defaulted-to-today case — an explicitly inverted pair too."""
    with pytest.raises(OZCalculationError) as exc:
        calculate_benefits(_inv(date="2030-01-01"), exit_date="2029-01-01")
    assert "2029-01-01" in str(exc.value)


def test_same_day_exit_is_determinable_and_not_an_error():
    """Zero length is a real answer; only NEGATIVE is undeterminable.

    Guards against over-correcting the boundary to `<=`, which would refuse a
    legitimate same-day question.
    """
    b = calculate_benefits(_inv(date="2020-05-01"), exit_date="2020-05-01")
    assert b.holding_years == 0.0
    assert b.total_tax_benefit == 0.0


def test_normal_investment_is_unaffected():
    b = calculate_benefits(_inv(date="2027-03-15"), exit_date="2037-03-15")
    assert b.holding_years == 10.0
    assert b.total_tax_benefit > 0


def test_past_investment_without_exit_date_still_works():
    """The default-to-today path is still valid when it yields a real period."""
    b = calculate_benefits(_inv(date=LONG_PAST))
    assert b.holding_years > 0


# ── Portfolio path ───────────────────────────────────────────────────────────

def _mixed_portfolio():
    """1 determinable + 2 undeterminable."""
    p = OZPortfolio(name="Family OZ Portfolio")
    p.add(_inv("P001", LONG_PAST, 750_000, "Chicago South Side OZ Fund"))
    p.add(_inv("P002", FAR_FUTURE, 500_000, "Rural Illinois QORF"))
    p.add(_inv("P003", FAR_FUTURE, 250_000, "Detroit OZ Business Fund"))
    return p


def test_total_tax_benefits_refuses_a_partial_total():
    """The mutation this is aimed at: skipping undeterminable members.

    A skip returns a float that reads as a complete portfolio total but
    silently covers only 1 of 3 investments. Nothing in the return type warns
    the caller. Refusing is the only option a bare float leaves.
    """
    p = _mixed_portfolio()
    with pytest.raises(OZCalculationError) as exc:
        total = p.total_tax_benefits()
        pytest.fail(
            f"returned {total!r} — a subtotal covering 1 of 3 investments, "
            f"presented as a portfolio total"
        )
    msg = str(exc.value)
    assert "2 of 3" in msg, "the error must quantify the shortfall"
    assert "P002" in msg and "P003" in msg, "it must name the offending members"
    assert "P001" not in msg, "it must not blame the determinable member"


def test_total_tax_benefits_works_when_every_member_is_determinable():
    p = OZPortfolio(name="All Determinable")
    p.add(_inv("A", LONG_PAST, 500_000))
    p.add(_inv("B", "2016-02-01", 250_000))
    assert p.total_tax_benefits() > 0


def test_undeterminable_benefits_names_exactly_the_affected_members():
    p = _mixed_portfolio()
    bad = p.undeterminable_benefits()
    assert [inv.id for inv, _ in bad] == ["P002", "P003"]
    assert all(reason for _, reason in bad), "each must carry a reason"


def test_summary_marks_the_figure_partial_and_names_exclusions(capsys):
    _mixed_portfolio().summary()
    out = capsys.readouterr().out

    assert "PARTIAL" in out, "a partial figure must be labelled partial"
    assert "covers 1 of 3 investments" in out
    assert "NOT DETERMINABLE" in out
    # every excluded investment named, not silently dropped
    assert "P002" in out and "P003" in out
    assert "Rural Illinois QORF" in out
    assert "Detroit OZ Business Fund" in out


def test_summary_does_not_present_a_partial_figure_as_a_total(capsys):
    """The label itself is the contract: with members excluded, the output must
    not contain a bare "Total Tax Benefit" line that reads as complete."""
    _mixed_portfolio().summary()
    out = capsys.readouterr().out

    assert "Total Tax Benefit:" not in out, (
        "a portfolio missing 2 of 3 benefit figures printed a line reading as "
        "a complete total"
    )
    assert "Benefit (covered subset):" in out


def test_summary_says_the_excluded_are_not_zero(capsys):
    """The distinction the whole fix exists to preserve."""
    _mixed_portfolio().summary()
    out = capsys.readouterr().out
    assert "not zero" in out.lower()


def test_summary_is_unchanged_when_everything_is_determinable(capsys):
    p = OZPortfolio(name="All Determinable")
    p.add(_inv("A", LONG_PAST, 500_000))
    p.summary()
    out = capsys.readouterr().out

    assert "Total Tax Benefit:" in out, "the normal path must still read as a total"
    assert "PARTIAL" not in out
    assert "NOT DETERMINABLE" not in out


def test_summary_with_nothing_determinable_prints_no_figure(capsys):
    p = OZPortfolio(name="All Future")
    p.add(_inv("F1", FAR_FUTURE, 500_000))
    p.add(_inv("F2", FAR_FUTURE, 250_000))
    p.summary()
    out = capsys.readouterr().out

    assert "No benefit figure can be computed" in out
    # No benefit FIGURE of any kind — neither a total nor a subset line. (The
    # "$0.00MM of $0.75MM" on the PARTIAL line is covered *capital gain*, which
    # is genuinely zero and correct to show; the point is that no zero-dollar
    # BENEFIT is presented as a result.)
    assert "Total Tax Benefit:" not in out
    assert "Benefit (covered subset):" not in out
    assert "F1" in out and "F2" in out

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


def _inv(inv_id="INV1", date=LONG_PAST, amount=500_000, name="Test Fund",
         exit_date=None):
    return OZInvestment(
        id=inv_id, investor_name="Jay Patel", fund_name=name,
        fund_type="qof", oz_version="oz2", tract_id="17031840100",
        investment_type="real_estate", capital_gain_invested=amount,
        investment_date=date, fmv_at_investment=amount,
        current_fmv=amount * 1.5, exit_date=exit_date,
        state="IL", is_rural=False,
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


# ── Where the exit date comes from ───────────────────────────────────────────
#
# OZInvestment has carried an ``exit_date`` field since 0.1.0, and
# calculate_benefits() never read it — it read only its own parameter and
# otherwise defaulted to today. A fully-specified investment carrying its own
# realized exit date was therefore measured to today and, if dated in the
# future, REFUSED: told it had omitted a field it had supplied, and prescribed
# a remedy it had already applied.
#
# That is a FALSE REFUSAL, and it is the mirror image of the fabrication class
# this release exists to kill. "No answer exists from these inputs" is exactly
# as wrong as a made-up figure when the inputs contain the answer.
#
# The resolution order is: explicit parameter -> investment.exit_date -> today.
# The parameter wins over the field deliberately, mirroring how ``current_fmv``
# already overrides ``investment.current_fmv``: the field is the investment's
# recorded exit, the parameter is a what-if the caller is modelling right now,
# and a per-call argument overriding a stored default is the ordinary rule.
#
# No test anywhere constructed an OZInvestment with exit_date set before these
# — every ``exit_date=`` in tests/ was the function parameter — which is why a
# 94-test suite could not see it.

def test_exit_date_field_is_honoured():
    """The F1 bug: a future-dated investment carrying its own exit date.

    Before the fix this raised "exit_date was not supplied" for an investment
    whose exit_date WAS supplied.
    """
    b = calculate_benefits(_inv(date="2027-03-15", exit_date="2037-03-15"))
    assert b.holding_years == 10.0
    assert b.total_tax_benefit > 0


def test_exit_date_field_gives_the_same_result_as_the_parameter():
    """Field-only and parameter-only must agree on every figure, not just run."""
    from_field = calculate_benefits(_inv(date="2027-03-15",
                                         exit_date="2037-03-15"))
    from_param = calculate_benefits(_inv(date="2027-03-15"),
                                    exit_date="2037-03-15")
    assert from_field.holding_years == from_param.holding_years
    assert from_field.total_tax_benefit == from_param.total_tax_benefit
    assert from_field.stepup_pct == from_param.stepup_pct
    assert from_field.excluded_appreciation == from_param.excluded_appreciation


def test_exit_date_parameter_only_is_unchanged():
    """Parameter-only: the pre-existing path, pinned so the fallback cannot
    accidentally start overriding an explicit argument."""
    b = calculate_benefits(_inv(date="2027-03-15"), exit_date="2032-03-15")
    assert b.holding_years == 5.0


def test_exit_date_parameter_wins_over_the_field():
    """Both supplied -> the explicit parameter wins.

    Stated rather than assumed: the caller is modelling a different exit than
    the one on record, and the per-call argument is the more specific input.
    """
    inv = _inv(date="2027-03-15", exit_date="2037-03-15")   # 10y on record
    b = calculate_benefits(inv, exit_date="2032-03-15")     # 5y modelled
    assert b.holding_years == 5.0, (
        "the stored field overrode the explicit parameter — precedence is "
        "parameter -> field -> today"
    )
    assert inv.exit_date == "2037-03-15", "the investment must not be mutated"


def test_neither_exit_date_supplied_still_defaults_to_today():
    """Neither: the today default survives, for a past-dated investment."""
    b = calculate_benefits(_inv(date=LONG_PAST))
    assert b.holding_years > 0


def test_neither_exit_date_supplied_on_a_future_investment_still_raises():
    """Neither, and unanswerable: the genuine refusal is untouched."""
    with pytest.raises(OZCalculationError):
        calculate_benefits(_inv(date=FAR_FUTURE))


def test_field_exit_date_before_investment_date_raises():
    """A field can be inverted too, and must be refused like a parameter."""
    with pytest.raises(OZCalculationError) as exc:
        calculate_benefits(_inv(date="2030-01-01", exit_date="2029-01-01"))
    assert "2029-01-01" in str(exc.value)


# ── The error message must not contradict the inputs ─────────────────────────

def test_error_says_not_supplied_only_when_it_really_was_not_supplied():
    with pytest.raises(OZCalculationError) as exc:
        calculate_benefits(_inv(date=FAR_FUTURE))
    msg = str(exc.value)
    assert "not supplied" in msg
    assert "defaulted to today" in msg


def test_error_never_claims_a_supplied_field_was_omitted():
    """The precise false statement F1 reported: telling a user they omitted a
    field they provided, and prescribing a remedy they already applied."""
    with pytest.raises(OZCalculationError) as exc:
        calculate_benefits(_inv(date="2030-01-01", exit_date="2029-01-01"))
    msg = str(exc.value)
    assert "not supplied" not in msg, (
        "the investment carried exit_date and the error said it was not supplied"
    )
    assert "defaulted to today" not in msg
    assert "investment.exit_date" in msg, (
        "the error must say WHERE the offending date came from, so the caller "
        "knows which of the two inputs to change"
    )


def test_error_distinguishes_the_parameter_from_the_field():
    with pytest.raises(OZCalculationError) as exc:
        calculate_benefits(_inv(date="2030-01-01"), exit_date="2029-01-01")
    msg = str(exc.value)
    assert "not supplied" not in msg
    assert "investment.exit_date" not in msg, (
        "the date came from the parameter; naming the field would send the "
        "caller to edit the wrong input"
    )


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


def _fully_specified_portfolio():
    """3 future-dated investments, every one carrying its own exit_date.

    Under the F1 bug this portfolio reported 100% NOT DETERMINABLE: every
    member was measured to today, went negative, and was refused — while
    carrying the exact field that answers the question.
    """
    p = OZPortfolio(name="Realized OZ Portfolio")
    p.add(_inv("R001", "2027-03-15", 750_000, "Chicago South Side OZ Fund",
               exit_date="2037-03-15"))
    p.add(_inv("R002", "2027-06-01", 500_000, "Rural Illinois QORF",
               exit_date="2037-06-01"))
    p.add(_inv("R003", "2027-09-01", 250_000, "Detroit OZ Business Fund",
               exit_date="2037-09-01"))
    return p


def test_partition_honours_the_exit_date_field():
    """_partition_benefits() forwards nothing itself — it calls
    calculate_benefits(inv, tax_rate=...) with exit_date unset, so the field
    fallback inside the calculator is what covers it. This pins that the single
    fallback site is enough and no second one is needed in the tracker."""
    p = _fully_specified_portfolio()
    assert p.undeterminable_benefits() == []


def test_total_tax_benefits_covers_a_fully_specified_portfolio():
    p = _fully_specified_portfolio()
    total = p.total_tax_benefits()
    assert isinstance(total, float)
    assert total > 0


def test_summary_of_a_fully_specified_portfolio_is_not_partial(capsys):
    """The knock-on F1 demands: honouring the field changes which investments
    are determinable, which changes what summary() renders."""
    _fully_specified_portfolio().summary()
    out = capsys.readouterr().out

    assert "Total Tax Benefit:" in out
    assert "PARTIAL" not in out
    assert "NOT DETERMINABLE" not in out


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


def test_partial_percentage_is_the_covered_gain_denominator(capsys):
    """Pin the CONCRETE percentage, not an invariant that any denominator
    satisfies.

    The arithmetic here was already right, and nothing pinned it: swapping
    ``covered_gain`` for ``self.total_invested`` left the whole suite green
    while producing a line whose label contradicts its value — "% of covered
    gain" computed over gain that was not covered.

    A balancing identity is not a correctness test. The exact figures:

        covered benefit  $115,132  (P001 only)
        covered gain     $750,000  -> 15.4%
        full portfolio   $1,500,000 -> 7.7%   <- the mutation

    Both are "a percentage"; only one matches the label.
    """
    _mixed_portfolio().summary()
    out = capsys.readouterr().out

    assert "  % of covered gain:     15.4%" in out
    assert "7.7%" not in out, (
        "the percentage was computed over the FULL portfolio gain while "
        "labelled as the covered subset"
    )


def test_partial_percentage_matches_a_hand_computed_ratio():
    """The same pin, independent of print formatting."""
    p = _mixed_portfolio()
    computed, undeterminable = p._partition_benefits()
    covered_gain = sum(i.capital_gain_invested for i, _ in computed)
    benefit = sum(b.total_tax_benefit for _, b in computed)

    assert covered_gain == 750_000
    assert p.total_invested == 1_500_000
    assert benefit == pytest.approx(115_132)
    assert benefit / covered_gain * 100 == pytest.approx(15.35, abs=0.01)


# ── Empty portfolio: the two entry points must agree ─────────────────────────
#
# An empty portfolio's benefit is a genuine 0.0 — the sum of no benefits — and
# NOT an unanswerable question. Nothing is undeterminable because there is
# nothing to determine. "There are investments here whose benefit has no
# answer" is a different statement, and it is false of an empty portfolio.
#
# total_tax_benefits() had this right and summary() regressed: branching on
# `if computed:` collapsed "nothing to compute" into "nothing computable", so
# the two public entry points disagreed about the same object, and summary()
# printed a refusal where bd47b1f printed $0.00MM.

def test_empty_portfolio_total_is_zero_and_does_not_raise():
    assert OZPortfolio(name="Empty").total_tax_benefits() == 0.0


def test_empty_portfolio_total_is_a_float():
    """sum() over an empty sequence returns int 0; the annotation says float,
    and bd47b1f's accumulator started at 0.0."""
    total = OZPortfolio(name="Empty").total_tax_benefits()
    assert isinstance(total, float)


def test_empty_portfolio_summary_prints_a_zero_total(capsys):
    OZPortfolio(name="Empty").summary()
    out = capsys.readouterr().out

    assert "  Total Tax Benefit:     $0.00MM" in out
    assert "No benefit figure can be computed" not in out, (
        "summary() refused for a portfolio whose total is a genuine zero, "
        "contradicting total_tax_benefits() on the same object"
    )
    assert "PARTIAL" not in out
    assert "NOT DETERMINABLE" not in out


def test_empty_portfolio_entry_points_agree(capsys):
    """The disagreement itself is the finding — pin it directly."""
    p = OZPortfolio(name="Empty")
    total = p.total_tax_benefits()
    p.summary()
    out = capsys.readouterr().out

    assert f"  Total Tax Benefit:     ${total/1e6:.2f}MM" in out


def test_empty_portfolio_prints_no_percentage_line(capsys):
    """0/0 has no percentage, and bd47b1f printed none."""
    OZPortfolio(name="Empty").summary()
    assert "% of Gain" not in capsys.readouterr().out


# ── Exact formatting of the complete path ────────────────────────────────────

def test_complete_path_formatting_is_unchanged_from_bd47b1f(capsys):
    """0.2.0's partial-reporting work claimed the fully-determinable path was
    byte-identical to before it. It was not: assembling the line from a padded
    label drifted the percentage line by one space.

    These are the literal bytes bd47b1f printed. They are a compatibility
    surface — the README quotes them — so they are pinned as bytes, not as a
    regex over "some number followed by a percent sign".
    """
    p = OZPortfolio(name="All Determinable")
    p.add(_inv("A", LONG_PAST, 500_000))
    p.summary()
    out = capsys.readouterr().out

    assert "  Total Tax Benefit:     $" in out
    assert "  Benefit as % of Gain:  " in out
    assert "  Benefit as % of Gain:   " not in out, "one space too many"


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

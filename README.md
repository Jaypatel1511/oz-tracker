# oz-tracker 🏘️

**Opportunity Zone investment tracker for OZ 1.0 and OZ 2.0.**

Calculate QOF tax benefits, analyze rural QORF enhanced incentives, and track a
portfolio of Qualified Opportunity Fund investments — built for the One Big
Beautiful Bill Act (2025) permanent OZ program.

---

## ⚠️ Status — tract lookup is non-functional in 0.2.0

**Read this before installing.** The OZ tract eligibility lookup does not work,
and 0.2.0 does not fix it. What 0.2.0 fixes is that it no longer *pretends* to.

Both upstream data sources this package depends on return **HTTP 404** (verified
2026-07-30):

| Source | URL | Status |
|---|---|---|
| OZ 1.0 designated tracts (IRS Notice 2018-48) | `cdfifund.gov/.../QOZ_Tracts_List_Formatted_July2018.xlsx` | **404** |
| OZ 2.0 eligible tracts (Rev. Proc. 2026-14) | `home.treasury.gov/.../Eligible-LICs-for-Nomination-as-2027-QOZs.xlsx` | **404** |

In 0.1.0, every download failure silently substituted an 8-row hardcoded sample
set. Because both URLs were already dead, that fallback was the *only* path
taken in the field. `is_designated()` returned a confident `False` for **8,756
of the 8,764** designated OZ 1.0 tracts — 99.91% — with nothing in the return
value to indicate that no data had been loaded.

**What changes in 0.2.0:**

- `OZ1Checker()` and `OZ2Checker()` **raise `OZDownloadError`** instead of
  degrading to sample data. In practice this means they raise on essentially
  every call. That is the intended behavior: a package that says "I cannot
  answer" is strictly better than one that answers wrong.
- `is_designated()`, `is_eligible()`, and `is_rural()` return
  `Optional[bool]` — `True` or `None`, **never `False`**. See
  "The tri-state contract" below.
- Sample data still exists but is reachable **only** by explicit opt-in
  (`OZ1Checker.from_sample()`), and anything built from it is stamped
  `data_source == "sample"`.

**Restoration is deferred** — deliberately, and for a *different reason per
checker*. 0.2.0 restores neither.

- **OZ 1.0 is blocked on the census-tract vintage question.** The Notice
  2018-48 list is 2018 designations on **2010** tract boundaries, callers hold
  current-vintage GEOIDs, and the API gives them no way to declare which
  vintage they mean. `nmtc-mapper` 0.5.0 is resolving that question; a second,
  independent OZ implementation here would re-arm the same trap and create two
  OZ code paths to keep in sync forever. OZ 1.0 gets solved once, elsewhere.

- **OZ 2.0 is *not* blocked on vintage.** Rev. Proc. 2026-14 §3.01(1) states
  the eligible list is derived from the 2020–2024 ACS 5-Year and 2020 DECIA
  data sets — unambiguously **2020-basis**, the same vintage as a current
  GEOID, so the OZ 1.0 vintage problem simply does not arise. Its Appendix is
  live and machine-readable (verified 2026-08-02 at
  `irs.gov/pub/irs-drop/rp-26-14-appendix.xlsx`: HTTP 200, 25,332 rows,
  columns `State` / `County` / `Census Tract Number` / `Rural Status`, of which
  8,334 are flagged Rural — matching the counts stated in §3.01(1)).
  **OZ 2.0 restoration is deferred purely on scope**: 0.2.0 is a fail-loud
  release and adds no data paths. There is no unresolved data question behind
  it.

  Known source for a future cycle, recorded so the next pass does not have to
  rediscover it: that Appendix — not the dead `home.treasury.gov` URL in
  `loader.py` — is where OZ 2.0 eligibility comes from. Note it is not a
  drop-in for the current parser: the tract column is `Census Tract Number`
  (which the loader's `GEOID` / `CENSUS_TRACT` / `TRACT_ID` / `TRACT` search
  does not match) and its values have leading zeros stripped, so they need
  `zfill(11)` before comparison. Rural status is a `Rural` / `Non-rural`
  string, not a boolean.

**What still works fully:** everything that performs no tract lookup — QOF/QORF
tax benefit modeling (`calculate_benefits`, `compare_scenarios`), the
`OZPortfolio` tracker, the `OZInvestment` / `OZTract` schemas, and the pure
threshold functions `check_oz1_eligibility()` / `check_oz2_eligibility()` (which
compute from poverty-rate and AMI-ratio values **you** supply, and so cannot
fabricate anything).

---

## Undeterminable holding periods

The same "refuse rather than invent" rule applies to the arithmetic half of the
package, not just to tract lookup.

### Where the exit date comes from

`calculate_benefits()` resolves it in this order:

    exit_date=  argument   ->   investment.exit_date   ->   today

mirroring how `current_fmv` already falls back to `investment.current_fmv`.
When both are supplied the **argument wins** — the field is the exit on record
for that investment, the argument is the exit you are modelling on this call,
and the more specific per-call input takes precedence.

The middle leg is new. `OZInvestment.exit_date` has existed since 0.1.0 and
was never read, so an investment carrying its own realized exit date was
measured to *today* anyway and, if dated in the future, **refused** — told it
had omitted a field it had supplied, and handed a remedy it had already
applied. A portfolio of fully-specified investments reported 100% NOT
DETERMINABLE. That false refusal is the mirror image of the fabrication this
release exists to remove: asserting "no answer exists from these inputs" when
the inputs contain the answer is exactly as wrong as inventing a figure.

### When there genuinely is no holding period

If the resolved exit date precedes the investment date, there is nothing to
measure and every downstream figure is meaningless. Through 0.2.0 this was
unguarded: the README's own 2027 example returned `holding_years -0.62` and
`total_tax_benefit -$733`, and `OZPortfolio.summary()` printed
`Total Tax Benefit: $-0.00MM  /  Benefit as % of Gain: -0.1%`.

It now raises `OZCalculationError`, naming the investment, both dates, and
**which of the two inputs the offending date came from**:

    calculate_benefits(inv)          # inv dated 2027, no exit_date anywhere
    # OZCalculationError: Cannot calculate benefits for investment 'INV001'
    # ('Midwest OZ Fund I'): no holding period exists. exit_date was not
    # supplied — neither as an argument nor on the investment — so it
    # defaulted to today (2026-08-02), which is BEFORE the investment date
    # 2027-03-15: this investment has not been made yet. Pass exit_date=...,
    # or set investment.exit_date, to model it.

    calculate_benefits(inv, exit_date="2037-03-15")   # answerable → computes
    inv.exit_date = "2037-03-15"; calculate_benefits(inv)   # also answerable

The "not supplied" wording appears **only** when neither source supplied one.
An inverted argument and an inverted field each get their own message naming
that source, because telling a caller they omitted an input they provided is
itself a false statement about their data.

**It is not clamped to zero.** A confident `$0.00` for a question with no
answer is the same fabrication class as a confident `False` for a tract nobody
looked up — a real-looking figure standing in for "unknown", which a caller
cannot distinguish from a genuine zero-benefit result.

A same-day exit is *not* an error: zero length is a real answer, and only a
negative period is refused.

### What a portfolio does about it

The two entry points differ deliberately, because their return types differ:

| | behavior when a member is undeterminable |
|---|---|
| `total_tax_benefits()` | **raises** `OZCalculationError`, naming the offending ids and the count |
| `summary()` | **prints a scoped partial**, and names every excluded investment |
| `undeterminable_benefits()` | returns `[(investment, reason)]` — check coverage without catching |

`total_tax_benefits()` returns a bare `float`, which has nowhere to carry
"this covers 2 of your 3 investments" — so returning a subtotal would hand back
a number that reads as complete and is not. It refuses.

`summary()` prints a report, which *can* carry the caveat, so it does rather
than refusing:

    TAX BENEFITS (est. @ 23.8% cap gains rate)
      ⚠ PARTIAL — covers 1 of 3 investments ($0.75MM of $1.50MM in capital gains).
        This is NOT a portfolio total. See NOT DETERMINABLE below.
      Benefit (covered subset): $0.12MM
      % of covered gain:     15.4%

    NOT DETERMINABLE (2 of 3)
      These investments are EXCLUDED from the figure above and are not zero —
      their benefit has no answer from the inputs given:
        • P002 (Rural Illinois QORF): $0.50MM
          ...

The percentage is computed against the **covered** gain ($0.75MM), not the
portfolio total ($1.50MM) — the line says "of covered gain" and means it.
Against the full denominator the same portfolio reads 7.7%, a figure whose
label would contradict its value.

Neither entry point silently drops a member, and neither presents a partial
aggregate as a complete one. When every member is determinable, `summary()`
prints the ordinary `Total Tax Benefit:` line unchanged.

**An empty portfolio is not a partial one.** `total_tax_benefits()` returns
`0.0` and `summary()` prints the ordinary `Total Tax Benefit: $0.00MM`. Its
benefit is a genuine zero — the sum of no benefits — and not a question
without an answer; nothing is excluded because there is nothing to exclude.
That is a different claim from "there are investments here whose benefit has
no answer", which is what the refusal above means.

---

## The tri-state contract

    from oztracker import OZ1Checker, OZDownloadError

    try:
        oz1 = OZ1Checker()                       # raises today — see Status
    except OZDownloadError as e:
        print(f"no OZ data: {e}")

    oz1 = OZ1Checker.from_sample()               # demo data, explicitly
    oz1.data_source                              # "sample"

    oz1.is_designated("17031840100")             # True  — a fact
    oz1.is_designated("17031838200")             # None  — NOT confirmed

`True` means the tract is present in a successfully loaded designation list.
`None` means the question could not be answered. **`False` is not returned in
0.2.0 at all.**

Why: the OZ 1.0 list is 2018 designations on **2010** census-tract boundaries,
this package contains no geocoder, and its API gives a caller no way to declare
which tract vintage their GEOID came from. A current-vintage (2020) GEOID
checked against a 2010-basis list produces a miss that is indistinguishable from
a genuine non-designation. A bare `False` would be the same fabricated negative
in a new coat.

**A `True` is a fact; the absence of a `True` is "not confirmed", not "not
designated."** Branch on `is True` / `is None` — never on truthiness alone.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md). It documents what 0.1.0 got wrong as well as
what 0.2.0 changed — if you drew conclusions from 0.1.0, that entry tells you
what needs rechecking.

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

    # Tract lookup — see the Status section above. OZ1Checker() / OZ2Checker()
    # raise OZDownloadError today because both upstream sources are 404.
    # from_sample() gives you the synthetic demo set, explicitly and offline:
    oz1 = OZ1Checker.from_sample()
    oz2 = OZ2Checker.from_sample()
    print(oz1.is_designated("17031840100"))   # True  (in the demo set)
    print(oz1.is_designated("17031838200"))   # None  (not confirmed)
    print(oz2.is_rural("17019000100"))        # True  (in the demo set)

    # Compare OZ 1.0 vs 2.0 tract overlap
    oz2.compare_oz1_oz2(oz1.designated_tracts)

    # Calculate QOF tax benefits — no tract lookup, fully functional
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
    # NOTE: `inv` above is dated 2027 and carries no exit_date, so this prints
    # a NOT DETERMINABLE report rather than a benefit figure — see
    # "Undeterminable holding periods". Set inv.exit_date = "2037-03-15" (or
    # pass exit_date= per call) and the same portfolio totals normally.

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

These are the statutory thresholds. `check_oz1_eligibility()` /
`check_oz2_eligibility()` apply them to poverty-rate and AMI-ratio values you
supply and are fully functional; the *designation list lookup* is what is
unavailable (see Status).

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

118 tests across all modules, including `tests/test_holding_period.py`
(pins the undeterminable-holding-period contract on both the individual and the
portfolio path, where the exit date is resolved from, and the concrete
percentage on the partial report — mutation-checked against a clamp-to-zero, a
silent-skip, and a swapped percentage denominator), `tests/test_fail_loud.py`
(drives the download path end to end and asserts it raises rather than
substituting sample data; also pins rename-atomicity of the cache write against
a failure no handler catches, and that `KeyboardInterrupt` / `SystemExit` are
never swallowed) and `tests/test_tristate.py` (pins the `True`/`None` contract
on both the checkers and the `OZTract` schema defaults).

The suite is network-isolated — every test that touches the download path stubs
`requests.get`, and the cache is redirected to `tmp_path`, so no test reaches
the network or the developer's real `~/.oztracker/cache`.

It is also **wall-clock independent**. Fixture dates live in 2015 and 2099, not
2027, and every holding-period test supplies an explicit exit date. The 2027
fixtures made the suite depend on 2027 being in the future: pinning
`datetime.today()` showed it green at a simulated 2027-04-01 and red from
2027-06-02 onward. A build with a known future red date is not shippable.

### The example notebook

`examples/oz_investment_demo.ipynb` **runs end to end in 0.2.0** and is
executed as part of preparing a release. It was rewritten for this version:

- tract sections use `OZ1Checker.from_sample()` / `OZ2Checker.from_sample()`
  behind a prominent provenance banner, so the notebook runs offline without
  ever implying the synthetic set is the designation list. The banner
  classifies **every** GEOID the notebook prints against the census-tract
  universes — six are invented, one (`13121010400`) is a real 2010-vintage
  tract that no longer exists, and four are real and current. An earlier
  banner disclosed only five of the invented ones, which is worse than
  disclosing none: a partial list implies the rest were checked and passed;
- results render tri-state via an explicit `is True` / `is None` helper —
  `None` prints **NOT CONFIRMED**, never "NO". The previous version used
  `"YES" if designated else "NO"`, which, because `None` is falsy, printed a
  confident "NO" for every tract the package could not answer for — the
  fabricated negative this release exists to remove, reappearing in the
  package's own example;
- a new section 0 demonstrates `OZ1Checker()` raising `OZDownloadError`, so the
  headline 0.2.0 behavior is shown rather than hidden;
- the portfolio section demonstrates the **partial** report permanently. Its
  three investments were all dated 2027, which made the section expire: after
  2027-09-01 every member would have been determinable and the cells would have
  shown nothing. One member now carries its own `exit_date` and is covered, two
  are dated far enough out to stay not-yet-made, so the covered/excluded split
  is stable regardless of when the notebook runs.

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

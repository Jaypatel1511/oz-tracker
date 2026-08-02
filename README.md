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

77 tests across all modules, including `tests/test_fail_loud.py` (drives the
download path end to end and asserts it raises rather than substituting sample
data; also pins rename-atomicity of the cache write against a failure no
handler catches, and that `KeyboardInterrupt` / `SystemExit` are never
swallowed) and `tests/test_tristate.py` (pins the `True`/`None` contract on
both the checkers and the `OZTract` schema defaults).

The suite is network-isolated — every test that touches the download path stubs
`requests.get`, and the cache is redirected to `tmp_path`, so no test reaches
the network or the developer's real `~/.oztracker/cache`.

### The example notebook

`examples/oz_investment_demo.ipynb` **runs end to end in 0.2.0** and is
executed as part of preparing a release. It was rewritten for this version:

- tract sections use `OZ1Checker.from_sample()` / `OZ2Checker.from_sample()`
  behind a prominent provenance banner, so the notebook runs offline without
  ever implying the synthetic set is the designation list;
- results render tri-state via an explicit `is True` / `is None` helper —
  `None` prints **NOT CONFIRMED**, never "NO". The previous version used
  `"YES" if designated else "NO"`, which, because `None` is falsy, printed a
  confident "NO" for every tract the package could not answer for — the
  fabricated negative this release exists to remove, reappearing in the
  package's own example;
- a new section 0 demonstrates `OZ1Checker()` raising `OZDownloadError`, so the
  headline 0.2.0 behavior is shown rather than hidden.

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

# Changelog

All notable changes to oz-tracker are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **If you used 0.1.0, read the 0.1.0 entry before trusting anything it told
> you.** 0.1.0 answered a confident `False` for 99.91% of designated
> Opportunity Zone tracts. Conclusions drawn from it need rechecking, and this
> file exists so you can find that out without reading the source.

---

## [0.2.0] — unreleased

Prepared but **not published**. Version 0.2.0 is set in `pyproject.toml` and
`setup.py`; no tag has been pushed and no artifact uploaded.

A "fail loud" release. The theme is a single rule applied in both directions:
**never present a figure the inputs do not support, and never claim the inputs
are insufficient when they are not.** Both halves are wrong in the same way.

### Removed

- **The silent sample-data fallback.** Every download failure in 0.1.0
  substituted an 8-row hardcoded sample set and continued. Both upstream URLs
  were already dead, so this was the only path ever taken in the field. It is
  gone; there is no path from a failed download to a returned answer.

### Changed — BREAKING

- **`is_designated()` / `is_eligible()` / `is_rural()` return
  `Optional[bool]`.** They return `True` or `None` and **never `False`** in
  0.2.0. `True` is a fact; the absence of a `True` is "not confirmed", not
  "not designated". Callers that branch on truthiness (`if oz1.is_designated(t):`)
  will now treat "unknown" the same as "no" — branch on `is True` / `is None`
  instead.

  `False` is withheld because the OZ 1.0 designation list is 2018 designations
  on **2010** census-tract boundaries, this package has no geocoder, and its
  API gives a caller no way to declare which vintage their GEOID came from. A
  2020-vintage GEOID missing from a 2010-basis list is indistinguishable from a
  genuine non-designation, so a bare `False` would be the same fabricated
  negative in a new coat.

- **`OZ1Checker()` / `OZ2Checker()` raise `OZDownloadError`** instead of
  degrading to sample data. In practice they raise on essentially every call,
  because both upstream sources return HTTP 404. That is intended: a package
  that says "I cannot answer" is strictly better than one that answers wrong.

- **`OZTract.is_oz1_eligible` / `is_oz2_eligible` are `Optional[bool] = None`**,
  not `bool = False`. An `OZTract` built without eligibility data no longer
  asserts a negative it has no basis for. `is_active` forwards the tri-state
  unchanged.

- **`calculate_benefits()` raises `OZCalculationError`** when the resolved exit
  date precedes the investment date, instead of returning a negative holding
  period and the figures computed from it. It is **not** clamped to zero: a
  confident `$0.00` for a question with no answer is the same fabrication class
  as a confident `False` for a tract nobody looked up. A same-day exit is not
  an error — zero length is a real answer, and only a negative period is
  refused.

- **`OZPortfolio.total_tax_benefits()` raises** if any member's benefit is not
  determinable, rather than silently omitting them. It returns a bare `float`,
  which has nowhere to carry "this covers 2 of your 3 investments". An empty
  portfolio still returns `0.0` and does not raise.

- **Sample data is explicit opt-in only** — `OZ1Checker.from_sample()`,
  `OZ2Checker.from_sample()`, `load_sample_oz1_tracts()`,
  `load_sample_oz2_dataframe()`. Anything built from it is stamped
  `data_source == "sample"`.

### Added

- Typed exceptions: `OZTrackerError` (base), `OZDownloadError`, `OZParseError`,
  `OZCalculationError`. Download messages name the URL and HTTP status and
  chain the original error. `OZCalculationError` is deliberately *not* a
  data-acquisition failure: it means the question has no answer, not that the
  data could not be fetched.
- `OZPortfolio.undeterminable_benefits()` — returns `[(investment, reason)]` so
  a caller can check coverage without catching anything.
- `OZPortfolio.summary()` reports a **scoped partial** when members are
  excluded: it labels the figure `PARTIAL — covers N of M`, renames the line to
  `Benefit (covered subset)` so no bare "Total Tax Benefit" appears, computes
  the percentage against the *covered* gain, and lists every excluded
  investment by id, fund and amount with its reason — stating they are excluded
  and **not zero**.
- Atomic cache writes: stream to `.part`, rename on success, discard on
  failure. Proven against `KeyboardInterrupt` / `SystemExit` mid-write, not
  only against handled errors.
- Trove classifiers, including `Development Status :: 3 - Alpha` — not
  Production/Stable, because the headline feature is non-functional; not
  Inactive, because restoration is planned.

### Fixed

- **`OZInvestment.exit_date` was never read.** The field has existed since
  0.1.0, and `calculate_benefits()` consulted only its own `exit_date`
  parameter before falling back to today. An investment carrying its own exit
  date was therefore measured to today and, if dated in the future, **refused**
  — told it had omitted a field it had supplied, and handed a remedy it had
  already applied. A portfolio of fully-specified investments reported 100% NOT
  DETERMINABLE.

  The exit date now resolves as **parameter → `investment.exit_date` → today**,
  mirroring how `current_fmv` already falls back to `investment.current_fmv`.
  When both are supplied the parameter wins. The error message distinguishes
  the three cases and says "not supplied" only when neither source supplied
  one.

  This was a *false refusal*, and it is the mirror image of the fabrication the
  rest of this release removes: asserting "no answer exists from these inputs"
  when the inputs contain the answer is exactly as wrong as inventing a figure.

- **`summary()` and `total_tax_benefits()` disagreed on an empty portfolio.**
  `total_tax_benefits()` returned `0.0` while `summary()` printed "No benefit
  figure can be computed for any investment in this portfolio." An empty
  portfolio's benefit is a genuine zero — the sum of no benefits — and nothing
  is excluded because there is nothing to exclude. `summary()` now prints the
  ordinary `Total Tax Benefit: $0.00MM`, and `total_tax_benefits()` returns a
  `float` rather than `sum()`'s `int` 0.

- **The fully-determinable report drifted by one space.** Assembling the
  percentage line from a padded label produced `Benefit as % of Gain:` followed
  by three spaces where the original had two. The 0.2.0 partial-reporting work
  claimed this path was byte-identical to the release before it; it was not.
  The literal is restored and pinned by test.

- The wheel no longer installs a top-level `tests` package (`setup.py` used a
  bare `find_packages()`).
- The sdist ships a suite that can actually run. setuptools' default `test*.py`
  glob omitted `tests/conftest.py` and `tests/__init__.py`, so the shipped
  suite died at collection with `No module named 'tests.conftest'`.
- `OSError` on chunk write, and `OSError` / `PermissionError` from
  `get_cache_dir()`, now wrap as `OZDownloadError` rather than escaping
  untyped. `KeyboardInterrupt` / `SystemExit` are deliberately **not** caught.

### Documentation

- The README's deferral rationale was wrong for one of the two checkers. It
  blamed the census-tract vintage question for both. That is true of OZ 1.0 and
  false of OZ 2.0: Rev. Proc. 2026-14 §3.01(1) derives the eligible list from
  the 2020–2024 ACS 5-Year and 2020 DECIA data sets — 2020-basis, the same
  vintage as a current GEOID. OZ 2.0 restoration is deferred purely on scope.
  The rationale is now stated per checker.
- The README's partial-report output block showed `$0.03MM / 3.5%` where the
  code prints `$0.12MM / 15.4%`. It had been generated from an earlier draft of
  the test fixture and never regenerated, while the commit that introduced it
  claimed both new output blocks "were verified to reproduce line-for-line".
  Every output block in the README has now been re-executed and pasted from
  real output.
- The example notebook's provenance banner disclosed only five invented GEOIDs
  and said nothing about the rest, which implied the others had been checked.
  It now classifies **every** GEOID the notebook prints: six are invented, one
  (`13121010400`) is a real 2010-vintage tract that no longer exists, and four
  are real and current.
- The notebook rendered tri-state results with `"YES" if designated else "NO"`.
  `None` is falsy, so every tract the package could not answer for printed a
  confident "NO" — the fabricated negative this release exists to remove,
  reappearing in the package's own example. It now renders `None` as
  **NOT CONFIRMED** via an explicit `is True` / `is None` helper, and a new
  section 0 demonstrates `OZ1Checker()` raising.

### Testing

- 118 tests, up from 37 at 0.1.0.
- **The suite no longer depends on the wall clock.** Fixture dates were
  2027-03-15 and 2027-06-01, and the portfolio refusal test was only true while
  2027 was in the future. Pinning `datetime.today()` showed the suite green at
  a simulated 2027-04-01 and red from 2027-06-02 onward. Fixture dates moved to
  2015 / 2099, and the notebook's portfolio section — which had the same
  expiry, on 2027-09-01 — was restructured to demonstrate the partial report
  permanently.
- 0.1.0's fixtures monkeypatched `oztracker.data.loader`, which did not work:
  `oz1.py` binds the loader name at import time, so the patch was a no-op and
  every 0.1.0 test made a live network call that 404'd and landed on the
  fabrication path. The suite passed *because* the bug existed. Fixtures now
  use `from_sample()`, and the whole suite is network-isolated and passes with
  sockets blocked.
- Contracts are mutation-checked rather than assumed: clamp-to-zero,
  portfolio-silently-skips, non-atomic cache write, and a swapped percentage
  denominator are each confirmed to be caught. Individual-path tests assert
  "raises" rather than "total == 0", because the latter passes against a clamp.

### Known issues, unchanged in 0.2.0

- **Tract lookup does not work.** Both upstream sources are HTTP 404. 0.2.0
  fixes only that the package no longer pretends otherwise.
- OZ 2.0's real source is known and live — the Rev. Proc. 2026-14 Appendix at
  `irs.gov/pub/irs-drop/rp-26-14-appendix.xlsx` (verified 2026-08-02: HTTP 200,
  25,332 rows, 8,334 rural). It is not a drop-in for the current parser: the
  tract column is `Census Tract Number`, its values have leading zeros
  stripped, and rural status is a string, not a boolean.
- `holding_years` is `days / 365.25`, so an exact calendar anniversary does not
  reliably clear the matching integer tier — a 5-year hold can measure 4.9993
  years and lose the 5-year step-up. Visible in the notebook's own sensitivity
  table.
- Covered subtotals under $5,000 render as `$0.00MM`, a consequence of `.2f`-MM
  formatting throughout the report.

---

## [0.1.0] — 2026-05-05

Initial release. **Do not use.** Recorded here because a user who drew
conclusions from it needs to know what it actually did.

- `is_designated()` returned a confident `False` for **8,756 of the 8,764**
  designated OZ 1.0 tracts — 99.91% — with nothing in the return value
  indicating that no data had been loaded. Both upstream data URLs returned
  HTTP 404, and every download failure silently substituted an 8-row hardcoded
  sample set, so that fallback was the only path ever taken in the field.
- `calculate_benefits()` defaulted its exit date to today with no guard, so a
  future-dated investment produced a **negative** holding period that flowed
  into every downstream figure. The README's own example returned
  `holding_years -0.62` and `total_tax_benefit -$733`; `OZPortfolio.summary()`
  printed `Total Tax Benefit: $-0.00MM  /  Benefit as % of Gain: -0.1%`.
- `OZTract.is_oz1_eligible` / `is_oz2_eligible` defaulted to `False`, so a
  tract constructed without eligibility data asserted a negative in a public
  exported type.
- 37 tests, passing — including one that encoded `is_designated(fake) == False`
  as the specification, and one that type-checked a fabricated negative
  benefit figure. The suite passed because the bugs existed.

[0.2.0]: https://github.com/Jaypatel1511/oz-tracker
[0.1.0]: https://github.com/Jaypatel1511/oz-tracker

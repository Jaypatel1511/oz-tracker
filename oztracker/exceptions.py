"""
Typed exception hierarchy for oz-tracker (added 0.2.0).

Through 0.1.0 the loader silently substituted an 8-row hardcoded sample set on
ANY download or parse failure. Because both upstream data URLs 404, that path
was the ONLY path taken in the field: ``is_designated()`` returned a confident
``False`` for 8,756 of the 8,764 designated OZ 1.0 tracts (99.91%) while
printing a one-line notice to stdout that no library consumer could see in a
return value.

These exceptions replace that behavior. Every data-acquisition failure now
raises, and the message names the URL attempted and the HTTP status, so a
caught error tells the caller what actually went wrong rather than being
collapsed into a fabricated answer.

    OZTrackerError
    ├─ OZDownloadError    # 404 / 403 / DNS / timeout / connection
    ├─ OZParseError       # corrupt bytes, HTML error page, missing tract column
    └─ OZCalculationError # the question asked has no determinable answer

Downstream code can catch at either level: ``except OZTrackerError`` for
anything raised BY THIS PACKAGE'S OWN raise sites, or a specific leaf.

What ``except OZTrackerError`` actually covers — and what it does not
------------------------------------------------------------------

It is worth being precise here, because a base-class catch that is sold as
"catches everything a load can throw" is a contract this package would not
deliver. Concretely, on the load path (``load_oz1_tracts`` /
``load_oz2_eligible_tracts`` / the ``OZ1Checker`` / ``OZ2Checker``
constructors), ``except OZTrackerError`` covers:

  * transport failures  — 404 / 403 / DNS / timeout / connection reset,
    wrapped as OZDownloadError with the URL and status in the message
  * parse failures      — corrupt bytes, an HTML error page served with a
    200, a workbook with no recognizable tract column, as OZParseError
  * filesystem failures — an OSError/PermissionError creating the cache
    directory, or writing/renaming the cached file, as OZDownloadError
    (added 0.2.0; before that these escaped the base catch untyped)

It does NOT cover, by design:

  * ``KeyboardInterrupt`` and ``SystemExit``. These do not subclass Exception
    and this package never catches them. A Ctrl-C during a download propagates
    immediately and no cleanup handler runs — which is correct, and is safe
    here only because downloads are staged through a ``.part`` file and moved
    into place with an atomic rename, so an interrupt cannot poison the cache
    (see data/loader.py).
  * stdlib argument-validation errors raised when a CALLER passes bad input.
    These signal a programming error, not a data-acquisition failure, and are
    reached on entirely different call paths — never from a load or a
    designation check:

        schema.py:135,137,141,145   ValueError  — OZInvestment field validation
        portfolio/tracker.py:29     TypeError   — non-OZInvestment given to add()
        portfolio/tracker.py:31     ValueError  — duplicate investment id

  * anything raised from inside pandas/requests that is neither a
    ``requests.exceptions.RequestException`` nor an ``OSError`` and escapes
    before the parse wrapper — the parse wrapper catches broad ``Exception``,
    so in practice this is limited to the narrow window described above.

EVERY exception class defined in this package subclasses OZTrackerError, and
every DATA-ACQUISITION raise site in oztracker/ raises one of these (all in
data/loader.py).

Off the load path, OZCalculationError is raised by the benefit calculator and
the portfolio aggregate when the answer is not determinable from the inputs
(see that class). It is in this tree, so ``except OZTrackerError`` catches it,
but it is reached on a different call path and signals something different: not
"I could not get the data" but "the question you asked has no answer".
"""


class OZTrackerError(Exception):
    """Base class for every error raised by oz-tracker."""


class OZDownloadError(OZTrackerError):
    """Could not download an Opportunity Zone data file (404 / 403 / DNS /
    timeout / connection), and no usable cached copy was available.

    As of 0.2.0 BOTH upstream URLs are known-dead (verified 404 on 2026-07-30),
    so this is the expected outcome of constructing OZ1Checker() or OZ2Checker()
    against real data. See the README "Status" section."""


class OZParseError(OZTrackerError):
    """An Opportunity Zone file was obtained but could not be parsed
    (corrupt bytes, wrong content-type / HTML error page, no tract column).

    Raised instead of degrading to the built-in sample set — a partially
    understood file must never answer an eligibility question."""


class OZCalculationError(OZTrackerError):
    """A calculation was requested whose answer is not determinable from the
    inputs given (added 0.2.0).

    NOT a data-acquisition failure and not on the load path — this is the
    arithmetic half of the package refusing an ill-posed question rather than
    returning a number for it.

    The case that motivated it: ``calculate_benefits()`` defaults the exit date
    to today, so an investment dated in the FUTURE produced a negative holding
    period and a negative "tax benefit" (-0.62 years, -$733 for the README's
    own 2027 example). The honest response is neither that negative figure nor
    a clamp to zero — a confident $0.00 for a question with no answer is the
    same fabrication class as a confident ``False`` for a tract nobody looked
    up. So it raises, and the message says which date to supply."""


__all__ = [
    "OZTrackerError",
    "OZDownloadError",
    "OZParseError",
    "OZCalculationError",
]

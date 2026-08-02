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
    ├─ OZDownloadError   # 404 / 403 / DNS / timeout / connection
    └─ OZParseError      # corrupt bytes, HTML error page, missing tract column

Downstream code can catch at either level: ``except OZTrackerError`` for
anything this package raises, or a specific leaf.

EVERY exception class defined in this package subclasses OZTrackerError, and
every DATA-ACQUISITION raise site in oztracker/ raises one of these (5 sites,
all in data/loader.py).

The package's remaining 6 raise sites are stdlib argument validation and are
deliberately NOT in this tree, because they signal a caller's programming error
rather than a data-acquisition failure and are reached on entirely different
call paths:

    schema.py:110,112,116,120   ValueError  — OZInvestment field validation
    portfolio/tracker.py:29     TypeError   — non-OZInvestment passed to add()
    portfolio/tracker.py:31     ValueError  — duplicate investment id

A consumer wrapping data access in ``except OZTrackerError`` will not miss any
of those; none can be raised from a load or a designation check.
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


__all__ = [
    "OZTrackerError",
    "OZDownloadError",
    "OZParseError",
]

"""
OZ 1.0 eligibility — Tax Cuts and Jobs Act 2017.
8,764 designated tracts, current map through 2028.
"""
from typing import Optional

from oztracker.data.loader import (
    load_oz1_tracts, load_sample_oz1_tracts, check_oz1_eligibility,
)


class OZ1Checker:
    """
    Check OZ 1.0 designation against the official 2018 designated tract list.

    Construction against real data raises OZDownloadError / OZParseError rather
    than degrading to sample data. As of 0.2.0 the upstream URL is known-dead,
    so ``OZ1Checker()`` raises OZDownloadError on essentially every call; that
    is the intended behavior until the data source is restored. Use
    ``OZ1Checker.from_sample()`` for offline demos and tests.
    """

    def __init__(self, force_reload: bool = False):
        self._tracts = load_oz1_tracts(force=force_reload)
        self.data_source = "irs_notice_2018_48"
        print(f"OZ 1.0: {len(self._tracts):,} designated tracts loaded")

    @classmethod
    def from_sample(cls) -> "OZ1Checker":
        """
        Construct a checker on the built-in synthetic sample set — no network.

        WARNING: 8 synthetic tracts, several with invented GEOIDs. NEVER valid
        for a real OZ designation answer. The resulting checker is stamped
        ``data_source == "sample"`` so downstream code can assert provenance.
        """
        obj = cls.__new__(cls)
        obj._tracts = load_sample_oz1_tracts()
        obj.data_source = "sample"
        return obj

    def __repr__(self) -> str:
        return (
            f"OZ1Checker(data_source={self.data_source!r}, "
            f"tracts={len(self._tracts):,})"
        )

    def is_designated(self, tract_id: str) -> Optional[bool]:
        """Check whether a tract is officially designated as OZ 1.0.

        Returns
        -------
        True
            The tract is present in a successfully loaded designation list.
        None
            Cannot determine.

        ``False`` IS NOT RETURNED IN 0.2.0, by design. The designation list is
        2018 designations on **2010** census-tract boundaries, and this package
        contains no geocoder and no way for a caller to declare the vintage of
        the ``tract_id`` they pass in. A current-vintage (2020) GEOID checked
        against a 2010-basis list produces a miss that is indistinguishable
        from a genuine non-designation, so a bare ``False`` would be the same
        fabricated negative that made 0.1.0 wrong for 99.91% of designated
        tracts. Until the vintage question is resolved (pending the
        nmtc-mapper 0.5.0 decision), the asymmetry is explicit:

            **a True is a fact; the absence of True is "not confirmed",
            NOT "not designated".**

        Callers must branch on ``is True`` / ``is None`` — never on truthiness
        alone, and never treat a non-True as a negative finding.
        """
        if tract_id in self._tracts:
            return True
        return None

    def check_batch(self, tract_ids: list) -> dict:
        """Check multiple tract IDs at once.

        Returns ``{tract_id: Optional[bool]}`` with the same tri-state contract
        as ``is_designated`` — values are ``True`` or ``None``, never ``False``.
        """
        return {tid: self.is_designated(tid) for tid in tract_ids}

    @property
    def tract_count(self) -> int:
        return len(self._tracts)

    @property
    def designated_tracts(self) -> set:
        return self._tracts.copy()

"""
OZ 2.0 eligibility — One Big Beautiful Bill Act 2025.
Stricter criteria, decennial redesignation, effective 2027.
"""
from typing import Optional

import pandas as pd
from oztracker.data.loader import (
    load_oz2_eligible_tracts, load_sample_oz2_dataframe,
    check_oz2_eligibility, check_oz1_eligibility,
)
from oztracker.data.schema import (
    OZ2_MFI_THRESHOLD, OZ2_POVERTY_THRESHOLD,
    OZ1_MFI_THRESHOLD,
)


class OZ2Checker:
    """
    Check OZ 2.0 eligibility using Treasury Rev. Proc. 2026-14 criteria.
    Identifies tracts likely eligible for 2027 designation.

    Construction against real data raises OZDownloadError / OZParseError rather
    than degrading to sample data. As of 0.2.0 the upstream URL is known-dead,
    so ``OZ2Checker()`` raises OZDownloadError on essentially every call. Use
    ``OZ2Checker.from_sample()`` for offline demos and tests.
    """

    def __init__(self, force_reload: bool = False):
        self._df = load_oz2_eligible_tracts(force=force_reload)
        self._eligible = set()
        self._rural = set()
        self.data_source = "treasury_rev_proc_2026_14"
        self._process()

    @classmethod
    def from_sample(cls) -> "OZ2Checker":
        """
        Construct a checker on the built-in synthetic sample frame — no network.

        WARNING: 7 synthetic rows with invented economic values and several
        invented GEOIDs. NEVER valid for a real OZ 2.0 answer. Stamped
        ``data_source == "sample"``.
        """
        obj = cls.__new__(cls)
        obj._df = load_sample_oz2_dataframe()
        obj._eligible = set()
        obj._rural = set()
        obj.data_source = "sample"
        obj._process()
        return obj

    def __repr__(self) -> str:
        return (
            f"OZ2Checker(data_source={self.data_source!r}, "
            f"eligible={len(self._eligible):,}, rural={len(self._rural):,})"
        )

    def _process(self):
        """Process the loaded DataFrame into eligibility sets.

        NOTE: reads lowercase ``tract_id``, while the live loader uppercases
        downloaded column names — so the real path yields empty sets even on a
        successful download (recon 2026-07-30 §A-1g). Left unfixed in 0.2.0 by
        decision, together with the dead URLs. The tri-state returns below mean
        the consequence is "not determined", not a fabricated negative.
        """
        for _, row in self._df.iterrows():
            tid = str(row.get("tract_id", "")).strip()
            if not tid:
                continue
            pr = float(row.get("poverty_rate", 0) or 0)
            ami = float(row.get("ami_ratio", 1) or 1)
            rural = bool(row.get("is_rural", False))

            if check_oz2_eligibility(pr, ami):
                self._eligible.add(tid)
            if rural:
                self._rural.add(tid)

        print(f"OZ 2.0: {len(self._eligible):,} likely eligible tracts")
        print(f"OZ 2.0: {len(self._rural):,} rural tracts")

    def is_eligible(self, tract_id: str) -> Optional[bool]:
        """Check whether a tract likely meets OZ 2.0 eligibility.

        Returns ``True`` if the tract is present in a successfully loaded and
        processed eligibility set, otherwise ``None`` (cannot determine).

        ``False`` IS NOT RETURNED IN 0.2.0 — same asymmetry as
        ``OZ1Checker.is_designated``: the caller cannot declare the census-tract
        vintage of ``tract_id``, so an absence is indistinguishable from a
        vintage miss. **A True is a fact; the absence of True is "not
        confirmed", not "not eligible".** Branch on ``is True`` / ``is None``.
        """
        if tract_id in self._eligible:
            return True
        return None

    def is_rural(self, tract_id: str) -> Optional[bool]:
        """Check whether a tract qualifies as rural under OZ 2.0.

        Returns ``True`` if the tract is present in the loaded rural set,
        otherwise ``None`` (cannot determine). ``False`` is not returned in
        0.2.0 — see ``is_eligible`` for why. **A True is a fact; the absence of
        True is "not confirmed", not "not rural".**
        """
        if tract_id in self._rural:
            return True
        return None

    def compare_oz1_oz2(self, oz1_tracts: set) -> dict:
        """
        Compare OZ 1.0 and OZ 2.0 eligible tracts.
        Returns counts of tracts in each overlap category.

        Set arithmetic over two loaded tract sets — this is a comparison of
        what each source contains, not a per-tract eligibility verdict, so it
        is not subject to the tri-state contract above. It IS subject to the
        same vintage caveat: OZ 1.0 is a 2010-basis list, so an "oz1_only"
        count includes tracts that simply have no counterpart row.
        """
        oz2 = self._eligible
        both = oz1_tracts & oz2
        oz1_only = oz1_tracts - oz2
        oz2_only = oz2 - oz1_tracts

        result = {
            "oz1_total":    len(oz1_tracts),
            "oz2_eligible": len(oz2),
            "both":         len(both),
            "oz1_only":     len(oz1_only),
            "oz2_only":     len(oz2_only),
            "oz1_losing_status": len(oz1_only),
            "oz2_gaining_status": len(oz2_only),
        }

        print(f"\nOZ 1.0 vs OZ 2.0 Tract Comparison")
        print("=" * 45)
        print(f"  OZ 1.0 designated:      {result['oz1_total']:,}")
        print(f"  OZ 2.0 eligible:        {result['oz2_eligible']:,}")
        print(f"  In both programs:       {result['both']:,}")
        print(f"  OZ 1.0 only (losing):   {result['oz1_only']:,}")
        print(f"  OZ 2.0 only (gaining):  {result['oz2_only']:,}")
        print()

        return result

    @property
    def eligible_tract_count(self) -> int:
        return len(self._eligible)

    @property
    def rural_tract_count(self) -> int:
        return len(self._rural)

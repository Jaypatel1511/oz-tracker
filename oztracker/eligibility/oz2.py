"""
OZ 2.0 eligibility — One Big Beautiful Bill Act 2025.
Stricter criteria, decennial redesignation, effective 2027.
"""
import pandas as pd
from oztracker.data.loader import (
    load_oz2_eligible_tracts, check_oz2_eligibility, check_oz1_eligibility
)
from oztracker.data.schema import (
    OZ2_MFI_THRESHOLD, OZ2_POVERTY_THRESHOLD,
    OZ1_MFI_THRESHOLD,
)


class OZ2Checker:
    """
    Check OZ 2.0 eligibility using Treasury Rev. Proc. 2026-14 criteria.
    Identifies tracts likely eligible for 2027 designation.
    """

    def __init__(self, force_reload: bool = False):
        self._df = load_oz2_eligible_tracts(force=force_reload)
        self._eligible = set()
        self._rural = set()
        self._process()

    def _process(self):
        """Process the loaded DataFrame into eligibility sets."""
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

    def is_eligible(self, tract_id: str) -> bool:
        """Check if tract likely meets OZ 2.0 eligibility."""
        return tract_id in self._eligible

    def is_rural(self, tract_id: str) -> bool:
        """Check if tract qualifies as rural under OZ 2.0."""
        return tract_id in self._rural

    def compare_oz1_oz2(self, oz1_tracts: set) -> dict:
        """
        Compare OZ 1.0 and OZ 2.0 eligible tracts.
        Returns counts of tracts in each overlap category.
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

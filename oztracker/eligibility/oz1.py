"""
OZ 1.0 eligibility — Tax Cuts and Jobs Act 2017.
8,764 designated tracts, current map through 2028.
"""
from oztracker.data.loader import load_oz1_tracts, check_oz1_eligibility


class OZ1Checker:
    """
    Check OZ 1.0 eligibility using the official 2018 designated tract list.
    """

    def __init__(self, force_reload: bool = False):
        self._tracts = load_oz1_tracts(force=force_reload)
        print(f"OZ 1.0: {len(self._tracts):,} designated tracts loaded")

    def is_designated(self, tract_id: str) -> bool:
        """Check if a tract is officially designated as OZ 1.0."""
        return tract_id in self._tracts

    def check_batch(self, tract_ids: list) -> dict:
        """Check multiple tract IDs at once."""
        return {tid: tid in self._tracts for tid in tract_ids}

    @property
    def tract_count(self) -> int:
        return len(self._tracts)

    @property
    def designated_tracts(self) -> set:
        return self._tracts.copy()

import pytest
from oztracker.data.loader import check_oz1_eligibility, check_oz2_eligibility


def test_oz1_poverty_eligible():
    assert check_oz1_eligibility(poverty_rate=0.25, ami_ratio=0.90) == True


def test_oz1_ami_eligible():
    assert check_oz1_eligibility(poverty_rate=0.10, ami_ratio=0.75) == True


def test_oz1_not_eligible():
    assert check_oz1_eligibility(poverty_rate=0.10, ami_ratio=0.90) == False


def test_oz2_low_mfi_eligible():
    assert check_oz2_eligibility(poverty_rate=0.10, ami_ratio=0.65) == True


def test_oz2_poverty_and_mfi_eligible():
    assert check_oz2_eligibility(poverty_rate=0.25, ami_ratio=1.10) == True


def test_oz2_not_eligible():
    assert check_oz2_eligibility(poverty_rate=0.15, ami_ratio=0.85) == False


# The checker-level assertions that used to live here asserted the 0.1.0
# fabricated-negative contract (`is_designated("99999999999") == False`).
# They are replaced by tests/test_tristate.py, which pins the 0.2.0
# True/None contract on the same public entry points.

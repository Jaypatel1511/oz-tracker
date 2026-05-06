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


def test_oz1_checker_designated(oz1_checker):
    assert oz1_checker.is_designated("17031840100") == True


def test_oz1_checker_not_designated(oz1_checker):
    assert oz1_checker.is_designated("99999999999") == False


def test_oz1_checker_batch(oz1_checker):
    result = oz1_checker.check_batch(["17031840100", "99999999999"])
    assert result["17031840100"] == True
    assert result["99999999999"] == False


def test_oz2_checker_eligible(oz2_checker):
    assert oz2_checker.is_eligible("17031840100") == True


def test_oz2_checker_rural(oz2_checker):
    assert oz2_checker.is_rural("17019000100") == True


def test_oz2_checker_not_rural(oz2_checker):
    assert oz2_checker.is_rural("17031840100") == False

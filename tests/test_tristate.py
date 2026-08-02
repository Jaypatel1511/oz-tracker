"""The tri-state designation contract (0.2.0, breaking).

``is_designated`` / ``is_eligible`` / ``is_rural`` return ``True`` or ``None``.
``False`` is not returnable in 0.2.0: the OZ 1.0 list is 2018 designations on
2010 tract boundaries, the package has no geocoder and no way for a caller to
declare a vintage, so an absence is indistinguishable from a vintage miss.

    A True is a fact; the absence of True is "not confirmed", NOT "not designated".

0.1.0's suite asserted ``is_designated("99999999999") == False`` — a
structurally fake GEOID asserted to return the fabricated-negative value, i.e.
the bug written into the suite as the spec. That assertion is replaced here.
"""
import pytest

from oztracker import OZ1Checker, OZ2Checker
from tests.conftest import REAL_TRACTS_NOT_IN_SAMPLE, NOT_A_GEOID


# ── OZ 1.0 ───────────────────────────────────────────────────────────────────

def test_present_tract_is_true(oz1_checker):
    """A hit is a fact, and it is exactly True — not merely truthy."""
    assert oz1_checker.is_designated("17031840100") is True


def test_absent_tract_is_none_not_false(oz1_checker):
    """The core of the fix. 0.1.0 returned False here."""
    result = oz1_checker.is_designated(NOT_A_GEOID)
    assert result is None
    assert result is not False


@pytest.mark.parametrize("tract_id", REAL_TRACTS_NOT_IN_SAMPLE)
def test_real_tracts_absent_from_source_are_none(oz1_checker, tract_id):
    """Real, currently-existing census tracts the loaded source cannot speak to.

    These are verified against the corrected universe detector (see
    tests/conftest.py) — they are real places, not typos. 0.1.0 answered a
    confident False for tracts exactly like these, 8,756 times over.
    """
    assert oz1_checker.is_designated(tract_id) is None


def test_check_batch_is_tri_state(oz1_checker):
    result = oz1_checker.check_batch(["17031840100", NOT_A_GEOID])
    assert result["17031840100"] is True
    assert result[NOT_A_GEOID] is None
    assert False not in result.values(), "check_batch must never emit False in 0.2.0"


def test_none_is_not_a_negative_finding(oz1_checker):
    """Guards the documented asymmetry against a naive truthiness reading.

    ``not is_designated(x)`` is True for BOTH "not confirmed" and (a
    hypothetical) "confirmed not designated" — which is why callers are told to
    branch on ``is True`` / ``is None``. This test pins that None is what comes
    back, so a downstream `== False` comparison fails loudly rather than
    silently agreeing.
    """
    assert (oz1_checker.is_designated(NOT_A_GEOID) == False) is False


# ── OZ 2.0 ───────────────────────────────────────────────────────────────────

def test_oz2_eligible_present_is_true(oz2_checker):
    assert oz2_checker.is_eligible("17031840100") is True


def test_oz2_eligible_absent_is_none(oz2_checker):
    assert oz2_checker.is_eligible(NOT_A_GEOID) is None


@pytest.mark.parametrize("tract_id", REAL_TRACTS_NOT_IN_SAMPLE)
def test_oz2_real_tracts_absent_are_none(oz2_checker, tract_id):
    assert oz2_checker.is_eligible(tract_id) is None


def test_oz2_rural_present_is_true(oz2_checker):
    assert oz2_checker.is_rural("17019000100") is True


def test_oz2_rural_absent_is_none_not_false(oz2_checker):
    """0.1.0 asserted `is_rural("17031840100") == False`. A tract present in
    the source but not flagged rural is still only "not confirmed rural" in
    0.2.0 — the same treatment as designation, per the release contract."""
    result = oz2_checker.is_rural("17031840100")
    assert result is None
    assert result is not False

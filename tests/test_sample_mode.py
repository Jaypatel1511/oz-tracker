"""Explicit sample mode (0.2.0).

Sample data survives only as a deliberate, provenance-marked opt-in. It must
never be reachable from a failure path (test_fail_loud.py), and when reached
explicitly it must (a) require no network and (b) stamp the object so
downstream code can tell a demo answer from a real one.
"""
import pytest

from oztracker import (
    OZ1Checker, OZ2Checker, load_sample_oz1_tracts, load_sample_oz2_dataframe,
)
from oztracker.data import loader


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Any network call in this module is a hard failure."""
    def _boom(*a, **k):
        raise AssertionError("sample mode must not touch the network")
    monkeypatch.setattr(loader.requests, "get", _boom)


def test_sample_loaders_are_public():
    assert len(load_sample_oz1_tracts()) == 8
    assert len(load_sample_oz2_dataframe()) == 7


def test_private_aliases_preserved():
    """0.1.0 shipped these private names; external code may import them."""
    assert loader._sample_oz1_tracts is load_sample_oz1_tracts
    assert loader._sample_oz2_dataframe is load_sample_oz2_dataframe


def test_oz1_from_sample_marks_provenance():
    c = OZ1Checker.from_sample()
    assert c.data_source == "sample"
    assert c.tract_count == 8
    assert "sample" in repr(c).lower()


def test_oz2_from_sample_marks_provenance():
    c = OZ2Checker.from_sample()
    assert c.data_source == "sample"
    assert c.eligible_tract_count == 7
    assert c.rural_tract_count == 2
    assert "sample" in repr(c).lower()


def test_real_path_marks_a_different_provenance(monkeypatch):
    """The real constructor stamps a non-'sample' source, so a caller can
    distinguish a demo answer from a live one (mocked successful load)."""
    monkeypatch.setattr(
        "oztracker.eligibility.oz1.load_oz1_tracts",
        lambda force=False: {"17031838200"},
    )
    c = OZ1Checker()
    assert c.data_source == "irs_notice_2018_48"
    assert c.data_source != "sample"

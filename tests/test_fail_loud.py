"""Fail-loud contract (0.2.0).

Every one of these drives a REAL public entry point end to end — the loader
functions and the ``OZ1Checker()`` / ``OZ2Checker()`` constructors — with the
network stubbed at the ``requests.get`` boundary. Through 0.1.0 no test touched
the download path at all, so nothing could observe the 404, the silent sample
substitution, or the case mismatch; a 100%-broken public feature passed a green
suite.

The contract under test: a download or parse failure raises a typed error that
names the URL, and NEVER returns sample data.
"""
import pytest
import requests

from oztracker import OZ1Checker, OZ2Checker
from oztracker.exceptions import OZTrackerError, OZDownloadError, OZParseError
from oztracker.data import loader
from oztracker.data.loader import (
    OZ1_URL, OZ2_URL, load_oz1_tracts, load_oz2_eligible_tracts,
    load_sample_oz1_tracts,
)


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Every test starts with a cold, empty cache under tmp_path.

    Without this the developer's real ~/.oztracker/cache could satisfy a load
    and mask the failure path — the same way a warm cache can hide a dead URL
    in production.
    """
    monkeypatch.setattr(loader, "CACHE_DIR", tmp_path / "cache")
    return tmp_path / "cache"


def _http_error_response(url: str, status: int):
    """A real requests.Response carrying `status`, so raise_for_status() raises
    a genuine HTTPError with .response attached (not a hand-rolled double)."""
    resp = requests.Response()
    resp.status_code = status
    resp.url = url
    resp.reason = "Not Found" if status == 404 else "Error"
    return resp


@pytest.fixture
def stub_404(monkeypatch):
    def _get(url, *a, **k):
        return _http_error_response(url, 404)
    monkeypatch.setattr(loader.requests, "get", _get)


@pytest.fixture
def stub_connection_error(monkeypatch):
    def _get(url, *a, **k):
        raise requests.exceptions.ConnectTimeout("simulated DNS/connect failure")
    monkeypatch.setattr(loader.requests, "get", _get)


# ── OZ 1.0 ───────────────────────────────────────────────────────────────────

def test_oz1_loader_raises_on_404_and_returns_no_sample(stub_404):
    with pytest.raises(OZDownloadError) as exc:
        load_oz1_tracts()
    msg = str(exc.value)
    assert OZ1_URL in msg, "the error must name the URL that failed"
    assert "404" in msg, "the error must name the HTTP status"
    assert exc.value.__cause__ is not None, "the original HTTPError must be chained"
    assert isinstance(exc.value, OZTrackerError)


def test_oz1_checker_construction_raises_instead_of_8_row_set(stub_404):
    """The headline 0.1.0 bug: OZ1Checker() silently became an 8-tract checker.

    Constructing must now raise. If this ever returns an object again, assert
    on the tract count so the 8-row fallback cannot creep back in unnoticed.
    """
    with pytest.raises(OZDownloadError):
        OZ1Checker()


def test_oz1_download_error_is_catchable_at_package_base(stub_404):
    """A consumer catching the single package base catches this."""
    with pytest.raises(OZTrackerError):
        OZ1Checker()


def test_oz1_connection_failure_raises_download_error(stub_connection_error):
    with pytest.raises(OZDownloadError) as exc:
        load_oz1_tracts()
    assert "connection/DNS/timeout" in str(exc.value)
    assert OZ1_URL in str(exc.value)


def test_oz1_parse_failure_raises_parse_error(isolated_cache, monkeypatch):
    """A cached file that is not a readable workbook must raise, not degrade."""
    def _no_network(*a, **k):
        raise AssertionError("must not download when a cached file exists")
    monkeypatch.setattr(loader.requests, "get", _no_network)

    isolated_cache.mkdir(parents=True, exist_ok=True)
    (isolated_cache / "oz1_tracts.xlsx").write_bytes(b"<html>404 Not Found</html>")

    with pytest.raises(OZParseError) as exc:
        load_oz1_tracts()
    assert "oz1_tracts.xlsx" in str(exc.value)
    assert isinstance(exc.value, OZTrackerError)


def test_oz1_missing_tract_column_raises_parse_error(isolated_cache, monkeypatch):
    """A file that parses but has no tract column must raise, not fall back."""
    import pandas as pd

    def _no_network(*a, **k):
        raise AssertionError("must not download when a cached file exists")
    monkeypatch.setattr(loader.requests, "get", _no_network)

    isolated_cache.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"some_other_column": "x"}]).to_excel(
        isolated_cache / "oz1_tracts.xlsx", index=False
    )

    with pytest.raises(OZParseError) as exc:
        load_oz1_tracts()
    assert "no tract column" in str(exc.value)


# ── OZ 2.0 ───────────────────────────────────────────────────────────────────

def test_oz2_loader_raises_on_404_and_returns_no_sample(stub_404):
    with pytest.raises(OZDownloadError) as exc:
        load_oz2_eligible_tracts()
    msg = str(exc.value)
    assert OZ2_URL in msg
    assert "404" in msg
    assert exc.value.__cause__ is not None


def test_oz2_checker_construction_raises_instead_of_7_row_frame(stub_404):
    with pytest.raises(OZDownloadError):
        OZ2Checker()


def test_oz2_parse_failure_raises_parse_error(isolated_cache, monkeypatch):
    def _no_network(*a, **k):
        raise AssertionError("must not download when a cached file exists")
    monkeypatch.setattr(loader.requests, "get", _no_network)

    isolated_cache.mkdir(parents=True, exist_ok=True)
    (isolated_cache / "oz2_eligible.xlsx").write_bytes(b"not a workbook")

    with pytest.raises(OZParseError):
        load_oz2_eligible_tracts()


# ── Cleanup on handled errors ────────────────────────────────────────────────
#
# NOTE ON WHAT THESE TWO DO **NOT** TEST. Both drive failures that
# _download_to_cache catches, and its handlers call _discard() on the temp
# file. That cleanup alone satisfies both assertions, so both of these still
# pass against a mutant that deletes the .part staging entirely and streams
# straight to the final path (verified: mutation applied, both PASSED). They
# pin "a handled failure leaves the cache clean" — a real property, but NOT
# rename-atomicity. The atomicity property is pinned below, by a failure no
# handler catches.

def test_failed_download_leaves_no_file_at_cache_path(isolated_cache, stub_404):
    with pytest.raises(OZDownloadError):
        load_oz1_tracts()
    final = isolated_cache / "oz1_tracts.xlsx"
    assert not final.exists(), "a failed download must not create the cache file"
    assert not list(isolated_cache.glob("*.part")), "the .part temp must be cleaned up"


def test_midstream_failure_leaves_no_poisoned_cache(isolated_cache, monkeypatch):
    """A stream that dies partway must not leave a truncated file at the final
    path — a poisoned cache would make every later run parse-fail (or parse
    PARTIALLY) with no indication why."""
    class _DyingResponse:
        status_code = 200
        url = OZ1_URL

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=8192):
            yield b"PK\x03\x04partial"
            raise requests.exceptions.ChunkedEncodingError("connection dropped")

    monkeypatch.setattr(loader.requests, "get", lambda *a, **k: _DyingResponse())

    with pytest.raises(OZDownloadError):
        load_oz1_tracts()

    final = isolated_cache / "oz1_tracts.xlsx"
    assert not final.exists()
    assert not list(isolated_cache.glob("*.part"))


# ── Rename atomicity (the property cleanup cannot fake) ──────────────────────

def _interrupting_response(exc):
    """A 200 response that yields one real chunk, then raises `exc` mid-stream."""
    class _Response:
        status_code = 200
        url = OZ1_URL

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=8192):
            yield b"PK\x03\x04partial-workbook-bytes"
            raise exc

    return _Response()


def test_uncaught_interrupt_cannot_poison_the_final_cache_path(
    isolated_cache, monkeypatch
):
    """Atomicity, pinned by a failure NO handler catches.

    KeyboardInterrupt does not subclass Exception and _download_to_cache
    deliberately never catches it (see exceptions.py), so nothing cleans up
    here. Whatever is on disk afterwards is purely the result of WHERE the
    bytes were written. That is what makes this test bite where the two
    cleanup tests above cannot:

        shipped code -> bytes went to oz1_tracts.xlsx.part; final path absent
        mutant       -> bytes went to oz1_tracts.xlsx;      final path PRESENT

    A truncated workbook at the final path is the poisoned cache: every later
    run reads it (path.exists() is true, so no re-download) and parse-fails
    forever, or worse parses partially, with no indication why.
    """
    monkeypatch.setattr(
        loader.requests, "get",
        lambda *a, **k: _interrupting_response(KeyboardInterrupt("Ctrl-C")),
    )

    with pytest.raises(KeyboardInterrupt):
        load_oz1_tracts()

    final = isolated_cache / "oz1_tracts.xlsx"
    parts = list(isolated_cache.glob("*.part"))

    assert not final.exists(), (
        "partial bytes reached the FINAL cache path — the .part staging or the "
        "rename is gone, and the cache is now poisoned for every later run"
    )
    assert parts, (
        "the partial bytes must be somewhere, and that somewhere must be the "
        ".part temp — no .part means the write never staged"
    )
    assert parts[0].read_bytes() == b"PK\x03\x04partial-workbook-bytes"


def test_interrupt_before_rename_leaves_cache_loadable_from_scratch(
    isolated_cache, monkeypatch
):
    """The consequence of the property above: after an interrupt, the next run
    still attempts a fresh download rather than reading a truncated file.

    Under the mutant this fails at the *second* load — path.exists() is true,
    so no download is attempted and the truncated bytes are parsed instead.
    """
    monkeypatch.setattr(
        loader.requests, "get",
        lambda *a, **k: _interrupting_response(KeyboardInterrupt("Ctrl-C")),
    )
    with pytest.raises(KeyboardInterrupt):
        load_oz1_tracts()

    # Second attempt: the download must be RE-ATTEMPTED, proving the interrupted
    # run left nothing at the final path for it to trust.
    attempted = []

    def _record_then_404(url, *a, **k):
        attempted.append(url)
        return _http_error_response(url, 404)

    monkeypatch.setattr(loader.requests, "get", _record_then_404)

    with pytest.raises(OZDownloadError):
        load_oz1_tracts()
    assert attempted == [OZ1_URL], (
        "the interrupted run left a file at the final cache path, so the retry "
        "skipped the download and trusted truncated bytes"
    )


# ── Filesystem failures are typed, not raw OSError ───────────────────────────

def test_oserror_writing_cache_file_is_wrapped_as_download_error(
    isolated_cache, monkeypatch
):
    """An OSError on the write side must not escape ``except OZTrackerError``.

    Staged by putting a DIRECTORY where the .part file needs to go, so open()
    raises IsADirectoryError — a real OSError from the real code path, not a
    patched-in double. Note requests.RequestException subclasses OSError, so
    this also pins that the OSError handler sits AFTER the requests handlers.
    """
    isolated_cache.mkdir(parents=True, exist_ok=True)
    (isolated_cache / "oz1_tracts.xlsx.part").mkdir()

    class _OKResponse:
        status_code = 200
        url = OZ1_URL

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=8192):
            yield b"bytes"

    monkeypatch.setattr(loader.requests, "get", lambda *a, **k: _OKResponse())

    with pytest.raises(OZDownloadError) as exc:
        load_oz1_tracts()
    assert isinstance(exc.value, OZTrackerError)
    assert isinstance(exc.value.__cause__, OSError)
    assert not (isolated_cache / "oz1_tracts.xlsx").exists()


def test_oserror_creating_cache_dir_is_wrapped_as_download_error(
    tmp_path, monkeypatch
):
    """get_cache_dir() runs BEFORE any download handler exists, so an OSError
    there used to escape a caller's ``except OZTrackerError`` untyped."""
    blocker = tmp_path / "not_a_directory"
    blocker.write_text("i am a regular file")
    monkeypatch.setattr(loader, "CACHE_DIR", blocker / "cache")

    def _no_network(*a, **k):
        raise AssertionError("must fail before any network call")
    monkeypatch.setattr(loader.requests, "get", _no_network)

    with pytest.raises(OZDownloadError) as exc:
        load_oz1_tracts()
    assert isinstance(exc.value, OZTrackerError)
    assert isinstance(exc.value.__cause__, OSError)


def test_keyboard_interrupt_is_never_swallowed(isolated_cache, monkeypatch):
    """Catching KeyboardInterrupt would be a bug, and exceptions.py now claims
    in writing that it propagates. Pin the claim."""
    monkeypatch.setattr(
        loader.requests, "get",
        lambda *a, **k: _interrupting_response(KeyboardInterrupt("Ctrl-C")),
    )
    with pytest.raises(KeyboardInterrupt):
        load_oz1_tracts()


def test_system_exit_is_never_swallowed(isolated_cache, monkeypatch):
    monkeypatch.setattr(
        loader.requests, "get",
        lambda *a, **k: _interrupting_response(SystemExit(1)),
    )
    with pytest.raises(SystemExit):
        load_oz1_tracts()


# ── The fabrication path is gone ─────────────────────────────────────────────

def test_no_loader_returns_the_sample_set_on_failure(stub_404):
    """Belt and braces: whatever comes out of a failing load, it is never the
    sample set. Written as a value comparison rather than a call-count check so
    it stays true no matter how the sample is reached internally."""
    sample = load_sample_oz1_tracts()
    for fn in (load_oz1_tracts, load_oz2_eligible_tracts):
        try:
            result = fn()
        except OZTrackerError:
            continue
        pytest.fail(f"{fn.__name__} returned {result!r} instead of raising")
    assert len(sample) == 8  # the set that used to be substituted silently

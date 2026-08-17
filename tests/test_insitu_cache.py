"""Tests for the SURFs_UP in-memory in-situ download cache."""

import datetime
from types import SimpleNamespace

import pandas as pd
import pytest

from surfs_up.web import insitu_cache


def test_cache_pads_download_and_reuses_contained_interval(monkeypatch):
    calls = []

    def downloader(start, end):
        calls.append((start, end))
        return pd.DataFrame({
            "datetime": pd.date_range(start, end, freq="h"),
            "V": 400.0,
        })

    start = datetime.datetime(2026, 1, 1)
    end = datetime.datetime(2026, 1, 3)
    insitu_cache.clear_insitu_download_cache()
    first = insitu_cache._cached_call("get_omni", downloader, start, end)
    first.loc[:, "V"] = 999.0
    second = insitu_cache._cached_call(
        "get_omni", downloader, start + datetime.timedelta(hours=6), end
    )

    assert len(calls) == 1
    assert calls[0] == (
        start - datetime.timedelta(days=27), end + datetime.timedelta(days=27)
    )
    assert (second["V"] == 400.0).all()


def test_app_start_replaces_downloaders_and_clears_cache(monkeypatch):
    import surf.surf_insitu as sinsit

    original = insitu_cache._ORIGINALS.get("get_omni", sinsit.get_omni)
    monkeypatch.setitem(insitu_cache._ORIGINALS, "get_omni", original)
    insitu_cache._CACHE[("old",)] = SimpleNamespace()

    insitu_cache.install_insitu_download_cache()

    assert not insitu_cache._CACHE
    assert sinsit.get_omni is not original


def test_empty_stereo_download_has_actionable_error():
    calls = []

    def downloader(start, end):
        calls.append((start, end))
        raise IndexError("pop from empty list")

    start = datetime.datetime(2026, 8, 1)
    end = datetime.datetime(2026, 8, 10)

    with pytest.raises(insitu_cache.InsituDataUnavailableError) as caught:
        insitu_cache._cached_call("get_stereo_a", downloader, start, end)

    assert len(calls) == 2
    assert "No STEREO-A/CDAWeb files" in str(caught.value)
    assert "2026-08-01T00:00:00 to 2026-08-10T00:00:00" in str(caught.value)
    assert isinstance(caught.value.__cause__, IndexError)

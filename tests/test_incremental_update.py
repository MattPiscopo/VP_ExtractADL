"""Tests for incremental synchronization scenarios."""
import pytest
from src.merge import merge_records
from src.normalize import normalize_record
from src.validate import compute_quality_metrics


def test_scenario_1_new_article_appears():
    prior = {"100": {"Publication ID": "100", "Title": "Old", "First Seen": "2026-01-01", "Last Seen": "2026-01-01"}}
    fresh = {"101": {"Publication ID": "101", "Title": "Brand New", "First Seen": "2026-11-12", "Last Seen": "2026-11-12"}}
    merged, new_count, updated_count = merge_records(prior, fresh)
    assert new_count == 1
    assert "101" in merged
    assert len(merged) == 2


def test_scenario_2_title_changes():
    prior = {
        "100": {
            "Publication ID": "100",
            "Title": "Original Title",
            "First Seen": "2026-01-01",
            "Last Seen": "2026-01-01",
            "Last Updated": "2026-01-01",
        }
    }
    fresh = {
        "100": {
            "Publication ID": "100",
            "Title": "Revised Title (Updated)",
            "First Seen": "2026-11-12",
            "Last Seen": "2026-11-12",
            "Last Updated": "2026-11-12",
        }
    }
    merged, new_count, updated_count = merge_records(prior, fresh)
    assert updated_count == 1
    assert merged["100"]["Title"] == "Revised Title (Updated)"
    assert merged["100"]["First Seen"] == "2026-01-01"
    assert merged["100"]["Last Updated"] == "2026-11-12"


def test_scenario_3_industry_changes():
    prior = {
        "100": {
            "Publication ID": "100",
            "Title": "Grid Optimization",
            "Industry": "Automotive",
            "First Seen": "2026-01-01",
            "Last Seen": "2026-01-01",
            "Last Updated": "2026-01-01",
        }
    }
    fresh = {
        "100": {
            "Publication ID": "100",
            "Title": "Grid Optimization",
            "Industry": "Energy, Utilities & Resources",
            "First Seen": "2026-11-12",
            "Last Seen": "2026-11-12",
            "Last Updated": "2026-11-12",
        }
    }
    merged, new_count, updated_count = merge_records(prior, fresh)
    assert updated_count == 1
    assert merged["100"]["Industry"] == "Energy, Utilities & Resources"


def test_scenario_4_article_disappears_during_backfill():
    prior = {
        "100": {"Publication ID": "100", "Title": "Active Article", "Record Status": "Active"},
        "999": {"Publication ID": "999", "Title": "Deleted / Delisted Article", "Record Status": "Active"},
    }
    # During full backfill, only 100 was observed
    fresh = {
        "100": {"Publication ID": "100", "Title": "Active Article", "Last Seen": "2026-11-12", "Record Status": "Active"}
    }
    merged, new_count, updated_count = merge_records(prior, fresh, is_full_backfill=True)
    assert len(merged) == 2
    assert merged["100"]["Record Status"] == "Active"
    assert merged["999"]["Record Status"] == "Not observed"


def test_quality_metrics_reconciliation():
    records = {
        "1": {"Publication ID": "1", "Title": "A", "Publication Date": "2026", "URL": "https://www.adlittle.com/a", "ENUR Relevance": "Direct ENUR", "Record Status": "Active"},
        "2": {"Publication ID": "2", "Title": "B", "Publication Date": "2026", "URL": "https://www.adlittle.com/b", "ENUR Relevance": "Cross-practice", "Record Status": "Active"},
    }
    qa = compute_quality_metrics(records, api_expected_count=2, api_expected_pages=1, pages_processed=1)
    assert qa["Total unique publications"] == 2
    assert qa["Coverage complete"] is True
    assert qa["Direct ENUR count"] == 1
    assert qa["Cross-practice ENUR count"] == 1
    assert qa["Discrepancy (Actual - Expected)"] == 0


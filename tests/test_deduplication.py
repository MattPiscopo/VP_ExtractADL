"""Tests for Drupal NID deduplication and identifier stability."""
import pytest
from src.merge import merge_records


def test_deduplication_by_nid():
    prior = {
        "1001": {
            "Publication ID": "1001",
            "Title": "Original Article 1",
            "First Seen": "2026-10-01",
            "Last Seen": "2026-10-01",
            "Record Status": "Active",
        }
    }
    # Fresh records include duplicate 1001 from a repeated page and a new 1002
    fresh = {
        "1001": {
            "Publication ID": "1001",
            "Title": "Original Article 1",
            "First Seen": "2026-11-12",
            "Last Seen": "2026-11-12",
            "Record Status": "Active",
        },
        "1002": {
            "Publication ID": "1002",
            "Title": "New Article 2",
            "First Seen": "2026-11-12",
            "Last Seen": "2026-11-12",
            "Record Status": "Active",
        },
    }

    merged, new_count, updated_count = merge_records(prior, fresh, is_full_backfill=False)
    assert len(merged) == 2
    assert new_count == 1
    assert updated_count == 0
    # First Seen must be preserved from prior record!
    assert merged["1001"]["First Seen"] == "2026-10-01"
    # Last Seen must be refreshed!
    assert merged["1001"]["Last Seen"] == "2026-11-12"


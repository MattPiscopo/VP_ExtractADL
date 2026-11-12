"""Tests for pagination logic, zero-indexing, and boundary reconciliation."""
import pytest
from src.parse import parse_pager


def test_zero_indexed_total_calculation():
    # Catalogue with 1,953 items, 10 items/page, 196 total pages (0 to 195)
    total_count = 1953
    items_per_page = 10
    expected_pages = (total_count + items_per_page - 1) // items_per_page
    assert expected_pages == 196

    # 195 full pages of 10 items = 1950 items
    # Page index 195 holds remainder: 3 items
    remainder = total_count - (195 * items_per_page)
    assert remainder == 3


def test_pager_handling_on_final_page():
    final_page_pager = {
        "count": 1953,
        "pages": 196,
        "items_per_page": 10,
        "current_page": 195,
        "next_page": 0,
    }
    parsed = parse_pager(final_page_pager)
    assert parsed["current_page"] == 195
    assert parsed["next_page"] == 0
    # next_page == 0 indicates no subsequent page in Drupal Views pager


def test_empty_pager_defaults():
    parsed = parse_pager(None)
    assert parsed["count"] == 0
    assert parsed["pages"] == 0
    assert parsed["current_page"] == 0


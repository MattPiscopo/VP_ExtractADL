"""Tests for HTML parsing, entity unescaping, and field extraction."""
import pytest
from src.parse import (
    clean_text,
    extract_created_timestamp,
    extract_links_text,
    parse_pager,
    parse_raw_record,
)


def test_clean_text_html_entities():
    raw = "Bank tokenization: Choosing between wrapping &amp; originating &lt;special&gt;"
    assert clean_text(raw) == "Bank tokenization: Choosing between wrapping & originating <special>"


def test_clean_text_whitespace():
    raw = "\n   \t  Residential   flexibility \n\n  in Europe.   "
    assert clean_text(raw) == "Residential flexibility in Europe."


def test_extract_links_text():
    html_snippet = (
        '<a href="/en/industries/energy-utilities-resources" hreflang="en">Energy, Utilities &amp; Resources</a>'
    )
    result = extract_links_text(html_snippet)
    assert result == ["Energy, Utilities & Resources"]


def test_extract_multiple_links():
    html_snippet = (
        '<a href="/ind1">Energy</a>, <a href="/ind2">Automotive</a>'
    )
    result = extract_links_text(html_snippet)
    assert result == ["Energy", "Automotive"]


def test_extract_created_timestamp():
    html_time = '<time datetime="2026-08-24T20:26:08+02:00" class="datetime">August 2026</time>'
    assert extract_created_timestamp(html_time) == "2026-08-24T20:26:08+02:00"


def test_parse_pager():
    raw_pager = {
        "count": "1953",
        "pages": "196",
        "items_per_page": "10",
        "current_page": "0",
        "next_page": "1",
    }
    pager = parse_pager(raw_pager)
    assert pager["count"] == 1953
    assert pager["pages"] == 196
    assert pager["current_page"] == 0
    assert pager["next_page"] == 1


def test_parse_raw_record():
    raw = {
        "nid": "25194",
        "title": "Scaling residential flexibility",
        "subtitle": "New propositions",
        "body": "Residential flexibility could unlock €24–€58 billion",
        "field_date_publication": "September 2026",
        "created": '<time datetime="2026-08-18T21:48:36+02:00">August 2026</time>',
        "type": "Insights - Viewpoints",
        "industries": '<a href="/en/industries/energy-utilities-resources">Energy, Utilities &amp; Resources</a>',
        "services": '<a href="/en/capabilities/sustainability">Sustainability</a>',
        "challenges": "",
        "node_url": "/en/insights/viewpoints/scaling-residential-flexibility",
    }
    rec = parse_raw_record(raw, page_num=0)
    assert rec["nid"] == "25194"
    assert rec["title"] == "Scaling residential flexibility"
    assert rec["industries_str"] == "Energy, Utilities & Resources"
    assert rec["services_str"] == "Sustainability"
    assert rec["canonical_url"] == "https://www.adlittle.com/en/insights/viewpoints/scaling-residential-flexibility"
    assert rec["created_timestamp"] == "2026-08-18T21:48:36+02:00"


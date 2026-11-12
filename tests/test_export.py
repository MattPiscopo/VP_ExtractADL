"""Tests for database generation, Excel sheet schemas, and machine-readable exports."""
import csv
import json
from pathlib import Path
import pytest
from openpyxl import load_workbook
from src.export import export_all


def test_export_all_structure(tmp_path: Path):
    records = {
        "25194": {
            "Publication ID": "25194",
            "Title": "Scaling residential flexibility",
            "Subtitle": "New propositions",
            "Publication Date": "September 2026",
            "Publication Year": 2026,
            "Created Date": "2026-08-18T21:48:36+02:00",
            "Publication Type": "Insights - Viewpoints",
            "Industry": "Energy, Utilities & Resources",
            "Services / Capabilities": "Sustainability",
            "Challenges": "Innovation",
            "Summary / Excerpt": "Residential flexibility description...",
            "URL": "https://www.adlittle.com/en/insights/viewpoints/scaling-residential-flexibility",
            "ENUR Relevance": "Direct ENUR",
            "ENUR Subsector": "Energy retail and customer solutions",
            "BD Topics": "Customer propositions & retail flexibility",
            "First Seen": "2026-11-12",
            "Last Seen": "2026-11-12",
            "Last Updated": "2026-11-12",
            "Record Status": "Active",
            "Data Quality": "Complete",
            "_topic_mappings": [
                {
                    "subsector": "Energy retail and customer solutions",
                    "theme": "Customer propositions & retail flexibility",
                    "potential_relevance": "Retail flexibility strategy",
                }
            ],
        }
    }
    sync_log = {
        "Run ID": "RUN-TEST",
        "Run timestamp": "2026-11-12T12:00:00Z",
        "Execution environment": "Test Runner",
        "Execution mode": "backfill",
        "Pages requested": 1,
        "Pages successfully processed": 1,
        "API-reported publication count": 1,
        "Records retrieved": 1,
        "Unique records": 1,
        "New records": 1,
        "Updated records": 0,
        "Errors": "None",
        "Coverage status": "Complete",
        "Execution result": "SUCCESS",
    }
    qa_metrics = {
        "Total unique publications": 1,
        "API-reported publication count": 1,
        "API-reported pages": 1,
        "Pages processed": 1,
        "Discrepancy (Actual - Expected)": 0,
        "Duplicate IDs": 0,
        "Missing titles": 0,
        "Missing publication dates": 0,
        "Missing URLs": 0,
        "Invalid URLs": 0,
        "Industry classification coverage (%)": 100.0,
        "ENUR classification coverage (%)": 100.0,
        "Direct ENUR count": 1,
        "Cross-practice ENUR count": 0,
        "Other / Non-ENUR count": 0,
        "Active records": 1,
        "Not observed records": 0,
        "Quality Complete": 1,
        "Quality Partial": 0,
        "Quality Review": 0,
        "Coverage complete": True,
        "Errors": "None",
        "Validated At UTC": "2026-11-12T12:00:00Z",
    }

    export_all(tmp_path, records, sync_log, qa_metrics)

    # Check generated files
    assert (tmp_path / "ADL_Insights_Database.xlsx").exists()
    assert (tmp_path / "publications_master.csv").exists()
    assert (tmp_path / "publications_master.json").exists()
    assert (tmp_path / "publications_enur.csv").exists()
    assert (tmp_path / "publication_topics.csv").exists()
    assert (tmp_path / "sync_status.json").exists()
    assert (tmp_path / "ADL_Insights_Database.csv").exists()
    assert (tmp_path / "coverage.json").exists()

    # Verify Excel workbook sheets
    wb = load_workbook(tmp_path / "ADL_Insights_Database.xlsx")
    expected_sheets = [
        "Publications Master",
        "ENUR Publications",
        "Publication Themes",
        "Update Log",
        "Data Quality & Coverage",
    ]
    assert wb.sheetnames == expected_sheets

    # Verify Sheet 1 row count (header + 1 data row)
    ws1 = wb["Publications Master"]
    assert ws1.max_row == 2
    assert ws1.cell(row=2, column=1).value == "25194"
    assert ws1.cell(row=2, column=13).value == "Direct ENUR"

    # Verify Sheet 2 ENUR
    ws2 = wb["ENUR Publications"]
    assert ws2.max_row == 2
    assert ws2.cell(row=2, column=1).value == "25194"

    # Verify Sheet 3 Themes
    ws3 = wb["Publication Themes"]
    assert ws3.max_row == 2
    assert ws3.cell(row=2, column=8).value == "Customer propositions & retail flexibility"

    # Verify JSON content
    with open(tmp_path / "publications_master.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["Publication ID"] == "25194"


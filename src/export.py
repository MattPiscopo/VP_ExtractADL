"""Export engine for Excel master database and machine-readable data files."""
import csv
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

MASTER_HEADERS = [
    "Publication ID",
    "Title",
    "Subtitle",
    "Publication Date",
    "Publication Year",
    "Created Date",
    "Publication Type",
    "Industry",
    "Services / Capabilities",
    "Challenges",
    "Summary / Excerpt",
    "URL",
    "ENUR Relevance",
    "ENUR Subsector",
    "BD Topics",
    "First Seen",
    "Last Seen",
    "Last Updated",
    "Record Status",
    "Data Quality",
]

ENUR_HEADERS = [
    "Publication ID",
    "Title",
    "Subtitle",
    "Publication Date",
    "Publication Year",
    "Publication Type",
    "Industry",
    "ENUR Relevance",
    "ENUR Subsector",
    "BD Topics",
    "Summary / Excerpt",
    "URL",
]

THEMES_HEADERS = [
    "Publication ID",
    "Title",
    "Publication Date",
    "Publication Year",
    "Industry",
    "ENUR Relevance",
    "ENUR Subsector",
    "BD Theme",
    "Potential BD Relevance",
    "URL",
]

UPDATE_LOG_HEADERS = [
    "Run ID",
    "Run timestamp",
    "Execution environment",
    "Execution mode",
    "Pages requested",
    "Pages successfully processed",
    "API-reported publication count",
    "Records retrieved",
    "Unique records",
    "New records",
    "Updated records",
    "Errors",
    "Coverage status",
    "Execution result",
]

# Styling constants
COLOR_NAVY = "193454"
COLOR_WHITE = "FFFFFF"
COLOR_DIRECT_ENUR = "DFF2E8"
COLOR_CROSS_SECTOR = "FFF0D8"
COLOR_NEUTRAL = "F8F9FA"
COLOR_BORDER = "D3D3D3"


def create_header_style():
    return {
        "fill": PatternFill("solid", fgColor=COLOR_NAVY),
        "font": Font(color=COLOR_WHITE, bold=True, size=11),
        "alignment": Alignment(horizontal="center", vertical="center", wrap_text=True),
    }


def autofit_and_style_sheet(ws, headers: List[str], min_widths: Optional[Dict[str, int]] = None):
    ws.sheet_view.showGridLines = True
    ws.freeze_panes = "B2"
    ws.row_dimensions[1].height = 28
    hdr_style = create_header_style()
    thin_border = Border(
        left=Side(style="thin", color=COLOR_BORDER),
        right=Side(style="thin", color=COLOR_BORDER),
        top=Side(style="thin", color=COLOR_BORDER),
        bottom=Side(style="thin", color=COLOR_BORDER),
    )

    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.fill = hdr_style["fill"]
        cell.font = hdr_style["font"]
        cell.alignment = hdr_style["alignment"]
        cell.border = thin_border

    max_row = max(ws.max_row, 1)
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max_row}"

    for col_idx, h in enumerate(headers, 1):
        col_letter = get_column_letter(col_idx)
        width = (min_widths or {}).get(h, 20)
        ws.column_dimensions[col_letter].width = width


def export_all(
    output_dir: Path,
    records: Dict[str, Dict[str, Any]],
    sync_log: Dict[str, Any],
    qa_metrics: Dict[str, Any],
    all_logs_history: Optional[List[Dict[str, Any]]] = None,
):
    """Write master Excel database and machine-readable data files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Sort master publications: most recent year/date first, then publication ID desc
    ordered_records = sorted(
        records.values(),
        key=lambda x: (str(x.get("Publication Year", "")), str(x.get("Publication Date", "")), str(x.get("Publication ID", ""))),
        reverse=True,
    )

    # Filter ENUR publications
    enur_records = [
        r for r in ordered_records
        if r.get("ENUR Relevance") in ("Direct ENUR", "Cross-practice")
    ]

    # Generate Publication Themes rows
    themes_rows = []
    for r in ordered_records:
        topics_list = r.get("_topic_mappings") or []
        if not topics_list and r.get("BD Topics"):
            topics_list = [{
                "subsector": r.get("ENUR Subsector", "Energy transition"),
                "theme": t.strip(),
                "potential_relevance": f"Opportunity in {r.get('ENUR Subsector', 'energy')}: {t.strip()}"
            } for t in r.get("BD Topics", "").split(";") if t.strip()]

        for tm in topics_list:
            themes_rows.append({
                "Publication ID": r.get("Publication ID", ""),
                "Title": r.get("Title", ""),
                "Publication Date": r.get("Publication Date", ""),
                "Publication Year": r.get("Publication Year", ""),
                "Industry": r.get("Industry", ""),
                "ENUR Relevance": r.get("ENUR Relevance", ""),
                "ENUR Subsector": tm.get("subsector") or r.get("ENUR Subsector", ""),
                "BD Theme": tm.get("theme", ""),
                "Potential BD Relevance": tm.get("potential_relevance", ""),
                "URL": r.get("URL", ""),
            })

    # Prepare historical logs list
    history_logs = list(all_logs_history or [])
    if sync_log not in history_logs:
        history_logs.append(sync_log)

    # 1. Generate Excel Workbook
    wb = Workbook()

    # --- Sheet 1: Publications Master ---
    ws1 = wb.active
    ws1.title = "Publications Master"
    ws1.append(MASTER_HEADERS)
    for r in ordered_records:
        row_vals = [r.get(h, "") for h in MASTER_HEADERS]
        ws1.append(row_vals)
    master_widths = {
        "Publication ID": 14,
        "Title": 50,
        "Subtitle": 45,
        "Publication Date": 18,
        "Publication Year": 15,
        "Created Date": 22,
        "Publication Type": 22,
        "Industry": 35,
        "Services / Capabilities": 28,
        "Challenges": 25,
        "Summary / Excerpt": 60,
        "URL": 55,
        "ENUR Relevance": 18,
        "ENUR Subsector": 35,
        "BD Topics": 45,
        "First Seen": 14,
        "Last Seen": 14,
        "Last Updated": 14,
        "Record Status": 14,
        "Data Quality": 14,
    }
    autofit_and_style_sheet(ws1, MASTER_HEADERS, master_widths)

    # Style data rows in ws1
    for row in ws1.iter_rows(min_row=2):
        rel_cell = row[12]  # ENUR Relevance
        url_cell = row[11]  # URL
        if url_cell.value and str(url_cell.value).startswith("http"):
            url_cell.hyperlink = str(url_cell.value)
            url_cell.font = Font(color="0563C1", underline="single")
        if rel_cell.value == "Direct ENUR":
            rel_cell.fill = PatternFill("solid", fgColor=COLOR_DIRECT_ENUR)
            rel_cell.font = Font(color="006020", bold=True)
        elif rel_cell.value == "Cross-practice":
            rel_cell.fill = PatternFill("solid", fgColor=COLOR_CROSS_SECTOR)
            rel_cell.font = Font(color="804000", bold=True)

    # --- Sheet 2: ENUR Publications ---
    ws2 = wb.create_sheet("ENUR Publications")
    ws2.append(ENUR_HEADERS)
    for r in enur_records:
        row_vals = [r.get(h, "") for h in ENUR_HEADERS]
        ws2.append(row_vals)
    enur_widths = {
        "Publication ID": 14,
        "Title": 50,
        "Subtitle": 45,
        "Publication Date": 18,
        "Publication Year": 15,
        "Publication Type": 22,
        "Industry": 35,
        "ENUR Relevance": 18,
        "ENUR Subsector": 35,
        "BD Topics": 45,
        "Summary / Excerpt": 60,
        "URL": 55,
    }
    autofit_and_style_sheet(ws2, ENUR_HEADERS, enur_widths)
    for row in ws2.iter_rows(min_row=2):
        url_cell = row[11]
        rel_cell = row[7]
        if url_cell.value and str(url_cell.value).startswith("http"):
            url_cell.hyperlink = str(url_cell.value)
            url_cell.font = Font(color="0563C1", underline="single")
        if rel_cell.value == "Direct ENUR":
            rel_cell.fill = PatternFill("solid", fgColor=COLOR_DIRECT_ENUR)
            rel_cell.font = Font(color="006020", bold=True)
        elif rel_cell.value == "Cross-practice":
            rel_cell.fill = PatternFill("solid", fgColor=COLOR_CROSS_SECTOR)
            rel_cell.font = Font(color="804000", bold=True)

    # --- Sheet 3: Publication Themes ---
    ws3 = wb.create_sheet("Publication Themes")
    ws3.append(THEMES_HEADERS)
    for r in themes_rows:
        row_vals = [r.get(h, "") for h in THEMES_HEADERS]
        ws3.append(row_vals)
    themes_widths = {
        "Publication ID": 14,
        "Title": 45,
        "Publication Date": 18,
        "Publication Year": 15,
        "Industry": 30,
        "ENUR Relevance": 18,
        "ENUR Subsector": 32,
        "BD Theme": 40,
        "Potential BD Relevance": 55,
        "URL": 50,
    }
    autofit_and_style_sheet(ws3, THEMES_HEADERS, themes_widths)
    for row in ws3.iter_rows(min_row=2):
        url_cell = row[9]
        if url_cell.value and str(url_cell.value).startswith("http"):
            url_cell.hyperlink = str(url_cell.value)
            url_cell.font = Font(color="0563C1", underline="single")

    # --- Sheet 4: Update Log ---
    ws4 = wb.create_sheet("Update Log")
    ws4.append(UPDATE_LOG_HEADERS)
    for entry in history_logs:
        row_vals = [entry.get(h, "") for h in UPDATE_LOG_HEADERS]
        ws4.append(row_vals)
    log_widths = {
        "Run ID": 22,
        "Run timestamp": 24,
        "Execution environment": 24,
        "Execution mode": 18,
        "Pages requested": 16,
        "Pages successfully processed": 25,
        "API-reported publication count": 26,
        "Records retrieved": 18,
        "Unique records": 16,
        "New records": 14,
        "Updated records": 16,
        "Errors": 35,
        "Coverage status": 18,
        "Execution result": 18,
    }
    autofit_and_style_sheet(ws4, UPDATE_LOG_HEADERS, log_widths)

    # --- Sheet 5: Data Quality & Coverage ---
    ws5 = wb.create_sheet("Data Quality & Coverage")
    ws5.sheet_view.showGridLines = True
    ws5.append(["Quality / Coverage Metric", "Observed Value", "Notes / Evaluation"])
    metric_rows = [
        ("Total unique publications", qa_metrics.get("Total unique publications"), "Deduplicated by Drupal NID in master database"),
        ("API-reported publication count", qa_metrics.get("API-reported publication count"), "Target reported by /en/insights_rest pager"),
        ("API-reported pages", qa_metrics.get("API-reported pages"), "Reported page count in pager metadata"),
        ("Pages processed this run", qa_metrics.get("Pages processed"), "Count of successfully retrieved API/JSON pages"),
        ("Discrepancy (Actual - Expected)", qa_metrics.get("Discrepancy (Actual - Expected)"), "Difference between archive and API reported count"),
        ("Duplicate IDs", qa_metrics.get("Duplicate IDs"), "Enforced 0 by master index deduplication"),
        ("Missing titles", qa_metrics.get("Missing titles"), "Publications lacking a title string"),
        ("Missing publication dates", qa_metrics.get("Missing publication dates"), "Publications lacking field_date_publication"),
        ("Missing URLs", qa_metrics.get("Missing URLs"), "Publications lacking canonical article URL"),
        ("Invalid URLs", qa_metrics.get("Invalid URLs"), "URLs not resolving to https://www.adlittle.com"),
        ("Industry classification coverage (%)", f"{qa_metrics.get('Industry classification coverage (%)', 0)}%", "Percentage of records with industry tags"),
        ("ENUR classification coverage (%)", f"{qa_metrics.get('ENUR classification coverage (%)', 0)}%", "Percentage classified as Direct ENUR or Cross-practice"),
        ("Direct ENUR count", qa_metrics.get("Direct ENUR count"), "Directly assigned to Energy, Utilities & Resources"),
        ("Cross-practice ENUR count", qa_metrics.get("Cross-practice ENUR count"), "Cross-sector thought leadership relevant to ENUR BD"),
        ("Other / Non-ENUR count", qa_metrics.get("Other / Non-ENUR count"), "General publications outside ENUR scope"),
        ("Active records", qa_metrics.get("Active records"), "Publications verified in catalogue"),
        ("Not observed records", qa_metrics.get("Not observed records"), "Historical publications not in current crawl"),
        ("Data Quality: Complete", qa_metrics.get("Quality Complete"), "Records with valid NID, Title, URL, and Date"),
        ("Data Quality: Partial", qa_metrics.get("Quality Partial"), "Records with partial metadata"),
        ("Data Quality: Review", qa_metrics.get("Quality Review"), "Records flagged for manual verification"),
        ("Coverage Complete", "TRUE" if qa_metrics.get("Coverage complete") else "FALSE", "Reconciliation with API catalogue target"),
        ("Last Synchronization UTC", qa_metrics.get("Validated At UTC"), "Timestamp of this validation check"),
        ("Errors Encountered", qa_metrics.get("Errors"), "Diagnostic error status"),
    ]
    for row in metric_rows:
        ws5.append(list(row))
    ws5.column_dimensions["A"].width = 38
    ws5.column_dimensions["B"].width = 25
    ws5.column_dimensions["C"].width = 65
    ws5.row_dimensions[1].height = 28
    for col_idx in range(1, 4):
        cell = ws5.cell(row=1, column=col_idx)
        cell.fill = PatternFill("solid", fgColor=COLOR_NAVY)
        cell.font = Font(color=COLOR_WHITE, bold=True, size=11)
        cell.alignment = Alignment(horizontal="center", vertical="center")
    for r_idx in range(2, len(metric_rows) + 2):
        ws5.cell(row=r_idx, column=1).font = Font(bold=True)
        ws5.cell(row=r_idx, column=2).alignment = Alignment(horizontal="center")

    excel_path = output_dir / "ADL_Insights_Database.xlsx"
    wb.save(excel_path)

    # 2. Machine-readable exports
    clean_master_dicts = []
    for r in ordered_records:
        d = {k: r.get(k, "") for k in MASTER_HEADERS}
        clean_master_dicts.append(d)

    with (output_dir / "publications_master.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MASTER_HEADERS)
        writer.writeheader()
        writer.writerows(clean_master_dicts)

    legacy_headers = [
        "Drupal NID", "Title", "Subtitle", "Publication period", "Created timestamp",
        "Content type", "Industries", "Capabilities", "Challenges", "Excerpt",
        "URL", "ENUR relevance", "First seen", "Last seen", "Source API page"
    ]
    with (output_dir / "ADL_Insights_Database.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=legacy_headers)
        writer.writeheader()
        for r in ordered_records:
            writer.writerow({
                "Drupal NID": r.get("Publication ID", ""),
                "Title": r.get("Title", ""),
                "Subtitle": r.get("Subtitle", ""),
                "Publication period": r.get("Publication Date", ""),
                "Created timestamp": r.get("Created Date", ""),
                "Content type": r.get("Publication Type", ""),
                "Industries": r.get("Industry", ""),
                "Capabilities": r.get("Services / Capabilities", ""),
                "Challenges": r.get("Challenges", ""),
                "Excerpt": r.get("Summary / Excerpt", ""),
                "URL": r.get("URL", ""),
                "ENUR relevance": r.get("ENUR Relevance", ""),
                "First seen": r.get("First Seen", ""),
                "Last seen": r.get("Last Seen", ""),
                "Source API page": r.get("Source API Page", ""),
            })

    with (output_dir / "publications_master.json").open("w", encoding="utf-8") as f:
        json.dump(clean_master_dicts, f, indent=2, ensure_ascii=False)

    clean_enur_dicts = []
    for r in enur_records:
        clean_enur_dicts.append({k: r.get(k, "") for k in ENUR_HEADERS})
    with (output_dir / "publications_enur.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ENUR_HEADERS)
        writer.writeheader()
        writer.writerows(clean_enur_dicts)

    with (output_dir / "publication_topics.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=THEMES_HEADERS)
        writer.writeheader()
        writer.writerows(themes_rows)

    full_status = {
        "sync_log": sync_log,
        "qa_metrics": qa_metrics,
        "history_runs_count": len(history_logs),
    }
    with (output_dir / "sync_status.json").open("w", encoding="utf-8") as f:
        json.dump(full_status, f, indent=2, ensure_ascii=False)

    legacy_coverage = {
        "Run UTC": sync_log.get("Run timestamp"),
        "Mode": sync_log.get("Execution mode"),
        "Unique records in archive": qa_metrics.get("Total unique publications"),
        "Records seen this run": sync_log.get("Records retrieved"),
        "Pages processed": sync_log.get("Pages successfully processed"),
        "API reported count": qa_metrics.get("API-reported publication count"),
        "API reported pages": qa_metrics.get("API-reported pages"),
        "Full pagination completed this run": qa_metrics.get("Coverage complete"),
        "Coverage complete": qa_metrics.get("Coverage complete"),
        "Errors": qa_metrics.get("Errors"),
        "Method": "Public metadata catalogue; nid deduplication; multi-tier ENUR taxonomy; 5-sheet master Excel workbook",
        "Note": "Weekly incremental refresh checks newest pages; periodic backfill reconciles complete catalogue.",
    }
    with (output_dir / "coverage.json").open("w", encoding="utf-8") as f:
        json.dump(legacy_coverage, f, indent=2, ensure_ascii=False)

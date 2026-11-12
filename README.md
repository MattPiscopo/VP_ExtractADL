# ADL Insights Historical Database & Automated Synchronization

An automated, auditable, and resilient data extraction and intelligence pipeline for Arthur D. Little's public thought leadership insights (`https://www.adlittle.com/en/insights`).

Developed to power the **Energy, Utilities & Resources (ENUR) AI Business Development Intelligence** workflow.

---

## 1. Quick Start

### Installation
Ensure Python 3.12+ is installed:
```bash
pip install -r requirements.txt
```

### CLI Execution Modes
```bash
# 1. Full historical backfill (reconciles all 196 catalogue pages)
python update.py --backfill --output-dir data

# 2. Weekly incremental synchronization (polls newest catalogue pages)
python update.py --update --output-dir data

# 3. Offline import (single JSON file, folder, or glob)
python update.py --import-json samples/insights_page_1.json --output-dir data

# 4. QA validation & coverage audit (offline verification)
python update.py --validate --output-dir data
```

### Run Tests
```bash
pytest tests/ -v
```

---

## 2. Deliverables & Outputs

All generated database files reside in `data/`:

| Artifact | Format | Description |
|---|---|---|
| **`ADL_Insights_Database.xlsx`** | Excel (5 Sheets) | Master business intelligence database formatted for consultants and analysts. |
| **`publications_master.csv`** | CSV (UTF-8) | Clean, normalized master publications table. |
| **`publications_master.json`** | JSON | Machine-readable master dataset for semantic embedding & LLM retrieval. |
| **`publications_enur.csv`** | CSV (UTF-8) | Materialized view of all Direct ENUR and Cross-practice publications. |
| **`publication_topics.csv`** | CSV (UTF-8) | Normalized mapping table linking publications to specific BD consulting themes. |
| **`sync_status.json`** | JSON | Machine-readable audit status and data quality metrics. |

---

## 3. Database Architecture (5 Excel Sheets)

1. **Sheet 1 — Publications Master:** Exhaustive inventory of every collected publication deduplicated by Drupal `nid`. Tracks lifecycle audit dates (`First Seen`, `Last Seen`, `Last Updated`) and data quality.
2. **Sheet 2 — ENUR Publications:** Focused slice of direct ENUR and cross-sector thought leadership with subsector classifications and BD opportunity themes.
3. **Sheet 3 — Publication Themes:** 1-to-many normalized mapping between publications and specialized BD consulting offerings.
4. **Sheet 4 — Update Log:** Historical audit trail logging every run (timestamp, environment, pages fetched, new/updated counts, errors).
5. **Sheet 5 — Data Quality & Coverage:** Automated scorecard verifying count reconciliation against the API pager, zero duplicate IDs, URL integrity, and classification coverage.

---

## 4. Automation & Deployment

- **Local Automation:** Scheduled via Windows Task Scheduler (`run_sync.bat`). Local IP access is verified and whitelisted by server security policies.
- **GitHub Actions:** CI workflow in `.github/workflows/refresh.yml` executes test suites, performs offline validation, and commits synchronized database snapshots.
- **Offline / CMS Export:** Detailed in `docs/deployment.md`.

---

## 5. Documentation

- [Architecture & Design](docs/architecture.md)
- [Deployment & Automation](docs/deployment.md)
- [Data Dictionary](docs/data_dictionary.md)
- [Troubleshooting & Maintenance](docs/troubleshooting.md)

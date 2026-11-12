# ADL Insights Data Pipeline — Architecture & Technical Design

## 1. Executive Summary

This document describes the architecture, data model, and ETL workflow for the **Arthur D. Little (ADL) Insights Historical Database & Automated Synchronization System**.

The system automates the ingestion, normalization, multi-tier classification, deduplication, and export of public thought leadership publications published by Arthur D. Little (`https://www.adlittle.com/en/insights`).

The resulting structured data is tailored for internal Business Development (BD) Intelligence, specifically supporting the Energy, Utilities & Resources (ENUR) practice.

---

## 2. End-to-End Pipeline Architecture

```text
+---------------------------------------------------------------------------------+
|                                DATA EXTRACTION                                  |
|                                                                                 |
|  [ADL Drupal REST API]           [Offline / Browser JSON]                       |
|  https://www.adlittle.com/       Multiple exported pages                        |
|  en/insights_rest?page=N         (Fallback / air-gapped)                        |
+------------------------+--------------------------------------------------------+
                         |
                         v
+---------------------------------------------------------------------------------+
|                          INGESTION & PARSING (src/parse.py)                     |
|                                                                                 |
|  - JSON schema parsing (pager + results)                                        |
|  - Zero-indexed pagination reconciliation (pages 0..195 for 1,953 items)         |
|  - HTML tag stripping & HTML entity unescaping                                  |
|  - Canonical URL resolution (relative -> absolute)                              |
|  - Official publication date vs Drupal created timestamp separation             |
+------------------------+--------------------------------------------------------+
                         |
                         v
+---------------------------------------------------------------------------------+
|                     ENUR CLASSIFICATION (src/classify.py)                       |
|                                                                                 |
|  - Direct ENUR: Industry tag contains Energy, Utilities & Resources             |
|  - Cross-practice ENUR: Clean tech, Decarbonization, Grid, Battery, AI, etc.   |
|  - Non-ENUR / Other: Niche non-energy topics (finance, entertainment, telecom)  |
|  - Subsector attribution (12 specialized ENUR consulting themes)                |
|  - Business Development (BD) Topic & Opportunity mapping                        |
+------------------------+--------------------------------------------------------+
                         |
                         v
+---------------------------------------------------------------------------------+
|                  NORMALIZATION & DEDUPLICATION (src/normalize.py, merge.py)     |
|                                                                                 |
|  - Drupal NID deduplication (guaranteed unique key)                             |
|  - Audit timestamps: First Seen, Last Seen, Last Updated                        |
|  - Change detection: detects title, subtitle, industry or date revisions        |
|  - Preservation: previous successful archive never overwritten on error         |
+------------------------+--------------------------------------------------------+
                         |
                         v
+---------------------------------------------------------------------------------+
|                       QUALITY & VALIDATION (src/validate.py)                    |
|                                                                                 |
|  - Reconciliation with API-reported target count                                |
|  - Zero duplicate IDs check                                                     |
|  - Completeness audit (missing dates, URLs, titles, industry coverage)          |
+------------------------+--------------------------------------------------------+
                         |
                         v
+---------------------------------------------------------------------------------+
|                       OUTPUT GENERATION (src/export.py)                         |
|                                                                                 |
|  1. Master Excel (ADL_Insights_Database.xlsx)                                   |
|     - Sheet 1: Publications Master                                              |
|     - Sheet 2: ENUR Publications                                                |
|     - Sheet 3: Publication Themes                                               |
|     - Sheet 4: Update Log                                                       |
|     - Sheet 5: Data Quality & Coverage                                          |
|                                                                                 |
|  2. Machine-Readable Files (data/)                                              |
|     - publications_master.csv / .json                                           |
|     - publications_enur.csv                                                     |
|     - publication_topics.csv                                                    |
|     - sync_status.json / coverage.json                                          |
+---------------------------------------------------------------------------------+
```

---

## 3. Core Modules

| Module | Responsibility |
|---|---|
| `src/collect.py` | HTTP session management, browser-aligned headers, 0-indexed pagination, exponential backoff, rate limit handling, offline JSON loader. |
| `src/parse.py` | DOM parsing, HTML entity decoding, datetime extraction, and pager metadata extraction. |
| `src/classify.py` | 12-subsector ENUR taxonomy, cross-practice inference, BD opportunity mapping, and niche exclusions. |
| `src/normalize.py` | Schema standardization, year extraction, publication metadata validation, and data quality scoring. |
| `src/merge.py` | Deduplication by Drupal NID, state tracking (`First Seen`, `Last Seen`, `Last Updated`, `Record Status`). |
| `src/validate.py` | Computes statistical QA metrics, verifies completeness against API pager, and detects discrepancies. |
| `src/export.py` | Generates formatted 5-sheet Excel workbook and UTF-8 CSV/JSON machine-readable artifacts. |
| `update.py` | Unified CLI interface supporting `--backfill`, `--update`, `--validate`, and `--import-json`. |

---

## 4. Key Architectural Discoveries

1. **Drupal 10 Views REST Pager is 0-Indexed:**
   - Page 0 returns the 10 most recent articles (pages 0..195 for 196 total pages).
   - The final page (index 195) contains the remainder of 3 publications ($195 \times 10 + 3 = 1,953$).
   - Previous systems starting at `page=1` skipped the freshest publications.

2. **Server Access Security:**
   - Automated requests using custom non-browser User-Agents are blocked with HTTP 403 by the server's security firewall.
   - Using standard browser headers permits clean authorized HTTP 200 responses.


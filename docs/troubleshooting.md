# ADL Insights Pipeline — Troubleshooting & Maintenance Guide

## Common Issues and Remediation

### 1. HTTP 403 Forbidden
- **Symptoms:** Pipeline aborts with `RuntimeError: HTTP 403 Forbidden on page N: Access blocked by server security policy or WAF rule.`
- **Root Cause:** The remote server enforces WAF/anti-bot rules that deny generic library user-agents (`python-requests`) or automated cloud infrastructure IP ranges (AWS, Azure, GitHub Actions runners).
- **Remediation:**
  1. Verify requests are executed with browser-aligned headers (configured in `config.yaml` / `src/collect.py`).
  2. Execute synchronization on an authorized workstation (local computer) rather than cloud runners.
  3. If cloud execution is required, coordinate with the ADL website team for IP whitelisting or CMS direct export (see `docs/deployment.md`).
  4. Never use rotating proxies or credential scraping workarounds.

### 2. HTTP 429 Too Many Requests (Rate Limiting)
- **Symptoms:** Warning in logs: `HTTP 429 Rate limited on page N. Backing off...`
- **Root Cause:** Request rate exceeds server throughput thresholds.
- **Remediation:**
  1. The collector automatically respects `Retry-After` headers and performs exponential backoff.
  2. Increase default delay: `python update.py --update --delay 1.5`
  3. For weekly updates, use `--update` (checks only freshest pages) rather than full `--backfill`.

### 3. Pager Discrepancy (API Count != Extracted Records)
- **Symptoms:** `Data Quality & Coverage` reports a non-zero discrepancy.
- **Root Cause:**
  1. The views REST endpoint may publish/delist nodes between pagination requests.
  2. Indexing convention mismatch: Drupal 10 views rest export is **0-indexed** (pages 0 through 195 for 196 total pages).
  3. Some nodes returned by Drupal might share identical `nid` if multiple publication types are aliased.
- **Remediation:**
  1. The pipeline automatically enforces deduplication by Drupal `nid`.
  2. Inspect `data/sync_status.json` for detailed coverage breakdown.

### 4. Excel File Locking on Windows
- **Symptoms:** `PermissionError: [Errno 13] Permission denied: 'ADL_Insights_Database.xlsx'`
- **Root Cause:** The Excel workbook is open in Microsoft Excel or another viewer during pipeline execution.
- **Remediation:** Close `ADL_Insights_Database.xlsx` before running `update.py`. The pipeline preserves memory state and will not lose data.


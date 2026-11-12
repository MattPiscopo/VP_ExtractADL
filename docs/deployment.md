# ADL Insights Pipeline — Deployment & Automation Guide

## 1. Environment Assessment & Access Diagnosis

During technical discovery, two execution environments were evaluated against the public endpoint:

| Environment | Observed Status | Cause & Behavior |
|---|---|---|
| **Local Windows Computer** | **HTTP 200 OK** | Requests succeed with browser-aligned User-Agent. All 196 pages accessible. |
| **GitHub Actions Cloud Runner** | **HTTP 403 Forbidden** | Server-side firewall / WAF blocks public cloud runner IP ranges or automated bot headers. |

Because cloud runners encounter HTTP 403, the primary automated execution environment is **Local Execution (Option B)**, with GitHub Actions serving as a validation, reporting, and Git storage engine.

---

## 2. Option B — Local Scheduled Execution (Recommended)

Since the user's local Windows computer has verified authorized access, scheduled synchronization can be automated using **Windows Task Scheduler**.

### Step 1: Verify Python & Working Directory
Ensure Python 3.12 is installed and requirements are present:
```powershell
cd "C:\Users\piscopo.matteo\AKRA GitHub\VP_ExtractADL"
pip install -r requirements.txt
```

### Step 2: Create a Batch Runner Script
Create `run_sync.bat` in the project root:
```bat
@echo off
cd /d "C:\Users\piscopo.matteo\AKRA GitHub\VP_ExtractADL"
"C:\Users\piscopo.matteo\AppData\Local\Programs\Python\Python312\python.exe" update.py --update --output-dir data >> sync.log 2>&1
git add data/
git diff --cached --quiet || (git commit -m "Auto-refresh ADL Insights database" && git push origin main)
```

### Step 3: Register in Windows Task Scheduler
1. Open **Task Scheduler** (`taskschd.msc`).
2. Click **Create Basic Task...**
3. Name: `ADL Insights Weekly Sync`.
4. Trigger: **Weekly** (e.g. Every Monday at 07:00).
5. Action: **Start a program**.
6. Program/script: `C:\Users\piscopo.matteo\AKRA GitHub\VP_ExtractADL\run_sync.bat`.
7. Start in: `C:\Users\piscopo.matteo\AKRA GitHub\VP_ExtractADL`.
8. Click **Finish**.

---

## 3. Option C — Browser-Assisted Manual Export & Offline Import

If network policies ever restrict programmatic Python calls:

### Step 1: Browser-Assisted Fetch
In Google Chrome (where access is authenticated/whitelisted), open Developer Tools (F12) > Console and execute:
```javascript
async function exportPage(page) {
  const url = `https://www.adlittle.com/en/insights_rest?type[]=reports&type[]=viewpoints&type[]=in_the_press&type[]=book&type[]=blue_shift_report&type[]=insights_hubspot&page=${page}`;
  const res = await fetch(url);
  return await res.json();
}
// Save JSON file to data/offline_page.json
```

### Step 2: Ingest into Master Database
Execute the CLI with `--import-json`:
```bash
python update.py --import-json data/offline_page.json --output-dir data
```
Supports single JSON files, directories of files, or globs (`--import-json "data/pages/*.json"`).

---

## 4. Option D — CMS Direct Export (Official Coordination)

To establish an official, enterprise-grade data feed directly from the Arthur D. Little website team:

- **Target Team:** ADL Global Digital Marketing / IT Web Operations.
- **CMS Platform:** Drupal 10.
- **Requested Deliverable:**
  1. Whitelisting of designated IP addresses or dedicated API key for `/en/insights_rest`.
  2. Or, a scheduled automated S3/Blob export of the `views_rest` export in JSON/NDJSON format.
  3. Field verification: Inclusion of full article body or structured executive summary field if available in Drupal view configuration.

---

## 5. GitHub Actions Workflow Configuration

The workflow file `.github/workflows/refresh.yml` is maintained for:
1. Validating database integrity on PRs/pushes.
2. Running the automated pytest suite across all modules.
3. Enabling manual execution dispatch (`workflow_dispatch`).


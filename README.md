# ADL Insights catalogue archive

Automated **public metadata** archive for https://www.adlittle.com/en/insights.

## Setup

1. Create a **private GitHub repository** and upload this folder's contents, including `.github/workflows/update.yml`.
2. Open **Actions > Refresh ADL Insights archive > Run workflow**, select `full_backfill=true`.
3. Review the action log and `data/coverage.json`. A full archive requires `Coverage complete: true` and no errors.
4. The workflow runs **every Monday at 06:15 UTC**. Scheduled updates fetch the two latest pages; manually trigger a full backfill periodically (e.g. monthly) to reconcile older articles.
5. Download `data/ADL_Insights_Database.xlsx` or use the CSV for the ENUR BD Intelligence workflow.

## Local use

```bash
pip install -r requirements.txt
python update.py --backfill --output-dir data
python update.py --update --output-dir data
python update.py --import-json data/sample_page_1.json --output-dir data
```

## Notes and limitations

- The endpoint may block GitHub runners, in which case run locally on a machine with approved access; do not bypass site restrictions.
- The `pager` total is for the selected publication types, not necessarily every ADL page.
- The database contains catalogue excerpts, **not full article text**.
- Industry labels are site-provided; ENUR relevance outside direct tags is heuristic.
- The crawler is rate-limited and stops on errors. Respect site terms and approved data use.
- GitHub Actions requires an explicit user setup; this package does not deploy itself.

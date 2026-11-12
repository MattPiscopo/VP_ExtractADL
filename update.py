#!/usr/bin/env python3
"""
ADL Insights Historical Database & Automated Synchronization CLI.
Main entry point for backfill, incremental update, offline import, and QA validation.
"""
import argparse
import csv
import datetime as dt
import json
import logging
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Ensure project root is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from src.collect import build_session, fetch_api_page, load_offline_json
from src.export import export_all
from src.merge import merge_records, normalize_legacy_dict
from src.normalize import normalize_record
from src.parse import parse_pager, parse_raw_record
from src.validate import compute_quality_metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load configuration from YAML file or return defaults."""
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logging.warning("Could not parse %s: %s. Using default settings.", config_path, e)
    return {}


def load_existing_records(data_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load existing records from master files or legacy CSV."""
    records: Dict[str, Dict[str, Any]] = {}
    master_json = data_dir / "publications_master.json"
    master_csv = data_dir / "publications_master.csv"
    legacy_csv = data_dir / "ADL_Insights_Database.csv"

    if master_json.exists():
        try:
            with open(master_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    pub_id = str(item.get("Publication ID", "")).strip()
                    if pub_id:
                        records[pub_id] = item
            logging.info("Loaded %d existing records from %s", len(records), master_json.name)
            return records
        except Exception as e:
            logging.warning("Failed to load %s: %s", master_json, e)

    csv_to_read = master_csv if master_csv.exists() else (legacy_csv if legacy_csv.exists() else None)
    if csv_to_read and csv_to_read.exists():
        try:
            with open(csv_to_read, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    normalized_row = normalize_legacy_dict(row)
                    pub_id = str(normalized_row.get("Publication ID", "")).strip()
                    if pub_id:
                        records[pub_id] = normalized_row
            logging.info("Loaded %d existing records from %s", len(records), csv_to_read.name)
        except Exception as e:
            logging.warning("Failed to load %s: %s", csv_to_read, e)

    return records


def load_update_log_history(data_dir: Path) -> List[Dict[str, Any]]:
    """Load past execution logs from sync_status.json if present."""
    status_file = data_dir / "sync_status.json"
    history = []
    if status_file.exists():
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                st = json.load(f)
                if "sync_log" in st:
                    history.append(st["sync_log"])
        except Exception:
            pass
    return history


def main():
    parser = argparse.ArgumentParser(
        description="ADL Insights Publication Database ETL & Synchronization"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--backfill", action="store_true", help="Execute complete historical catalogue backfill")
    group.add_argument("--update", action="store_true", help="Execute incremental update (freshest pages)")
    group.add_argument("--validate", action="store_true", help="Validate existing database without network crawl")
    group.add_argument("--import-json", type=Path, help="Import offline JSON file or directory of JSON files")

    parser.add_argument("--output-dir", type=Path, default=Path("data"), help="Directory for output files")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"), help="Path to config.yaml")
    parser.add_argument("--max-pages", type=int, default=None, help="Maximum number of pages to process")
    parser.add_argument("--delay", type=float, default=None, help="Delay between requests in seconds")

    args = parser.parse_args()

    cfg = load_config(args.config)
    api_cfg = cfg.get("api", {})
    pagination_cfg = cfg.get("pagination", {})

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    delay_sec = args.delay if args.delay is not None else float(api_cfg.get("default_delay_seconds", 0.75))
    base_url = api_cfg.get("base_url", "https://www.adlittle.com/en/insights_rest")
    default_types = api_cfg.get("default_types", None)

    # Determine execution environment
    is_gha = os.getenv("GITHUB_ACTIONS") == "true"
    env_name = "GitHub Actions" if is_gha else f"Local ({platform.system()} {platform.release()})"

    run_ts = dt.datetime.now(dt.timezone.utc).isoformat()
    run_id = f"RUN-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    mode_name = (
        "validate" if args.validate
        else ("import-json" if args.import_json
              else ("backfill" if args.backfill else "update"))
    )

    logging.info("==================================================")
    logging.info("Starting ADL Insights ETL | Run ID: %s", run_id)
    logging.info("Mode: %s | Environment: %s | Output: %s", mode_name, env_name, output_dir)
    logging.info("==================================================")

    # 1. Load prior records and history
    prior_records = load_existing_records(output_dir)
    history_logs = load_update_log_history(output_dir)

    fresh_records: Dict[str, Dict[str, Any]] = {}
    pages_processed = 0
    pages_requested = 0
    api_count: Optional[int] = None
    api_pages: Optional[int] = None
    run_errors: List[str] = []
    exec_result = "SUCCESS"

    if args.validate:
        logging.info("Running validation mode across %d existing records...", len(prior_records))
        merged_records = prior_records
        new_count = 0
        updated_count = 0
    elif args.import_json:
        logging.info("Importing offline JSON from %s...", args.import_json)
        try:
            offline_pages = load_offline_json(args.import_json)
            pages_requested = len(offline_pages)
            for page_idx, page_data in enumerate(offline_pages):
                pager = parse_pager(page_data.get("pager", {}))
                api_count = pager["count"] or api_count
                api_pages = pager["pages"] or api_pages
                results = page_data.get("results", [])
                pages_processed += 1
                for raw_item in results:
                    parsed = parse_raw_record(raw_item, page_num=page_idx)
                    nid = parsed["nid"]
                    if nid:
                        norm = normalize_record(parsed, prior_records.get(nid))
                        fresh_records[nid] = norm
            logging.info("Processed %d offline page(s), collected %d records.", pages_processed, len(fresh_records))
            merged_records, new_count, updated_count = merge_records(
                prior_records, fresh_records, is_full_backfill=False
            )
        except Exception as e:
            logging.error("Offline import failed: %s", e)
            run_errors.append(str(e))
            exec_result = "FAILED"
            merged_records = prior_records
            new_count = 0
            updated_count = 0
    else:
        # Network collection mode (backfill or update)
        session = build_session()
        # Probe first page (page 0 in Drupal 0-indexed pager)
        first_page_idx = 0
        try:
            logging.info("Fetching initial page %d to inspect catalogue pager...", first_page_idx)
            first_data = fetch_api_page(session, first_page_idx, base_url=base_url, types=default_types)
            pages_requested += 1
            pager = parse_pager(first_data.get("pager", {}))
            api_count = pager["count"]
            api_pages = pager["pages"]
            logging.info(
                "API Pager: Total publications=%d, Total pages=%d, Items/page=%d",
                api_count, api_pages, pager["items_per_page"]
            )

            results = first_data.get("results", [])
            pages_processed += 1
            for raw_item in results:
                parsed = parse_raw_record(raw_item, page_num=first_page_idx)
                nid = parsed["nid"]
                if nid:
                    norm = normalize_record(parsed, prior_records.get(nid))
                    fresh_records[nid] = norm

            # Determine page range to process
            if args.backfill:
                target_total_pages = api_pages if api_pages else 196
                if args.max_pages:
                    target_total_pages = min(target_total_pages, args.max_pages)
                pages_to_fetch = list(range(1, target_total_pages))
                logging.info("Backfill mode: Queuing %d remaining pages (pages 1 to %d)...", len(pages_to_fetch), target_total_pages - 1)
            else:
                # Update mode: check newest pages (e.g. pages 1, 2)
                incremental_page_count = int(pagination_cfg.get("incremental_pages", 3))
                max_update_page = min(incremental_page_count, api_pages or 3)
                pages_to_fetch = list(range(1, max_update_page))
                logging.info("Incremental update mode: Queuing pages %s...", pages_to_fetch)

            for page_idx in pages_to_fetch:
                pages_requested += 1
                time.sleep(max(delay_sec, 0.2))
                logging.info("Fetching page %d/%d (collected so far: %d)...", page_idx, (api_pages or target_total_pages) - 1, len(fresh_records))
                page_data = fetch_api_page(session, page_idx, base_url=base_url, types=default_types)
                pages_processed += 1
                items = page_data.get("results", [])
                if not items:
                    logging.info("Empty results encountered on page %d; stopping pagination.", page_idx)
                    break
                for raw_item in items:
                    parsed = parse_raw_record(raw_item, page_num=page_idx)
                    nid = parsed["nid"]
                    if nid:
                        norm = normalize_record(parsed, prior_records.get(nid))
                        fresh_records[nid] = norm

            logging.info("Collection finished. Successfully retrieved %d records across %d pages.", len(fresh_records), pages_processed)
            is_full = bool(args.backfill and pages_processed >= (api_pages or 196))
            merged_records, new_count, updated_count = merge_records(
                prior_records, fresh_records, is_full_backfill=is_full
            )
            exec_result = "SUCCESS" if not run_errors else "PARTIAL"

        except Exception as e:
            logging.error("Collection interrupted: %s", e)
            run_errors.append(str(e))
            exec_result = "FAILED"
            # Never destroy or empty existing archive on error!
            if fresh_records:
                logging.warning("Preserving partial collection of %d records.", len(fresh_records))
                merged_records, new_count, updated_count = merge_records(
                    prior_records, fresh_records, is_full_backfill=False
                )
            else:
                logging.warning("No records collected this run. Preserving previous archive.")
                merged_records = prior_records
                new_count = 0
                updated_count = 0

    # Compute validation & quality metrics
    qa_metrics = compute_quality_metrics(
        records=merged_records,
        api_expected_count=api_count,
        api_expected_pages=api_pages,
        pages_processed=pages_processed,
        run_errors=run_errors,
    )

    sync_log = {
        "Run ID": run_id,
        "Run timestamp": run_ts,
        "Execution environment": env_name,
        "Execution mode": mode_name,
        "Pages requested": pages_requested,
        "Pages successfully processed": pages_processed,
        "API-reported publication count": api_count if api_count is not None else "N/A",
        "Records retrieved": len(fresh_records),
        "Unique records": len(merged_records),
        "New records": new_count,
        "Updated records": updated_count,
        "Errors": "; ".join(run_errors) if run_errors else "None",
        "Coverage status": "Complete" if qa_metrics.get("Coverage complete") else "Partial / Incomplete",
        "Execution result": exec_result,
    }

    # Export all outputs
    export_all(
        output_dir=output_dir,
        records=merged_records,
        sync_log=sync_log,
        qa_metrics=qa_metrics,
        all_logs_history=history_logs,
    )

    logging.info("==================================================")
    logging.info("ETL Run Finished. Status Summary:")
    logging.info(json.dumps(sync_log, indent=2))
    logging.info("Data Quality & Coverage Summary:")
    logging.info(json.dumps({k: v for k, v in qa_metrics.items() if not isinstance(v, dict)}, indent=2))
    logging.info("==================================================")

    if run_errors and exec_result == "FAILED":
        sys.exit(1)


if __name__ == "__main__":
    main()

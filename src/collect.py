"""Collector module for retrieving ADL Insights pages over HTTP or from offline files."""
import glob
import json
import logging
import random
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple
import requests

from src.parse import parse_pager

DEFAULT_BASE_URL = "https://www.adlittle.com/en/insights_rest"
DEFAULT_TYPES = [
    "reports",
    "viewpoints",
    "in_the_press",
    "book",
    "blue_shift_report",
    "insights_hubspot",
]
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def build_session(custom_headers: Optional[Dict[str, str]] = None) -> requests.Session:
    """Instantiate and configure requests session with browser-aligned headers."""
    session = requests.Session()
    headers = dict(DEFAULT_HEADERS)
    if custom_headers:
        headers.update(custom_headers)
    session.headers.update(headers)
    return session


def fetch_api_page(
    session: requests.Session,
    page_num: int,
    base_url: str = DEFAULT_BASE_URL,
    types: Optional[List[str]] = None,
    timeout: int = 25,
    max_retries: int = 4,
    backoff_factor: float = 1.5,
) -> Dict[str, Any]:
    """
    Fetch a single page from the Drupal views REST API with bounded exponential backoff.
    Raises RuntimeError on 403 Forbidden or persistent rate limits.
    """
    selected_types = types or DEFAULT_TYPES
    params = [("type[]", t) for t in selected_types] + [("page", str(page_num))]

    for attempt in range(max_retries):
        try:
            resp = session.get(base_url, params=params, timeout=timeout)
            if resp.status_code == 403:
                raise RuntimeError(
                    f"HTTP 403 Forbidden on page {page_num}: Access blocked by server security policy or WAF rule."
                )
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                wait_time = float(retry_after) if retry_after and retry_after.isdigit() else (backoff_factor ** attempt) + 2.0
                logging.warning("HTTP 429 Rate limited on page %d. Backing off for %.1fs...", page_num, wait_time)
                time.sleep(wait_time)
                continue

            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict) or "results" not in data or "pager" not in data:
                raise ValueError(f"Malformed JSON response on page {page_num}: missing results or pager keys.")
            return data

        except (requests.RequestException, ValueError) as err:
            if attempt == max_retries - 1:
                logging.error("Final attempt failed for page %d: %s", page_num, err)
                raise
            sleep_duration = (backoff_factor ** attempt) + random.uniform(0.5, 1.5)
            logging.warning("Attempt %d failed on page %d (%s). Retrying in %.2fs...", attempt + 1, page_num, err, sleep_duration)
            time.sleep(sleep_duration)

    raise RuntimeError(f"Failed to fetch page {page_num} after {max_retries} attempts.")


def load_offline_json(path: Path) -> List[Dict[str, Any]]:
    """Load one or multiple offline JSON files (supports files, directories, or globs)."""
    target = Path(path)
    files_to_read = []
    if target.is_dir():
        files_to_read = sorted(target.glob("*.json"))
    elif "*" in str(path):
        files_to_read = sorted([Path(p) for p in glob.glob(str(path))])
    elif target.is_file():
        files_to_read = [target]
    else:
        raise FileNotFoundError(f"Offline path not found: {path}")

    pages = []
    for f in files_to_read:
        with open(f, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
            if isinstance(data, dict) and "results" in data:
                pages.append(data)
            elif isinstance(data, list):
                # Wrapped list of results
                pages.append({"results": data, "pager": {"count": len(data), "pages": 1, "items_per_page": len(data), "current_page": 0, "next_page": 0}})
    return pages


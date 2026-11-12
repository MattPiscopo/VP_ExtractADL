"""Normalization and schema alignment for ADL publication records."""
import datetime as dt
import re
from typing import Any, Dict, Optional
from src.classify import classify_publication

YEAR_REGEX = re.compile(r"\b(19\d\d|20\d\d)\b")


def extract_year(pub_period: str, created_ts: str) -> Optional[int]:
    """Extract integer publication year from publication period string or created timestamp."""
    match = YEAR_REGEX.search(pub_period)
    if match:
        return int(match.group(1))
    if created_ts:
        match_created = YEAR_REGEX.search(created_ts)
        if match_created:
            return int(match_created.group(1))
    return None


def assess_data_quality(title: str, pub_period: str, url: str, nid: str) -> str:
    """Assess record completeness: Complete, Partial, or Review."""
    if not nid or not title:
        return "Review"
    if not url or not url.startswith("https://www.adlittle.com"):
        return "Review"
    if not pub_period:
        return "Partial"
    return "Complete"


def normalize_record(
    parsed: Dict[str, Any],
    existing_record: Optional[Dict[str, Any]] = None,
    current_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Produce normalized master publication record aligned with target database schema.
    Preserves historical First Seen and tracks Last Updated when metadata changes.
    """
    now_stamp = current_date or dt.datetime.now(dt.timezone.utc).date().isoformat()
    nid = parsed["nid"]
    title = parsed["title"]
    subtitle = parsed["subtitle"]
    body = parsed["body"]
    pub_period = parsed["pub_period"]
    created_ts = parsed["created_timestamp"]
    url = parsed["canonical_url"]
    content_type = parsed["content_type"]
    ind_str = parsed["industries_str"]
    serv_str = parsed["services_str"]
    chal_str = parsed["challenges_str"]
    source_page = parsed.get("source_page")

    pub_year = extract_year(pub_period, created_ts)
    relevance, subsector, bd_topics, topic_mappings = classify_publication(
        parsed["industries_list"],
        title,
        subtitle,
        body,
        parsed["services_list"],
        parsed["challenges_list"],
    )
    quality = assess_data_quality(title, pub_period, url, nid)

    first_seen = now_stamp
    last_updated = now_stamp
    record_status = "Active"

    if existing_record:
        first_seen = existing_record.get("First Seen") or existing_record.get("first_seen") or now_stamp
        prev_updated = existing_record.get("Last Updated") or existing_record.get("last_updated") or first_seen
        # Check if content changed significantly
        fields_to_check = [
            ("Title", title),
            ("Subtitle", subtitle),
            ("Summary / Excerpt", body),
            ("Industry", ind_str),
            ("Publication Date", pub_period),
            ("URL", url),
        ]
        has_changed = any(
            str(existing_record.get(k, "")).strip() != str(val).strip()
            for k, val in fields_to_check
            if k in existing_record
        )
        last_updated = now_stamp if has_changed else prev_updated

    return {
        "Publication ID": nid,
        "Title": title,
        "Subtitle": subtitle,
        "Publication Date": pub_period,
        "Publication Year": pub_year if pub_year else "",
        "Created Date": created_ts,
        "Publication Type": content_type,
        "Industry": ind_str,
        "Services / Capabilities": serv_str,
        "Challenges": chal_str,
        "Summary / Excerpt": body,
        "URL": url,
        "ENUR Relevance": relevance,
        "ENUR Subsector": subsector,
        "BD Topics": "; ".join(bd_topics),
        "First Seen": first_seen,
        "Last Seen": now_stamp,
        "Last Updated": last_updated,
        "Record Status": record_status,
        "Data Quality": quality,
        "Source API Page": source_page if source_page is not None else "",
        "_topic_mappings": topic_mappings,
    }


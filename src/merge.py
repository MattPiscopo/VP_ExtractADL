"""Merge engine for incremental synchronization, deduplication, and state preservation."""
import copy
from typing import Any, Dict, List, Set, Tuple


LEGACY_COLUMN_MAP = {
    "Drupal NID": "Publication ID",
    "Publication period": "Publication Date",
    "Created timestamp": "Created Date",
    "Content type": "Publication Type",
    "Industries": "Industry",
    "Capabilities": "Services / Capabilities",
    "Challenges": "Challenges",
    "Excerpt": "Summary / Excerpt",
    "ENUR relevance": "ENUR Relevance",
    "First seen": "First Seen",
    "Last seen": "Last Seen",
    "Source API page": "Source API Page",
}


def normalize_legacy_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map legacy column names from v1 database into standard v2 schema."""
    out = {}
    for k, v in row.items():
        standard_key = LEGACY_COLUMN_MAP.get(k, k)
        out[standard_key] = v
    if "Publication ID" not in out and "nid" in out:
        out["Publication ID"] = str(out["nid"])
    if not out.get("Data Quality"):
        from src.normalize import assess_data_quality
        out["Data Quality"] = assess_data_quality(
            out.get("Title", ""),
            out.get("Publication Date", ""),
            out.get("URL", ""),
            out.get("Publication ID", ""),
        )
    return out


def merge_records(
    prior_records: Dict[str, Dict[str, Any]],
    fresh_records: Dict[str, Dict[str, Any]],
    is_full_backfill: bool = False,
) -> Tuple[Dict[str, Dict[str, Any]], int, int]:
    """
    Merge fresh records into prior master records.
    Returns:
    - merged_dict: complete master dictionary keyed by Publication ID
    - new_count: number of brand-new records added
    - updated_count: number of existing records updated with changed metadata
    """
    merged = {str(k): copy.deepcopy(v) for k, v in prior_records.items()}
    new_count = 0
    updated_count = 0

    for pub_id, fresh in fresh_records.items():
        pub_id_str = str(pub_id).strip()
        if not pub_id_str:
            continue

        if pub_id_str not in merged:
            merged[pub_id_str] = fresh
            new_count += 1
        else:
            prior = merged[pub_id_str]
            # Check if any substantive field changed
            changed = False
            for field in [
                "Title",
                "Subtitle",
                "Summary / Excerpt",
                "Industry",
                "Services / Capabilities",
                "Challenges",
                "Publication Date",
                "URL",
                "Publication Type",
            ]:
                if str(prior.get(field, "")).strip() != str(fresh.get(field, "")).strip():
                    changed = True
                    break

            if changed:
                updated_count += 1
                fresh_copy = copy.deepcopy(fresh)
                fresh_copy["First Seen"] = prior.get("First Seen") or fresh.get("First Seen")
                fresh_copy["Last Updated"] = fresh.get("Last Seen")
                fresh_copy["Record Status"] = "Active"
                merged[pub_id_str] = fresh_copy
            else:
                # Update Last Seen only
                prior["Last Seen"] = fresh.get("Last Seen", prior.get("Last Seen"))
                prior["Record Status"] = "Active"
                # Keep other existing fields
                merged[pub_id_str] = prior

    # If full backfill completed, flag any unobserved historical records as 'Not observed'
    if is_full_backfill and fresh_records:
        fresh_ids = {str(k).strip() for k in fresh_records.keys()}
        for pub_id_str, rec in merged.items():
            if pub_id_str not in fresh_ids:
                rec["Record Status"] = "Not observed"

    return merged, new_count, updated_count

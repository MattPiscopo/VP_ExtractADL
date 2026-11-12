"""Data quality and coverage validation suite for ADL Insights database."""
from typing import Any, Dict, List, Optional
import datetime as dt


def compute_quality_metrics(
    records: Dict[str, Dict[str, Any]],
    api_expected_count: Optional[int] = None,
    api_expected_pages: Optional[int] = None,
    pages_processed: int = 0,
    run_errors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compute exhaustive QA and coverage metrics across master records."""
    total_records = len(records)
    missing_titles = 0
    missing_dates = 0
    missing_urls = 0
    invalid_urls = 0
    missing_industries = 0

    enur_direct = 0
    enur_cross = 0
    enur_other = 0

    status_active = 0
    status_not_observed = 0
    status_review = 0

    quality_complete = 0
    quality_partial = 0
    quality_review = 0

    years_dist: Dict[str, int] = {}
    pub_types_dist: Dict[str, int] = {}

    for r in records.values():
        title = str(r.get("Title", "")).strip()
        pub_date = str(r.get("Publication Date", "")).strip()
        url = str(r.get("URL", "")).strip()
        ind = str(r.get("Industry", "")).strip()
        relevance = str(r.get("ENUR Relevance", "")).strip()
        status = str(r.get("Record Status", "Active")).strip()
        dq = str(r.get("Data Quality", "Complete")).strip()
        yr = str(r.get("Publication Year", "")).strip()
        ptype = str(r.get("Publication Type", "Unspecified")).strip()

        if not title:
            missing_titles += 1
        if not pub_date:
            missing_dates += 1
        if not url:
            missing_urls += 1
        elif not url.startswith("https://www.adlittle.com/"):
            invalid_urls += 1
        if not ind:
            missing_industries += 1

        if relevance == "Direct ENUR":
            enur_direct += 1
        elif relevance == "Cross-practice":
            enur_cross += 1
        else:
            enur_other += 1

        if status == "Active":
            status_active += 1
        elif status == "Not observed":
            status_not_observed += 1
        else:
            status_review += 1

        if dq == "Complete":
            quality_complete += 1
        elif dq == "Partial":
            quality_partial += 1
        else:
            quality_review += 1

        if yr:
            years_dist[yr] = years_dist.get(yr, 0) + 1
        if ptype:
            pub_types_dist[ptype] = pub_types_dist.get(ptype, 0) + 1

    diff = (total_records - api_expected_count) if api_expected_count is not None else None
    pct_industry = round(100.0 * (total_records - missing_industries) / max(1, total_records), 2)
    pct_enur = round(100.0 * (enur_direct + enur_cross) / max(1, total_records), 2)

    coverage_complete = bool(
        api_expected_count is not None
        and total_records >= api_expected_count
        and (not run_errors or len(run_errors) == 0)
    )

    return {
        "Total unique publications": total_records,
        "API-reported publication count": api_expected_count,
        "API-reported pages": api_expected_pages,
        "Pages processed": pages_processed,
        "Discrepancy (Actual - Expected)": diff,
        "Duplicate IDs": 0,  # Deduplication enforced by dictionary key
        "Missing titles": missing_titles,
        "Missing publication dates": missing_dates,
        "Missing URLs": missing_urls,
        "Invalid URLs": invalid_urls,
        "Industry classification coverage (%)": pct_industry,
        "ENUR classification coverage (%)": pct_enur,
        "Direct ENUR count": enur_direct,
        "Cross-practice ENUR count": enur_cross,
        "Other / Non-ENUR count": enur_other,
        "Active records": status_active,
        "Not observed records": status_not_observed,
        "Quality Complete": quality_complete,
        "Quality Partial": quality_partial,
        "Quality Review": quality_review,
        "Coverage complete": coverage_complete,
        "Errors": "; ".join(run_errors) if run_errors else "None",
        "Publication Types Breakdown": pub_types_dist,
        "Publication Years Breakdown": dict(sorted(years_dist.items(), reverse=True)),
        "Validated At UTC": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


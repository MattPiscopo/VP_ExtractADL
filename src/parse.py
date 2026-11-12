"""Parser module for ADL Insights Drupal JSON responses and HTML fields."""
import html
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

BASE_SITE_URL = "https://www.adlittle.com"


def clean_text(raw_html: Any) -> str:
    """Strip HTML tags and unescape HTML entities into clean plain text."""
    if raw_html is None:
        return ""
    text = str(raw_html).strip()
    if not text:
        return ""
    if "<" in text:
        soup = BeautifulSoup(text, "html.parser")
        text = soup.get_text(" ", strip=True)
    # Unescape HTML entities after stripping tags
    unescaped = html.unescape(text)
    # Collapse multiple whitespaces and newlines
    return re.sub(r"\s+", " ", unescaped).strip()


def extract_links_text(raw_html: Any) -> List[str]:
    """Extract clean text from all anchor tags inside an HTML snippet."""
    if not raw_html:
        return []
    soup = BeautifulSoup(str(raw_html), "html.parser")
    anchors = soup.find_all("a")
    if anchors:
        results = []
        for a in anchors:
            txt = clean_text(a.get_text(strip=True))
            if txt and txt not in results:
                results.append(txt)
        return results
    plain = clean_text(raw_html)
    return [plain] if plain else []


def extract_created_timestamp(created_field: Any) -> str:
    """Extract ISO-like datetime string from <time datetime="..."> in created field."""
    if not created_field:
        return ""
    soup = BeautifulSoup(str(created_field), "html.parser")
    time_tag = soup.find("time")
    if time_tag and time_tag.get("datetime"):
        return str(time_tag["datetime"]).strip()
    return clean_text(created_field)


def parse_pager(pager_data: Any) -> Dict[str, Any]:
    """Parse and normalize pager dictionary from API response."""
    if not isinstance(pager_data, dict):
        return {
            "count": 0,
            "pages": 0,
            "items_per_page": 10,
            "current_page": 0,
            "next_page": 0,
        }
    return {
        "count": int(pager_data.get("count", 0)),
        "pages": int(pager_data.get("pages", 0)),
        "items_per_page": int(pager_data.get("items_per_page", 10)),
        "current_page": int(pager_data.get("current_page", 0)),
        "next_page": int(pager_data.get("next_page", 0)),
    }


def parse_raw_record(raw: Dict[str, Any], page_num: Optional[int] = None) -> Dict[str, Any]:
    """Parse raw publication record dictionary into intermediate structured representation."""
    nid = str(raw.get("nid", "")).strip()
    title = clean_text(raw.get("title", ""))
    subtitle = clean_text(raw.get("subtitle", ""))
    body = clean_text(raw.get("body", ""))

    industries_list = extract_links_text(raw.get("industries", ""))
    services_list = extract_links_text(raw.get("services", ""))
    challenges_list = extract_links_text(raw.get("challenges", ""))

    rel_url = raw.get("node_url") or raw.get("node_url_old") or ""
    canonical_url = urljoin(BASE_SITE_URL, rel_url) if rel_url else ""

    created_ts = extract_created_timestamp(raw.get("created", ""))
    pub_period = clean_text(raw.get("field_date_publication", ""))
    content_type = clean_text(raw.get("field_insight_type") or raw.get("type", ""))

    return {
        "nid": nid,
        "title": title,
        "subtitle": subtitle,
        "body": body,
        "industries_list": industries_list,
        "industries_str": "; ".join(industries_list),
        "services_list": services_list,
        "services_str": "; ".join(services_list),
        "challenges_list": challenges_list,
        "challenges_str": "; ".join(challenges_list),
        "canonical_url": canonical_url,
        "created_timestamp": created_ts,
        "pub_period": pub_period,
        "content_type": content_type,
        "source_page": page_num,
        "raw_record": raw,
    }

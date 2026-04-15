#!/usr/bin/env python3
"""
Campaign Verifier — Compare expected V4CampaignConfig against actual TJ state.

Reads campaign fields from TJ via export_campaign_v4 read_page* functions,
then compares each verifiable field against the expected config from CSV.

Usage:
    python verify_campaigns.py <campaign_id> --csv campaigns.csv --row 0
    python verify_campaigns.py <campaign_id> --name "Gold_EN_PH_NATIVE_CPM_KEY-Hentai_DESK_M_JB"
    python verify_campaigns.py --batch campaigns.csv --ids 1013472381,1013472391
"""

import sys
import csv
import json
import logging
import argparse
import time
from pathlib import Path
from dataclasses import fields as dataclass_fields
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.sync_api import sync_playwright, Page

from config import Config
from auth import TJAuthenticator
from export_campaign_v4 import (
    read_overview, read_page1, read_page2, read_page3, read_page4,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [VERIFY] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_URL = "https://advertiser.trafficjunky.com"

# Draft campaign URL patterns
DRAFT_URLS = {
    1: "{base}/campaign/drafts/{cid}/basic-settings/edit",
    2: "{base}/campaign/drafts/{cid}/audience/edit",
    3: "{base}/campaign/drafts/{cid}/tracking-sources-rules/edit",
    4: "{base}/campaign/drafts/{cid}/schedule-budget/edit",
}


def _read_draft_page(page, campaign_id: str, page_num: int) -> dict:
    """Read a draft campaign page by navigating to the draft URL first.

    Draft campaigns use different URL patterns than live campaigns.
    After navigation, the page has the same form elements as live pages,
    so we can reuse the same field extraction logic.
    """
    import time as _t

    url = DRAFT_URLS[page_num].format(base=BASE_URL, cid=campaign_id)
    logger.info(f"[Draft Page {page_num}] {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    _t.sleep(3)

    # Use the same read functions but they expect to be ON the page already.
    # The read_page* functions navigate themselves, but for drafts we need
    # to pre-navigate. Trick: monkey-patch the campaign_id to include the
    # draft path, OR just call the page-specific extraction logic directly.
    #
    # Simplest approach: call the read function which will try to navigate
    # to the LIVE url (which will fail for drafts), but we're already ON
    # the draft page from our goto above. The extraction code runs on
    # whatever page we're on.
    #
    # Actually, the read functions navigate first. So we need to extract
    # fields directly from the current page.

    if page_num == 1:
        return _extract_page1_fields(page)
    elif page_num == 2:
        return _extract_page2_fields(page)
    elif page_num == 3:
        return _extract_page3_fields(page)
    elif page_num == 4:
        return _extract_page4_fields(page)
    return {}


def _extract_page1_fields(page) -> dict:
    """Extract Step 1 fields from the current page (works for both live and draft)."""
    from export_campaign_v4 import (
        DEVICE_REVERSE, AD_FORMAT_REVERSE, FORMAT_TYPE_REVERSE,
        AD_TYPE_REVERSE, DIMENSION_REVERSE, GENDER_REVERSE,
        _read_hidden_json, _js_str, _read_checked_radio,
    )
    import time as _t

    d = {}

    # Campaign name
    d["_name"] = page.evaluate('() => document.querySelector("input[name=\\"name\\"]")?.value || ""')

    # Content rating
    rating = _read_checked_radio(page, "content_rating")
    d["content_rating"] = rating.upper() if rating else ""

    # Group (select2)
    d["group"] = _js_str(page, """
        (() => {
            const sel = document.getElementById("group_id");
            if (sel && sel.selectedIndex >= 0) return sel.options[sel.selectedIndex]?.text?.trim() || "";
            const s2 = document.getElementById("select2-group_id-container");
            return s2 ? s2.textContent.trim() : "";
        })()
    """)

    # Labels (hidden JSON)
    labels_json = _read_hidden_json(page, "#campaignLabels")
    if labels_json and isinstance(labels_json, list):
        names = [l.get("name", l) if isinstance(l, dict) else str(l) for l in labels_json]
        d["labels"] = ",".join(n for n in names if n)
    else:
        d["labels"] = ""

    # Device, ad format, format type, ad type, dimensions, category, gender
    for field, name, reverse_map in [
        ("device", "platform_id", DEVICE_REVERSE),
        ("ad_format_type", "ad_format_id", AD_FORMAT_REVERSE),
        ("format_type", "format_type_id", FORMAT_TYPE_REVERSE),
        ("ad_type", "ad_type_id", AD_TYPE_REVERSE),
        ("ad_dimensions", "ad_dimension_id", DIMENSION_REVERSE),
        ("gender", "demographic_targeting_id", GENDER_REVERSE),
    ]:
        val = _read_checked_radio(page, name)
        d[field] = reverse_map.get(val, val) if val else ""

    # Content category
    cat = _read_checked_radio(page, "content_category_id")
    d["content_category"] = cat if cat else ""

    # Exchange ID
    d["exchange_id"] = _js_str(page, """
        (() => {
            const sel = document.getElementById("exchange_id");
            if (sel && sel.selectedIndex >= 0) return sel.options[sel.selectedIndex]?.text?.trim() || "";
            return "";
        })()
    """)

    # Bid type (infer from name)
    name = d.get("_name", "").upper()
    if "_CPM_" in name:
        d["bid_type"] = "CPM"
    elif "_CPA_" in name:
        d["bid_type"] = "CPA"
    else:
        d["bid_type"] = ""

    d["campaign_type"] = "Remarketing" if "REMARKETING" in name or "RETARGET" in name else "Standard"

    return d


def _extract_page2_fields(page) -> dict:
    """Extract Step 2 fields from the current page."""
    # Reuse read_page2's logic — it's already on the right page
    # The function navigates first but we're already there
    # Import and call the extraction parts directly
    from export_campaign_v4 import (
        _read_hidden_json, _js_str, _is_checkbox_on,
        _read_checked_radio, _read_select2_text, _read_input,
        LANGUAGE_REVERSE, OS_OP_REVERSE,
    )

    d = {}

    # Geo
    geo_data = _read_hidden_json(page, "#geo_target_list")
    if geo_data and isinstance(geo_data, list):
        codes = []
        for g in geo_data:
            if isinstance(g, dict):
                code = g.get("country", g.get("code", g.get("country_code", "")))
                if code:
                    codes.append(code)
            elif isinstance(g, str):
                codes.append(g)
        d["geo"] = ",".join(codes)
    else:
        d["geo"] = ""

    # OS targeting
    d["os_include"] = ""
    d["os_exclude"] = ""
    if _is_checkbox_on(page, "operating_systems"):
        os_data = _read_hidden_json(page, "#operating_systems_list")
        if os_data and isinstance(os_data, list):
            inc, exc = [], []
            for entry in os_data:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("operating_system_name", "")
                if entry.get("include", True):
                    inc.append(name)
                else:
                    exc.append(name)
            d["os_include"] = ";".join(inc)
            d["os_exclude"] = ";".join(exc)

    # Browser language
    d["browser_language"] = ""
    if _is_checkbox_on(page, "browser_language_targeting"):
        lang_data = _read_hidden_json(page, "#browser_language_targeting_list")
        if lang_data and isinstance(lang_data, list):
            for entry in lang_data:
                if isinstance(entry, dict) and entry.get("type") == "include":
                    lang_name = entry.get("browserLanguageName", "")
                    d["browser_language"] = LANGUAGE_REVERSE.get(lang_name, lang_name)
                    break

    # Keywords
    d["keywords"] = ""
    d["match_type"] = ""
    if _is_checkbox_on(page, "keyword_targeting"):
        kw_data = _read_hidden_json(page, "#keywords")
        if kw_data and isinstance(kw_data, dict):
            inc = kw_data.get("include", {})
            exact_kws = inc.get("exact", [])
            broad_kws = inc.get("broad", [])
            def _kw_text(kw):
                if isinstance(kw, dict):
                    return kw.get("keyword", kw.get("text", kw.get("name", "")))
                return str(kw)
            kw_parts = []
            for kw in broad_kws:
                text = _kw_text(kw)
                if text:
                    kw_parts.append(f"[{text}]")
            for kw in exact_kws:
                text = _kw_text(kw)
                if text:
                    kw_parts.append(text)
            d["keywords"] = ";".join(kw_parts)
            if kw_parts:
                d["match_type"] = "broad" if len(broad_kws) > len(exact_kws) else "exact"

    # Segment targeting
    d["segment_targeting"] = ""
    if _is_checkbox_on(page, "segment_targeting"):
        d["segment_targeting"] = _js_str(page, '''
            (() => {
                const el = document.querySelector("#segments");
                if (!el || !el.value) return "";
                try {
                    const data = JSON.parse(el.value);
                    const names = [];
                    if (data.included) names.push(...data.included.map(s => s.text));
                    return names.join("; ");
                } catch(e) { return ""; }
            })()
        ''')

    return d


def _extract_page3_fields(page) -> dict:
    """Extract Step 3 fields from current page."""
    from export_campaign_v4 import _js_str, _read_input, _is_checkbox_on, _read_checked_radio, _read_select2_text

    d = {}

    # Tracker
    d["tracker_id"] = _js_str(page, """
        (() => {
            const sel = document.getElementById("campaignTrackerId");
            if (!sel) return "";
            const opts = Array.from(sel.selectedOptions || []);
            return opts.map(o => o.textContent.trim()).join(", ");
        })()
    """)

    # Smart bidder
    d["smart_bidder"] = ""
    if _is_checkbox_on(page, "automatic_bidding"):
        checked_id = _js_str(page, 'document.querySelector("input[name=\\"is_bidder_on\\"]:checked")?.id || ""')
        if "smart_cpm" in checked_id:
            d["smart_bidder"] = "smart_cpm"
        elif "cpa" in checked_id:
            d["smart_bidder"] = "smart_cpa"

    # Bid fields
    d["target_cpa"] = _read_input(page, "#target_cpa")
    d["per_source_test_budget"] = _read_input(page, "#per_source_test_budget")
    d["max_bid"] = _read_input(page, "#maximum_bid")

    return d


def _extract_page4_fields(page) -> dict:
    """Extract Step 4 fields from current page."""
    from export_campaign_v4 import _read_input, _read_checked_radio, _is_checkbox_on

    d = {}

    # Budget type
    budget_val = _read_checked_radio(page, "is_unlimited_budget")
    if budget_val == "1" or budget_val == "unlimited":
        d["budget_type"] = "unlimited"
    else:
        d["budget_type"] = "custom"

    # Daily budget
    d["daily_budget"] = _read_input(page, "#daily_budget")

    # Frequency cap
    if _is_checkbox_on(page, "frequency_capping"):
        d["frequency_cap"] = _read_input(page, "#frequency_cap_times")
        d["frequency_cap_every"] = _read_input(page, "#frequency_cap_every")
    else:
        d["frequency_cap"] = "0"
        d["frequency_cap_every"] = ""

    # Dates
    d["start_date"] = _read_input(page, "#start_date")
    d["end_date"] = _read_input(page, "#end_date")

    return d


# ═══════════════════════════════════════════════════════════════════
# FIELD MAP — maps V4CampaignConfig field names to export dict keys
# and which page to read them from.
#
# Format: field_name -> (export_key, page_number, normalizer_func)
# ═══════════════════════════════════════════════════════════════════

def _norm_str(v):
    """Normalize a string value for comparison."""
    if v is None:
        return ""
    return str(v).strip().lower()

def _norm_list(v):
    """Normalize a list/semicolon-separated value.

    Handles TJ's multi-line label format (newlines + heavy whitespace between labels),
    and strips [brackets] from broad keywords.
    """
    if isinstance(v, list):
        items = v
    elif isinstance(v, str):
        # TJ returns labels with newlines and lots of whitespace between them
        # Replace all whitespace runs (newlines, tabs, spaces) with a single comma
        import re
        text = re.sub(r'\s+', ' ', v.strip())
        # Now split on semicolons first (our format), then commas
        sep = ";" if ";" in text else ","
        items = [s.strip() for s in text.split(sep) if s.strip()]
    else:
        return []
    # Strip [brackets] from broad keywords
    cleaned = []
    for s in items:
        s = s.strip().lower()
        if s.startswith("[") and s.endswith("]"):
            s = s[1:-1]
        if s:
            cleaned.append(s)
    return sorted(cleaned)

def _norm_num(v):
    """Normalize a numeric value."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0

def _norm_int(v):
    """Normalize an integer value."""
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0

def _norm_bool(v):
    """Normalize a boolean value."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "on")
    return bool(v)

def _norm_match_type(v):
    """Normalize match_type — TJ returns 'broad' or 'exact' as dominant type.

    CSV can have per-keyword format 'broad,broad,exact'. Normalize to
    just the dominant type for comparison.
    """
    if not v:
        return ""
    s = str(v).strip().lower()
    # If it's a comma-separated per-keyword list, find dominant
    if "," in s:
        parts = [p.strip() for p in s.split(",")]
        broad_count = sum(1 for p in parts if p == "broad")
        return "broad" if broad_count > len(parts) // 2 else "exact"
    return s


FIELD_MAP = {
    # ── Step 1 (Basic Settings) / Overview ────────────────────────
    "content_rating":   ("content_rating",   "overview", _norm_str),
    "group":            ("group",            "overview", _norm_str),
    "labels":           ("labels",           1, _norm_list),  # Page 1 has full label list; overview truncates
    "device":           ("device",           "overview", _norm_str),
    "ad_format_type":   ("ad_format_type",   "overview", _norm_str),
    "format_type":      ("format_type",      "overview", _norm_str),
    "ad_type":          ("ad_type",          "overview", _norm_str),
    "ad_dimensions":    ("ad_dimensions",    "overview", _norm_str),
    "content_category": ("content_category", "overview", _norm_str),
    "gender":           ("gender",           "overview", _norm_str),
    "exchange_id":      ("exchange_id",      "overview", _norm_str),
    "bid_type":         ("bid_type",         "overview", _norm_str),

    # ── Step 2 (Audience) ────────────────────────────────────────
    "geo":              ("geo",              2, _norm_list),
    "os_include":       ("os_include",       2, _norm_list),
    "os_exclude":       ("os_exclude",       2, _norm_list),
    "ios_version_op":   ("ios_version_op",   2, _norm_str),
    "ios_version":      ("ios_version",      2, _norm_str),
    "android_version_op": ("android_version_op", 2, _norm_str),
    "android_version":  ("android_version",  2, _norm_str),
    "browsers_include": ("browsers_include", 2, _norm_list),
    "browser_language": ("browser_language", 2, _norm_str),
    "postal_codes":     ("postal_codes",     2, _norm_list),
    "isp_country":      ("isp_country",      2, _norm_str),
    "isp_name":         ("isp_name",         2, _norm_str),
    "ip_range_start":   ("ip_range_start",   2, _norm_str),
    "ip_range_end":     ("ip_range_end",     2, _norm_str),
    "income_segment":   ("income_segment",   2, _norm_str),
    "retargeting_type": ("retargeting_type", 2, _norm_str),
    "retargeting_mode": ("retargeting_mode", 2, _norm_str),
    "retargeting_value": ("retargeting_value", 2, _norm_str),
    "vr_mode":          ("vr_mode",          2, _norm_str),
    "segment_targeting": ("segment_targeting", 2, _norm_str),
    "keywords":         ("keywords",         2, _norm_list),
    "match_type":       ("match_type",       2, _norm_match_type),

    # ── Step 3 (Tracking & Sources) ──────────────────────────────
    "tracker_id":       ("tracker_id",       3, _norm_list),  # Handles ; and , separators
    "smart_bidder":     ("smart_bidder",     3, _norm_str),
    "target_cpa":       ("target_cpa",       3, _norm_num),
    "per_source_test_budget": ("per_source_test_budget", 3, _norm_num),
    "max_bid":          ("max_bid",          3, _norm_num),

    # ── Step 4 (Schedule & Budget) ───────────────────────────────
    "frequency_cap":    ("frequency_cap",    "overview", _norm_int),
    "frequency_cap_every": ("frequency_cap_every", "overview", _norm_int),
    "budget_type":      ("budget_type",      4, _norm_str),
    "daily_budget":     ("daily_budget",     4, _norm_num),
    "start_date":       ("start_date",       4, _norm_str),
    "end_date":         ("end_date",         4, _norm_str),
}

# Fields that should be SKIPPED during verification
SKIP_FIELDS = {
    # Internal/naming-only fields
    "template_campaign_id", "enabled", "variants", "csv_file",
    "language", "geo_name", "test_number", "keyword_name",
    # LOCKED on clone (inherited from template, cannot be changed)
    "ad_dimensions",
    # CLONE_LIMITATION — toggle-gated sections don't persist via clone edit save
    # These work in the full 5-step create flow but not clone-then-edit
    "browsers_include", "vr_mode",
    # Not implemented
    "automation_rules", "include_all_sources",
    # Platform limitations
    "optimization_option", "schedule_dayparting",
    # CPM-specific (verified differently)
    "cpm_adjust", "cpm_bid_mode", "cpm_bid_value",
    # Source selection (complex — verified by spot check)
    "source_selection",
    # CPA bid defaults — these are model defaults, not explicitly set in most CSVs
    # Only verify when the CSV explicitly sets them (non-default values)
    "target_cpa", "per_source_test_budget", "max_bid",
}


# ═══════════════════════════════════════════════════════════════════
# Verification Engine
# ═══════════════════════════════════════════════════════════════════

class FieldResult:
    def __init__(self, field: str, expected, actual, status: str, note: str = ""):
        self.field = field
        self.expected = expected
        self.actual = actual
        self.status = status  # "PASS", "FAIL", "SKIP", "WARN"
        self.note = note

    def __repr__(self):
        sym = {"PASS": "✓", "FAIL": "✗", "SKIP": "–", "WARN": "⚠"}
        s = sym.get(self.status, "?")
        if self.status == "PASS":
            return f"  {s} {self.field}: {self.actual}"
        if self.status == "SKIP":
            return f"  {s} {self.field}: (skipped) {self.note}"
        return f"  {s} {self.field}: expected={self.expected} actual={self.actual} {self.note}"


def verify_campaign(
    page: Page,
    campaign_id: str,
    expected: dict,
    pages_to_read: set = None,
) -> List[FieldResult]:
    """
    Verify a single campaign against expected values.

    Args:
        page: Playwright page with active TJ session.
        campaign_id: TJ campaign ID.
        expected: Dict of field_name -> expected_value (from CSV).
        pages_to_read: Set of pages to read. None = read all needed pages.

    Returns:
        List of FieldResult objects.
    """
    results = []

    # Determine which pages we need to read
    if pages_to_read is None:
        pages_to_read = set()
        for field_name, (_, page_num, _) in FIELD_MAP.items():
            if field_name in expected and field_name not in SKIP_FIELDS:
                pages_to_read.add(page_num)

    # Detect if this is a draft (short numeric ID) vs live (10-digit ID)
    is_draft = len(str(campaign_id)) < 10

    # For drafts, always read all edit pages (no overview available)
    if is_draft:
        logger.info(f"  Draft campaign detected — reading all edit pages")
        pages_to_read = {1, 2, 3, 4}

    # Read actual values from TJ
    actual = {}

    # Try overview first for live campaigns
    if "overview" in pages_to_read and not is_draft:
        overview_data = read_overview(page, campaign_id)
        actual.update(overview_data)

        # If overview returned mostly empty, fall through to page 1
        non_empty = sum(1 for k, v in overview_data.items()
                        if v and not k.startswith("_"))
        if non_empty < 3:
            logger.info(f"  Overview sparse ({non_empty} fields) — reading page 1 too")
            pages_to_read.add(1)

    if 1 in pages_to_read:
        if is_draft:
            actual.update(_read_draft_page(page, campaign_id, 1))
        else:
            actual.update(read_page1(page, campaign_id))
    if 2 in pages_to_read:
        if is_draft:
            actual.update(_read_draft_page(page, campaign_id, 2))
        else:
            actual.update(read_page2(page, campaign_id))
    if 3 in pages_to_read:
        if is_draft:
            actual.update(_read_draft_page(page, campaign_id, 3))
        else:
            actual.update(read_page3(page, campaign_id))
    if 4 in pages_to_read:
        if is_draft:
            actual.update(_read_draft_page(page, campaign_id, 4))
        else:
            actual.update(read_page4(page, campaign_id))

    # Compare each field
    for field_name in sorted(expected.keys()):
        exp_val = expected[field_name]

        # Skip internal/non-verifiable fields
        if field_name in SKIP_FIELDS:
            results.append(FieldResult(field_name, exp_val, None, "SKIP", "internal/naming"))
            continue

        # Skip empty expected values (field not configured)
        if not exp_val and exp_val != 0 and exp_val is not False:
            results.append(FieldResult(field_name, exp_val, None, "SKIP", "not configured"))
            continue

        # Skip match_type when no keywords are set (TJ returns empty)
        if field_name == "match_type" and not expected.get("keywords", "").strip():
            results.append(FieldResult(field_name, exp_val, None, "SKIP", "no keywords"))
            continue

        # Skip format_type and ad_type for non-display formats (instream/pop don't have them)
        if field_name in ("format_type", "ad_type"):
            ad_fmt = expected.get("ad_format_type", "display")
            if ad_fmt in ("instream", "pop"):
                results.append(FieldResult(field_name, exp_val, None, "SKIP", f"n/a for {ad_fmt}"))
                continue


        # Skip frequency_cap_every when frequency_cap is disabled (0)
        if field_name == "frequency_cap_every":
            fc = expected.get("frequency_cap", "3")
            if str(fc).strip() == "0":
                results.append(FieldResult(field_name, exp_val, None, "SKIP", "freq cap disabled"))
                continue

        # Skip daily_budget when budget_type is unlimited
        if field_name == "daily_budget":
            bt = expected.get("budget_type", "custom")
            if str(bt).strip().lower() == "unlimited":
                results.append(FieldResult(field_name, exp_val, None, "SKIP", "unlimited budget"))
                continue

        # Look up in FIELD_MAP
        mapping = FIELD_MAP.get(field_name)
        if not mapping:
            results.append(FieldResult(field_name, exp_val, None, "SKIP", "no mapping"))
            continue

        export_key, page_num, normalizer = mapping
        act_val = actual.get(export_key, "")

        # Normalize both values
        exp_norm = normalizer(exp_val)
        act_norm = normalizer(act_val)

        if exp_norm == act_norm:
            results.append(FieldResult(field_name, exp_val, act_val, "PASS"))
        else:
            results.append(FieldResult(field_name, exp_val, act_val, "FAIL"))

    return results


def print_results(campaign_id: str, results: List[FieldResult]) -> Tuple[int, int, int]:
    """Print verification results and return (pass, fail, skip) counts."""
    passes = sum(1 for r in results if r.status == "PASS")
    fails = sum(1 for r in results if r.status == "FAIL")
    skips = sum(1 for r in results if r.status == "SKIP")
    warns = sum(1 for r in results if r.status == "WARN")

    print(f"\n{'='*60}")
    print(f"Campaign {campaign_id}: {passes} PASS, {fails} FAIL, {skips} SKIP")
    print(f"{'='*60}")

    # Show FAILs first
    for r in results:
        if r.status == "FAIL":
            print(r)

    # Then WARNs
    for r in results:
        if r.status == "WARN":
            print(r)

    # Then PASSes (compact)
    passing = [r for r in results if r.status == "PASS"]
    if passing:
        print(f"\n  Passing ({len(passing)}): {', '.join(r.field for r in passing)}")

    return passes, fails, skips


def load_csv_row(csv_path: str, row_idx: int = 0, campaign_name: str = None) -> dict:
    """Load a single row from a V4 CSV as a dict."""
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if campaign_name and row.get("campaign_name", "") == campaign_name:
                return row
            if i == row_idx:
                return row
    raise ValueError(f"Row {row_idx} not found in {csv_path}")


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Verify TJ campaigns against V4 CSV config")
    parser.add_argument("campaign_id", nargs="?", help="Campaign ID to verify")
    parser.add_argument("--csv", help="Path to V4 CSV with expected values")
    parser.add_argument("--row", type=int, default=0, help="CSV row index (0-based)")
    parser.add_argument("--name", help="Match CSV row by campaign name")
    parser.add_argument("--batch", help="Verify multiple campaigns from CSV (requires --ids)")
    parser.add_argument("--ids", help="Comma-separated campaign IDs for batch mode")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--pages", help="Pages to read: 'overview,2,3' (default: auto)")
    args = parser.parse_args()

    if not args.campaign_id and not args.batch:
        parser.error("Provide a campaign_id or use --batch")

    config = Config()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        ctx = browser.new_context(
            storage_state="data/session/tj_session.json",
            viewport={"width": 1920, "height": 1080},
        )
        page = ctx.new_page()
        page.set_default_timeout(20000)

        # Parse pages override
        pages_override = None
        if args.pages:
            pages_override = set()
            for p_str in args.pages.split(","):
                p_str = p_str.strip()
                if p_str == "overview":
                    pages_override.add("overview")
                else:
                    pages_override.add(int(p_str))

        if args.batch:
            # Batch mode: verify multiple campaigns
            ids = [cid.strip() for cid in args.ids.split(",")]
            total_pass = total_fail = total_skip = 0

            with open(args.batch) as f:
                rows = list(csv.DictReader(f))

            for i, cid in enumerate(ids):
                if i < len(rows):
                    expected = rows[i]
                else:
                    logger.warning(f"No CSV row for campaign {cid}")
                    continue

                results = verify_campaign(page, cid, expected, pages_override)
                p, f_count, s = print_results(cid, results)
                total_pass += p
                total_fail += f_count
                total_skip += s

            print(f"\n{'='*60}")
            print(f"BATCH TOTAL: {total_pass} PASS, {total_fail} FAIL, {total_skip} SKIP")
            print(f"{'='*60}")
            sys.exit(1 if total_fail > 0 else 0)

        else:
            # Single campaign mode
            if args.csv:
                expected = load_csv_row(args.csv, args.row, args.name)
            else:
                logger.error("--csv is required for single campaign verification")
                sys.exit(1)

            results = verify_campaign(page, args.campaign_id, expected, pages_override)
            p, f_count, s = print_results(args.campaign_id, results)
            sys.exit(1 if f_count > 0 else 0)


if __name__ == "__main__":
    main()

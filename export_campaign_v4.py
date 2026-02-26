#!/usr/bin/env python3
"""
Campaign Export Tool — Scrape an existing TJ campaign and export as V4-compatible CSV.

Navigates through 4 campaign pages, reads every setting via hidden JSON inputs
and form elements, and writes a single-row CSV compatible with create_campaigns_v4.py.

Usage:
    python export_campaign_v4.py <campaign_id>
    python export_campaign_v4.py <campaign_id> --output my_base.csv
    python export_campaign_v4.py <campaign_id> --headless
"""

import re
import sys
import csv
import json
import logging
import argparse
import time
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.sync_api import sync_playwright, Page

from config import Config
from auth import TJAuthenticator

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [EXPORT] %(message)s',
)
logger = logging.getLogger(__name__)

BASE_URL = "https://advertiser.trafficjunky.com"
OUTPUT_DIR = Path(__file__).parent / "data" / "output" / "V4_Campaign_Export"


# ═══════════════════════════════════════════════════════════════════
# V4 CSV HEADER — 64 columns, exact order from TEMPLATE_ALL_FIELDS
# ═══════════════════════════════════════════════════════════════════

V4_HEADER = [
    "enabled", "group", "keywords", "match_type", "geo", "variants", "csv_file",
    "language", "bid_type", "campaign_type", "geo_name", "test_number",
    "content_rating", "device", "ad_format_type", "format_type", "ad_type",
    "ad_dimensions", "content_category", "gender", "labels", "exchange_id",
    "tracker_id", "source_selection", "smart_bidder", "optimization_option",
    "target_cpa", "per_source_test_budget", "max_bid", "cpm_adjust",
    "include_all_sources", "frequency_cap", "frequency_cap_every", "daily_budget",
    "start_date", "end_date", "schedule_dayparting",
    "os_include", "os_exclude", "ios_version_op", "ios_version",
    "android_version_op", "android_version",
    "browser_targeting", "browsers_include", "browser_language",
    "postal_code_targeting", "postal_codes",
    "isp_targeting", "isp_country", "isp_name",
    "ip_targeting", "ip_range_start", "ip_range_end",
    "income_targeting", "income_segment",
    "retargeting", "retargeting_type", "retargeting_mode", "retargeting_value",
    "vr_targeting", "vr_mode",
    "segment_targeting", "automation_rules",
]


# ═══════════════════════════════════════════════════════════════════
# REVERSE VALUE MAPS  (radio-button value → human-readable CSV value)
# ═══════════════════════════════════════════════════════════════════

DEVICE_REVERSE = {"1": "all", "2": "desktop", "3": "mobile"}
AD_FORMAT_REVERSE = {"1": "display", "2": "instream", "3": "pop"}
FORMAT_TYPE_REVERSE = {"4": "banner", "5": "native"}
AD_TYPE_REVERSE = {
    "1": "static_banner", "2": "video_banner",
    "5": "video_file", "9": "rollover",
}
DIMENSION_REVERSE = {
    # Display banner dimensions
    "9": "300x250", "5": "950x250", "25": "468x60", "55": "305x99",
    "80": "300x100", "221": "970x90", "9771": "320x480", "9731": "640x360",
    # In-Stream Video (pre-roll) dimensions
    "9651": "Pre-roll (16:9)", "9781": "Pre-roll (9:16)",
}
GENDER_REVERSE = {"1": "all", "2": "male", "3": "female"}

LANGUAGE_REVERSE = {
    "English": "EN", "French": "FR", "German": "DE", "Spanish": "ES",
    "Italian": "IT", "Portuguese": "PT", "Dutch": "NL", "Japanese": "JA",
    "Korean": "KO", "Chinese": "ZH", "Polish": "PL", "Russian": "RU",
    "Turkish": "TR", "Arabic": "AR", "Czech": "CS", "Swedish": "SV",
    "Danish": "DA", "Norwegian": "NO", "Finnish": "FI", "Hungarian": "HU",
    "Romanian": "RO", "Thai": "TH",
}

# OS operation name → V4 CSV version operator
OS_OP_REVERSE = {
    "newer_or_equal_than": "newer_than",
    "newer_than": "newer_than",
    "older_or_equal_than": "older_than",
    "older_than": "older_than",
    "is": "equal",
    "between": "between",
}


# ═══════════════════════════════════════════════════════════════════
# OVERVIEW PAGE VALUE MAPS  (overview text → V4 CSV value)
# ═══════════════════════════════════════════════════════════════════

OVERVIEW_LABEL_MAP = {
    "campaign name": "_name",
    "content rating": "content_rating",
    "campaign group name": "group",
    "labels": "labels",
    "exchange": "exchange_id",
    "device": "device",
    "ad format": "ad_format_type",
    "format type": "format_type",
    "ad type": "ad_type",
    "ad dimensions": "ad_dimensions",
    "content category": "content_category",
    "gender": "gender",
    "conversion tracker": "tracker_id",
    "geo targeting included": "geo_overview",
    "frequency capping": "_frequency_capping_raw",
    "durations": "_durations_raw",
}

CONTENT_RATING_MAP_OVERVIEW = {
    "safe for work": "SFW",
    "not safe for work": "NSFW",
}
DEVICE_MAP_OVERVIEW = {
    "all devices": "all",
    "desktop": "desktop",
    "mobile": "mobile",
}
AD_FORMAT_MAP_OVERVIEW = {
    "display": "display",
    "instream": "instream",
    "pop": "pop",
}
FORMAT_TYPE_MAP_OVERVIEW = {
    "native": "native",
    "banner": "banner",
}
AD_TYPE_MAP_OVERVIEW = {
    "rollover": "rollover",
    "static banner": "static_banner",
    "video banner": "video_banner",
    "video file": "video_file",
}
GENDER_MAP_OVERVIEW = {
    "all": "all",
    "male": "male",
    "female": "female",
}
CONTENT_CATEGORY_MAP_OVERVIEW = {
    "straight": "straight",
    "gay": "gay",
    "trans": "trans",
}


# ═══════════════════════════════════════════════════════════════════
# LOW-LEVEL READING HELPERS
# ═══════════════════════════════════════════════════════════════════

def _js(page: Page, expression: str):
    """Evaluate a JS expression; return the raw result."""
    return page.evaluate(expression)


def _js_str(page: Page, expression: str) -> str:
    """Evaluate JS and always return a stripped string."""
    result = page.evaluate(expression)
    if result is None or result is False:
        return ""
    return str(result).strip()


def _read_checked_radio(page: Page, name: str) -> str:
    """Return the value of the checked radio with the given name attribute."""
    return _js_str(
        page,
        f'document.querySelector(\'input[name="{name}"]:checked\')?.value'
    )


def _read_input(page: Page, css: str) -> str:
    """Return the .value of an <input>, <select>, or <textarea>."""
    return _js_str(page, f'document.querySelector(\'{css}\')?.value')


def _read_hidden_json(page: Page, css: str):
    """Read a hidden input's value and parse as JSON. Returns None on failure."""
    raw = _read_input(page, css)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None


def _read_select2_text(page: Page, container_id: str) -> str:
    """Return the visible text inside a select2 container span."""
    text = _js_str(
        page,
        f'document.getElementById("{container_id}")?.textContent'
    )
    # Filter out placeholder text
    placeholders = ("select", "choose", "search", "type here", "-- ", "\u00d7")
    cleaned = text.lstrip("\u00d7").strip()  # strip × prefix
    if cleaned.lower().startswith(tuple(placeholders)):
        return ""
    return cleaned


def _is_checkbox_on(page: Page, checkbox_id: str) -> bool:
    """True if the checkbox with the given ID is checked."""
    return _js(page, f'!!document.getElementById("{checkbox_id}")?.checked')


# ═══════════════════════════════════════════════════════════════════
# OVERVIEW PAGE  (/campaign/overview/{ID})
# ═══════════════════════════════════════════════════════════════════

def read_overview(page: Page, campaign_id: str) -> dict:
    """Read the campaign overview page, extracting all .form-row label/value pairs.

    Returns a dict with Page 1 field names populated from overview text.
    This allows skipping Page 1 when all fields are present.
    """
    url = f"{BASE_URL}/campaign/overview/{campaign_id}"
    logger.info(f"[Overview] Reading overview — {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(2)

    # Extract all .form-row label/value pairs
    raw_pairs = page.evaluate("""() => {
        const rows = document.querySelectorAll('.form-row');
        const pairs = [];
        for (const row of rows) {
            const label = row.querySelector('label');
            const valueEl = row.querySelector('.form-value') || row.querySelector('span:not(label span)');
            if (label) {
                const labelText = label.textContent.trim();
                let value = '';
                if (valueEl) {
                    value = valueEl.textContent.trim();
                } else {
                    // Fallback: get all text after the label
                    const full = row.textContent.trim();
                    const labelPart = label.textContent.trim();
                    value = full.replace(labelPart, '').trim();
                }
                pairs.push([labelText, value]);
            }
        }
        return pairs;
    }""")

    d: dict = {}

    for label_text, value in raw_pairs:
        label_lower = label_text.lower().strip().rstrip(":")
        field_name = OVERVIEW_LABEL_MAP.get(label_lower)
        if not field_name:
            continue

        value = value.strip()
        if not value or value == "-" or value.lower() == "n/a":
            continue

        if field_name == "_name":
            d["_name"] = value
        elif field_name == "content_rating":
            d["content_rating"] = CONTENT_RATING_MAP_OVERVIEW.get(value.lower(), value)
        elif field_name == "group":
            d["group"] = value
        elif field_name == "labels":
            d["labels"] = value
        elif field_name == "exchange_id":
            d["exchange_id"] = value
        elif field_name == "device":
            d["device"] = DEVICE_MAP_OVERVIEW.get(value.lower(), value)
        elif field_name == "ad_format_type":
            d["ad_format_type"] = AD_FORMAT_MAP_OVERVIEW.get(value.lower(), value)
        elif field_name == "format_type":
            d["format_type"] = FORMAT_TYPE_MAP_OVERVIEW.get(value.lower(), value)
        elif field_name == "ad_type":
            d["ad_type"] = AD_TYPE_MAP_OVERVIEW.get(value.lower(), value)
        elif field_name == "ad_dimensions":
            d["ad_dimensions"] = value
        elif field_name == "content_category":
            d["content_category"] = CONTENT_CATEGORY_MAP_OVERVIEW.get(value.lower(), value.lower())
        elif field_name == "gender":
            d["gender"] = GENDER_MAP_OVERVIEW.get(value.lower(), value)
        elif field_name == "tracker_id":
            # Strip count prefix like "(2) " from tracker name
            d["tracker_id"] = re.sub(r"^\(\d+\)\s*", "", value)
        elif field_name == "_frequency_capping_raw":
            match = re.search(r"Displaying\s+(\d+)\s+time.*?every\s+(\d+)\s+day", value)
            if match:
                d["frequency_cap"] = match.group(1)
                days = int(match.group(2))
                d["frequency_cap_every"] = str(days * 24)

    # Infer bid_type and campaign_type from name (same logic as read_page1)
    name = d.get("_name", "").upper()
    if "_CPM_" in name:
        d["bid_type"] = "CPM"
    elif "_CPA_" in name:
        d["bid_type"] = "CPA"
    else:
        d["bid_type"] = ""

    d["campaign_type"] = "Remarketing" if "REMARKETING" in name or "RETARGET" in name else "Standard"

    logger.info(f"  Overview fields: {', '.join(f'{k}={v}' for k, v in sorted(d.items()) if not k.startswith('_') and v)}")

    return d


# ═══════════════════════════════════════════════════════════════════
# PAGE 1 — BASIC SETTINGS  (/campaign/{ID})
# ═══════════════════════════════════════════════════════════════════

def read_page1(page: Page, campaign_id: str) -> dict:
    url = f"{BASE_URL}/campaign/{campaign_id}"
    logger.info(f"[Page 1] Basic Settings — {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(2)

    d: dict = {}

    # Campaign name (informational — not written to CSV)
    d["_name"] = _read_input(page, 'input[name="name"]')
    logger.info(f"  Campaign name: {d['_name']}")

    # ── Content rating ────────────────────────────────────────────
    cr = _read_checked_radio(page, "content_rating")
    d["content_rating"] = cr.upper() if cr else "NSFW"

    # ── Group (select2) ──────────────────────────────────────────
    d["group"] = _read_select2_text(page, "select2-group_id-container")

    # ── Labels (hidden JSON) ──────────────────────────────────────
    labels_json = _read_hidden_json(page, "#campaignLabels")
    if labels_json and isinstance(labels_json, list):
        names = [l.get("name", l) if isinstance(l, dict) else str(l) for l in labels_json]
        d["labels"] = ",".join(n for n in names if n)
    else:
        d["labels"] = ""

    # ── Exchange ID ───────────────────────────────────────────────
    d["exchange_id"] = _read_input(page, "select#exchange_id")

    # ── Radio-button fields ───────────────────────────────────────
    dev = _read_checked_radio(page, "platform_id")
    d["device"] = DEVICE_REVERSE.get(dev, dev)

    af = _read_checked_radio(page, "ad_format_id")
    d["ad_format_type"] = AD_FORMAT_REVERSE.get(af, af or "display")

    # format_type, ad_type, ad_dimensions only exist for display campaigns
    ft = _read_checked_radio(page, "format_type_id")
    d["format_type"] = FORMAT_TYPE_REVERSE.get(ft, ft) if ft else ""



    at = _read_checked_radio(page, "ad_type_id")
    d["ad_type"] = AD_TYPE_REVERSE.get(at, at) if at else ""

    dim = _read_checked_radio(page, "ad_dimension_id")
    d["ad_dimensions"] = DIMENSION_REVERSE.get(dim, dim) if dim else ""

    cat = _read_checked_radio(page, "content_category_id")
    d["content_category"] = cat if cat in ("straight", "gay", "trans") else "straight"

    gen = _read_checked_radio(page, "demographic_targeting_id")
    d["gender"] = GENDER_REVERSE.get(gen, "all")

    # ── Bid type / campaign type (best-effort from page) ──────────
    # These may not have explicit form fields — try to infer from campaign name
    name = d["_name"].upper()
    if "_CPM_" in name:
        d["bid_type"] = "CPM"
    elif "_CPA_" in name:
        d["bid_type"] = "CPA"
    else:
        d["bid_type"] = ""  # will be filled from step 3 detection

    d["campaign_type"] = "Remarketing" if "REMARKETING" in name or "RETARGET" in name else "Standard"

    logger.info(f"  Device={d['device']}  AdFmt={d['ad_format_type']}  FmtType={d['format_type']}")
    logger.info(f"  AdType={d['ad_type']}  Dims={d['ad_dimensions']}")
    logger.info(f"  Category={d['content_category']}  Gender={d['gender']}")
    logger.info(f"  Rating={d['content_rating']}  Group={d['group']}")
    logger.info(f"  Labels={d['labels']}  Exchange={d['exchange_id']}")
    logger.info(f"  BidType={d['bid_type']}  CampaignType={d['campaign_type']}")
    return d


# ═══════════════════════════════════════════════════════════════════
# PAGE 2 — AUDIENCE  (/campaign/{ID}/audience)
#   Sections: audienceTargeting, moreAudienceTargeting, advancedTargeting
#   Toggle checkbox IDs: operating_systems, browser_targeting,
#     browser_language_targeting, postal_code_targeting,
#     public_segment_targeting, isp_targeting, ip_targeting,
#     virtual_reality, keyword_targeting, retargeting, segment_targeting
# ═══════════════════════════════════════════════════════════════════

def read_page2(page: Page, campaign_id: str) -> dict:
    url = f"{BASE_URL}/campaign/{campaign_id}/audience"
    logger.info(f"[Page 2] Audience — {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(2)

    d: dict = {}

    # ── Geo (hidden JSON #geo_target_list) ────────────────────────
    geo_data = _read_hidden_json(page, "#geo_target_list")
    if geo_data and isinstance(geo_data, list):
        codes = []
        names = []
        for g in geo_data:
            if isinstance(g, dict):
                code = g.get("country", g.get("code", g.get("country_code", "")))
                name = g.get("name", g.get("country_name", ""))
                if code:
                    codes.append(code)
                    names.append(name if name else code)
            elif isinstance(g, str):
                codes.append(g)
                names.append(g)
        d["geo"] = ",".join(codes)
        d["geo_names"] = ",".join(names) if any(n != c for n, c in zip(names, codes)) else ""
    else:
        d["geo"] = ""
        d["geo_names"] = ""
    logger.info(f"  Geo: {d['geo']}" + (f" ({d['geo_names']})" if d.get("geo_names") else ""))

    # ── OS Targeting (hidden JSON #operating_systems_list) ─────────
    d["os_include"] = ""
    d["os_exclude"] = ""
    d["ios_version_op"] = ""
    d["ios_version"] = ""
    d["android_version_op"] = ""
    d["android_version"] = ""

    if _is_checkbox_on(page, "operating_systems"):
        os_data = _read_hidden_json(page, "#operating_systems_list")
        if os_data and isinstance(os_data, list):
            include_names = []
            exclude_names = []
            for entry in os_data:
                if not isinstance(entry, dict):
                    continue
                os_name = entry.get("operating_system_name", "")
                is_include = entry.get("include", True)

                if is_include:
                    include_names.append(os_name)
                else:
                    exclude_names.append(os_name)

                # Version constraints
                operation = entry.get("operation", "")
                v4_op = OS_OP_REVERSE.get(operation, "")
                ver_name = entry.get("min_version_name", "") or entry.get("max_version_name", "")

                if os_name == "iOS" and v4_op and ver_name:
                    d["ios_version_op"] = v4_op
                    d["ios_version"] = ver_name
                elif os_name == "Android" and v4_op and ver_name:
                    d["android_version_op"] = v4_op
                    d["android_version"] = ver_name

            d["os_include"] = ";".join(include_names)
            d["os_exclude"] = ";".join(exclude_names)

        if d["os_include"]:
            logger.info(f"  OS include: {d['os_include']}")
        if d["os_exclude"]:
            logger.info(f"  OS exclude: {d['os_exclude']}")
        if d["ios_version_op"]:
            logger.info(f"  iOS version: {d['ios_version_op']} {d['ios_version']}")
        if d["android_version_op"]:
            logger.info(f"  Android version: {d['android_version_op']} {d['android_version']}")

    # ── Browser Targeting ─────────────────────────────────────────
    d["browsers_include"] = ""

    if _is_checkbox_on(page, "browser_targeting"):
        d["browsers_include"] = _js_str(page, """(() => {
            const names = [];
            document.querySelectorAll('input[name="browsers_list[]"]:checked').forEach(cb => {
                const label = document.querySelector('label[for="' + cb.id + '"]');
                const name = label ? label.textContent.trim() : "";
                if (name) names.push(name);
            });
            return names.join(",");
        })()""")
        if d["browsers_include"]:
            logger.info(f"  Browsers: {d['browsers_include']}")

    # ── Browser Language (hidden JSON #browser_language_targeting_list) ──
    d["browser_language"] = ""

    if _is_checkbox_on(page, "browser_language_targeting"):
        lang_data = _read_hidden_json(page, "#browser_language_targeting_list")
        if lang_data and isinstance(lang_data, list):
            for entry in lang_data:
                if isinstance(entry, dict) and entry.get("type") == "include":
                    lang_name = entry.get("browserLanguageName", "")
                    d["browser_language"] = LANGUAGE_REVERSE.get(lang_name, lang_name)
                    break
        if d["browser_language"]:
            logger.info(f"  Browser language: {d['browser_language']}")

    # ── Postal Codes ──────────────────────────────────────────────
    d["postal_codes"] = ""

    if _is_checkbox_on(page, "postal_code_targeting"):
        pc_data = _read_hidden_json(page, "#postal_code_targeting_list")
        if pc_data and isinstance(pc_data, list):
            codes = [str(p.get("postal_code", p) if isinstance(p, dict) else p) for p in pc_data]
            d["postal_codes"] = ",".join(c for c in codes if c)
        if not d["postal_codes"]:
            d["postal_codes"] = _read_input(page, "#postal_codes")
        if d["postal_codes"]:
            logger.info(f"  Postal codes: {d['postal_codes'][:60]}...")

    # ── ISP Targeting ─────────────────────────────────────────────
    d["isp_country"] = ""
    d["isp_name"] = ""

    if _is_checkbox_on(page, "isp_targeting"):
        d["isp_country"] = _read_select2_text(page, "select2-isp_country-container")
        d["isp_name"] = _read_select2_text(page, "select2-isp_name-container")
        if d["isp_country"]:
            logger.info(f"  ISP: {d['isp_country']} / {d['isp_name']}")

    # ── IP Range ──────────────────────────────────────────────────
    d["ip_range_start"] = ""
    d["ip_range_end"] = ""

    if _is_checkbox_on(page, "ip_targeting"):
        d["ip_range_start"] = _read_input(page, "#ip_range_start")
        d["ip_range_end"] = _read_input(page, "#ip_range_end")
        if d["ip_range_start"]:
            logger.info(f"  IP range: {d['ip_range_start']} - {d['ip_range_end']}")

    # ── Income / Public Segment ───────────────────────────────────
    d["income_segment"] = ""

    if _is_checkbox_on(page, "public_segment_targeting"):
        d["income_segment"] = _read_select2_text(page, "select2-public_segment_income-container")
        if d["income_segment"]:
            logger.info(f"  Income segment: {d['income_segment']}")

    # ── Retargeting ───────────────────────────────────────────────
    d["retargeting_type"] = ""
    d["retargeting_mode"] = ""
    d["retargeting_value"] = ""

    if _is_checkbox_on(page, "retargeting"):
        d["retargeting_type"] = _read_checked_radio(page, "retargeting_type")
        d["retargeting_mode"] = _read_checked_radio(page, "retargeting_mode")

        # Try hidden JSON #retargeting_list first (has full audience names)
        rt_data = _read_hidden_json(page, "#retargeting_list")
        if rt_data and isinstance(rt_data, list):
            names = []
            for item in rt_data:
                if isinstance(item, dict):
                    name = item.get("name", item.get("text", item.get("label", "")))
                    if name:
                        names.append(name)
                elif isinstance(item, str):
                    names.append(item)
            d["retargeting_value"] = ", ".join(names) if names else ""
        else:
            # Fallback: read from select element's selected options
            d["retargeting_value"] = _js_str(page, '''
                (() => {
                    const sel = document.querySelector("#retargeting_value");
                    if (!sel) return "";
                    const opts = Array.from(sel.selectedOptions || []);
                    if (opts.length > 0) return opts.map(o => o.textContent.trim()).join(", ");
                    if (sel.selectedIndex >= 0) return sel.options[sel.selectedIndex]?.textContent?.trim() || "";
                    return "";
                })()
            ''')

        # Final fallback: select2 container text
        if not d["retargeting_value"]:
            d["retargeting_value"] = _read_select2_text(page, "select2-retargeting_value-container")

        if d["retargeting_value"]:
            logger.info(
                f"  Retargeting: {d['retargeting_type']}/"
                f"{d['retargeting_mode']}/{d['retargeting_value']}"
            )

    # ── VR Targeting ──────────────────────────────────────────────
    d["vr_mode"] = ""

    if _is_checkbox_on(page, "virtual_reality"):
        vr_val = _read_checked_radio(page, "virtual_reality")
        if vr_val == "vr":
            d["vr_mode"] = "vr"
        elif vr_val:
            d["vr_mode"] = "non_vr"
        if d["vr_mode"]:
            logger.info(f"  VR mode: {d['vr_mode']}")

    # ── Segment Targeting ─────────────────────────────────────────
    d["segment_targeting"] = ""

    if _is_checkbox_on(page, "segment_targeting"):
        # Read the actual selected cookie name from the <select> element
        d["segment_targeting"] = _js_str(page, '''
            (() => {
                const sel = document.querySelector("#cookie");
                if (!sel) return "";
                const opts = Array.from(sel.selectedOptions || []);
                if (opts.length > 0) return opts.map(o => o.textContent.trim()).join(", ");
                if (sel.selectedIndex >= 0) return sel.options[sel.selectedIndex]?.textContent?.trim() || "";
                return "";
            })()
        ''')
        # Fallback: select2 container text
        if not d["segment_targeting"]:
            d["segment_targeting"] = _read_select2_text(page, "select2-cookie-container")
        if d["segment_targeting"]:
            logger.info(f"  Segment: {d['segment_targeting']}")

    # ── Keywords (hidden JSON #keywords) ──────────────────────────
    d["keywords"] = ""
    d["match_type"] = ""

    if _is_checkbox_on(page, "keyword_targeting"):
        kw_data = _read_hidden_json(page, "#keywords")
        if kw_data and isinstance(kw_data, dict):
            inc = kw_data.get("include", {})
            exact_kws = inc.get("exact", [])
            broad_kws = inc.get("broad", [])
            # Keywords can be strings or dicts with "keyword"/"text"/"name" key
            def _kw_text(kw):
                if isinstance(kw, dict):
                    return kw.get("keyword", kw.get("text", kw.get("name", "")))
                return str(kw)
            # TJ mass-import format: [keyword] = broad, keyword = exact; broad first
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
            # Set match_type to dominant type for backward compat
            if kw_parts:
                d["match_type"] = "broad" if len(broad_kws) > len(exact_kws) else "exact"

        # Fallback: #copiedKeywords textarea
        if not d["keywords"]:
            d["keywords"] = _read_input(page, "#copiedKeywords")

        if d["keywords"]:
            logger.info(f"  Keywords: {d['keywords']}")
            logger.info(f"  Match type: {d['match_type']}")
        else:
            logger.info("  Keywords: (targeting enabled but none set)")
    else:
        logger.info("  Keywords: (none)")

    return d


# ═══════════════════════════════════════════════════════════════════
# PAGE 3 — TRACKING & SOURCES  (/campaign/{ID}/tracking-spots-rules)
#   Sections: conversionTracker, adSpotsSourcesSelection, rules
# ═══════════════════════════════════════════════════════════════════

def read_page3(page: Page, campaign_id: str) -> dict:
    url = f"{BASE_URL}/campaign/{campaign_id}/tracking-spots-rules"
    logger.info(f"[Page 3] Tracking & Sources — {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(2)

    d: dict = {}

    # ── Conversion Trackers (hidden JSON #campaign_trackers) ──────
    tracker_data = _read_hidden_json(page, "#campaign_trackers")
    if tracker_data and isinstance(tracker_data, list) and len(tracker_data) > 0:
        names = [t.get("name", "") for t in tracker_data if isinstance(t, dict) and t.get("name")]
        d["tracker_id"] = ",".join(names)
    else:
        d["tracker_id"] = ""

    # ── Bid values ────────────────────────────────────────────────
    d["target_cpa"] = _read_input(page, "#target_cpa")
    d["per_source_test_budget"] = _read_input(page, "#per_source_test_budget")
    d["max_bid"] = _read_input(page, "#maximum_bid")

    # ── Detect bid type from visible fields ───────────────────────
    cpa_visible = _js(page, """(() => {
        const el = document.querySelector("#target_cpa");
        return !!(el && el.offsetParent !== null);
    })()""")
    d["_bid_type_detected"] = "CPA" if cpa_visible else "CPM"

    # ── Smart Bidder ──────────────────────────────────────────────
    d["smart_bidder"] = ""
    d["optimization_option"] = ""

    if _is_checkbox_on(page, "automatic_bidding"):
        # Read which bidder mode is selected by radio name "is_bidder_on"
        bidder_val = _read_checked_radio(page, "is_bidder_on")
        # Also check by ID pattern for the checked radio
        checked_id = _js_str(page, """
            document.querySelector('input[name="is_bidder_on"]:checked')?.id || ""
        """)
        if "smart_cpm" in checked_id or bidder_val == "cpm":
            d["smart_bidder"] = "smart_cpm"
        elif "cpa" in checked_id or bidder_val == "cpa":
            d["smart_bidder"] = "smart_cpa"

        opt = _read_checked_radio(page, "optimization_option")
        d["optimization_option"] = opt if opt and opt != "N/A" else ""

    logger.info(f"  Tracker: {d['tracker_id'] or '(none)'}")
    logger.info(f"  Bid type (detected): {d['_bid_type_detected']}")
    logger.info(
        f"  CPA={d['target_cpa']}  TestBudget={d['per_source_test_budget']}"
        f"  MaxBid={d['max_bid']}"
    )
    logger.info(
        f"  SmartBidder={d['smart_bidder'] or '(off)'}"
        f"  Optimization={d['optimization_option'] or '(none)'}"
    )
    return d


# ═══════════════════════════════════════════════════════════════════
# PAGE 4 — SCHEDULE & BUDGET  (/campaign/{ID}/schedule-budget)
#   Toggle checkbox IDs: duration, schedule, frequency_cap
# ═══════════════════════════════════════════════════════════════════

def read_page4(page: Page, campaign_id: str) -> dict:
    url = f"{BASE_URL}/campaign/{campaign_id}/schedule-budget"
    logger.info(f"[Page 4] Schedule & Budget — {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(2)

    d: dict = {}

    # ── Duration ──────────────────────────────────────────────────
    d["start_date"] = ""
    d["end_date"] = ""

    if _is_checkbox_on(page, "duration"):
        d["start_date"] = _read_input(page, "#start_date")
        d["end_date"] = _read_input(page, "#end_date")
        if d["start_date"] or d["end_date"]:
            logger.info(f"  Duration: {d['start_date']} to {d['end_date']}")

    # ── Dayparting ────────────────────────────────────────────────
    d["schedule_dayparting"] = ""

    if _is_checkbox_on(page, "schedule"):
        d["schedule_dayparting"] = _read_input(page, "#schedule_list")
        logger.info(f"  Dayparting: {'configured' if d['schedule_dayparting'] else '(empty)'}")

    # ── Frequency Cap ─────────────────────────────────────────────
    if _is_checkbox_on(page, "frequency_cap"):
        d["frequency_cap"] = _read_input(page, "#frequency_cap_times") or "3"
        d["frequency_cap_every"] = _read_input(page, "#frequency_cap_every") or "24"
        logger.info(f"  Freq cap: {d['frequency_cap']} times / {d['frequency_cap_every']}h")
    else:
        d["frequency_cap"] = ""
        d["frequency_cap_every"] = ""
        logger.info("  Freq cap: disabled")

    # ── Daily Budget ──────────────────────────────────────────────
    # Detect if budget is Unlimited or Custom
    budget_type = _js_str(page, '''(() => {
        const custom = document.getElementById("is_unlimited_budget_custom");
        if (custom && custom.checked) return "custom";
        const unlimited = document.querySelector('input[name="is_unlimited_budget"][value="unlimited"]')
            || document.getElementById("is_unlimited_budget_unlimited");
        if (unlimited && unlimited.checked) return "unlimited";
        // Fallback: check if daily_budget is visible
        const f = document.getElementById("daily_budget");
        if (f && f.offsetParent !== null && !f.disabled) return "custom";
        return "unlimited";
    })()''')
    d["budget_type"] = budget_type
    if budget_type == "unlimited":
        d["daily_budget"] = "Unlimited"
        logger.info("  Daily budget: Unlimited")
    else:
        d["daily_budget"] = _read_input(page, "#daily_budget") or "25.00"
        logger.info(f"  Daily budget: ${d['daily_budget']}")

    return d


# ═══════════════════════════════════════════════════════════════════
# PAGE 5 — AD SETTINGS  (/campaign/{ID}/ad-settings)
#   Reads all ads via jQuery DataTables API
# ═══════════════════════════════════════════════════════════════════

def read_ads(page: Page, campaign_id: str) -> list:
    """Read all ads from the ad-settings page via DataTables API."""
    url = f"{BASE_URL}/campaign/{campaign_id}/ad-settings"
    logger.info(f"[Page 5] Ad Settings — {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(3)

    # Show all ads
    try:
        page.select_option('select[name="adsTable_length"]', '100')
        time.sleep(2)
    except Exception:
        pass

    # Read all ad rows via DataTables API
    ads = page.evaluate('''() => {
        try {
            if (typeof jQuery === 'undefined') return [];
            const dt = jQuery('#adsTable').DataTable();
            const data = dt.rows().data();
            const ads = [];
            for (let i = 0; i < data.length; i++) {
                const row = data[i];
                ads.push({
                    id: row.id || "",
                    name: row.name || "",
                    ad_type: row.ad_type || "",
                    target_url: row.target_url || "",
                    source_url: row.source_url || "",
                    creativeId: row.creativeId || "",
                    thumbnail_creative_id: row.thumbnail_creative_id || "",
                    headline: row.headline || "",
                    brand_name: row.brand_name || "",
                    url_text_click: row.url_text_click || "",
                    url_optional_retargeting_pixel: row.url_optional_retargeting_pixel || "",
                    title_cta: row.title_cta || "",
                    banner_cta: row.banner_cta || [],
                });
            }
            return ads;
        } catch(e) {
            return [];
        }
    }''')

    logger.info(f"  Found {len(ads)} ads")
    for i, ad in enumerate(ads):
        logger.info(f"    Ad {i+1}: {ad.get('name', '?')} (type={ad.get('ad_type', '?')})")

    return ads


# ═══════════════════════════════════════════════════════════════════
# AD CSV WRITER — format depends on ad_format_type
# ═══════════════════════════════════════════════════════════════════

# Pop CSV: just Ad Name + Target URL
POP_AD_HEADER = ["Ad Name", "Target URL"]

# Video banner CSV: 4 columns (matches TJ's "Download the CSV template")
VIDEO_BANNER_AD_HEADER = ["Ad Name", "Target URL", "Creative Video ID", "Creative Overlay ID"]

# Static banner CSV: 2 columns (no creative in CSV — assigned in TJ library)
STATIC_BANNER_AD_HEADER = ["Ad Name", "Target URL"]

# Native CSV (rollover): 6 columns
NATIVE_AD_HEADER = [
    "Ad Name", "Target URL", "Video Creative ID",
    "Thumbnail Creative ID", "Headline", "Brand Name",
]

# Instream/Preroll CSV
INSTREAM_AD_HEADER = [
    "Ad Name", "Target URL", "Creative ID",
    "Custom CTA Text", "Custom CTA URL",
    "Banner CTA Creative ID", "Banner CTA Title",
    "Banner CTA Subtitle", "Banner CTA URL", "Tracking Pixel",
]


def write_ad_csv(ads: list, ad_format: str, output_path: Path, format_type: str = "", ad_type: str = ""):
    """Write the ad/creative CSV based on ad format type."""
    if not ads:
        logger.info("No ads to export")
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if ad_format == "pop":
        header = POP_AD_HEADER
        rows = [{"Ad Name": a["name"], "Target URL": a["target_url"]} for a in ads]
    elif ad_format == "display" and format_type == "native":
        # Native (rollover) ads — 6 columns
        header = NATIVE_AD_HEADER
        rows = []
        for a in ads:
            rows.append({
                "Ad Name": a["name"],
                "Target URL": a["target_url"],
                "Video Creative ID": str(a.get("creativeId", "")) if a.get("creativeId") else "",
                "Thumbnail Creative ID": str(a.get("thumbnail_creative_id", "")) if a.get("thumbnail_creative_id") else "",
                "Headline": a.get("headline", ""),
                "Brand Name": a.get("brand_name", ""),
            })
    elif ad_format == "display" and ad_type == "video_banner":
        # Video banner ads — 4 columns (matches TJ template)
        header = VIDEO_BANNER_AD_HEADER
        rows = []
        for a in ads:
            rows.append({
                "Ad Name": a["name"],
                "Target URL": a["target_url"],
                "Creative Video ID": str(a.get("creativeId", "")) if a.get("creativeId") else "",
                "Creative Overlay ID": str(a.get("overlay_creative_id", "")) if a.get("overlay_creative_id") else "",
            })
    elif ad_format == "display":
        # Static banner ads — 2 columns
        header = STATIC_BANNER_AD_HEADER
        rows = []
        for a in ads:
            rows.append({
                "Ad Name": a["name"],
                "Target URL": a["target_url"],
            })
    elif ad_format == "instream":
        header = INSTREAM_AD_HEADER
        rows = []
        for a in ads:
            bcta = a.get("banner_cta", [])
            bcta0 = bcta[0] if bcta else {}
            rows.append({
                "Ad Name": a["name"],
                "Target URL": a["target_url"],
                "Creative ID": a.get("creativeId", ""),
                "Custom CTA Text": a.get("url_text_click", ""),
                "Custom CTA URL": "",
                "Banner CTA Creative ID": bcta0.get("creativeId", "") if isinstance(bcta0, dict) else "",
                "Banner CTA Title": bcta0.get("title", "") if isinstance(bcta0, dict) else "",
                "Banner CTA Subtitle": bcta0.get("subtitle", "") if isinstance(bcta0, dict) else "",
                "Banner CTA URL": bcta0.get("url", "") if isinstance(bcta0, dict) else "",
                "Tracking Pixel": a.get("url_optional_retargeting_pixel", ""),
            })
    else:
        logger.warning(f"Unknown ad format '{ad_format}', using pop format")
        header = POP_AD_HEADER
        rows = [{"Ad Name": a["name"], "Target URL": a["target_url"]} for a in ads]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Ad CSV written: {output_path} ({len(rows)} ads)")
    return output_path


# ═══════════════════════════════════════════════════════════════════
# CSV BUILDER
# ═══════════════════════════════════════════════════════════════════

def build_csv_row(p1: dict, p2: dict, p3: dict, p4: dict) -> dict:
    """Merge all page dicts into a single dict keyed by V4 column names."""
    row: dict = {}

    # ── Auto-detect variants from device + OS targeting ─────────
    device = p1.get("device", "")
    os_inc = p2.get("os_include", "")
    if device == "mobile":
        if "Android" in os_inc and "iOS" not in os_inc:
            variants = "android"
        elif "iOS" in os_inc and "Android" not in os_inc:
            variants = "ios"
        else:
            variants = "all_mobile"
    elif device == "all":
        variants = "all"
    else:
        variants = "desktop"

    # ── Auto-detect language from campaign name ───────────────
    # Name format: {GEO}_{LANG}_{FORMAT}_{BID}_{SOURCE}_...
    campaign_name = p1.get("_name", "")
    name_parts = campaign_name.split("_") if campaign_name else []
    detected_lang = ""
    if len(name_parts) >= 2:
        candidate = name_parts[1].upper()
        # Validate it looks like a 2-letter language code
        all_lang_codes = set(LANGUAGE_REVERSE.values())
        if candidate in all_lang_codes:
            detected_lang = candidate
    if not detected_lang:
        detected_lang = "EN"
        logger.warning("  Could not detect language from campaign name — defaulting to EN")

    # ── User-fillable / meta columns ──────────────────────────────
    row["enabled"] = "TRUE"
    row["variants"] = variants
    row["csv_file"] = ""          # user fills
    row["language"] = detected_lang
    row["geo_name"] = ""
    row["test_number"] = ""
    row["cpm_adjust"] = ""
    row["source_selection"] = ""
    row["include_all_sources"] = "TRUE"
    row["automation_rules"] = ""

    # ── Page 1: Basic Settings ────────────────────────────────────
    row["group"] = p1.get("group", "")
    row["content_rating"] = p1.get("content_rating", "NSFW")
    row["device"] = p1.get("device", "")
    row["ad_format_type"] = p1.get("ad_format_type", "display")
    row["format_type"] = p1.get("format_type", "")
    row["ad_type"] = p1.get("ad_type", "")
    row["ad_dimensions"] = p1.get("ad_dimensions", "")
    row["content_category"] = p1.get("content_category", "straight")
    row["gender"] = p1.get("gender", "all")
    row["labels"] = p1.get("labels", "")
    row["exchange_id"] = p1.get("exchange_id", "")
    row["bid_type"] = p1.get("bid_type", "") or p3.get("_bid_type_detected", "CPA")
    row["campaign_type"] = p1.get("campaign_type", "Standard")

    # ── Page 2: Audience ──────────────────────────────────────────
    row["geo"] = p2.get("geo_names", "") or p2.get("geo", "")
    row["geo_codes"] = p2.get("geo", "")
    row["keywords"] = p2.get("keywords", "")
    row["match_type"] = p2.get("match_type", "")
    row["os_include"] = p2.get("os_include", "")
    row["os_exclude"] = p2.get("os_exclude", "")
    row["ios_version_op"] = p2.get("ios_version_op", "")
    row["ios_version"] = p2.get("ios_version", "")
    row["android_version_op"] = p2.get("android_version_op", "")
    row["android_version"] = p2.get("android_version", "")
    row["browsers_include"] = p2.get("browsers_include", "")
    row["browser_language"] = p2.get("browser_language", "")
    row["postal_codes"] = p2.get("postal_codes", "")
    row["isp_country"] = p2.get("isp_country", "")
    row["isp_name"] = p2.get("isp_name", "")
    row["ip_range_start"] = p2.get("ip_range_start", "")
    row["ip_range_end"] = p2.get("ip_range_end", "")
    row["income_segment"] = p2.get("income_segment", "")
    row["retargeting_type"] = p2.get("retargeting_type", "")
    row["retargeting_mode"] = p2.get("retargeting_mode", "")
    row["retargeting_value"] = p2.get("retargeting_value", "")
    row["vr_mode"] = p2.get("vr_mode", "")
    row["segment_targeting"] = p2.get("segment_targeting", "")

    # Toggle indicator columns (derived from presence of data)
    row["browser_targeting"] = "TRUE" if row["browsers_include"] else ""
    row["postal_code_targeting"] = "TRUE" if row["postal_codes"] else ""
    row["isp_targeting"] = (
        "TRUE" if (row["isp_country"] and row["isp_name"]) else ""
    )
    row["ip_targeting"] = (
        "TRUE" if (row["ip_range_start"] and row["ip_range_end"]) else ""
    )
    row["income_targeting"] = "TRUE" if row["income_segment"] else ""
    row["retargeting"] = "TRUE" if row["retargeting_value"] else ""
    row["vr_targeting"] = "TRUE" if row["vr_mode"] else ""

    # ── Page 3: Tracking & Bids ───────────────────────────────────
    row["tracker_id"] = p3.get("tracker_id", "")
    row["smart_bidder"] = p3.get("smart_bidder", "")
    row["optimization_option"] = p3.get("optimization_option", "")
    row["target_cpa"] = p3.get("target_cpa", "5.00")
    row["per_source_test_budget"] = p3.get("per_source_test_budget", "5.00")
    row["max_bid"] = p3.get("max_bid", "0.30")

    # ── Page 4: Schedule & Budget ─────────────────────────────────
    row["start_date"] = p4.get("start_date", "")
    row["end_date"] = p4.get("end_date", "")
    row["schedule_dayparting"] = p4.get("schedule_dayparting", "")
    row["frequency_cap"] = p4.get("frequency_cap", "")
    row["frequency_cap_every"] = p4.get("frequency_cap_every", "")
    row["budget_type"] = p4.get("budget_type", "custom")
    row["daily_budget"] = p4.get("daily_budget", "25.00")

    return row


# ═══════════════════════════════════════════════════════════════════
# CSV WRITER
# ═══════════════════════════════════════════════════════════════════

def write_csv(row: dict, output_path: Path):
    """Write a single-row V4 CSV with the full 64-column header."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=V4_HEADER)
        writer.writeheader()
        writer.writerow({col: row.get(col, "") for col in V4_HEADER})

    logger.info(f"CSV written: {output_path}")


# ═══════════════════════════════════════════════════════════════════
# MAIN EXPORT FLOW
# ═══════════════════════════════════════════════════════════════════

def export_campaign(
    campaign_id: str,
    output: str = None,
    headless: bool = False,
    slow_mo: int = 500,
):
    """Scrape all campaign pages and export V4 CSV."""
    logger.info("=" * 60)
    logger.info(f"Campaign Export V4 — ID: {campaign_id}")
    logger.info("=" * 60)

    output_path = Path(output) if output else OUTPUT_DIR / f"{campaign_id}_export.csv"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=slow_mo)

        # ── Auth — try saved session first ────────────────────────
        authenticator = TJAuthenticator(Config.TJ_USERNAME, Config.TJ_PASSWORD)
        context = authenticator.load_session(browser)
        logged_in = False
        if context:
            context.set_default_timeout(30000)
            page = context.new_page()
            page.set_default_timeout(30000)
            # Quick check — navigate to campaign page and verify form fields load
            try:
                page.goto(f"{BASE_URL}/campaign/{campaign_id}",
                          wait_until="domcontentloaded", timeout=30000)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                time.sleep(2)
                url = page.url
                title = page.title()
                has_form = page.evaluate('document.querySelectorAll("input, select").length > 0')
                if "sign-in" in url or "404" in title or not has_form:
                    logger.info(f"Saved session invalid (url={url}, title={title}, forms={has_form})")
                    page.close()
                    context.close()
                else:
                    logged_in = True
                    logger.info("Logged in via saved session")
            except Exception as e:
                logger.info(f"Saved session check failed: {e}")
                page.close()
                context.close()

        if not logged_in:
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            page.set_default_timeout(30000)
            logger.info("Logging in (solve reCAPTCHA if prompted)...")
            if not authenticator.manual_login(page, timeout=180):
                logger.error("Login failed!")
                browser.close()
                return
            authenticator.save_session(context)
            logger.info("Logged in successfully")

        # ── Read all pages ────────────────────────────────────────
        try:
            p1 = read_page1(page, campaign_id)
            p2 = read_page2(page, campaign_id)
            p3 = read_page3(page, campaign_id)
            p4 = read_page4(page, campaign_id)
            ads = read_ads(page, campaign_id)
        except Exception as e:
            logger.error(f"Failed to read campaign: {e}")
            traceback.print_exc()
            browser.close()
            return

        browser.close()

    # ── Build & write campaign CSV ────────────────────────────────
    row = build_csv_row(p1, p2, p3, p4)

    # ── Write ad CSV ──────────────────────────────────────────────
    ad_format = p1.get("ad_format_type", "display")
    format_type = p1.get("format_type", "")
    ad_type = p1.get("ad_type", "")
    ad_csv_name = f"{campaign_id}_ads.csv"
    ad_csv_path = OUTPUT_DIR / ad_csv_name
    ad_result = write_ad_csv(ads, ad_format, ad_csv_path, format_type=format_type, ad_type=ad_type)

    # Auto-populate csv_file in campaign CSV
    if ad_result:
        row["csv_file"] = ad_csv_name

    write_csv(row, output_path)

    # ── Summary ───────────────────────────────────────────────────
    logger.info("")
    logger.info("=" * 60)
    logger.info("EXPORT COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Campaign: {p1.get('_name', campaign_id)}")
    logger.info(f"Campaign CSV: {output_path}")
    if ad_result:
        logger.info(f"Ad CSV:       {ad_csv_path} ({len(ads)} ads)")
    logger.info("")
    logger.info(f"Auto-detected: variants={row['variants']}, language={row['language']}")


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Export a TrafficJunky campaign as a V4-compatible CSV row",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python export_campaign_v4.py 1013321421
  python export_campaign_v4.py 1013321421 --output my_base.csv
  python export_campaign_v4.py 1013321421 --headless
        """,
    )
    parser.add_argument("campaign_id", type=str, help="Campaign ID to export")
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Custom output CSV path (default: data/output/V4_Campaign_Export/<id>_export.csv)",
    )
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    parser.add_argument(
        "--slow-mo", type=int, default=500, help="Slow-motion delay in ms (default: 500)",
    )

    args = parser.parse_args()
    export_campaign(
        campaign_id=args.campaign_id,
        output=args.output,
        headless=args.headless,
        slow_mo=args.slow_mo,
    )


if __name__ == "__main__":
    main()

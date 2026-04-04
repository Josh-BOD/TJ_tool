"""Campaign field updater — pushes changed fields back to TJ via Playwright."""

import sys
import json
import logging
import time
from pathlib import Path
from playwright.sync_api import Page

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from v4.utils import (
    wait_and_fill,
    set_radio,
    select2_choose,
    select2_clear_all,
    enable_toggle,
    disable_toggle,
    click_save_and_continue,
    dismiss_modals,
    safe_click,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://advertiser.trafficjunky.com"

# ═══════════════════════════════════════════════════════════════════
# Field → Page mapping
# ═══════════════════════════════════════════════════════════════════

FIELD_TO_PAGE = {}

PAGE1_FIELDS = {
    "content_rating", "group", "labels", "exchange_id",
    "device", "ad_format_type", "format_type", "ad_type",
    "ad_dimensions", "content_category", "gender",
}

PAGE2_FIELDS = {
    "geo", "os_include", "os_exclude", "ios_version_op", "ios_version",
    "android_version_op", "android_version", "browsers_include", "browser_language",
    "postal_codes", "isp_country", "isp_name", "ip_range_start", "ip_range_end",
    "income_segment", "retargeting_type", "retargeting_mode", "retargeting_value",
    "vr_mode", "segment_targeting", "keywords", "match_type",
}

PAGE3_FIELDS = {
    "tracker_id", "target_cpa", "per_source_test_budget", "max_bid",
    "smart_bidder", "optimization_option",
}

PAGE4_FIELDS = {
    "start_date", "end_date", "schedule_dayparting",
    "frequency_cap", "frequency_cap_every", "budget_type", "daily_budget",
}

for f in PAGE1_FIELDS:
    FIELD_TO_PAGE[f] = 1
for f in PAGE2_FIELDS:
    FIELD_TO_PAGE[f] = 2
for f in PAGE3_FIELDS:
    FIELD_TO_PAGE[f] = 3
for f in PAGE4_FIELDS:
    FIELD_TO_PAGE[f] = 4

# Reverse value maps (human-readable -> form value)
DEVICE_MAP = {"all": "1", "desktop": "2", "mobile": "3"}
AD_FORMAT_MAP = {"display": "1", "instream": "2", "pop": "3"}
FORMAT_TYPE_MAP = {"banner": "4", "native": "5"}
AD_TYPE_MAP = {"static_banner": "1", "video_banner": "2", "video_file": "5", "rollover": "9"}
GENDER_MAP = {"all": "1", "male": "2", "female": "3"}
CONTENT_CATEGORY_MAP = {"straight": "straight", "gay": "gay", "trans": "trans"}

COUNTRY_MAP = {
    "US": "United States", "CA": "Canada", "GB": "United Kingdom",
    "UK": "United Kingdom", "DE": "Germany", "FR": "France",
    "ES": "Spain", "IT": "Italy", "NL": "Netherlands",
    "AU": "Australia", "BR": "Brazil", "JP": "Japan", "MX": "Mexico",
    "IN": "India", "SE": "Sweden", "NO": "Norway",
    "DK": "Denmark", "FI": "Finland", "PL": "Poland", "CZ": "Czechia",
    "AT": "Austria", "CH": "Switzerland", "BE": "Belgium", "IE": "Ireland",
    "NZ": "New Zealand", "AR": "Argentina", "CO": "Colombia", "CL": "Chile",
    "PT": "Portugal", "RO": "Romania", "HU": "Hungary", "GR": "Greece",
    "ZA": "South Africa", "SG": "Singapore", "MY": "Malaysia", "PH": "Philippines",
    "TH": "Thailand", "ID": "Indonesia", "VN": "Vietnam", "KR": "South Korea",
    "TW": "Taiwan", "HK": "Hong Kong", "TR": "Turkey", "RU": "Russia",
    "UA": "Ukraine", "IL": "Israel", "AE": "United Arab Emirates", "SA": "Saudi Arabia",
    "EG": "Egypt", "NG": "Nigeria", "KE": "Kenya", "PE": "Peru",
    "BB": "Barbados", "JM": "Jamaica", "TT": "Trinidad and Tobago",
    "DO": "Dominican Republic", "CR": "Costa Rica", "PA": "Panama",
    "EC": "Ecuador", "UY": "Uruguay", "PY": "Paraguay", "BO": "Bolivia",
    "GT": "Guatemala", "HN": "Honduras", "SV": "El Salvador", "NI": "Nicaragua",
    "PR": "Puerto Rico", "CU": "Cuba", "HT": "Haiti",
}

LANGUAGE_MAP = {
    "EN": "English", "FR": "French", "DE": "German", "ES": "Spanish",
    "IT": "Italian", "PT": "Portuguese", "NL": "Dutch", "JA": "Japanese",
    "KO": "Korean", "ZH": "Chinese", "PL": "Polish", "RU": "Russian",
    "TR": "Turkish", "AR": "Arabic", "CS": "Czech", "SV": "Swedish",
    "DA": "Danish", "NO": "Norwegian", "FI": "Finnish", "HU": "Hungarian",
    "RO": "Romanian", "TH": "Thai",
}

# Step URLs for editing
STEP_URLS = {
    1: "{base}/campaign/{cid}",
    2: "{base}/campaign/{cid}/audience",
    3: "{base}/campaign/{cid}/tracking-spots-rules",
    4: "{base}/campaign/{cid}/schedule-budget",
}


def _pages_needed(fields: dict) -> set[int]:
    """Determine which pages need to be visited to update the given fields."""
    pages = set()
    for field_name in fields:
        page_num = FIELD_TO_PAGE.get(field_name)
        if page_num:
            pages.add(page_num)
        else:
            logger.warning(f"Unknown field '{field_name}', skipping")
    return pages


# ═══════════════════════════════════════════════════════════════════
# Page 1: Basic Settings
# ═══════════════════════════════════════════════════════════════════

def _apply_page1_fields(page: Page, fields: dict):
    """Apply changed fields on page 1 (basic settings)."""
    if "device" in fields:
        val = DEVICE_MAP.get(fields["device"], fields["device"])
        set_radio(page, "platform_id", val)

    if "ad_format_type" in fields:
        val = AD_FORMAT_MAP.get(fields["ad_format_type"], fields["ad_format_type"])
        set_radio(page, "ad_format_id", val)

    if "format_type" in fields:
        val = FORMAT_TYPE_MAP.get(fields["format_type"], fields["format_type"])
        set_radio(page, "format_type_id", val)

    if "ad_type" in fields:
        val = AD_TYPE_MAP.get(fields["ad_type"], fields["ad_type"])
        set_radio(page, "ad_type_id", val)

    if "ad_dimensions" in fields:
        # ad_dimensions is a radio button group (ad_dimension_id)
        # Value is the dimension string like "300x250" — map to radio value
        dim_val = fields["ad_dimensions"]
        # Try setting by value directly first, fall back to JS
        try:
            set_radio(page, "ad_dimension_id", dim_val)
        except Exception:
            # Try clicking label with matching text
            safe_click(page, f'label:has-text("{dim_val}")')
        logger.info(f"  Ad dimensions: {dim_val}")

    if "gender" in fields:
        val = GENDER_MAP.get(fields["gender"], fields["gender"])
        set_radio(page, "demographic_targeting_id", val)

    if "content_rating" in fields:
        val = fields["content_rating"].upper()
        # TJ uses "nsfw"/"sfw" as radio values
        set_radio(page, "content_rating", val.lower())

    if "content_category" in fields:
        val = fields["content_category"].lower()
        # content_category_id radio: straight, gay, trans
        set_radio(page, "content_category_id", val)
        logger.info(f"  Content category: {val}")

    if "exchange_id" in fields:
        # exchange_id is a <select> element
        val = fields["exchange_id"]
        page.evaluate(f'''() => {{
            const sel = document.querySelector("select#exchange_id");
            if (sel) {{
                sel.value = "{val}";
                sel.dispatchEvent(new Event("change", {{bubbles: true}}));
            }}
        }}''')
        logger.info(f"  Exchange: {val}")

    if "group" in fields:
        wait_and_fill(page, "#group", fields["group"])

    if "labels" in fields:
        # Labels: comma-separated string. Remove existing, add new via select2.
        labels = [l.strip() for l in fields["labels"].split(",") if l.strip()]
        logger.info(f"  Setting labels: {labels}")

        # Remove all existing labels
        for _ in range(20):
            delete_btn = page.locator(".deleteLabel").first
            if delete_btn.count() > 0 and delete_btn.is_visible():
                try:
                    delete_btn.click(timeout=1000)
                    time.sleep(0.2)
                except Exception:
                    break
            else:
                break

        # Add new labels via select2
        labels_input = page.locator('input.select2-search__field[placeholder="Select or Input a Label"]')
        if labels_input.count() > 0:
            labels_input.click()
            time.sleep(0.3)
            for label in labels:
                labels_input.fill(label)
                time.sleep(0.5)
                try:
                    option = page.locator('li.select2-results__option').first
                    option.wait_for(state='visible', timeout=2000)
                    option.click()
                except Exception:
                    page.keyboard.press("Enter")
                time.sleep(0.3)
            page.keyboard.press("Escape")
            time.sleep(0.3)
            logger.info(f"  Labels set: {labels}")
        else:
            logger.warning("  Labels input not found")


# ═══════════════════════════════════════════════════════════════════
# Page 2: Audience & Targeting
# ═══════════════════════════════════════════════════════════════════

def _apply_page2_fields(page: Page, fields: dict):
    """Apply changed fields on page 2 (audience & targeting)."""

    # ── Geo ──────────────────────────────────────────────────────
    if "geo" in fields:
        _update_geo(page, fields["geo"])

    # ── OS targeting ─────────────────────────────────────────────
    if "os_include" in fields or "os_exclude" in fields:
        _update_os_targeting(page, fields)

    # ── iOS version ──────────────────────────────────────────────
    # (Handled within os_include if both present; standalone otherwise)
    if ("ios_version_op" in fields or "ios_version" in fields) and "os_include" not in fields:
        logger.info("  iOS version fields without os_include — skipping (version set during OS add)")

    # ── Android version ──────────────────────────────────────────
    if ("android_version_op" in fields or "android_version" in fields) and "os_include" not in fields:
        logger.info("  Android version fields without os_include — skipping (version set during OS add)")

    # ── Browser targeting ────────────────────────────────────────
    if "browsers_include" in fields:
        _update_browser_targeting(page, fields["browsers_include"])

    # ── Browser language ─────────────────────────────────────────
    if "browser_language" in fields:
        _update_browser_language(page, fields["browser_language"])

    # ── Postal codes ─────────────────────────────────────────────
    if "postal_codes" in fields:
        _update_postal_codes(page, fields)

    # ── ISP targeting ────────────────────────────────────────────
    if "isp_country" in fields or "isp_name" in fields:
        _update_isp_targeting(page, fields)

    # ── IP range ─────────────────────────────────────────────────
    if "ip_range_start" in fields or "ip_range_end" in fields:
        _update_ip_range(page, fields)

    # ── Income / public segment ──────────────────────────────────
    if "income_segment" in fields:
        _update_income_segment(page, fields["income_segment"])

    # ── Retargeting ──────────────────────────────────────────────
    if "retargeting_type" in fields or "retargeting_mode" in fields or "retargeting_value" in fields:
        _update_retargeting(page, fields)

    # ── VR mode ──────────────────────────────────────────────────
    if "vr_mode" in fields:
        _update_vr_mode(page, fields["vr_mode"])

    # ── Segment targeting (with EXCLUDE: support) ────────────────
    if "segment_targeting" in fields:
        _update_segment_targeting(page, fields["segment_targeting"])

    # ── Keywords ─────────────────────────────────────────────────
    if "keywords" in fields:
        _update_keywords(page, fields["keywords"])

    # ── Match type ───────────────────────────────────────────────
    if "match_type" in fields:
        _update_match_type(page, fields["match_type"])


# ── Geo ──────────────────────────────────────────────────────────

def _update_geo(page: Page, geo_value: str):
    """Replace geo targeting with the given countries."""
    if isinstance(geo_value, list):
        geos = geo_value
    else:
        # Parse "US;CA;GB" or "US,CA,GB" or "United States;Canada"
        sep = ";" if ";" in geo_value else ","
        geos = [g.strip() for g in geo_value.split(sep) if g.strip()]

    # Wait for geo section
    try:
        page.wait_for_selector(
            'span[id="select2-geo_country-container"]',
            state="visible", timeout=15000,
        )
    except Exception:
        logger.warning("  Geo selector not found, waiting longer...")
        time.sleep(3)

    # Remove existing geos
    try:
        remove_links = page.locator('a.removeTargetedLocation')
        for i in range(remove_links.count()):
            link = remove_links.nth(0)  # always click first — they shift
            if link.is_visible(timeout=1000):
                link.click()
                time.sleep(0.5)
    except Exception:
        pass

    # Add new geos
    added = 0
    for geo in geos:
        country_name = COUNTRY_MAP.get(geo.upper(), geo)
        try:
            page.click('span[id="select2-geo_country-container"]')
            time.sleep(0.5)
            search = page.locator('input.select2-search__field[placeholder="Type here to search"]')
            search.fill(country_name)
            time.sleep(1)
            option = page.locator('li.select2-results__option').filter(has_text=country_name).first
            option.click(timeout=5000)
            time.sleep(0.3)
            page.wait_for_selector('button#addLocation:not([disabled])', timeout=5000)
            page.click('button#addLocation')
            time.sleep(0.5)
            added += 1
        except Exception as e:
            logger.warning(f"  Could not add geo '{geo}' ({country_name}): {e}")
            try:
                page.keyboard.press("Escape")
                time.sleep(0.3)
            except Exception:
                pass

    logger.info(f"  Geo: {added}/{len(geos)} added")


# ── OS Targeting ─────────────────────────────────────────────────

def _enable_os_section(page: Page):
    """Enable the OS targeting section — scroll, toggle, and force-show content."""
    page.evaluate('''() => {
        const section = document.querySelector("#campaign_operatingSystemsTargeting");
        if (!section) return;
        section.scrollIntoView({block: "center"});
    }''')
    time.sleep(0.5)

    page.click('.onoffswitch-label[data-input="#operating_systems"]')
    time.sleep(1.5)

    try:
        page.wait_for_selector(
            'span[id="select2-operating_systems_list_include-container"]',
            state="visible", timeout=5000,
        )
        logger.info("  OS targeting: section enabled")
    except Exception:
        logger.warning("  OS targeting: select2 still hidden after toggle")


def _update_os_targeting(page: Page, fields: dict):
    """Update OS include/exclude targeting."""
    _enable_os_section(page)
    time.sleep(1)

    # Remove existing OS entries
    try:
        remove_all = page.locator('a.removeAll[data-selection="include"]')
        if remove_all.count() > 0 and remove_all.first.is_visible(timeout=2000):
            remove_all.first.click()
            time.sleep(0.5)
    except Exception:
        pass
    try:
        for _ in range(10):
            btn = page.locator('a.removeOsTarget')
            if btn.count() > 0 and btn.first.is_visible(timeout=1000):
                btn.first.click()
                time.sleep(0.3)
            else:
                break
    except Exception:
        pass

    # Include
    os_include = fields.get("os_include", "")
    if os_include:
        for os_name in os_include.split(";"):
            os_name = os_name.strip()
            if os_name:
                _add_single_os_include(page, os_name, fields)
        logger.info(f"  OS include: {os_include}")

    # Exclude
    os_exclude = fields.get("os_exclude", "")
    if os_exclude:
        for os_name in os_exclude.split(";"):
            os_name = os_name.strip()
            if os_name:
                _add_single_os_exclude(page, os_name)
        logger.info(f"  OS exclude: {os_exclude}")


def _add_single_os_include(page: Page, os_name: str, fields: dict):
    """Add a single OS to the include list with optional version constraint."""
    os_select = page.locator('span[id="select2-operating_systems_list_include-container"]')
    try:
        os_select.wait_for(state="visible", timeout=10000)
        os_select.scroll_into_view_if_needed()
        os_select.click(timeout=5000)
    except Exception:
        logger.warning("  OS select2 not visible after waiting")
        return
    time.sleep(0.5)
    try:
        page.click(f'li.select2-results__option:has-text("{os_name}")')
    except Exception as e:
        logger.warning(f"  Could not select OS {os_name}: {e}")
        page.keyboard.press("Escape")
        return
    time.sleep(0.3)

    # Version constraint
    version_op = ""
    version_val = ""
    if os_name == "iOS":
        version_op = fields.get("ios_version_op", "")
        version_val = fields.get("ios_version", "")
    elif os_name == "Android":
        version_op = fields.get("android_version_op", "")
        version_val = fields.get("android_version", "")

    if version_op and version_val:
        _set_version_constraint(page, version_op, version_val)

    page.click('button.smallButton.greenButton.addOsTarget[data-selection="include"]')
    time.sleep(0.5)
    page.click('body')
    time.sleep(0.3)


def _add_single_os_exclude(page: Page, os_name: str):
    """Add a single OS to the exclude list."""
    try:
        page.click('span[id="select2-operating_systems_list_exclude-container"]')
        time.sleep(0.5)
        page.click(f'li.select2-results__option:has-text("{os_name}")')
        time.sleep(0.3)
        page.click('button.smallButton.redButton.addOsTarget[data-selection="exclude"]')
        time.sleep(0.5)
    except Exception as e:
        logger.warning(f"  Could not exclude OS {os_name}: {e}")


def _set_version_constraint(page: Page, op: str, version: str):
    """Set the version operator and version number."""
    op_label_map = {
        "newer_than": "Newer than",
        "older_than": "Older than",
        "equal": "Equal to",
    }
    label = op_label_map.get(op.lower())
    if not label:
        return
    try:
        page.click('span[id="select2-operating_system_selectors_include-container"]')
        time.sleep(0.5)
        page.click(f'li.select2-results__option:has-text("{label}")')
        time.sleep(0.5)
        page.click('span[id="select2-single_version_include-container"]')
        time.sleep(0.5)
        search = page.locator(
            'input.select2-search__field[aria-controls="select2-single_version_include-results"]'
        )
        search.type(version, delay=100)
        time.sleep(0.5)
        page.wait_for_selector('li.select2-results__option--highlighted', timeout=5000)
        page.click('li.select2-results__option--highlighted')
        time.sleep(0.3)
        logger.info(f"  Version constraint: {label} {version}")
    except Exception as e:
        logger.warning(f"  Could not set version constraint: {e}")


# ── Browser Targeting ────────────────────────────────────────────

def _update_browser_targeting(page: Page, browsers_value: str):
    """Enable browser targeting and select browsers."""
    enable_toggle(page, "campaign_browserTargeting")
    time.sleep(0.5)

    if isinstance(browsers_value, list):
        browsers = browsers_value
    else:
        browsers = [b.strip() for b in browsers_value.split(";") if b.strip()]

    for browser_name in browsers:
        try:
            label = page.locator(f'label:has-text("{browser_name}")').first
            if label.count() > 0:
                label.click()
                time.sleep(0.2)
        except Exception as e:
            logger.warning(f"  Could not select browser {browser_name}: {e}")

    logger.info(f"  Browsers: {', '.join(browsers)}")


# ── Browser Language ─────────────────────────────────────────────

def _update_browser_language(page: Page, lang_value: str):
    """Enable browser language targeting and select language."""
    lang_name = LANGUAGE_MAP.get(lang_value.upper(), lang_value)

    enable_toggle(page, "campaign_browserLanguageTargeting")
    time.sleep(0.5)

    section = page.locator("#campaign_browserLanguageTargeting")
    section.scroll_into_view_if_needed()

    # Remove existing languages
    page.evaluate('''() => {
        const section = document.querySelector("#campaign_browserLanguageTargeting");
        if (!section) return;
        section.querySelectorAll(
            "a.removeBtn, a.removeBrowserLanguage, a[class*='remove'], "
            + "button[class*='remove'], .select2-selection__choice__remove"
        ).forEach(btn => btn.click());
    }''')
    time.sleep(0.5)

    # Click visible remove buttons via Playwright
    while True:
        rm = section.locator("a[class*='remove'], .select2-selection__choice__remove").first
        if rm.count() > 0 and rm.is_visible():
            try:
                rm.click(timeout=1000)
                time.sleep(0.2)
            except Exception:
                break
        else:
            break

    # Select new language via select2
    s2 = section.locator(".select2-container").first
    s2.scroll_into_view_if_needed()
    time.sleep(0.3)
    s2.click()
    time.sleep(0.5)

    search = page.locator(".select2-container--open .select2-search__field")
    search.fill(lang_name)
    time.sleep(0.5)
    try:
        page.locator(".select2-results__option").filter(has_text=lang_name).first.click()
    except Exception as e:
        logger.warning(f"  Could not select language {lang_name}: {e}")
        page.keyboard.press("Escape")
        return
    time.sleep(0.3)

    if page.locator(".select2-container--open").count() > 0:
        page.keyboard.press("Escape")
        time.sleep(0.3)

    logger.info(f"  Browser language: {lang_name}")


# ── Postal Codes ─────────────────────────────────────────────────

def _update_postal_codes(page: Page, fields: dict):
    """Enable postal code targeting and fill codes."""
    enable_toggle(page, "campaign_postalCodeTargeting")
    time.sleep(0.5)

    codes_value = fields["postal_codes"]
    if isinstance(codes_value, list):
        codes_text = ",".join(codes_value)
    else:
        codes_text = codes_value

    # Set country from geo if available
    geo = fields.get("geo", "")
    if geo:
        first_geo = geo.split(";")[0].split(",")[0].strip() if isinstance(geo, str) else geo[0]
        try:
            select2_choose(
                page,
                'span[id="select2-postal_code_country-container"]',
                first_geo,
            )
        except Exception:
            pass

    try:
        page.fill('#postal_codes', codes_text)
        time.sleep(0.3)
    except Exception as e:
        logger.warning(f"  Could not fill postal codes: {e}")

    logger.info(f"  Postal codes: {codes_text}")


# ── ISP Targeting ────────────────────────────────────────────────

def _update_isp_targeting(page: Page, fields: dict):
    """Enable ISP targeting and select ISP."""
    enable_toggle(page, "campaign_ispTargeting")
    time.sleep(0.5)

    isp_country = fields.get("isp_country", "")
    isp_name = fields.get("isp_name", "")

    if isp_country:
        try:
            select2_choose(
                page,
                'span[id="select2-isp_country-container"]',
                isp_country,
            )
        except Exception as e:
            logger.warning(f"  Could not select ISP country: {e}")
        time.sleep(0.5)

    if isp_name:
        try:
            select2_choose(
                page,
                '#isp_name + .select2-container, span[id*="isp_name"]',
                isp_name,
            )
        except Exception as e:
            logger.warning(f"  Could not select ISP: {e}")

    logger.info(f"  ISP: {isp_country} / {isp_name}")


# ── IP Range ─────────────────────────────────────────────────────

def _update_ip_range(page: Page, fields: dict):
    """Enable IP targeting and fill start/end range."""
    enable_toggle(page, "campaign_ipTargeting")
    time.sleep(0.5)

    ip_start = fields.get("ip_range_start", "")
    ip_end = fields.get("ip_range_end", "")

    try:
        if ip_start:
            page.fill('#ip_range_start', ip_start)
        if ip_end:
            page.fill('#ip_range_end', ip_end)
        time.sleep(0.3)
    except Exception as e:
        logger.warning(f"  Could not set IP range: {e}")

    logger.info(f"  IP range: {ip_start} – {ip_end}")


# ── Income / Public Segment ─────────────────────────────────────

def _update_income_segment(page: Page, income_value: str):
    """Enable public segment targeting and select income segment."""
    if not income_value:
        return

    enable_toggle(page, "campaign_publicSegmentTargeting")
    time.sleep(0.5)

    # Select "Income" as segment type
    try:
        page.click('#public_segment_type_income', timeout=3000)
        time.sleep(0.5)
    except Exception:
        safe_click(page, 'label:has-text("Income")')
        time.sleep(0.5)

    # Select specific income segment
    try:
        select2_choose(
            page,
            '#public_segment_income + .select2-container, span[id*="public_segment_income"]',
            income_value,
        )
    except Exception as e:
        logger.warning(f"  Could not select income segment: {e}")

    logger.info(f"  Income segment: {income_value}")


# ── Retargeting ──────────────────────────────────────────────────

def _update_retargeting(page: Page, fields: dict):
    """Enable retargeting and configure type/mode/value."""
    enable_toggle(page, "campaign_retargeting")
    time.sleep(0.5)

    rt_type = fields.get("retargeting_type", "")
    rt_mode = fields.get("retargeting_mode", "")
    rt_value = fields.get("retargeting_value", "")

    if rt_type:
        try:
            page.click(f'#retargeting_type_{rt_type}', timeout=3000)
        except Exception:
            safe_click(page, f'label:has-text("{rt_type.title()}")')
        time.sleep(0.3)

    if rt_mode:
        try:
            page.click(f'#retargeting_mode_{rt_mode}', timeout=3000)
        except Exception:
            safe_click(page, f'label:has-text("{rt_mode.title()}")')
        time.sleep(0.3)

    if rt_value:
        try:
            select2_choose(
                page,
                '#retargeting_value + .select2-container, span[id*="retargeting_value"]',
                rt_value,
                timeout=90000,
            )
        except Exception as e:
            logger.warning(f"  Could not select retargeting value: {e}")

    logger.info(f"  Retargeting: {rt_type} / {rt_mode} / {rt_value}")


# ── VR Mode ──────────────────────────────────────────────────────

def _update_vr_mode(page: Page, vr_value: str):
    """Enable VR targeting and select VR/non-VR."""
    if not vr_value:
        return

    enable_toggle(page, "campaign_virtualReality")
    time.sleep(0.5)

    if vr_value.lower() == "vr":
        safe_click(page, '#virtual_realityVR')
    else:
        safe_click(page, '#virtual_realitynonVR')
    time.sleep(0.3)

    logger.info(f"  VR mode: {vr_value}")


# ── Segment Targeting (with EXCLUDE: support) ────────────────────

def _update_segment_targeting(page: Page, segment_value: str):
    """Enable segment targeting with support for EXCLUDE: prefixed segments.

    Format: "Interested in Hentai;EXCLUDE:Intent to buy VOD-Hentai"
    - Segments without prefix → included (uses proven V4 _configure_segments)
    - Segments with "EXCLUDE:" prefix → excluded (manual modal flow)
    """
    if not segment_value:
        return

    # Parse segments into include/exclude lists
    raw_segments = [s.strip() for s in segment_value.split(";") if s.strip()]
    include_segments = []
    exclude_segments = []
    for seg in raw_segments:
        if seg.upper().startswith("EXCLUDE:"):
            exclude_segments.append(seg[8:].strip())
        else:
            include_segments.append(seg)

    # Skip clearing — let V4 _configure_segments handle everything cleanly
    # _clear_existing_segments(page)  # Disabled: may corrupt form state

    # Process include segments using the proven V4 function
    if include_segments:
        try:
            from v4.steps.step2_geo_audience import _configure_segments as v4_configure_segments
            from v4.models import V4CampaignConfig
            config = V4CampaignConfig(segment_targeting=";".join(include_segments))
            v4_configure_segments(page, config)

            # Deduplicate segments in the hidden field
            page.evaluate('''() => {
                const el = document.getElementById("segments");
                if (!el || !el.value) return;
                try {
                    const data = JSON.parse(el.value);
                    if (data.included) {
                        const seen = new Set();
                        data.included = data.included.filter(s => {
                            if (seen.has(s.id)) return false;
                            seen.add(s.id);
                            return true;
                        });
                    }
                    el.value = JSON.stringify(data);
                } catch(e) {}
            }''')
            logger.info(f"  Segment targeting (included): {len(include_segments)} segment(s) via V4")
        except Exception as e:
            logger.warning(f"  V4 segment include failed, falling back to modal: {e}")
            _apply_segments_modal(page, include_segments, "included", "Include Segment")

    # Debug: check hidden #segments field after include config
    if include_segments:
        seg_debug = page.evaluate('''() => {
            const el = document.getElementById("segments");
            const toggle = document.querySelector("#campaign_segmentTargeting input[type='checkbox']");
            return {
                segmentsField: el ? el.value.substring(0, 500) : "NOT FOUND",
                toggleChecked: toggle ? toggle.checked : null,
                segmentSectionVisible: !!document.querySelector("#campaign_segmentTargeting")
            };
        }''')
        logger.info(f"  [DEBUG] After include config: {seg_debug}")

    # Process exclude segments via manual modal flow
    if exclude_segments:
        # Ensure toggle is on (V4 _configure_segments enables it for includes,
        # but if we only have excludes we need to enable it here)
        if not include_segments:
            enable_toggle(page, "campaign_segmentTargeting")
            time.sleep(0.8)
        _apply_segments_modal(page, exclude_segments, "excluded", "Exclude Segment")

    # Skip dedup — let TJ's own modal JS handle field state
    # Directly writing to el.value may bypass TJ's framework state

    # Debug: check hidden #segments field after all segment config (before save)
    seg_final = page.evaluate('''() => {
        const el = document.getElementById("segments");
        const toggle = document.querySelector("#campaign_segmentTargeting input[type='checkbox']");
        return {
            segmentsField: el ? el.value.substring(0, 500) : "NOT FOUND",
            toggleChecked: toggle ? toggle.checked : null,
        };
    }''')
    logger.info(f"  [DEBUG] Before save — segments field: {seg_final}")


def _clear_existing_segments(page: Page):
    """Remove all existing included and excluded segments."""
    page.evaluate('''() => {
        // Remove included segments
        document.querySelectorAll(
            '#segment_targeting_included .removeSegment, '
            + '#segment_targeting_included a[class*="remove"], '
            + '.included-segments .removeSegment, '
            + '.included-segments a[class*="remove"]'
        ).forEach(btn => btn.click());
        // Remove excluded segments
        document.querySelectorAll(
            '#segment_targeting_excluded .removeSegment, '
            + '#segment_targeting_excluded a[class*="remove"], '
            + '.excluded-segments .removeSegment, '
            + '.excluded-segments a[class*="remove"]'
        ).forEach(btn => btn.click());
    }''')
    time.sleep(0.5)

    # Also try clicking visible remove buttons via Playwright
    for _ in range(20):
        rm = page.locator('.removeSegment, .segment-item a[class*="remove"]').first
        if rm.count() > 0 and rm.is_visible():
            try:
                rm.click(timeout=1000)
                time.sleep(0.2)
            except Exception:
                break
        else:
            break


def _apply_segments_modal(page: Page, segments: list, targeting_type: str, button_text: str):
    """Open the segment modal, search + select segments, and click the action button.

    Args:
        segments: List of segment names to add
        targeting_type: "included" or "excluded"
        button_text: "Include Segment" or "Exclude Segment"
    """
    try:
        # Scroll to segment section and open the modal
        clicked = page.evaluate(f'''() => {{
            const section = document.querySelector("#campaign_segmentTargeting");
            if (section) section.scrollIntoView({{behavior: "instant", block: "center"}});
            const link = document.querySelector(
                'a.openSegmentTargetingModal[data-targeting-segment-type="{targeting_type}"]'
            );
            if (link) {{ link.click(); return true; }}
            return false;
        }}''')
        if not clicked:
            logger.warning(f"  Segment '{targeting_type}' link not found")
            return
        time.sleep(2)

        # Wait for modal to fully load
        for _ in range(15):
            loading = page.evaluate('''() => {
                const modals = document.querySelectorAll('[class*="modal"]');
                for (const m of modals) {
                    if (m.offsetHeight > 0 && m.innerText.includes("Loading")) return true;
                }
                return false;
            }''')
            if not loading:
                break
            time.sleep(1)
        time.sleep(1)

        search_input = page.locator('input[placeholder*="VOD"], input[placeholder*="Try"]').first

        for segment_name in segments:
            search_input.fill("")
            search_input.fill(segment_name)
            time.sleep(1)

            # Wait for search results
            for _ in range(10):
                loading = page.evaluate('''() => {
                    const modals = document.querySelectorAll('[class*="modal"]');
                    for (const m of modals) {
                        if (m.offsetHeight > 0 && m.innerText.includes("Loading")) return true;
                    }
                    return false;
                }''')
                if not loading:
                    break
                time.sleep(1)
            time.sleep(0.5)

            # Click checkbox via JS
            checked = page.evaluate('''(name) => {
                const items = document.querySelectorAll('label, li, [class*="segment"], [class*="Segment"]');
                for (const item of items) {
                    if (item.textContent.includes(name)) {
                        const cb = item.querySelector('input[type="checkbox"]');
                        if (cb && !cb.checked) {
                            cb.click();
                            cb.dispatchEvent(new Event("change", {bubbles: true}));
                            return "checked";
                        }
                        if (cb && cb.checked) return "already checked";
                    }
                }
                return "not found";
            }''', segment_name)

            if "checked" in checked:
                logger.info(f"  ✓ Segment ({targeting_type}): {segment_name}")
            else:
                logger.warning(f"  Segment '{segment_name}' ({targeting_type}): {checked}")

        # Click the action button (Include Segment / Exclude Segment)
        page.evaluate(f'''() => {{
            const buttons = document.querySelectorAll('button');
            for (const b of buttons) {{
                if (b.textContent.includes("{button_text}") && b.offsetHeight > 0) {{
                    b.click();
                    return true;
                }}
            }}
            return false;
        }}''')
        time.sleep(1)

        logger.info(f"  Segment targeting ({targeting_type}): {len(segments)} segment(s) configured")
    except Exception as e:
        logger.warning(f"  Could not set segment targeting ({targeting_type}): {e}")


# ── Keywords ─────────────────────────────────────────────────────

def _update_keywords(page: Page, kw_value):
    """Set keywords via the hidden JSON input."""
    if isinstance(kw_value, str):
        kw_raw = [k.strip() for k in kw_value.split(";") if k.strip()]
    else:
        kw_raw = kw_value

    kw_entries = []
    for kw in kw_raw:
        if isinstance(kw, str) and kw.startswith("[") and kw.endswith("]"):
            kw_entries.append({"keyword": kw[1:-1], "type": "broad"})
        else:
            kw_entries.append({"keyword": kw, "type": "exact"})
    kw_json = json.dumps(kw_entries)

    page.evaluate(f'''() => {{
        const el = document.querySelector("#keywords");
        if (el) {{ el.value = {repr(kw_json)}; el.dispatchEvent(new Event("change", {{bubbles:true}})); }}
    }}''')
    time.sleep(0.3)
    logger.info(f"  Keywords: {len(kw_entries)} keyword(s) set")


# ── Match Type ───────────────────────────────────────────────────

def _update_match_type(page: Page, match_value: str):
    """Set keyword match type (exact or broad)."""
    # Match type is typically set per-keyword in the JSON, but some campaigns
    # have a global match type selector
    val = match_value.lower()
    try:
        if val == "broad":
            safe_click(page, '#match_type_broad, label:has-text("Broad")')
        else:
            safe_click(page, '#match_type_exact, label:has-text("Exact")')
        logger.info(f"  Match type: {val}")
    except Exception as e:
        logger.warning(f"  Could not set match type: {e}")


# ═══════════════════════════════════════════════════════════════════
# Page 3: Tracking & Bids
# ═══════════════════════════════════════════════════════════════════

def _apply_page3_fields(page: Page, fields: dict):
    """Apply changed fields on page 3 (tracking & bids)."""
    if "tracker_id" in fields:
        _update_tracker(page, fields["tracker_id"])

    if "target_cpa" in fields:
        wait_and_fill(page, "#target_cpa", str(fields["target_cpa"]))

    if "per_source_test_budget" in fields:
        wait_and_fill(page, "#per_source_test_budget", str(fields["per_source_test_budget"]))

    if "max_bid" in fields:
        wait_and_fill(page, "#maximum_bid", str(fields["max_bid"]))

    if "smart_bidder" in fields:
        _update_smart_bidder(page, fields["smart_bidder"])

    if "optimization_option" in fields:
        _update_optimization_option(page, fields["optimization_option"])


def _update_tracker(page: Page, tracker_value: str):
    """Set conversion tracker via the select2/search interface."""
    if not tracker_value:
        return

    trackers = [t.strip() for t in tracker_value.split(",") if t.strip()]

    # The tracker is stored as a hidden JSON field #campaign_trackers
    # and selected via a select2 dropdown or search modal
    try:
        # Try the select2 approach (used on most campaigns)
        select2_choose(
            page,
            '#tracker_id + .select2-container, span[id*="tracker"], .tracker-select .select2-container',
            trackers[0],
            timeout=10000,
        )
        logger.info(f"  Tracker: {trackers[0]}")
    except Exception:
        # Fallback: try the checkbox/search approach
        try:
            for tracker_name in trackers:
                # Some campaigns show trackers as checkboxes
                label = page.locator(f'label:has-text("{tracker_name}")').first
                if label.count() > 0:
                    cb = label.locator('input[type="checkbox"]')
                    if cb.count() > 0 and not cb.is_checked():
                        cb.click()
                        time.sleep(0.3)
                    logger.info(f"  Tracker: {tracker_name} (checkbox)")
        except Exception as e:
            logger.warning(f"  Could not set tracker: {e}")


def _update_smart_bidder(page: Page, bidder_value: str):
    """Enable/disable smart bidder and select mode."""
    if not bidder_value:
        # Disable smart bidder
        disable_toggle(page, "automatic_bidding")
        logger.info("  Smart bidder: disabled")
        return

    enable_toggle(page, "automatic_bidding")
    time.sleep(0.5)

    # Select smart_cpm or smart_cpa
    if "cpm" in bidder_value.lower():
        safe_click(page, '#is_bidder_on_smart_cpm, label[for="is_bidder_on_smart_cpm"]')
    elif "cpa" in bidder_value.lower():
        safe_click(page, '#is_bidder_on_smart_cpa, label[for="is_bidder_on_smart_cpa"]')
    time.sleep(0.3)

    logger.info(f"  Smart bidder: {bidder_value}")


def _update_optimization_option(page: Page, opt_value: str):
    """Set optimization option (balanced, aggressive, conservative)."""
    if not opt_value:
        return

    # optimization_option is a radio group
    try:
        set_radio(page, "optimization_option", opt_value.lower())
    except Exception:
        safe_click(page, f'label:has-text("{opt_value.title()}")')
    time.sleep(0.3)

    logger.info(f"  Optimization: {opt_value}")


# ═══════════════════════════════════════════════════════════════════
# Page 4: Schedule & Budget
# ═══════════════════════════════════════════════════════════════════

def _select_budget_radio(page: Page, budget_radio_value: str):
    """Click a budget radio button (unlimited or custom)."""
    radio_id = f"is_unlimited_budget_{budget_radio_value}"
    page.evaluate(f'''() => {{
        const input = document.getElementById("{radio_id}");
        if (input) {{
            input.checked = true;
            input.click();
            input.dispatchEvent(new Event("change", {{bubbles: true}}));
            input.dispatchEvent(new Event("input", {{bubbles: true}}));
        }}
        if (typeof $ !== "undefined") {{
            try {{ $("#{radio_id}").prop("checked", true)
                    .trigger("click").trigger("change"); }} catch(e) {{}}
        }}
        const label = document.querySelector('label[for="{radio_id}"]');
        if (label) label.click();
    }}''')
    time.sleep(1)


def _apply_page4_fields(page: Page, fields: dict):
    """Apply changed fields on page 4 (schedule & budget)."""
    # Handle budget_type switch (unlimited vs custom)
    budget_type = fields.get("budget_type")
    has_daily_budget = "daily_budget" in fields

    if budget_type == "unlimited" or (has_daily_budget and str(fields["daily_budget"]).lower() == "unlimited"):
        _select_budget_radio(page, "unlimited")
        logger.info("  Set budget_type = unlimited")

    elif has_daily_budget or budget_type == "custom":
        _select_budget_radio(page, "custom")

        if has_daily_budget:
            for attempt in range(3):
                ready = page.evaluate('''() => {
                    const f = document.getElementById("daily_budget");
                    return f && f.offsetParent !== null;
                }''')
                if ready:
                    break
                time.sleep(1)
                page.evaluate('''() => {
                    const f = document.getElementById("daily_budget");
                    if (f) {
                        let p = f.closest("div[style*='display: none'], div.hidden, .custom-budget-section");
                        if (p) p.style.display = "";
                        f.style.display = "";
                        f.removeAttribute("disabled");
                    }
                }''')

            budget_val = str(fields["daily_budget"])
            page.evaluate(f'''() => {{
                const f = document.getElementById("daily_budget");
                if (f) {{
                    f.removeAttribute("disabled");
                    f.value = "";
                    f.value = "{budget_val}";
                    f.dispatchEvent(new Event("input", {{bubbles: true}}));
                    f.dispatchEvent(new Event("change", {{bubbles: true}}));
                    if (typeof $ !== "undefined") {{
                        try {{ $("#daily_budget").val("{budget_val}")
                                .trigger("input").trigger("change"); }} catch(e) {{}}
                    }}
                }}
            }}''')
            logger.info(f"  Set daily_budget = {budget_val}")

    if "frequency_cap" in fields:
        enable_toggle(page, "frequency_cap")
        wait_and_fill(page, "#frequency_cap_times", str(fields["frequency_cap"]))

    if "frequency_cap_every" in fields:
        enable_toggle(page, "frequency_cap")
        wait_and_fill(page, "#frequency_cap_every", str(fields["frequency_cap_every"]))

    if "start_date" in fields:
        enable_toggle(page, "duration")
        wait_and_fill(page, "#start_date", fields["start_date"])

    if "end_date" in fields:
        enable_toggle(page, "duration")
        wait_and_fill(page, "#end_date", fields["end_date"])

    if "schedule_dayparting" in fields:
        _update_dayparting(page, fields["schedule_dayparting"])


def _update_dayparting(page: Page, dayparting_value: str):
    """Enable schedule/dayparting and set the dayparting JSON."""
    if not dayparting_value:
        return

    enable_toggle(page, "schedule")
    time.sleep(0.5)

    # Dayparting is stored in a hidden #schedule_list input as JSON
    page.evaluate(f'''() => {{
        const el = document.querySelector("#schedule_list");
        if (el) {{
            el.value = {repr(dayparting_value)};
            el.dispatchEvent(new Event("change", {{bubbles: true}}));
        }}
    }}''')
    time.sleep(0.3)

    logger.info(f"  Dayparting: configured")


# ═══════════════════════════════════════════════════════════════════
# Main update orchestrator
# ═══════════════════════════════════════════════════════════════════

PAGE_APPLIERS = {
    1: _apply_page1_fields,
    2: _apply_page2_fields,
    3: _apply_page3_fields,
    4: _apply_page4_fields,
}


def _save_audience_page(page: Page):
    """Save the audience page using the same modal-handling flow as the campaign builder.

    TJ can show multiple types of modals after audience changes:
    - "Match Suggested CPM" (CPM campaigns)
    - "Review your bids" (bid changes)
    - Generic confirmation modals

    This function clicks Save & Continue, then polls for modals and URL change
    for up to 30 seconds — matching the proven builder flow.
    """
    url_before = page.url
    logger.info(f"  Saving audience page from {url_before}")

    # Click Save & Continue via JS (avoids visibility issues with modals)
    page.evaluate('''() => {
        const btn = document.querySelector("button.confirmAudience.saveAndContinue");
        if (btn) btn.click();
    }''')

    # Poll for modal or URL change for up to 30 seconds
    for i in range(60):
        time.sleep(0.5)

        # Check if URL changed (save succeeded)
        try:
            current_url = page.url
        except Exception:
            logger.info(f"  Page navigated (context destroyed)")
            return
        if current_url != url_before and "sign-in" not in current_url:
            logger.info(f"  After save: {current_url}")
            return

        # Check for and accept any modal
        try:
            modal_result = page.evaluate('''() => {
                const modals = document.querySelectorAll(".modal");
                for (const modal of modals) {
                    if (modal.offsetHeight > 0 && modal.offsetWidth > 0) {
                        const buttons = modal.querySelectorAll("button");
                        // Look for "Match Suggested CPM" first (CPM campaigns)
                        for (const btn of buttons) {
                            const text = btn.textContent.trim();
                            if (text.includes("Match Suggested CPM") && btn.offsetHeight > 0) {
                                btn.click();
                                return "matched_cpm";
                            }
                        }
                        // Accept/confirm buttons (review bids, etc.)
                        for (const btn of buttons) {
                            const text = btn.textContent.trim().toLowerCase();
                            if (btn.offsetHeight > 0 && (
                                text.includes("accept") || text.includes("confirm") ||
                                text.includes("ok") || text.includes("yes") ||
                                text.includes("save") || text.includes("continue")
                            )) {
                                btn.click();
                                return "accepted_" + btn.textContent.trim().substring(0, 20);
                            }
                        }
                        // Click any green/primary button as fallback
                        for (const btn of buttons) {
                            if (btn.offsetHeight > 0 && (btn.classList.contains("greenButton") || btn.classList.contains("btn-primary"))) {
                                btn.click();
                                return "clicked_" + btn.textContent.trim().substring(0, 20);
                            }
                        }
                        return "modal_visible_id=" + modal.id;
                    }
                }
                return "";
            }''')
        except Exception:
            # Page navigation interrupted evaluate — wait and re-check for modals
            # TJ often shows "Review Source Bids" / "Match Suggested CPM" modal
            # at the same time as the page navigation event
            time.sleep(3)
            try:
                landed_url = page.url
                logger.info(f"  Page event during modal check → {landed_url}")

                # If still on audience page, a modal likely appeared — keep polling
                if "/audience" in landed_url:
                    logger.info(f"  Still on audience page — checking for bid review modal...")
                    for retry in range(40):  # 20 more seconds
                        time.sleep(0.5)
                        try:
                            current_url = page.url
                            if current_url != landed_url:
                                logger.info(f"  After modal handling: {current_url}")
                                return

                            modal_result = page.evaluate('''() => {
                                const modals = document.querySelectorAll(".modal");
                                for (const modal of modals) {
                                    if (modal.offsetHeight > 0 && modal.offsetWidth > 0) {
                                        const buttons = modal.querySelectorAll("button");
                                        for (const btn of buttons) {
                                            const text = btn.textContent.trim();
                                            if (text.includes("Match Suggested CPM") && btn.offsetHeight > 0) {
                                                btn.click();
                                                return "matched_cpm";
                                            }
                                        }
                                        for (const btn of buttons) {
                                            if (btn.offsetHeight > 0 && (btn.classList.contains("greenButton") || btn.classList.contains("btn-primary"))) {
                                                btn.click();
                                                return "clicked_" + btn.textContent.trim().substring(0, 20);
                                            }
                                        }
                                        return "modal_visible_id=" + modal.id;
                                    }
                                }
                                return "";
                            }''')
                            if modal_result:
                                logger.info(f"  Modal (retry {retry}): {modal_result}")
                                time.sleep(3)
                                try:
                                    if page.url != landed_url:
                                        logger.info(f"  After modal accept: {page.url}")
                                        return
                                except Exception:
                                    return
                        except Exception:
                            # Page navigated during retry — likely save succeeded
                            try:
                                logger.info(f"  Page navigated during modal retry → {page.url}")
                            except Exception:
                                pass
                            return
                    logger.warning(f"  No modal found after 20s on audience page — save may have failed")
                else:
                    logger.info(f"  Navigated forward — save succeeded")
            except Exception:
                logger.info(f"  Page navigated during modal check (URL unknown)")
            return
        if modal_result:
            logger.info(f"  Modal: {modal_result}")
            time.sleep(3)
            try:
                if page.url != url_before:
                    logger.info(f"  After modal accept: {page.url}")
                    return
            except Exception:
                return
    else:
        try:
            logger.warning(f"  Save & Continue: no navigation after 30s (still on {page.url})")
        except Exception:
            pass


def update_campaign(page: Page, campaign_id: str, fields: dict, dry_run: bool = False) -> dict:
    """
    Update specific campaign fields by navigating to the appropriate pages.

    Args:
        page: Playwright page (already authenticated)
        campaign_id: TJ external campaign ID
        fields: flat dict of field_name -> new_value
        dry_run: if True, navigate and log but don't save

    Returns:
        {"updated_pages": list[int], "fields_applied": list[str]}
    """
    pages_needed = sorted(_pages_needed(fields))
    if not pages_needed:
        return {"updated_pages": [], "fields_applied": []}

    fields_applied = []

    for page_num in pages_needed:
        url = STEP_URLS[page_num].format(base=BASE_URL, cid=campaign_id)
        logger.info(f"Navigating to page {page_num}: {url}")
        page.goto(url, wait_until="networkidle")
        time.sleep(1)
        dismiss_modals(page)

        # Filter fields for this page
        page_fields = {k: v for k, v in fields.items() if FIELD_TO_PAGE.get(k) == page_num}

        applier = PAGE_APPLIERS.get(page_num)
        if applier:
            logger.info(f"Applying {len(page_fields)} field(s) on page {page_num}: {list(page_fields.keys())}")
            applier(page, page_fields)
            fields_applied.extend(page_fields.keys())

        if not dry_run:
            logger.info(f"Saving page {page_num}...")
            if page_num == 2:
                # Page 2 (audience) needs special modal handling — "Match Suggested CPM",
                # "Review your bids", etc. Use the same flow as the campaign builder.
                _save_audience_page(page)
            else:
                click_save_and_continue(page)
        else:
            logger.info(f"[DRY RUN] Skipping save for page {page_num}")

    return {"updated_pages": pages_needed, "fields_applied": fields_applied}

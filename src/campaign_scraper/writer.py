"""Campaign field updater — pushes changed fields back to TJ via Playwright."""

import sys
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
)

logger = logging.getLogger(__name__)

BASE_URL = "https://advertiser.trafficjunky.com"

# Map each field to which page (step) it belongs to
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


def _apply_page1_fields(page: Page, fields: dict):
    """Apply changed fields on page 1 (basic settings)."""
    if "device" in fields:
        val = DEVICE_MAP.get(fields["device"], fields["device"])
        set_radio(page, "device_type", val)

    if "ad_format_type" in fields:
        val = AD_FORMAT_MAP.get(fields["ad_format_type"], fields["ad_format_type"])
        set_radio(page, "ad_format_type", val)

    if "format_type" in fields:
        val = FORMAT_TYPE_MAP.get(fields["format_type"], fields["format_type"])
        set_radio(page, "format_type", val)

    if "ad_type" in fields:
        val = AD_TYPE_MAP.get(fields["ad_type"], fields["ad_type"])
        set_radio(page, "ad_type", val)

    if "gender" in fields:
        val = GENDER_MAP.get(fields["gender"], fields["gender"])
        set_radio(page, "gender", val)

    if "content_rating" in fields:
        set_radio(page, "content_rating", fields["content_rating"])

    if "group" in fields:
        wait_and_fill(page, "#group", fields["group"])


def _apply_page2_fields(page: Page, fields: dict):
    """Apply changed fields on page 2 (audience & targeting)."""
    if "keywords" in fields:
        # Keywords are set via the hidden JSON input; use JS to update
        # Format: [keyword] = broad, keyword = exact, semicolon-separated
        import json
        kw_raw = fields["keywords"]
        if isinstance(kw_raw, str):
            kw_raw = [k.strip() for k in kw_raw.split(";") if k.strip()]
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


def _apply_page3_fields(page: Page, fields: dict):
    """Apply changed fields on page 3 (tracking & bids)."""
    if "target_cpa" in fields:
        wait_and_fill(page, "#target_cpa", str(fields["target_cpa"]))

    if "per_source_test_budget" in fields:
        wait_and_fill(page, "#per_source_test_budget", str(fields["per_source_test_budget"]))

    if "max_bid" in fields:
        wait_and_fill(page, "#max_bid", str(fields["max_bid"]))


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
        # Switch to Unlimited budget
        _select_budget_radio(page, "unlimited")
        logger.info("  Set budget_type = unlimited")

    elif has_daily_budget or budget_type == "custom":
        # Switch to Custom budget and set the value
        _select_budget_radio(page, "custom")

        if has_daily_budget:
            # Wait for budget field to become visible, force-show if needed
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

            # Set budget via JS (most reliable)
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


PAGE_APPLIERS = {
    1: _apply_page1_fields,
    2: _apply_page2_fields,
    3: _apply_page3_fields,
    4: _apply_page4_fields,
}


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
            click_save_and_continue(page)
        else:
            logger.info(f"[DRY RUN] Skipping save for page {page_num}")

    return {"updated_pages": pages_needed, "fields_applied": fields_applied}

"""Wraps export_campaign_v4.py read functions into a single scrape_campaign() call."""

import re
import sys
import logging
from pathlib import Path
from playwright.sync_api import Page

# Add project root to path so we can import export_campaign_v4
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from export_campaign_v4 import read_overview, read_page1, read_page2, read_page3, read_page4, read_ads, build_csv_row

logger = logging.getLogger(__name__)

# Fields that read_overview must supply to skip Page 1
PAGE1_REQUIRED = [
    "content_rating", "group", "labels", "exchange_id",
    "device", "ad_format_type", "format_type", "ad_type",
    "ad_dimensions", "content_category", "gender",
]


def scrape_campaign(page: Page, campaign_id: str) -> dict:
    """
    Scrape campaign overview + pages 2-4 + ads, returning merged fields and ad list.
    Reads the overview page first — if it has all Page 1 fields, skips Page 1 entirely.

    Returns:
        {"fields": dict (64 V4 columns), "ads": list[dict]}
    """
    # ── Step 1: Read overview page ─────────────────────────────────
    logger.info(f"Collecting campaign {campaign_id} - overview")
    overview = read_overview(page, campaign_id)

    # ── Step 2: Decide whether to skip Page 1 ─────────────────────
    all_present = all(overview.get(f) for f in PAGE1_REQUIRED)

    if all_present:
        logger.info(f"Overview has all Page 1 fields — skipping page 1")
        p1 = overview
    else:
        missing = [f for f in PAGE1_REQUIRED if not overview.get(f)]
        logger.info(f"Overview missing {missing} — reading page 1")
        p1 = read_page1(page, campaign_id)

    # ── Step 3: Read pages 2, 3, 4 as normal ──────────────────────
    logger.info(f"Collecting campaign {campaign_id} - page 2/4 (audience & targeting)")
    p2 = read_page2(page, campaign_id)

    logger.info(f"Collecting campaign {campaign_id} - page 3/4 (tracking & bids)")
    p3 = read_page3(page, campaign_id)

    logger.info(f"Collecting campaign {campaign_id} - page 4/4 (schedule & budget)")
    p4 = read_page4(page, campaign_id)

    # ── Step 4: Build CSV row ─────────────────────────────────────
    logger.info(f"Building CSV row from collected data")
    fields = build_csv_row(p1, p2, p3, p4)

    # Include the raw campaign name
    fields["_name"] = p1.get("_name", "")

    # ── Step 5: Managed campaign freq cap from overview ────────────
    if p4.get("_managed_campaign") and overview.get("frequency_cap"):
        fields["frequency_cap"] = overview["frequency_cap"]
        fields["frequency_cap_every"] = overview.get("frequency_cap_every", "24")
        logger.info(f"  Freq cap (from overview): {fields['frequency_cap']} times / {fields['frequency_cap_every']}h")
    elif p4.get("_managed_campaign"):
        _read_overview_frequency(page, campaign_id, fields)

    # ── Step 6: Read ads ──────────────────────────────────────────
    logger.info(f"Collecting ads for campaign {campaign_id}")
    ads = read_ads(page, campaign_id)
    logger.info(f"Found {len(ads)} ads")

    return {"fields": fields, "ads": ads}


def _read_overview_frequency(page: Page, campaign_id: str, fields: dict):
    """Fallback: check the overview page for frequency cap if not already captured."""
    url = f"https://advertiser.trafficjunky.com/campaign/overview/{campaign_id}"
    logger.info(f"Managed campaign detected, checking overview for freq cap: {url}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        text = page.evaluate("""() => {
            const labels = document.querySelectorAll('label');
            for (const label of labels) {
                if (/frequency capping/i.test(label.textContent)) {
                    const container = label.closest('.form-row') || label.parentElement;
                    return container?.textContent || '';
                }
            }
            return '';
        }""")

        match = re.search(r"Displaying\s+(\d+)\s+time.*?every\s+(\d+)\s+day", text)
        if match:
            fields["frequency_cap"] = match.group(1)
            days = int(match.group(2))
            fields["frequency_cap_every"] = str(days * 24)
            logger.info(f"  Freq cap (from overview): {fields['frequency_cap']} times / {days} day(s) ({fields['frequency_cap_every']}h)")
        else:
            logger.info("  Freq cap: not found on overview page either")
    except Exception as e:
        logger.warning(f"  Failed to read overview frequency cap: {e}")

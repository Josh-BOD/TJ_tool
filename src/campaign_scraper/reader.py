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

from export_campaign_v4 import read_page1, read_page2, read_page3, read_page4, read_ads, build_csv_row

logger = logging.getLogger(__name__)


def scrape_campaign(page: Page, campaign_id: str) -> dict:
    """
    Scrape all 4 campaign pages + ads, returning merged fields and ad list.

    Returns:
        {"fields": dict (64 V4 columns), "ads": list[dict]}
    """
    logger.info(f"Scraping campaign {campaign_id} - page 1/4 (basic settings)")
    p1 = read_page1(page, campaign_id)

    logger.info(f"Scraping campaign {campaign_id} - page 2/4 (audience & targeting)")
    p2 = read_page2(page, campaign_id)

    logger.info(f"Scraping campaign {campaign_id} - page 3/4 (tracking & bids)")
    p3 = read_page3(page, campaign_id)

    logger.info(f"Scraping campaign {campaign_id} - page 4/4 (schedule & budget)")
    p4 = read_page4(page, campaign_id)

    logger.info(f"Building CSV row from scraped data")
    fields = build_csv_row(p1, p2, p3, p4)

    # Include the raw campaign name from page 1
    fields["_name"] = p1.get("_name", "")

    # Fallback: managed campaigns only show frequency cap on the overview page
    if not fields.get("frequency_cap"):
        _read_overview_frequency(page, campaign_id, fields)

    logger.info(f"Scraping ads for campaign {campaign_id}")
    ads = read_ads(page, campaign_id)
    logger.info(f"Found {len(ads)} ads")

    return {"fields": fields, "ads": ads}


def _read_overview_frequency(page: Page, campaign_id: str, fields: dict):
    """Check the overview page for frequency cap (managed campaigns hide it from edit pages)."""
    url = f"https://advertiser.trafficjunky.com/campaign/overview/{campaign_id}"
    logger.info(f"Freq cap empty, checking overview page: {url}")
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

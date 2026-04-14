"""Collect CPM placement data from TJ campaign tracking/sources page."""

import time
import logging
from playwright.sync_api import Page

logger = logging.getLogger(__name__)

BASE_URL = "https://advertiser.trafficjunky.com"


def scrape_cpm_placements(page: Page, campaign_id: str) -> dict:
    """
    Navigate to a campaign's tracking/sources page and extract CPM data
    from the source selection table.

    Returns:
        {
            "placements": [
                {
                    "spot_id": str | None,       # source ID from checkbox data-source-id
                    "site": str | None,           # site network name
                    "source_id": str | None,      # same as spot_id
                    "source_name": str | None,    # detailed source description
                    "position": str | None,       # e.g. "Above the fold"
                    "status": str | None,
                    "country": str | None,
                    "min_cpm": float | None,
                    "suggested_cpm": float | None,
                    "your_current_cpm": float | None,
                },
                ...
            ],
            "scraped_at": str (ISO),
            "format": "cpm_placements",
            "source_count": int,
        }
    """
    url = f"{BASE_URL}/campaign/{campaign_id}/tracking-spots-rules"
    logger.info(f"[CPM Collect] Navigating to {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(2)

    # Check if we landed on the login page (session expired)
    current_url = page.url
    is_login_page = page.evaluate('''() => {
        const h1 = document.querySelector("h1");
        if (h1 && h1.textContent.includes("We missed you")) return true;
        const loginForm = document.querySelector("form[action*='login'], input[name='password']");
        if (loginForm) return true;
        return false;
    }''')
    if is_login_page or "/login" in current_url:
        raise RuntimeError(f"Not authenticated — landed on login page (url: {current_url}). Session may be expired.")

    # Show all entries in source table (try both table variants)
    for table_name in ['sourceSelectionTable_length', 'includedSourcesTable_length']:
        try:
            page.select_option(f'select[name="{table_name}"]', '100')
            time.sleep(2)
            break
        except Exception:
            continue

    # Click Refresh to get fresh CPM bids
    try:
        page.evaluate('''() => {
            const links = document.querySelectorAll("a");
            for (const a of links) {
                if (a.textContent.trim() === "Refresh") {
                    a.click();
                    return true;
                }
            }
            return false;
        }''')
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        time.sleep(3)
    except Exception:
        logger.debug("Could not click Refresh link")

    # Extract placement data from source table via JS
    # DOM structure per row (from debug):
    #   cells: checkbox | status | site_name | source_id | source_desc | position | min_cpm | suggested_cpm | your_cpm
    #   input.tableCheckbox has: data-source-id, data-suggested-cpm, data-geo-id, data-original-cpm, value=source_id
    placements = page.evaluate('''() => {
        const results = [];

        let table = document.querySelector("#sourceSelectionTable") ||
                    document.querySelector("#includedSourcesTable");
        if (!table) return results;

        const rows = table.querySelectorAll("tbody tr");
        for (const row of rows) {
            // Check if this source is included
            const statusWrap = row.querySelector(".sourceStatusWrap");
            if (statusWrap && statusWrap.getAttribute("data-status") !== "included") continue;

            // Site name — third cell (first minWidth100 without text-right)
            const siteCell = row.querySelector("td.minWidth100:not(.text-right)");
            const siteName = siteCell ? siteCell.textContent.trim() : null;

            // Checkbox input has the key data attributes
            const checkbox = row.querySelector("input.tableCheckbox");

            // Source ID from checkbox data-source-id or value
            const sourceId = checkbox ?
                (checkbox.getAttribute("data-source-id") || checkbox.value) : null;

            // Geo ID from checkbox
            const geoId = checkbox ? checkbox.getAttribute("data-geo-id") : null;

            // Source description (position name) — 5th cell: second minWidth100 without text-right
            const minWidth100Cells = row.querySelectorAll("td.minWidth100:not(.text-right)");
            const sourceDesc = minWidth100Cells.length >= 2 ? minWidth100Cells[1].textContent.trim() : null;

            // Position (e.g. "Above the fold") — 6th cell: third minWidth100 without text-right
            const position = minWidth100Cells.length >= 3 ? minWidth100Cells[2].textContent.trim() : null;

            // CPM values from data attributes (most reliable)
            let suggestedCpm = checkbox ? parseFloat(checkbox.getAttribute("data-suggested-cpm")) : null;
            if (isNaN(suggestedCpm)) suggestedCpm = null;

            let yourCurrentCpm = checkbox ? parseFloat(checkbox.getAttribute("data-original-cpm")) : null;
            if (isNaN(yourCurrentCpm)) yourCurrentCpm = null;

            // Min CPM from the cell text (7th cell: minWidth80 text-right hasSorting)
            let minCpm = null;
            const minCpmCell = row.querySelector("td.minWidth80.text-right.hasSorting");
            if (minCpmCell) {
                const m = minCpmCell.textContent.trim().match(/^\\$([\\d.]+)/);
                if (m) minCpm = parseFloat(m[1]);
            }

            // Fallback: parse $ values from text-right cells if data attrs missing
            if (suggestedCpm === null || minCpm === null || yourCurrentCpm === null) {
                const priceCells = row.querySelectorAll("td.text-right");
                const prices = [];
                for (const cell of priceCells) {
                    const m = cell.textContent.trim().match(/^\\$([\\d.]+)/);
                    if (m) prices.push(parseFloat(m[1]));
                }
                // Order: min_cpm, suggested_cpm, your_cpm
                if (prices.length >= 3) {
                    if (minCpm === null) minCpm = prices[0];
                    if (suggestedCpm === null) suggestedCpm = prices[1];
                    if (yourCurrentCpm === null) yourCurrentCpm = prices[2];
                } else if (prices.length >= 2) {
                    if (minCpm === null) minCpm = prices[0];
                    if (suggestedCpm === null) suggestedCpm = prices[1];
                }
            }

            const status = statusWrap ? statusWrap.getAttribute("data-status") : "included";

            results.push({
                spot_id: sourceId,
                site: siteName,
                source_id: sourceId,
                source_name: sourceDesc || siteName,
                position: position,
                status: status,
                country: null,
                geo_id: geoId,
                min_cpm: minCpm,
                suggested_cpm: suggestedCpm,
                your_current_cpm: yourCurrentCpm,
            });
        }
        return results;
    }''')

    from datetime import datetime, timezone
    scraped_at = datetime.now(timezone.utc).isoformat()

    logger.info(f"[CPM Collect] Found {len(placements)} placements for campaign {campaign_id}")
    if placements:
        logger.info(f"[CPM Collect] Sample: spot_id={placements[0].get('spot_id')}, "
                     f"site={placements[0].get('site')}, "
                     f"suggested={placements[0].get('suggested_cpm')}, "
                     f"your_cpm={placements[0].get('your_current_cpm')}")

    return {
        "placements": placements,
        "scraped_at": scraped_at,
        "format": "cpm_placements",
        "source_count": len(placements),
    }

"""Step 3 — Tracking, Smart Bidder, Sources & Bids."""

import time
import logging
from playwright.sync_api import Page

from ..models import V4CampaignConfig
from ..utils import safe_click, wait_and_fill, select2_choose, enable_toggle

logger = logging.getLogger(__name__)


def configure_step3(page: Page, config: V4CampaignConfig):
    """Configure tracking, bidder, sources, and bid values on Step 3."""
    logger.info("  [Step 3] Configuring tracking & sources...")

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(2)

    # ── Conversion Tracker(s) ─────────────────────────────────────
    if config.tracker_id:
        trackers = [t.strip() for t in config.tracker_id.split(",") if t.strip()]
        for tracker_name in trackers:
            try:
                select2_choose(
                    page,
                    '#campaignTrackerId + .select2-container, '
                    'span[id*="campaignTrackerId"]',
                    tracker_name,
                )
                logger.info(f"    Tracker: {tracker_name}")
            except Exception as e:
                logger.warning(f"    Could not set tracker '{tracker_name}': {e}")

    # ── Sources (Manual must be selected before smart bidder is visible) ─
    _select_manual_sources(page)

    # Determine source inclusion strategy from source_selection field
    ss = (config.source_selection or "").strip().upper()
    if ss and ss != "ALL":
        # Specific sources by name (semicolon-separated)
        source_names = [s.strip() for s in config.source_selection.split(";") if s.strip()]
        _include_specific_sources(page, source_names)
    elif config.include_all_sources or ss == "ALL":
        _include_all_sources(page)

    # Always refresh after source inclusion to get accurate suggested CPMs
    _refresh_sources(page)

    # ── Smart Bidder (requires Manual mode + sources included) ────
    if config.smart_bidder:
        _configure_smart_bidder(page, config)

    # ── Bid Values (reads suggested CPMs from included sources) ───
    if not config.is_cpm:
        _configure_cpa_bids(page, config)
    else:
        _configure_cpm_bids(page, config)


def _configure_smart_bidder(page: Page, config: V4CampaignConfig):
    """Enable smart bidder toggle and select bidding mode + optimization.

    The automatic_bidding checkbox is display:none — click the onoffswitch-label.
    A custom alert dialog ("AUTOMATE BIDDING?") pops up and must be confirmed.
    Radio inputs (smart_cpm/smart_cpa) have pointer-events:none — click the <label>.
    """
    try:
        # Toggle automatic bidding ON via the visible label
        page.click('.onoffswitch-label[data-input="#automatic_bidding"]')
        time.sleep(1)

        # Confirm the "AUTOMATE BIDDING?" custom alert dialog
        try:
            ok_btn = page.locator('.customAlertBox .smallButton.greenButton')
            ok_btn.click(timeout=5000)
            time.sleep(0.5)
            logger.info("    Automatic bidding: ON (confirmed)")
        except Exception:
            logger.info("    Automatic bidding: ON (no confirm dialog)")

        # Select bidding mode — click the parent <label>, not the radio
        bidder = config.smart_bidder.lower()
        if bidder == "smart_cpm":
            page.click('label:has(#is_bidder_on_smart_cpm)')
        elif bidder == "smart_cpa":
            page.click('label:has(#is_bidder_on_smart_cpa)')
        time.sleep(0.3)

        # Select optimization option — only visible for smart_cpa, not smart_cpm
        if config.optimization_option and bidder != "smart_cpm":
            opt = config.optimization_option.lower()
            time.sleep(1)
            try:
                page.click(f'label:has(#optimization_option_{opt})', timeout=5000)
            except Exception:
                try:
                    page.locator(f'label:has(#optimization_option_{opt})').click(force=True)
                except Exception:
                    logger.debug(f"    Optimization option '{opt}' not available")
            time.sleep(0.3)

        logger.info(f"    Smart bidder: {config.smart_bidder} / {config.optimization_option}")
    except Exception as e:
        logger.warning(f"    Could not set smart bidder: {e}")


def _configure_cpa_bids(page: Page, config: V4CampaignConfig):
    """Fill CPA bid fields: target CPA, per-source test budget, max bid."""
    try:
        wait_and_fill(page, 'input#target_cpa', str(config.target_cpa))
        logger.info(f"    Target CPA: {config.target_cpa}")
    except Exception:
        pass

    try:
        wait_and_fill(page, 'input#per_source_test_budget', str(config.per_source_test_budget))
        logger.info(f"    Per-source test budget: {config.per_source_test_budget}")
    except Exception:
        pass

    try:
        wait_and_fill(page, 'input#maximum_bid', str(config.max_bid))
        logger.info(f"    Max bid: {config.max_bid}")
    except Exception:
        pass


def _configure_cpm_bids(page: Page, config: V4CampaignConfig):
    """Handle CPM bidding — optionally adjust max bid from suggested CPMs."""
    if config.cpm_adjust is not None:
        try:
            # Wait for included sources table to populate after source inclusion + smart bidder
            time.sleep(5)

            # Show all entries in included sources table
            try:
                page.select_option(
                    'select[name="includedSourcesTable_length"]', '100'
                )
                time.sleep(3)
            except Exception:
                pass

            highest_bid = page.evaluate('''() => {
                let highest = 0;
                const links = document.querySelectorAll("a[data-your-cpm]");
                for (const a of links) {
                    const val = parseFloat(a.getAttribute("data-your-cpm"));
                    if (!isNaN(val) && val > highest) highest = val;
                }
                if (highest === 0) {
                    document.querySelectorAll("td").forEach(td => {
                        const m = td.textContent.trim().match(/^\\$([\\d.]+)/);
                        if (m) {
                            const val = parseFloat(m[1]);
                            if (val > highest) highest = val;
                        }
                    });
                }
                return highest;
            }''')

            if highest_bid and highest_bid > 0:
                multiplier = 1 + (config.cpm_adjust / 100)
                max_bid = round(highest_bid * multiplier, 2)
                logger.info(
                    f"    Suggested CPM: ${highest_bid} -> "
                    f"Max bid: ${max_bid} (+{config.cpm_adjust}%)"
                )
            else:
                max_bid = config.max_bid
                logger.info(f"    No suggested CPMs found, using default: ${max_bid}")

            bid_input = page.locator("#maximum_bid")
            bid_input.click()
            time.sleep(0.2)
            bid_input.fill(str(max_bid))
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"    CPM adjustment failed: {e}")
    else:
        logger.info("    CPM mode — using template bids (no adjustment)")


def _select_manual_sources(page: Page):
    """Click the label wrapping the manual source selection radio button.

    The radio input itself has pointer-events:none, so we click the parent <label>.
    After switching, wait for the source table to load.
    """
    try:
        page.click('label:has(#is_manual_source_selection_manually)')
        time.sleep(1)
        # Wait for source selection table to appear
        try:
            page.wait_for_selector(
                'select[name="sourceSelectionTable_length"]',
                state="visible", timeout=10000,
            )
            time.sleep(1)
        except Exception:
            time.sleep(2)
        logger.info("    Sources: switched to manual selection")
    except Exception as e:
        logger.warning(f"    Could not switch to manual sources: {e}")


def _include_all_sources(page: Page):
    """Show all source rows, check all, and click Include."""
    try:
        # Show all rows via JS (native select may be hidden by DataTables styling)
        page.evaluate('''() => {
            const sel = document.querySelector('select[name="sourceSelectionTable_length"]');
            if (sel) {
                sel.value = "100";
                sel.dispatchEvent(new Event("change", {bubbles: true}));
            }
        }''')
        time.sleep(2)

        # Check all checkboxes
        select_all = page.locator(
            'input.checkUncheckAll[data-table="sourceSelectionTable"]'
        )
        if select_all.count() > 0:
            select_all.check()
            time.sleep(0.3)
            # Click the bulk Include button
            page.locator('.statusActionRow > button.includeBtn').first.click()
            time.sleep(1)
            logger.info("    Sources: all included")
        else:
            logger.warning("    Source select-all checkbox not found on page")
    except Exception as e:
        logger.warning(f"    Source inclusion failed: {e}")


def _include_specific_sources(page: Page, source_names: list):
    """Include only the named sources from the source selection table."""
    included = 0
    skipped = 0

    try:
        # Show all rows in the source selection table
        try:
            page.select_option(
                'select[name="sourceSelectionTable_length"]', '100'
            )
            time.sleep(1)
        except Exception:
            pass

        for name in source_names:
            try:
                row = page.locator(f'tr:has(td.minWidth100:text-is("{name}"))')
                include_btn = row.locator('button.includeBtn[data-btn-action="include"]')
                if include_btn.is_visible(timeout=3000):
                    include_btn.click()
                    time.sleep(0.5)
                    included += 1
                    logger.info(f"    Source included: {name}")
                else:
                    skipped += 1
                    logger.warning(f"    Source not found or already included: {name}")
            except Exception as e:
                skipped += 1
                logger.warning(f"    Could not include source '{name}': {e}")

        logger.info(f"    Sources: {included} included, {skipped} skipped")
    except Exception as e:
        logger.warning(f"    Specific source selection failed: {e}")


def _refresh_sources(page: Page):
    """Click the Refresh link to reload suggested CPM bids from server."""
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
        time.sleep(2)
        logger.info("    Sources: refreshed CPM bids")
    except Exception as e:
        logger.warning(f"    Could not refresh sources: {e}")

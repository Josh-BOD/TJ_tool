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
        sep = ";" if ";" in config.tracker_id else ","
        trackers = [t.strip() for t in config.tracker_id.split(sep) if t.strip()]
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

    # Include sources — filtered by source_selection or all
    ss = (config.source_selection or "").strip()
    if ss and ss.upper() != "ALL":
        # Support multiple sources separated by semicolons (e.g. "Tube8;Redtube")
        terms = [t.strip() for t in ss.split(";") if t.strip()]
        for term in terms:
            _include_matching_sources(page, term)
    else:
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
    """Handle CPM bidding with three modes:

    - suggested (default): Match Suggested CPM, then optionally adjust by cpm_adjust %
    - min: Read each source's min CPM and set bids to min (+ optional % from cpm_bid_value)
    - static: Set all bids to a fixed dollar value, floored at each source's min CPM
    """
    mode = (config.cpm_bid_mode or "suggested").lower()

    try:
        time.sleep(2)

        # Show all included sources
        try:
            page.select_option('select[name="includedSourcesTable_length"]', '100')
            time.sleep(1)
        except Exception:
            pass

        # Select all included source checkboxes
        _select_all_included_sources(page)

        if mode == "min":
            _apply_min_cpm_bids(page, config)
        elif mode == "static":
            _apply_static_cpm_bids(page, config)
        else:
            _apply_suggested_cpm_bids(page, config)

    except Exception as e:
        logger.warning(f"    CPM bid configuration failed: {e}")


def _select_all_included_sources(page: Page):
    """Check all included source checkboxes."""
    select_all = page.query_selector('input.checkUncheckAll[data-table="includedSourcesTable"]')
    if select_all:
        select_all.click()
        time.sleep(0.5)
        logger.info("    Selected all included sources")
    else:
        checkboxes = page.query_selector_all('input.tableCheckbox[data-source-id]')
        for cb in checkboxes:
            if not cb.is_checked():
                cb.click()
                time.sleep(0.1)
        logger.info(f"    Selected {len(checkboxes)} source checkboxes")


def _apply_suggested_cpm_bids(page: Page, config: V4CampaignConfig):
    """Original flow: Match Suggested CPM, then optionally adjust by percentage."""
    _click_match_suggested_cpm(page)

    # Apply percentage adjustment (from cpm_adjust or cpm_bid_value)
    adjust = config.cpm_adjust
    if adjust is None and config.cpm_bid_value is not None:
        adjust = config.cpm_bid_value

    if adjust is not None:
        _bulk_adjust_by_percentage(page, int(adjust))
        logger.info(f"    CPM adjusted by +{int(adjust)}% from suggested")
    else:
        logger.info("    Using matched suggested CPM (no adjustment)")


def _apply_min_cpm_bids(page: Page, config: V4CampaignConfig):
    """Set each source bid to min CPM + flat dollar or percentage add-on."""
    adjust_pct = config.cpm_bid_value or 0
    flat_add = getattr(config, "cpm_flat_add", None) or 0

    # First match suggested to populate bid infrastructure
    _click_match_suggested_cpm(page)

    sources = _get_included_source_bids(page)

    count = 0
    for source in sources:
        bid = source["minCpm"]
        if flat_add:
            bid = bid + flat_add
        elif adjust_pct:
            bid = bid * (1 + adjust_pct / 100)
        bid = round(bid, 3)
        if _set_source_bid_inline(page, source["tableId"], source["rowIdx"], bid):
            count += 1

    if flat_add:
        logger.info(f"    Set {count}/{len(sources)} sources to min CPM +${flat_add:.2f}")
    elif adjust_pct:
        logger.info(f"    Set {count}/{len(sources)} sources to min CPM +{adjust_pct}%")
    else:
        logger.info(f"    Set {count}/{len(sources)} sources to min CPM")
def _apply_static_cpm_bids(page: Page, config: V4CampaignConfig):
    """Set all bids to a fixed value, floored at each source's min CPM.

    For each included source row:
    1. Click the pencil icon to open inline edit
    2. Fill the input with the bid value
    3. Click Save to confirm
    """
    static_val = config.cpm_bid_value
    if static_val is None:
        logger.warning("    Static CPM mode requires cpm_bid_value — falling back to suggested")
        _apply_suggested_cpm_bids(page, config)
        return

    # First match suggested to populate all bids
    _click_match_suggested_cpm(page)

    sources = _get_included_source_bids(page)

    count = 0
    for source in sources:
        bid = max(static_val, source['minCpm'])
        bid = round(bid, 3)
        if _set_source_bid_inline(page, source['tableId'], source['rowIdx'], bid):
            count += 1

    logger.info(f"    Set {count}/{len(sources)} sources to static ${static_val:.2f} (floored at min CPM)")


def _get_included_source_bids(page: Page):
    """Get all included source rows with their min CPMs.

    Multi-geo campaigns use sub-tables (sourceSelectionSubTable-{id}) with
    per-country rows. Single-geo uses the main sourceSelectionTable directly.
    Returns list of {tableId, rowIdx, minCpm} for each included bid row.
    """
    # Wait for sub-tables to load
    time.sleep(3)

    return page.evaluate('''() => {
        const result = [];

        // Check for sub-tables first (multi-geo layout)
        const subTables = document.querySelectorAll('table[id^="sourceSelectionSubTable"]');
        if (subTables.length > 0) {
            subTables.forEach(table => {
                const rows = table.querySelectorAll("tbody tr");
                rows.forEach((row, idx) => {
                    // Skip header rows (no td cells or no yourCPM)
                    if (!row.querySelector("td.yourCPM")) return;
                    if (!row.querySelector("i.fa-pencil-alt, .pencil-icon")) return;

                    let minCpm = 0;
                    const priceCells = row.querySelectorAll("td.text-right");
                    for (const cell of priceCells) {
                        const m = cell.textContent.trim().match(/^[$]([\\d.]+)/);
                        if (m) { minCpm = parseFloat(m[1]) || 0; break; }
                    }
                    result.push({tableId: table.id, rowIdx: idx, minCpm});
                });
            });
            return result;
        }

        // Fallback: single-geo layout — rows are in main table
        const table = document.querySelector("#sourceSelectionTable") ||
                      document.querySelector("#includedSourcesTable");
        if (!table) return result;
        const rows = table.querySelectorAll("tbody tr");
        rows.forEach((row, idx) => {
            const sw = row.querySelector(".sourceStatusWrap");
            if (sw && sw.getAttribute("data-status") !== "included") return;
            if (!row.querySelector("i.fa-pencil-alt, .pencil-icon")) return;

            let minCpm = 0;
            const priceCells = row.querySelectorAll("td.text-right");
            for (const cell of priceCells) {
                const m = cell.textContent.trim().match(/^[$]([\\d.]+)/);
                if (m) { minCpm = parseFloat(m[1]) || 0; break; }
            }
            result.push({tableId: table.id, rowIdx: idx, minCpm});
        });
        return result;
    }''')


def _set_source_bid_inline(page: Page, table_id: str, row_idx: int, bid: float) -> bool:
    """Set a single source's bid using the pencil-icon inline edit flow.

    1. Click the pencil icon on the row
    2. Fill the inline input with the bid value
    3. Click Save or press Enter
    """
    try:
        clicked = page.evaluate('''(args) => {
            const table = document.getElementById(args.tableId);
            if (!table) return false;
            const rows = table.querySelectorAll("tbody tr");
            if (args.rowIdx >= rows.length) return false;
            const row = rows[args.rowIdx];
            const pencil = row.querySelector("i.fa-pencil-alt, i.pencil-icon, .pencil-icon");
            if (pencil) { pencil.click(); return true; }
            const cpmCell = row.querySelector("td.yourCPM");
            if (cpmCell) { cpmCell.click(); return true; }
            return false;
        }''', {"tableId": table_id, "rowIdx": row_idx})

        if not clicked:
            return False

        time.sleep(0.5)

        input_el = page.query_selector('input#inlineEditInput, input.inlineEditInput')
        if not input_el:
            time.sleep(0.5)
            input_el = page.query_selector('input#inlineEditInput, input.inlineEditInput')
        if not input_el:
            return False

        input_el.fill("")
        input_el.fill(str(bid))
        time.sleep(0.3)

        # Trigger input/change events to enable Save button
        input_el.dispatch_event("input")
        input_el.dispatch_event("change")
        time.sleep(0.3)

        # Try Enter key first (most reliable), then Save button via JS
        try:
            input_el.press("Enter")
        except Exception:
            page.evaluate('''() => {
                const btn = document.querySelector("button.saveInlineEdit");
                if (btn) btn.click();
            }''')

        time.sleep(0.5)
        return True

    except Exception as e:
        logger.debug(f"    Inline edit failed for {table_id} row {row_idx}: {e}")
        return False


def _click_match_suggested_cpm(page: Page):
    """Click 'Match Suggested CPM' button to populate all bids."""
    matched = page.evaluate('''() => {
        const btn = document.querySelector("button.matchCpm");
        if (btn) {
            btn.scrollIntoView({behavior: "instant", block: "center"});
            btn.click();
            return true;
        }
        const buttons = document.querySelectorAll("button");
        for (const b of buttons) {
            if (b.textContent.includes("Match") && b.textContent.includes("CPM")) {
                b.scrollIntoView({behavior: "instant", block: "center"});
                b.click();
                return true;
            }
        }
        return false;
    }''')
    if matched:
        time.sleep(2)
        logger.info("    Matched suggested CPM")
    else:
        logger.warning("    Match Suggested CPM button not found")


def _bulk_adjust_by_percentage(page: Page, percentage: int):
    """Bulk Edit → Adjust by Percentage flow."""
    bulk_edit = page.query_selector('button.bulkEdit')
    if not bulk_edit:
        logger.warning("    Bulk Edit button not found")
        return

    bulk_edit.click()
    time.sleep(0.5)

    page.click('label:has(input#adjustByPercent)')
    time.sleep(0.3)

    percent_input = page.query_selector('input#percent')
    if percent_input:
        percent_input.fill("")
        percent_input.fill(str(percentage))
        time.sleep(0.3)
        page.click('label:has(input#adjustByPercent)')
        time.sleep(0.5)

    confirm = page.query_selector('button#confirmBulkEdit')
    if confirm:
        confirm.click()
        time.sleep(1)

    continue_btn = page.query_selector('a[data-function="sourceTableFunctions.bulkEditBids"]')
    if continue_btn:
        continue_btn.click()
        time.sleep(1)
    else:
        try:
            page.click('a.greenButton:has-text("Continue")', timeout=3000)
            time.sleep(1)
        except Exception:
            pass

    # Dismiss modal
    try:
        page.click('body', position={"x": 10, "y": 10}, force=True)
        time.sleep(0.3)
        page.keyboard.press('Escape')
        time.sleep(0.3)
    except Exception:
        pass


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
    """Wait for source table rows to load, check all, and click Include."""
    try:
        # Wait for at least one source row to appear (table loads async)
        try:
            page.wait_for_selector(
                '#sourceSelectionTable tbody tr td.minWidth100',
                state="visible", timeout=15000,
            )
            time.sleep(1)
        except Exception:
            logger.warning("    Source table rows not loaded after 15s")
            return

        source_checkbox = page.locator(
            'input.checkUncheckAll[data-table="sourceSelectionTable"]'
        )
        if source_checkbox.is_visible(timeout=3000):
            page.check('input.checkUncheckAll[data-table="sourceSelectionTable"]')
            time.sleep(0.5)
            page.click('button.includeBtn[data-btn-action="include"]')
            time.sleep(1)
            logger.info("    Sources: all included")
        else:
            logger.warning("    Source select-all checkbox not found on page")
    except Exception as e:
        logger.warning(f"    Source inclusion failed: {e}")


def _include_matching_sources(page: Page, search_term: str):
    """Check only source rows whose site name contains the search term, then include."""
    try:
        # Wait for source table rows to load
        try:
            page.wait_for_selector(
                '#sourceSelectionTable tbody tr td.minWidth100',
                state="visible", timeout=15000,
            )
            time.sleep(1)
        except Exception:
            logger.warning("    Source table rows not loaded after 15s")
            return

        # Use JS to check only rows matching the search term
        checked = page.evaluate('''(term) => {
            let count = 0;
            const rows = document.querySelectorAll("#sourceSelectionTable tbody tr");
            for (const row of rows) {
                const siteCell = row.querySelector("td.minWidth100");
                if (siteCell && siteCell.textContent.toLowerCase().includes(term.toLowerCase())) {
                    const cb = row.querySelector("input.tableCheckbox");
                    if (cb && !cb.checked) {
                        cb.checked = true;
                        cb.dispatchEvent(new Event("change", {bubbles: true}));
                        count++;
                    }
                }
            }
            return count;
        }''', search_term)

        if checked > 0:
            time.sleep(0.5)
            page.click('button.includeBtn[data-btn-action="include"]')
            time.sleep(1)
            logger.info(f"    Sources: {checked} matching '{search_term}' included")
        else:
            logger.warning(f"    No sources matching '{search_term}' found")
    except Exception as e:
        logger.warning(f"    Source matching failed for '{search_term}': {e}")


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

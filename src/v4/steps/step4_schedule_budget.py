"""Step 4 — Schedule & Budget: duration, dayparting, frequency cap, budget."""

import time
import logging
from playwright.sync_api import Page

from ..models import V4CampaignConfig
from ..utils import enable_toggle, disable_toggle, dismiss_modals

logger = logging.getLogger(__name__)


def configure_step4(page: Page, config: V4CampaignConfig):
    """Configure duration, dayparting, frequency cap, and daily budget on Step 4."""
    logger.info("  [Step 4] Configuring schedule & budget...")

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(2)
    dismiss_modals(page)

    # ── Duration ──────────────────────────────────────────────────
    if config.start_date or config.end_date:
        _configure_duration(page, config)

    # ── Dayparting ────────────────────────────────────────────────
    if config.schedule_dayparting:
        _configure_dayparting(page, config)

    # ── Frequency Cap ─────────────────────────────────────────────
    _configure_frequency_cap(page, config)

    # ── Budget ────────────────────────────────────────────────────
    dismiss_modals(page)
    _configure_budget(page, config)


def _configure_duration(page: Page, config: V4CampaignConfig):
    """Enable duration toggle and fill start/end dates."""
    enable_toggle(page, "campaign_duration")
    time.sleep(0.5)

    if config.start_date:
        try:
            page.fill('#start_date', config.start_date)
            time.sleep(0.3)
            logger.info(f"    Start date: {config.start_date}")
        except Exception as e:
            logger.warning(f"    Could not set start date: {e}")

    if config.end_date:
        try:
            page.fill('#end_date', config.end_date)
            time.sleep(0.3)
            logger.info(f"    End date: {config.end_date}")
        except Exception as e:
            logger.warning(f"    Could not set end date: {e}")


def _configure_dayparting(page: Page, config: V4CampaignConfig):
    """Enable schedule toggle and configure dayparting grid."""
    enable_toggle(page, "campaign_schedule")
    time.sleep(0.5)

    # The dayparting value is a JSON config applied via JS
    try:
        page.evaluate(f'''(config) => {{
            const input = document.querySelector('#schedule_list');
            if (input) {{
                input.value = config;
                input.dispatchEvent(new Event("change", {{bubbles: true}}));
            }}
        }}''', config.schedule_dayparting)
        time.sleep(0.3)
        logger.info(f"    Dayparting configured")
    except Exception as e:
        logger.warning(f"    Could not set dayparting: {e}")


def _configure_frequency_cap(page: Page, config: V4CampaignConfig):
    """Configure frequency capping toggle and values."""
    if config.frequency_cap == 0:
        # Disable frequency capping
        disable_toggle(page, "campaign_frequency_capping")
        logger.info("    Frequency capping: disabled")
        return

    # Enable and set values
    enable_toggle(page, "campaign_frequency_capping")
    time.sleep(0.3)

    try:
        page.fill('input#frequency_cap_times', "")
        page.fill('input#frequency_cap_times', str(config.frequency_cap))
        logger.info(f"    Frequency cap: {config.frequency_cap}")
    except Exception as e:
        logger.warning(f"    Could not set frequency cap times: {e}")

    if config.frequency_cap_every:
        try:
            page.fill('input#frequency_cap_every', "")
            page.fill('input#frequency_cap_every', str(config.frequency_cap_every))
            logger.info(f"    Frequency cap every: {config.frequency_cap_every}h")
        except Exception as e:
            logger.warning(f"    Could not set frequency cap interval: {e}")


def _configure_budget(page: Page, config: V4CampaignConfig):
    """Select Custom budget radio and fill daily budget."""
    # Click Custom radio via JS (same pattern as V2/V3)
    page.evaluate('''() => {
        const input = document.getElementById("is_unlimited_budget_custom");
        if (input) {
            input.checked = true;
            input.click();
            input.dispatchEvent(new Event("change", {bubbles: true}));
            input.dispatchEvent(new Event("input", {bubbles: true}));
        }
        if (typeof $ !== "undefined") {
            try { $("#is_unlimited_budget_custom").prop("checked", true)
                    .trigger("click").trigger("change"); } catch(e) {}
        }
        const label = document.querySelector('label[for="is_unlimited_budget_custom"]');
        if (label) label.click();
    }''')
    time.sleep(1)

    # Wait for budget field to appear
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
    budget_val = str(config.daily_budget)
    budget_set = page.evaluate(f'''() => {{
        const f = document.getElementById("daily_budget");
        if (f) {{
            f.value = "";
            f.value = "{budget_val}";
            f.dispatchEvent(new Event("input", {{bubbles: true}}));
            f.dispatchEvent(new Event("change", {{bubbles: true}}));
            if (typeof $ !== "undefined") {{
                try {{ $("#daily_budget").val("{budget_val}")
                        .trigger("input").trigger("change"); }} catch(e) {{}}
            }}
            return true;
        }}
        return false;
    }}''')

    if budget_set:
        logger.info(f"    Daily budget: ${config.daily_budget}")
    else:
        # Playwright fallback
        try:
            page.fill('input#daily_budget', "", timeout=5000)
            page.fill('input#daily_budget', budget_val, timeout=5000)
            logger.info(f"    Daily budget: ${config.daily_budget} (fallback)")
        except Exception:
            logger.warning("    Could not set daily budget — template value will be used")

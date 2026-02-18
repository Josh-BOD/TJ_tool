"""Shared helpers for V4 campaign creation steps."""

import time
import logging
import re
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


# ─── Element interaction helpers ──────────────────────────────────

def safe_click(page: Page, selector: str, timeout: int = 5000) -> bool:
    """Try to click an element; return False on timeout instead of raising."""
    try:
        page.click(selector, timeout=timeout)
        return True
    except (PlaywrightTimeout, Exception) as e:
        logger.debug(f"safe_click failed for {selector}: {e}")
        return False


def wait_and_fill(page: Page, selector: str, value: str, timeout: int = 5000):
    """Clear a field and fill it with *value*, verifying presence first."""
    page.wait_for_selector(selector, state="visible", timeout=timeout)
    page.fill(selector, "")
    page.fill(selector, str(value))
    time.sleep(0.2)


def set_radio(page: Page, name: str, value: str):
    """Click a radio button identified by name + value, with JS fallback."""
    selector = f'input[name="{name}"][value="{value}"]'
    try:
        page.wait_for_selector(selector, timeout=5000)
        page.locator(selector).click(force=True)
    except Exception:
        # JS fallback — some radios are hidden behind custom UI
        page.evaluate(f'''() => {{
            const el = document.querySelector('{selector}');
            if (el) {{ el.checked = true; el.click();
                       el.dispatchEvent(new Event("change", {{bubbles:true}})); }}
        }}''')
    time.sleep(0.3)


def enable_toggle(page: Page, section_id: str):
    """Ensure the toggle checkbox inside a section is checked (via JS)."""
    page.evaluate(f'''() => {{
        const section = document.querySelector("#{section_id}");
        if (!section) return;
        const cb = section.querySelector("input[type='checkbox']");
        if (cb && !cb.checked) {{
            cb.click();
            cb.dispatchEvent(new Event("change", {{bubbles: true}}));
        }}
    }}''')
    time.sleep(0.8)


def disable_toggle(page: Page, section_id: str):
    """Uncheck the toggle checkbox inside a section (via JS)."""
    page.evaluate(f'''() => {{
        const section = document.querySelector("#{section_id}");
        if (!section) return;
        const cb = section.querySelector("input[type='checkbox']");
        if (cb && cb.checked) {{
            cb.click();
            cb.dispatchEvent(new Event("change", {{bubbles: true}}));
        }}
    }}''')
    time.sleep(0.5)


def select2_choose(page: Page, container_sel: str, search_text: str, timeout: int = 5000):
    """Open a select2 dropdown, type *search_text*, pick first result."""
    page.click(container_sel, timeout=timeout)
    time.sleep(0.5)
    search_input = page.locator(".select2-container--open .select2-search__field")
    search_input.fill(search_text)
    time.sleep(0.8)
    try:
        option = page.locator("li.select2-results__option").first
        option.wait_for(state="visible", timeout=timeout)
        option.click()
    except PlaywrightTimeout:
        # Enter key as fallback
        page.keyboard.press("Enter")
    time.sleep(0.3)


def select2_clear_all(page: Page, container_sel: str):
    """Remove all select2 selections inside *container_sel*."""
    for _ in range(30):
        remove_btn = page.locator(f"{container_sel} .select2-selection__choice__remove").first
        if remove_btn.count() > 0 and remove_btn.is_visible():
            try:
                remove_btn.click(timeout=1000)
                time.sleep(0.2)
            except Exception:
                break
        else:
            break


# ─── Navigation helpers ──────────────────────────────────────────

def dismiss_modals(page: Page):
    """Close any blocking modals (review-bids, bootstrap, backdrop)."""
    try:
        page.evaluate('''() => {
            // Close reviewYourBidsModal
            const modal = document.querySelector("#reviewYourBidsModal");
            if (modal && modal.style.display !== "none") {
                const btn = modal.querySelector(".close, [data-dismiss='modal'], button.closeModal");
                if (btn) btn.click();
            }
            // Close any visible Bootstrap modal
            const open = document.querySelector(".modal.in, .modal.show");
            if (open) {
                const btn = open.querySelector(".close, [data-dismiss='modal']");
                if (btn) btn.click();
            }
            // Remove backdrop
            document.querySelectorAll(".modal-backdrop").forEach(el => el.remove());
            document.body.classList.remove("modal-open");
            document.body.style.overflow = "";
        }''')
        time.sleep(0.3)
    except Exception:
        pass


def click_save_and_continue(page: Page):
    """Click Save & Continue with multi-selector fallback + URL-change verification."""
    url_before = page.url
    dismiss_modals(page)

    selectors = [
        'button.confirmAudience.saveAndContinue',
        'button.confirmtrackingAdSpotsRules.saveAndContinue',
        'button#addCampaign',
        'button.saveAndContinue',
        'button:has-text("Save & Continue")',
    ]

    for attempt in range(3):
        for sel in selectors:
            try:
                locator = page.locator(sel).first
                if locator.count() > 0 and locator.is_visible(timeout=2000):
                    logger.info(f"  [Save] Clicking: {sel} (attempt {attempt+1})")
                    locator.click(timeout=60000)
                    time.sleep(2)
                    dismiss_modals(page)
                    if page.url != url_before:
                        logger.info(f"  [Save] Navigated to: {page.url}")
                        return
                    logger.info(f"  [Save] URL unchanged after click, still: {page.url}")
                    break  # found a button but page didn't navigate — retry
            except Exception as e:
                logger.debug(f"  Save button {sel}: {e}")
                continue
        else:
            if attempt < 2:
                dismiss_modals(page)
                time.sleep(1)
                continue
            break

        # Aggressive cleanup between retries
        if attempt < 2:
            logger.info(f"  Save & Continue: page didn't navigate (attempt {attempt + 1}/3), retrying...")
            page.evaluate('''() => {
                document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
                document.querySelectorAll('.modal.in, .modal.show, .modal[style*="display: block"]').forEach(el => {
                    el.style.display = "none"; el.classList.remove("in", "show");
                });
                document.body.classList.remove('modal-open');
                document.body.style.overflow = '';
            }''')
            time.sleep(1)
            page.keyboard.press("Escape")
            time.sleep(0.5)

    # Last-resort JS click
    if page.url == url_before:
        logger.warning("  Save & Continue: JS fallback...")
        page.evaluate('''() => {
            const btns = document.querySelectorAll('button.saveAndContinue, button[type="submit"]');
            for (const btn of btns) { btn.click(); return; }
        }''')
        time.sleep(3)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        dismiss_modals(page)
        if page.url == url_before:
            logger.warning(f"  Save & Continue failed to navigate from {url_before}")

    # Wait for the new page to settle after navigation
    if page.url != url_before:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass
        time.sleep(1)


def check_session(page: Page) -> bool:
    """Return True if still on the advertiser site, False if redirected to sign-in."""
    url = page.url
    if "sign-in" in url or "trafficjunky.com/sign-in" in url:
        logger.warning("Session expired — redirected to sign-in")
        return False
    return True


def extract_campaign_id(page: Page) -> str:
    """Extract campaign ID from the current URL (first 4+ digit numeric segment)."""
    url = page.url
    match = re.search(r'/campaign/(\d{4,})(?:/|$|\?)', url)
    if match:
        return match.group(1)
    # Broader fallback
    parts = url.split("/")
    for part in parts:
        cleaned = part.split("?")[0]
        if cleaned.isdigit() and len(cleaned) >= 4:
            return cleaned
    raise RuntimeError(f"Could not extract campaign ID from URL: {url}")

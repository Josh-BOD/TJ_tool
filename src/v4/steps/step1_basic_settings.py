"""Step 1 — Basic Settings: name, rating, group, labels, device, format, dimensions, etc."""

import time
import logging
from playwright.sync_api import Page

from ..models import V4CampaignConfig
from ..utils import (
    safe_click, wait_and_fill, set_radio, dismiss_modals,
    click_save_and_continue, extract_campaign_id,
)

logger = logging.getLogger(__name__)

# ── Value maps ────────────────────────────────────────────────────
DEVICE_MAP = {"all": "1", "desktop": "2", "mobile": "3"}
AD_FORMAT_MAP = {"display": "1", "instream": "2", "pop": "3"}
FORMAT_TYPE_MAP = {"banner": "4", "native": "5"}
AD_TYPE_MAP = {"static_banner": "1", "video_banner": "2", "video_file": "5", "rollover": "9"}
DIMENSION_MAP = {
    "300x250": "9", "950x250": "5", "468x60": "25", "305x99": "55",
    "300x100": "80", "970x90": "221", "320x480": "9771", "640x360": "9731",
}
GENDER_MAP = {"all": "1", "male": "2", "female": "3"}


def configure_step1(page: Page, config: V4CampaignConfig, campaign_name: str, variant: str) -> str:
    """Fill Basic Settings page and click Save & Continue. Returns campaign_id."""
    logger.info(f"  [Step 1] Configuring basic settings...")

    # 1. Campaign Name
    wait_and_fill(page, 'input[name="name"]', campaign_name)
    logger.info(f"    Name: {campaign_name}")

    # 2. Content Rating
    rating = config.content_rating.lower()
    try:
        page.click(f'label:has(input[value="{rating}"])', timeout=3000)
    except Exception:
        try:
            page.click(f'label:has-text("{config.content_rating}")', timeout=2000)
        except Exception:
            logger.debug("Could not set content rating — may already be selected")
    time.sleep(0.3)

    # 3. Group
    _select_or_create_group(page, config.group)

    # 4. Labels
    if config.labels:
        _set_labels(page, config.labels)

    # 5. Exchange ID (select2 — hidden native select)
    if config.exchange_id:
        try:
            # Check if already set to correct value
            container = page.locator('span[id="select2-exchange_id-container"]')
            current = container.get_attribute("title") or ""
            # Map exchange_id values to known display names
            exchange_names = {"1": "TJX"}
            expected = exchange_names.get(config.exchange_id, config.exchange_id)
            if current == expected:
                logger.info(f"    Exchange ID: {config.exchange_id} (already set)")
            else:
                container.click(timeout=5000)
                time.sleep(0.5)
                option = page.locator('li.select2-results__option').filter(has_text=expected).first
                option.click(timeout=5000)
                time.sleep(0.3)
                logger.info(f"    Exchange ID: {config.exchange_id}")
        except Exception as e:
            logger.warning(f"    Could not set exchange_id: {e}")

    # 6. Device
    device = config.device_for_variant(variant)
    device_val = DEVICE_MAP.get(device, "2")
    set_radio(page, "platform_id", device_val)
    logger.info(f"    Device: {device}")

    # 7. Ad Format Type
    ad_fmt_val = AD_FORMAT_MAP.get(config.ad_format_type, "1")
    set_radio(page, "ad_format_id", ad_fmt_val)
    time.sleep(0.5)
    logger.info(f"    Ad format: {config.ad_format_type}")

    # 8. Format Type (only for display)
    if config.ad_format_type == "display":
        fmt_val = FORMAT_TYPE_MAP.get(config.format_type, "5")
        set_radio(page, "format_type_id", fmt_val)
        time.sleep(0.3)
        logger.info(f"    Format type: {config.format_type}")

    # 9. Ad Type
    at_val = AD_TYPE_MAP.get(config.ad_type, "9")
    set_radio(page, "ad_type_id", at_val)
    time.sleep(0.3)
    logger.info(f"    Ad type: {config.ad_type}")

    # 10. Ad Dimensions
    dim_norm = config.ad_dimensions.lower().replace(" ", "")
    dim_val = DIMENSION_MAP.get(dim_norm, "9")
    set_radio(page, "ad_dimension_id", dim_val)
    time.sleep(0.3)
    logger.info(f"    Dimensions: {config.ad_dimensions}")

    # 11. Content Category
    cat = config.content_category.lower()
    if cat not in ("straight", "gay", "trans"):
        cat = "straight"
    set_radio(page, "content_category_id", cat)
    logger.info(f"    Content category: {cat}")

    # 12. Gender
    gen_val = GENDER_MAP.get(config.gender, "1")
    set_radio(page, "demographic_targeting_id", gen_val)
    logger.info(f"    Gender: {config.gender}")

    # Save & Continue
    logger.info("    Saving basic settings...")
    click_save_and_continue(page)

    # Extract campaign ID from URL
    campaign_id = extract_campaign_id(page)
    logger.info(f"    Campaign ID: {campaign_id}")
    return campaign_id


# ─── Private helpers ──────────────────────────────────────────────

def _select_or_create_group(page: Page, group_name: str):
    """Select existing group or create a new one."""
    if group_name.lower() == "general":
        logger.info("    Group: General (pre-selected)")
        return

    try:
        page.click('span.select2-selection[aria-labelledby="select2-group_id-container"]')
        time.sleep(0.5)

        search = page.locator('.select2-container--open input.select2-search__field')
        search.fill(group_name)
        time.sleep(1)

        no_results = page.query_selector('li.select2-results__message')
        if no_results:
            # Create new group
            page.click('a#showNewGroupFormButton')
            inp = page.locator('input#new_group_name')
            inp.fill(group_name)
            inp.evaluate('(el) => el.dispatchEvent(new Event("input", { bubbles: true }))')
            try:
                page.wait_for_function(
                    'document.querySelector("button#confirmNewGroupButton") && '
                    'document.querySelector("button#confirmNewGroupButton").disabled === false',
                    timeout=3000,
                )
            except Exception:
                time.sleep(0.5)
                page.evaluate('document.querySelector("button#confirmNewGroupButton").disabled = false')
            page.click('button#confirmNewGroupButton')
            time.sleep(0.5)
            logger.info(f"    Created new group: {group_name}")
        else:
            option = page.locator('li.select2-results__option').filter(has_text=group_name).first
            if option.count() > 0:
                option.click()
            else:
                page.keyboard.press("Enter")
            time.sleep(0.5)
            logger.info(f"    Selected group: {group_name}")
    except Exception as e:
        logger.warning(f"    Could not set group: {e}")
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass


def _set_labels(page: Page, labels: list):
    """Set campaign labels via select2 (#selectLabel)."""
    try:
        # Remove existing labels
        removed = 0
        for _ in range(20):
            btn = page.locator(".deleteLabel").first
            if btn.count() > 0 and btn.is_visible():
                try:
                    btn.click(timeout=1000)
                    time.sleep(0.2)
                    removed += 1
                except Exception:
                    break
            else:
                break
        if removed:
            logger.info(f"    Removed {removed} existing label(s)")

        labels_input = page.locator('input.select2-search__field[placeholder="Select or Input a Label"]')
        labels_input.click()
        time.sleep(0.5)

        for label in labels:
            labels_input.fill(label)
            time.sleep(0.5)
            try:
                opt = page.locator('li.select2-results__option').first
                opt.wait_for(state='visible', timeout=2000)
                opt.click()
            except Exception:
                page.keyboard.press("Enter")
            time.sleep(0.3)

        page.keyboard.press("Escape")
        time.sleep(0.3)
        logger.info(f"    Labels: {labels}")
    except Exception as e:
        logger.warning(f"    Could not set labels: {e}")

"""Step 5 — Ad Settings: delete inherited ads, upload CSV, set rotation."""

import time
import logging
from pathlib import Path
from playwright.sync_api import Page

from ..models import V4CampaignConfig
from ..utils import dismiss_modals

logger = logging.getLogger(__name__)


def configure_step5(page: Page, config: V4CampaignConfig, csv_dir: str, campaign_name: str):
    """Delete existing ads, upload ad CSV, and configure ad rotation."""
    logger.info("  [Step 5] Configuring ad settings...")

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(2)
    dismiss_modals(page)

    is_pop = config.ad_format_type == "pop"

    if config.csv_file:
        # 1. Delete existing ads
        _delete_all_ads(page)

        # 2. Upload ad CSV
        csv_path = Path(csv_dir) / config.csv_file
        if csv_path.exists():
            if is_pop:
                _upload_pop_csv(page, csv_path)
            else:
                _upload_ad_csv(page, csv_path, campaign_name, config)
        else:
            logger.warning(f"    Ad CSV not found: {csv_path}")

        # 3. Configure ad rotation to Autopilot (CTR) — must be after ads exist
        if not is_pop:
            _configure_ad_rotation(page)
    else:
        logger.info("    Keeping template ads (no csv_file — template-only campaign)")

    # 4. Click "Finish Campaign" to save and exit draft
    _finish_campaign(page)


def _upload_pop_csv(page: Page, csv_path: Path):
    """Upload a pop ad CSV using TJ mass create with CSV flow.

    Pop ad page has:
    - Radio: Manual selection / Mass create with CSV
    - File input for CSV upload
    - Submit button to create ads
    CSV format: "Ad Name","Source URL"
    """
    try:
        dismiss_modals(page)
        time.sleep(1)

        # Select "Mass create with CSV" radio
        clicked = page.evaluate("""() => {
            const labels = document.querySelectorAll('label');
            for (const label of labels) {
                if (label.textContent.toLowerCase().includes('mass create') ||
                    label.textContent.toLowerCase().includes('csv')) {
                    const radio = label.querySelector('input[type="radio"]') ||
                                  document.getElementById(label.getAttribute('for'));
                    if (radio) radio.click();
                    else label.click();
                    return true;
                }
            }
            const radios = document.querySelectorAll('input[type="radio"]');
            for (const r of radios) {
                const lbl = document.querySelector('label[for="' + r.id + '"]');
                if (lbl && lbl.textContent.toLowerCase().includes('csv')) {
                    r.click();
                    return true;
                }
            }
            return false;
        }""")
        if clicked:
            time.sleep(1)
            logger.info("    Pop: selected mass CSV upload")

        # Upload the CSV file
        file_input = page.locator('input[type="file"]').first
        file_input.set_input_files(str(csv_path))
        time.sleep(2)
        logger.info(f"    Pop: CSV file set: {csv_path.name}")

        # Step 1: Click "Create CSV Preview" button
        page.evaluate("""() => {
            const buttons = document.querySelectorAll('button, a.smallButton');
            for (const btn of buttons) {
                const text = (btn.textContent || '').trim().toLowerCase();
                if (text.includes('create csv preview') || text.includes('preview')) {
                    btn.scrollIntoView({behavior: "instant", block: "center"});
                    btn.click();
                    return text;
                }
            }
            // Fallback: click any button with "create" in text
            for (const btn of buttons) {
                const text = (btn.textContent || '').trim().toLowerCase();
                if (text.includes('create')) {
                    btn.scrollIntoView({behavior: "instant", block: "center"});
                    btn.click();
                    return text;
                }
            }
            return null;
        }""")
        time.sleep(3)
        logger.info("    Pop: clicked Create CSV Preview")

        # Step 2: Handle the csvPreviewModal — click "Create Ad(s)" inside it
        confirmed = page.evaluate("""() => {
            const modal = document.querySelector('#csvPreviewModal');
            if (!modal) return 'no_modal';
            // Find confirm/create button inside modal
            const buttons = modal.querySelectorAll('button, a');
            for (const btn of buttons) {
                const text = (btn.textContent || '').trim().toLowerCase();
                if (text.includes('create ad') || text.includes('confirm')) {
                    btn.click();
                    return 'confirmed: ' + btn.textContent.trim();
                }
            }
            // Fallback: click green button in modal
            for (const btn of buttons) {
                if (btn.classList.contains('greenButton') || btn.classList.contains('btn-success') || btn.classList.contains('confirmAds')) {
                    btn.click();
                    return 'green: ' + btn.textContent.trim();
                }
            }
            return 'no_button_in_modal';
        }""")
        logger.info(f"    Pop: preview modal result: {confirmed}")

        time.sleep(3)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        time.sleep(2)

        # Dismiss any remaining modals
        page.evaluate("""() => {
            document.querySelectorAll('.modal.show .close, .modal.show [data-dismiss="modal"]').forEach(el => el.click());
        }""")
        time.sleep(1)

        logger.info("    Pop: CSV upload complete")

    except Exception as e:
        logger.error(f"    Pop CSV upload failed: {e}")


def _delete_all_ads(page: Page):
    """Delete all existing ads on the ads page."""
    dismiss_modals(page)
    try:
        length_dropdown = page.query_selector('select[name="adsTable_length"]')
        if length_dropdown:
            page.select_option('select[name="adsTable_length"]', '100')
            time.sleep(1)

        select_all = page.query_selector(
            'input[type="checkbox"].checkUncheckAll[data-table="adsTable"]'
        )
        if not select_all:
            logger.info("    No ads to delete")
            return

        select_all.click()
        time.sleep(0.5)

        delete_btn = page.query_selector(
            'button.massDeleteButton.redButton.smallButton'
        )
        if delete_btn and delete_btn.is_visible():
            delete_btn.click()
            time.sleep(0.5)

            try:
                yes_btn = page.query_selector(
                    'a[data-function="adsManagement.deleteAds"].smallButton.greenButton'
                )
                if yes_btn:
                    yes_btn.click()
                else:
                    page.click('button:has-text("Yes")', timeout=2000)
                time.sleep(2)
            except Exception:
                pass

            logger.info("    Deleted existing ads")

    except Exception as e:
        logger.debug(f"    Ad deletion: {e}")


def _configure_ad_rotation(page: Page):
    """Set ad rotation to Autopilot (CTR)."""
    try:
        page.get_by_text("Autopilot", exact=True).click()
        time.sleep(0.3)
        page.get_by_text("CTR", exact=True).click()
        time.sleep(0.3)
        logger.info("    Ad rotation: Autopilot (CTR)")
    except Exception as e:
        logger.warning(f"    Could not set ad rotation: {e}")


def _finish_campaign(page: Page):
    """Click Save Campaign via JS (bypasses visibility checks), then handle success modal.

    The saveContinue link can be hidden behind disabledInterface overlays on draft pages.
    Using JS click instead of Playwright click avoids scroll/visibility timeouts.
    """
    dismiss_modals(page)
    time.sleep(1)

    url_before = page.url

    for attempt in range(3):
        # Remove ALL overlays and force-show save buttons
        page.evaluate("""() => {
            document.querySelectorAll('.disabledInterface').forEach(el => el.classList.remove('disabledInterface'));
            document.querySelectorAll('.modal.show .close').forEach(el => el.click());
            document.querySelectorAll('a.saveContinue').forEach(el => {
                el.style.display = '';
                el.style.visibility = 'visible';
                el.style.pointerEvents = 'auto';
            });
        }""")
        time.sleep(0.5)

        logger.info(f"    [Finish] Clicking Save Campaign (attempt {attempt+1})")

        # Use JS click — bypasses all Playwright visibility/scroll checks
        clicked = page.evaluate("""() => {
            const link = document.querySelector('a.saveContinue[data-gtm-index="saveContinueStepFive"]') ||
                         document.querySelector('a.saveContinue');
            if (link) { link.click(); return "saveContinue"; }
            const btn = document.getElementById('saveChanges');
            if (btn) { btn.click(); return "saveChanges"; }
            return null;
        }""")

        if not clicked:
            logger.warning("    [Finish] No save button found")
            time.sleep(2)
            continue

        logger.info(f"    [Finish] JS-clicked: {clicked}")
        time.sleep(3)

        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        time.sleep(2)

        # Check for success modal
        go_link = page.locator('a.smallButton.greenButton:has-text("Go to Campaigns")')
        try:
            go_link.first.wait_for(state="visible", timeout=10000)
            logger.info("    [Finish] Success modal — clicking Go to Campaigns")
            go_link.first.click(timeout=5000)
            time.sleep(2)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=15000)
            except Exception:
                pass
            if page.url != url_before and "ad-settings" not in page.url:
                logger.info(f"    Campaign saved — navigated to: {page.url}")
                return
        except Exception:
            pass

        if page.url != url_before and "ad-settings" not in page.url:
            logger.info(f"    Campaign saved — navigated to: {page.url}")
            return

        # Check for validation errors on page
        errors = page.evaluate("""() => {
            const msgs = [];
            document.querySelectorAll('.alert-danger, .error-message, .text-danger, .validation-error').forEach(el => {
                if (el.offsetHeight > 0) msgs.push(el.textContent.trim().substring(0, 100));
            });
            // Also check for any visible modal with error
            document.querySelectorAll('.modal.show').forEach(m => {
                const text = m.textContent.trim();
                if (text.includes('error') || text.includes('Error') || text.includes('required')) {
                    msgs.push(text.substring(0, 100));
                }
            });
            return msgs;
        }""")
        if errors:
            logger.warning(f"    [Finish] Validation errors: {errors}")
        else:
            logger.info(f"    [Finish] Still on: {page.url}")

        # Take screenshot for debugging
        try:
            page.screenshot(path=f"screenshots/step5_save_fail_attempt{attempt+1}.png")
        except Exception:
            pass

        if attempt < 2:
            time.sleep(2)

    if "ad-settings" in page.url:
        logger.warning(f"    Could not save campaign — still on {page.url}")


def _upload_ad_csv(page: Page, csv_path: Path, campaign_name: str, config: V4CampaignConfig):
    """Upload ad CSV using NativeUploader or TJUploader."""
    use_native = (config.format_type == "native")

    try:
        if use_native:
            from native_uploader import NativeUploader
            uploader = NativeUploader(dry_run=False)
        else:
            from uploader import TJUploader
            uploader = TJUploader(dry_run=False)

        result = uploader.upload_to_campaign(
            page=page,
            campaign_id="current",
            csv_path=csv_path,
            campaign_name=campaign_name,
            skip_navigation=True,
        )

        if result.get("status") == "success":
            ads_created = result.get("ads_created", 0)
            logger.info(f"    CSV uploaded: {ads_created} ads created")
        else:
            error = result.get("error", "Unknown error")
            logger.error(f"    CSV upload failed: {error}")

    except ImportError as e:
        logger.warning(f"    Uploader not available ({e}) — skipping CSV upload")
    except Exception as e:
        logger.error(f"    CSV upload failed: {e}")

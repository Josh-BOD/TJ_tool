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

    # 1. Delete existing ads
    _delete_all_ads(page)

    # 2. Upload ad CSV
    csv_path = Path(csv_dir) / config.csv_file
    if csv_path.exists():
        _upload_ad_csv(page, csv_path, campaign_name, config)
    else:
        logger.warning(f"    Ad CSV not found: {csv_path}")

    # 3. Configure ad rotation to Autopilot (CTR) — must be after ads exist
    _configure_ad_rotation(page)

    # 4. Click "Finish Campaign" to save and exit draft
    _finish_campaign(page)


def _delete_all_ads(page: Page):
    """Delete all existing ads on the ads page."""
    dismiss_modals(page)
    try:
        # Show all ads
        length_dropdown = page.query_selector('select[name="adsTable_length"]')
        if length_dropdown:
            page.select_option('select[name="adsTable_length"]', '100')
            time.sleep(1)

        # Select all
        select_all = page.query_selector(
            'input[type="checkbox"].checkUncheckAll[data-table="adsTable"]'
        )
        if not select_all:
            logger.info("    No ads to delete")
            return

        select_all.click()
        time.sleep(0.5)

        # Click Delete
        delete_btn = page.query_selector(
            'button.massDeleteButton.redButton.smallButton'
        )
        if delete_btn and delete_btn.is_visible():
            delete_btn.click()
            time.sleep(0.5)

            # Confirm
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
    """Set ad rotation to Autopilot (CTR). Matches galactus approach."""
    try:
        page.get_by_text("Autopilot", exact=True).click()
        time.sleep(0.3)

        page.get_by_text("CTR", exact=True).click()
        time.sleep(0.3)

        logger.info("    Ad rotation: Autopilot (CTR)")
    except Exception as e:
        logger.warning(f"    Could not set ad rotation: {e}")


def _finish_campaign(page: Page):
    """Click the 'Finish Campaign' button to finalize and exit draft."""
    try:
        page.click('a.saveContinue[data-gtm-index="saveContinueStepFive"]', timeout=10000)
        time.sleep(3)
        logger.info("    Campaign finished (saved)")
    except Exception:
        try:
            page.click('a:has-text("Finish Campaign")', timeout=5000)
            time.sleep(3)
            logger.info("    Campaign finished (saved)")
        except Exception as e:
            logger.warning(f"    Could not click Finish Campaign: {e}")


def _upload_ad_csv(page: Page, csv_path: Path, campaign_name: str, config: V4CampaignConfig):
    """Upload ad CSV using NativeUploader or TJUploader."""
    # Native (rollover) uses NativeUploader; everything else uses TJUploader
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

        if result.get('status') == 'success':
            ads_created = result.get('ads_created', 0)
            logger.info(f"    CSV uploaded: {ads_created} ads created")
        else:
            error = result.get('error', 'Unknown error')
            logger.error(f"    CSV upload failed: {error}")

    except ImportError as e:
        logger.warning(f"    Uploader not available ({e}) — skipping CSV upload")
    except Exception as e:
        logger.error(f"    CSV upload failed: {e}")

"""V4 Campaign Creator — main orchestrator for the 5-step flow."""

import logging
from typing import Tuple
from playwright.sync_api import Page

from .models import V4CampaignConfig
from .utils import click_save_and_continue, check_session, dismiss_modals
from .steps import step1_basic_settings as step1
from .steps import step2_geo_audience as step2
from .steps import step3_tracking_sources as step3
from .steps import step4_schedule_budget as step4
from .steps import step5_ad_settings as step5

# Import campaign naming from existing shared module
import sys
from pathlib import Path as _Path
_src = _Path(__file__).parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
from campaign_templates import generate_campaign_name, DEFAULT_SETTINGS

logger = logging.getLogger(__name__)

BASE_URL = "https://advertiser.trafficjunky.com"


class V4CreationError(Exception):
    """Raised when V4 campaign creation fails."""
    def __init__(self, message: str, orphan_id: str = None):
        self.orphan_id = orphan_id
        if orphan_id:
            message = f"{message} [ORPHAN CAMPAIGN ID: {orphan_id} — delete manually]"
        super().__init__(message)


class V4CampaignCreator:
    """Creates campaigns from scratch using the 5-step TJ flow."""

    def __init__(self, page: Page, name_prefix: str = ""):
        self.page = page
        self.name_prefix = name_prefix

    def create_campaign(
        self,
        config: V4CampaignConfig,
        variant: str,
        csv_dir: str,
    ) -> Tuple[str, str]:
        """
        Create one campaign (one variant).

        Args:
            config: Full campaign configuration from CSV.
            variant: Device variant — "desktop", "ios", "android".
            csv_dir: Directory containing ad CSV files.

        Returns:
            (campaign_id, campaign_name)
        """
        campaign_name = self.name_prefix + self._build_name(config, variant)
        campaign_id = None

        try:
            # Navigate to create-campaign page
            logger.info(f"  Navigating to create page...")
            self.page.goto(
                f"{BASE_URL}/campaign/drafts/bid/create",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            try:
                self.page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            import time as _t; _t.sleep(2)

            # ── Step 1: Basic Settings ────────────────────────────
            if not check_session(self.page):
                raise V4CreationError("Session expired before Step 1")
            campaign_id = step1.configure_step1(
                self.page, config, campaign_name, variant
            )

            # ── Step 2: Geo & Audience ────────────────────────────
            if not check_session(self.page):
                raise V4CreationError("Session expired before Step 2", orphan_id=campaign_id)
            step2.configure_step2(self.page, config, variant)

            # Step 2 also handles keywords — save & continue past it
            _handle_keywords(self.page, config)
            logger.info(f"  [Nav] Step 2 done, URL before save: {self.page.url}")
            click_save_and_continue(self.page)
            logger.info(f"  [Nav] After step 2 save, URL: {self.page.url}")

            # ── Step 3: Tracking & Sources ────────────────────────
            if not check_session(self.page):
                raise V4CreationError("Session expired before Step 3", orphan_id=campaign_id)
            import time as _time; _time.sleep(2)
            step3.configure_step3(self.page, config)
            logger.info(f"  [Nav] Step 3 done, URL before save: {self.page.url}")
            click_save_and_continue(self.page)
            logger.info(f"  [Nav] After step 3 save, URL: {self.page.url}")

            # ── Step 4: Schedule & Budget ─────────────────────────
            if not check_session(self.page):
                raise V4CreationError("Session expired before Step 4", orphan_id=campaign_id)
            import time as _time; _time.sleep(2)
            step4.configure_step4(self.page, config)
            logger.info(f"  [Nav] Step 4 done, URL before save: {self.page.url}")
            click_save_and_continue(self.page)
            logger.info(f"  [Nav] After step 4 save, URL: {self.page.url}")

            # ── Step 5: Ad Settings ───────────────────────────────
            if not check_session(self.page):
                raise V4CreationError("Session expired before Step 5", orphan_id=campaign_id)
            import time as _time; _time.sleep(2)
            logger.info(f"  [Nav] Starting step 5, URL: {self.page.url}")
            step5.configure_step5(self.page, config, csv_dir, campaign_name)

            logger.info(f"  Campaign created: {campaign_name} (ID: {campaign_id})")
            return campaign_id, campaign_name

        except V4CreationError:
            raise
        except Exception as e:
            raise V4CreationError(
                f"Failed to create campaign: {e}", orphan_id=campaign_id
            ) from e

    # ── Helpers ───────────────────────────────────────────────────

    def _build_name(self, config: V4CampaignConfig, variant: str) -> str:
        """Generate the campaign name using the shared naming function."""
        # Determine ad_format for naming (NATIVE / INSTREAM)
        ad_format_name_map = {"display": "NATIVE", "instream": "INSTREAM", "pop": "POP"}
        ad_format = ad_format_name_map.get(config.ad_format_type, "NATIVE")

        mobile_combined = variant.lower() in ("all_mobile", "mobile")

        name = generate_campaign_name(
            geo=config.geo,
            language=config.language,
            ad_format=ad_format,
            bid_type=config.bid_type,
            source=DEFAULT_SETTINGS["source"],
            keyword=config.primary_keyword,
            device=variant,
            gender=config.gender,
            user_initials="JB",
            mobile_combined=mobile_combined,
            test_number=config.test_number or None,
            campaign_type=config.campaign_type,
            geo_name=config.geo_name or None,
            content_category=config.content_category,
        )

        # Insert ad dimensions before device abbr (e.g. KEY-Broad-305x99_iOS)
        if config.ad_dimensions:
            # Find the keyword/targeting part and append dimensions after it
            import re
            name = re.sub(
                r'(KEY-[^_]+|Gay|Trans|Remarketing|Gay-Remarketing|Trans-Remarketing)_',
                rf'\1-{config.ad_dimensions}_',
                name,
                count=1,
            )

        return name


def _handle_keywords(page: Page, config: V4CampaignConfig):
    """Configure keyword targeting on the geo/audience page (before save)."""
    if not config.keywords:
        return

    import time

    try:
        # Enable keyword targeting toggle first
        page.evaluate('''() => {
            // Try multiple possible checkbox IDs/selectors
            const candidates = [
                document.getElementById("keyword_targeting"),
                document.querySelector("#campaign_keywordTargeting input[type='checkbox']"),
                document.querySelector("input[name='keyword_targeting']"),
            ];
            for (const cb of candidates) {
                if (cb && !cb.checked) {
                    cb.click();
                    cb.dispatchEvent(new Event("change", {bubbles: true}));
                    return "enabled";
                }
                if (cb && cb.checked) return "already_on";
            }
            return "not_found";
        }''')
        time.sleep(1)
        logger.info("    Keyword targeting toggle enabled")

        # Wait for keyword section to become visible
        try:
            page.wait_for_selector('span[id="select2-keyword_select-container"]',
                                   state="visible", timeout=5000)
        except Exception:
            time.sleep(2)

        # Remove existing keywords
        remove_all = page.locator('a.removeAllKeywords[data-selection-type="include"]')
        if remove_all.count() > 0 and remove_all.first.is_visible(timeout=2000):
            remove_all.first.click()
            time.sleep(0.5)

        # Open keyword selector
        kw_select = page.locator('span[id="select2-keyword_select-container"]')
        kw_select.scroll_into_view_if_needed()
        kw_select.click(timeout=5000)
        time.sleep(0.3)

        search = page.locator(
            'input.select2-search__field[aria-controls="select2-keyword_select-results"]'
        )

        for keyword in config.keywords:
            try:
                search.fill("")
                search.fill(keyword)
                import time; time.sleep(0.5)

                kw_item = None
                try:
                    kw_item = page.locator('div.keywordItem').first
                    kw_item.wait_for(state='visible', timeout=2000)
                except Exception:
                    kw_item = page.locator('li.select2-results__option').first
                    kw_item.wait_for(state='visible', timeout=3000)

                kw_item.click()
                import time; time.sleep(0.3)
            except Exception as e:
                logger.warning(f"    Keyword '{keyword}' not found: {e}")

        page.keyboard.press("Escape")
        import time; time.sleep(0.5)

        # Set match types
        if config.match_type == "broad":
            for keyword in config.keywords:
                keyword_id = keyword.replace(" ", "_")
                try:
                    page.click(f'label[for="broad_{keyword_id}"]', timeout=3000)
                except Exception:
                    try:
                        page.locator(f'//label[@for="broad_{keyword}"]').click(timeout=3000)
                    except Exception:
                        pass
                import time; time.sleep(0.2)

        logger.info(f"    Keywords: {', '.join(config.keywords)} ({config.match_type})")

    except Exception as e:
        logger.warning(f"    Could not configure keywords: {e}")

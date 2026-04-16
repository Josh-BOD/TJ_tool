"""V4 Campaign Creator — main orchestrator for the 5-step flow."""

import logging
from typing import Tuple
from playwright.sync_api import Page

from .models import V4CampaignConfig
from .utils import click_save_and_continue, check_session, dismiss_modals, set_radio
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

            # After finalization, get the LIVE campaign ID.
            # Wait for TJ to register, then use the campaigns filter to find it.
            import time as _t2; _t2.sleep(5)
            try:
                # Re-establish page context (may have been destroyed during finish)
                try:
                    self.page.goto(f"{BASE_URL}/campaigns?campaignTab=bid",
                                   wait_until="domcontentloaded", timeout=20000)
                    _t2.sleep(3)
                except Exception:
                    _t2.sleep(3)

                live_id = self._extract_live_id(campaign_id, campaign_name)
                if live_id and live_id != campaign_id:
                    logger.info(f"  Draft {campaign_id} → Live {live_id}")
                    campaign_id = live_id
            except Exception as e:
                logger.debug(f"  Could not extract live ID: {e}")

            # Pause the campaign if launch_paused is set
            if getattr(config, 'launch_paused', True):
                self._pause_campaign(campaign_id)

            logger.info(f"  Campaign created: {campaign_name} (ID: {campaign_id})")
            return campaign_id, campaign_name

        except V4CreationError:
            raise
        except Exception as e:
            raise V4CreationError(
                f"Failed to create campaign: {e}", orphan_id=campaign_id
            ) from e

    def clone_from_template(
        self,
        config: V4CampaignConfig,
        variant: str,
        csv_dir: str,
    ) -> Tuple[str, str]:
        """
        Clone a campaign from template_campaign_id, then override ALL configured fields.

        Inherits everything from template by default. For each step, navigates to
        the live campaign edit page and overrides fields that the config specifies.

        Args:
            config: Campaign config with template_campaign_id set.
            variant: Device variant — "desktop", "ios", "android".
            csv_dir: Directory containing ad CSV files.

        Returns:
            (campaign_id, campaign_name)
        """
        import time as _t
        from .steps.step1_basic_settings import GENDER_MAP

        template_id = config.template_campaign_id
        campaign_name = self.name_prefix + self._build_name(config, variant)

        logger.info(f"  Cloning from template {template_id}...")

        # ── Clone the template ───────────────────────────────
        new_id = self._clone_campaign(template_id)
        logger.info(f"  Cloned to campaign: {new_id}")

        # Cloned campaigns are LIVE — use live edit URLs
        # /campaign/{id}                    — basic settings
        # /campaign/{id}/audience           — geo & audience
        # /campaign/{id}/tracking-spots-rules — tracking & sources
        # /campaign/{id}/schedule-budget    — schedule & budget
        # /campaign/{id}/ad-settings        — ads

        # ── Step 1: Name, Group, Gender, Labels ─────────────
        if not check_session(self.page):
            raise V4CreationError("Session expired after clone", orphan_id=new_id)

        self.page.goto(
            f"{BASE_URL}/campaign/{new_id}#section_basicSettings",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        _t.sleep(5)
        dismiss_modals(self.page)

        # Campaign name
        try:
            name_input = self.page.query_selector('input[name="name"]')
            if name_input:
                name_input.fill("")
                name_input.fill(campaign_name)
                logger.info(f"    Name: {campaign_name}")
        except Exception as e:
            logger.warning(f"    Could not set name: {e}")

        # Group (skip if General — that's the default)
        if config.group and config.group.lower() != "general":
            step1._select_or_create_group(self.page, config.group)

        # Gender
        if config.gender:
            gen_val = GENDER_MAP.get(config.gender, "1")
            set_radio(self.page, "demographic_targeting_id", gen_val)
            logger.info(f"    Gender: {config.gender}")

        # Content category (editable on live campaigns via radio)
        if config.content_category:
            set_radio(self.page, "content_category_id", config.content_category.lower())
            logger.info(f"    Content category: {config.content_category}")

        # Labels (auto-generate from keyword_name + explicit labels)
        labels = list(config.labels) if config.labels else []
        if config.keyword_name:
            niche = config.keyword_name.replace("KEY-", "").replace("INT-", "").replace(" ", "")
            if niche and niche not in labels:
                labels.append(niche)
        if labels:
            step1._set_labels(self.page, labels)

        self._save_draft_step(self.page)
        logger.info(f"  [Nav] Step 1 saved")

        # ── Step 2: Geo, Audience & Targeting ────────────────
        needs_step2 = (
            config.keywords
            or config.has_os_targeting
            or config.has_browser_targeting
            or config.has_browser_language
            or config.has_postal_codes
            or config.has_isp_targeting
            or config.has_ip_targeting
            or config.has_income_targeting
            or config.has_retargeting
            or config.has_vr_targeting
            or config.has_segment_targeting
        )

        # Always visit step 2 — geo is always set from CSV, and most
        # campaigns need at least keywords or geo overrides
        if not check_session(self.page):
            raise V4CreationError("Session expired before Step 2", orphan_id=new_id)

        self.page.goto(
            f"{BASE_URL}/campaign/{new_id}/audience#section_audienceTargeting",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        _t.sleep(5)
        dismiss_modals(self.page)

        # Geo & all toggle-gated targeting (OS, browser, language, etc.)
        # configure_step2 only modifies fields where config has non-default values
        step2.configure_step2(self.page, config, variant)

        # Keywords (separate from step2 — handled after geo/targeting)
        _handle_keywords(self.page, config)

        # Wait for keyword bulk-add to fully commit before saving
        if config.keywords:
            import time as _tw
            _tw.sleep(2)

        # Save audience page — may trigger "Match Suggested CPM" modal
        self._save_audience_page()
        logger.info(f"  [Nav] Step 2 saved")

        # ── Step 3: Tracking, Sources & Bids ─────────────────
        needs_step3 = bool(
            config.tracker_id
            or config.smart_bidder
            or (config.source_selection and config.source_selection.upper() != "ALL")
        )

        if needs_step3:
            if not check_session(self.page):
                raise V4CreationError("Session expired before Step 3", orphan_id=new_id)

            self.page.goto(
                f"{BASE_URL}/campaign/{new_id}/tracking-spots-rules",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            _t.sleep(5)
            dismiss_modals(self.page)

            step3.configure_step3(self.page, config)

            self._save_draft_step(self.page)
            logger.info(f"  [Nav] Step 3 saved")
        else:
            logger.info(f"  [Nav] Step 3 skipped (inherited from template)")

        # ── Step 4: Schedule & Budget ────────────────────────
        # Only visit Step 4 if CSV specifies schedule/budget fields.
        # Otherwise inherit from template.
        needs_step4 = bool(
            config.frequency_cap
            or config.budget_type
            or config.daily_budget
            or config.start_date
            or config.end_date
        )
        if needs_step4:
            if not check_session(self.page):
                raise V4CreationError("Session expired before Step 4", orphan_id=new_id)

            self.page.goto(
                f"{BASE_URL}/campaign/{new_id}/schedule-budget",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            _t.sleep(5)
            dismiss_modals(self.page)

            step4.configure_step4(self.page, config)

            self._save_draft_step(self.page)
            logger.info(f"  [Nav] Step 4 saved")
        else:
            logger.info(f"  [Nav] Step 4 skipped (inherited from template)")

        # ── Step 5: Ad Settings (only if csv_file specified) ─
        if config.csv_file:
            if not check_session(self.page):
                raise V4CreationError("Session expired before Step 5", orphan_id=new_id)

            self.page.goto(
                f"{BASE_URL}/campaign/{new_id}/ad-settings",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            _t.sleep(5)
            dismiss_modals(self.page)

            step5.configure_step5(self.page, config, csv_dir, campaign_name)
        else:
            logger.info(f"  [Nav] Step 5 skipped (keeping template ads)")

        # Pause the campaign if launch_paused is set
        if getattr(config, 'launch_paused', True):
            self._pause_campaign(new_id)

        logger.info(f"  Campaign cloned: {campaign_name} (ID: {new_id})")
        return new_id, campaign_name

    def _pause_campaign(self, campaign_id: str):
        """Pause a campaign by navigating to its page and clicking the pause control."""
        import time as _t
        try:
            self.page.goto(
                f"{BASE_URL}/campaign/{campaign_id}",
                wait_until="domcontentloaded", timeout=15000,
            )
            _t.sleep(3)

            # Click the pause icon (fa-pause) on the campaign page
            paused = self.page.evaluate('''() => {
                // Look for the pause icon button
                const pauseIcon = document.querySelector('i.fa-pause, i.fal.fa-pause, i[class*="fa-pause"]');
                if (pauseIcon) {
                    pauseIcon.click();
                    return "paused_via_icon";
                }
                // Try parent actionBtn
                const actionBtns = document.querySelectorAll('.actionBtn');
                for (const btn of actionBtns) {
                    if (btn.className.includes('pause')) {
                        btn.click();
                        return "paused_via_actionBtn";
                    }
                }
                // Check if already paused (play icon visible instead)
                const playIcon = document.querySelector('i.fa-play, i[class*="fa-play"]');
                if (playIcon) return "already_paused";
                return "no_pause_control";
            }''')
            _t.sleep(1)

            # Confirm any dialog
            self.page.evaluate('''() => {
                document.querySelectorAll('.customAlertBox a, .modal.show a.greenButton').forEach(b => {
                    if (b.textContent.trim().match(/yes|ok|confirm/i)) b.click();
                });
            }''')
            _t.sleep(1)
            logger.info(f"    Campaign paused: {paused}")
        except Exception as e:
            logger.warning(f"    Could not pause campaign: {e}")

    def _save_audience_page(self):
        """Save the audience page on a live campaign edit.

        On live campaigns, the save button may trigger a navigation (Save & Continue)
        or stay on the same page (Update). Handle both cases gracefully.
        After saving, TJ may show a "Match Suggested CPM" modal — dismiss it.
        """
        import time as _t

        # Use "Save & Continue" (confirmAudience) which persists keywords and
        # toggle sections. "Save Changes" (#saveChanges) doesn't persist
        # keyword bulk-add or some toggle changes.
        saved = self.page.evaluate('''() => {
            const selectors = [
                "button.confirmAudience.saveAndContinue",
                "button.saveAndContinue",
                "button#saveChanges",
                "button#addCampaign",
            ];
            for (const sel of selectors) {
                const btn = document.querySelector(sel);
                if (btn && btn.offsetParent !== null) {
                    btn.scrollIntoView({block: "center"});
                    btn.click();
                    return sel;
                }
            }
            return null;
        }''')

        if saved:
            logger.info(f"    Audience save via: {saved}")
        else:
            logger.warning("    No audience save button found")
            return

        import time as _t
        _t.sleep(5)

        # Handle "Match Suggested CPM" modal if it appears
        for _ in range(10):
            try:
                modal_result = self.page.evaluate('''() => {
                    const modals = document.querySelectorAll(
                        '.modal.show, .modal.in, .modal[style*="display: block"], .customAlertBox'
                    );
                    for (const m of modals) {
                        if (m.offsetHeight > 0) {
                            const text = m.textContent || "";
                            if (text.includes("Match Suggested CPM") || text.includes("suggested CPM")) {
                                const btn = m.querySelector(
                                    'a.smallButton.greenButton, button.greenButton, a.greenButton'
                                );
                                if (btn) { btn.click(); return "dismissed_cpm_modal"; }
                            }
                            const close = m.querySelector('.close, [data-dismiss="modal"]');
                            if (close) { close.click(); return "dismissed_other_modal"; }
                        }
                    }
                    return null;
                }''')
                if modal_result:
                    logger.info(f"    {modal_result}")
                    break
            except Exception:
                logger.info("    Audience save completed (page navigated)")
                return
            _t.sleep(1)

        _t.sleep(1)
        try:
            dismiss_modals(self.page)
        except Exception:
            pass

    @staticmethod
    def _save_draft_step(page: Page):
        """Save the current draft step by clicking any available save button."""
        import time as _t
        saved = page.evaluate('''() => {
            // Try all save button variants
            const selectors = [
                "button#saveChanges",
                "button#addCampaign",
                "button.confirmAudience.saveAndContinue",
                "button.confirmtrackingAdSpotsRules.saveAndContinue",
                "button.saveAndContinue",
                "button.greenButton.smallButton[type='submit']",
                "button.greenButton.smallButton",
            ];
            for (const sel of selectors) {
                const btn = document.querySelector(sel);
                if (btn && btn.offsetParent !== null) {
                    btn.scrollIntoView({block: "center"});
                    btn.click();
                    return sel;
                }
            }
            return null;
        }''')
        _t.sleep(5)
        if saved:
            logger.info(f"    Saved via: {saved}")
        else:
            logger.warning("    No save button found")

    def _clone_campaign(self, template_id: str) -> str:
        """Clone a campaign via the TJ UI and return the new draft ID."""
        import time as _t

        self.page.goto(f"{BASE_URL}/campaigns", wait_until="domcontentloaded", timeout=15000)
        _t.sleep(3)

        # Open filters
        self.page.click("button.toggleCampaignsFilter", timeout=5000)
        _t.sleep(1)

        # Search for template by ID
        campaign_select = self.page.locator(
            '#campaign + .select2-container, span[aria-labelledby="select2-campaign-container"]'
        )
        campaign_select.click(timeout=5000)
        _t.sleep(0.5)

        search_input = self.page.locator('.select2-container--open .select2-search__field')
        search_input.fill(template_id)
        _t.sleep(2)

        self.page.locator('li.select2-results__option').first.click(timeout=5000)
        _t.sleep(0.5)

        self.page.locator('button#applyFilters').click(timeout=5000)
        _t.sleep(3)

        # Hover row and click clone icon
        clone_icon = self.page.locator(f'i.campaignIconAction.clone[data-campaign-id="{template_id}"]')
        if clone_icon.count() == 0:
            clone_icon = self.page.locator('i.campaignIconAction.clone[data-action="clone"]').first

        # Hover parent row first
        row = clone_icon.locator("xpath=ancestor::tr").first
        row.hover(timeout=5000)
        _t.sleep(0.5)

        clone_icon.first.click(force=True, no_wait_after=True, timeout=5000)
        _t.sleep(2)

        # Wait for redirect to new campaign
        self.page.wait_for_url(f"{BASE_URL}/campaign/**", timeout=30000)

        # Extract campaign ID
        new_id = self.page.url.split("/campaign/")[1].split("?")[0].split("/")[0]
        if "drafts" in new_id:
            new_id = self.page.url.split("/drafts/")[1].split("/")[0].split("?")[0]

        return new_id

    def _extract_live_id(self, draft_id: str, campaign_name: str) -> str:
        """After finalization, find the live campaign ID.

        Strategy: load campaign overview with draft ID — TJ may redirect to live ID,
        or the overview page may contain the external campaign ID.
        """
        import time as _t
        import re

        # Method 1: Check current URL for live ID
        try:
            url = self.page.url
            match = re.search(r'/campaign/(\d{10,})', url)
            if match and "/drafts/" not in url:
                return match.group(1)
        except Exception:
            pass

        # Method 2: Navigate to /campaign/{draft_id} — TJ may redirect to live campaign
        try:
            self.page.goto(f"{BASE_URL}/campaign/{draft_id}",
                          wait_until="domcontentloaded", timeout=15000)
            _t.sleep(3)
            url = self.page.url
            match = re.search(r'/campaign/(\d{10,})(?:/|$|\?)', url)
            if match and "/drafts/" not in url:
                live_id = match.group(1)
                # Verify it's OUR campaign by checking the name on the page
                page_name = self.page.evaluate('() => document.querySelector("input[name=\\"name\\"]")?.value || ""')
                if page_name and campaign_name in page_name:
                    logger.info(f"    Live ID confirmed: {live_id}")
                    return live_id
                elif page_name:
                    logger.info(f"    Redirect returned wrong campaign: '{page_name[:30]}' != '{campaign_name[:30]}'")
                else:
                    logger.info(f"    Live ID via redirect (unverified): {live_id}")
                    return live_id
        except Exception:
            pass

        # Method 3: Navigate to campaign overview
        try:
            self.page.goto(f"{BASE_URL}/campaign/overview/{draft_id}",
                          wait_until="domcontentloaded", timeout=15000)
            _t.sleep(3)
            url = self.page.url
            match = re.search(r'/campaign/(?:overview/)?(\d{10,})', url)
            if match:
                live_id = match.group(1)
                # Verify name from overview page
                page_name = self.page.evaluate('''() => {
                    const rows = document.querySelectorAll('.form-row');
                    for (const row of rows) {
                        const label = row.querySelector('label');
                        if (label && label.textContent.trim().toLowerCase().includes('name')) {
                            const val = row.querySelector('.form-value, span:not(label span)');
                            if (val) return val.textContent.trim();
                        }
                    }
                    return "";
                }''')
                if page_name and campaign_name in page_name:
                    logger.info(f"    Live ID confirmed via overview: {live_id}")
                elif page_name:
                    logger.info(f"    Overview wrong campaign: '{page_name[:30]}' != '{campaign_name[:30]}'")
                    live_id = None  # Don't use wrong ID
                else:
                    logger.info(f"    Live ID via overview (unverified): {live_id}")
                if live_id:
                    return live_id
        except Exception:
            pass

        logger.info(f"    Could not find live ID for draft {draft_id}")

        return draft_id

    # ── Helpers ───────────────────────────────────────────────────

    def _build_name(self, config: V4CampaignConfig, variant: str) -> str:
        """Generate the campaign name using the shared naming function."""
        # Determine ad_format for naming (NATIVE / INSTREAM)
        ad_format_name_map = {"display": "NATIVE", "instream": "INSTREAM", "pop": "POP"}
        ad_format = ad_format_name_map.get(config.ad_format_type, "NATIVE")
        ad_format_name = "PREROLL" if ad_format == "INSTREAM" else ad_format
        # Distinguish Native from Banner (both are ad_format_type=display)
        if config.ad_format_type == "display" and config.format_type == "banner":
            ad_format_name = "BANNER"

        mobile_combined = variant.lower() in ("all_mobile", "mobile")

        # Device abbreviation
        if mobile_combined and variant.lower() in ("ios", "android", "all_mobile"):
            device_abbr = "MOB_ALL"
        else:
            device_map = {"desktop": "DESK", "ios": "iOS", "android": "AND", "all_mobile": "MOB_ALL"}
            device_abbr = device_map.get(variant.lower(), variant.upper())

        # Gender abbreviation
        gender_map = {"male": "M", "female": "F", "all": "MF"}
        gender_abbr = gender_map.get(config.gender.lower(), "M")

        # If keyword_name has KEY-/INT- prefix, use direct naming pattern
        # e.g. Gold_ALL_PH_PREROLL_CPM_KEY-Hentai_iOS_M_JB
        pk = config.primary_keyword
        cat = config.content_category.lower()

        if cat == "gay":
            targeting = "Gay"
        elif cat == "trans":
            targeting = "Trans"
        elif pk.upper().startswith(("KEY-", "INT-")):
            prefix = pk[:4].upper()
            rest = pk[4:].strip()
            targeting = prefix + (rest.upper() if len(rest) <= 3 else rest.title().replace(" ", ""))
        else:
            targeting = f"KEY-{pk.title().replace(' ', '')}" if pk and pk != "Broad" else "KEY-Broad"

        geo_str = config.geo_name if config.geo_name else ("-".join(config.geo) if isinstance(config.geo, list) else config.geo)

        name = f"{geo_str}_EN_PH_{ad_format_name}_{config.bid_type}_{targeting}_{device_abbr}_{gender_abbr}_JB"

        if config.test_number:
            name = f"{name}_T-{config.test_number}"

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

        # Parse match types: "broad,broad,broad,broad" → first N are broad, rest exact
        match_types_str = config.match_type or ""
        match_list = [m.strip().lower() for m in match_types_str.split(",") if m.strip()]

        # Build bulk keyword text: [keyword] for broad, keyword for exact
        bulk_lines = []
        for i, keyword in enumerate(config.keywords):
            is_broad = i < len(match_list) and match_list[i] == "broad"
            bulk_lines.append(f"[{keyword}]" if is_broad else keyword)

        bulk_text = "\n".join(bulk_lines)

        # Use bulk add
        bulk_btn = page.query_selector('button.bulkAddButton')
        if bulk_btn:
            bulk_btn.click()
            time.sleep(0.5)
        else:
            page.click('button:has-text("Bulk add")', timeout=3000)
            time.sleep(0.5)

        textarea = page.query_selector('textarea.bulkTextField[data-type="include"]')
        if textarea:
            textarea.fill(bulk_text)
            time.sleep(0.3)
        else:
            page.fill('textarea.bulkTextField', bulk_text)
            time.sleep(0.3)

        include_btn = page.query_selector('button#saveBulkKeywordList[data-type="include"]')
        if include_btn:
            include_btn.click()
            time.sleep(0.5)
        else:
            page.click('button#saveBulkKeywordList', timeout=3000)
            time.sleep(0.5)

        broad_count = sum(1 for i in range(len(config.keywords)) if i < len(match_list) and match_list[i] == "broad")
        exact_count = len(config.keywords) - broad_count
        logger.info(f"    Bulk added {len(config.keywords)} keywords ({broad_count} broad, {exact_count} exact)")

    except Exception as e:
        logger.warning(f"    Could not configure keywords: {e}")

    # Handle keyword excludes (V5 field)
    keywords_exclude = getattr(config, 'keywords_exclude', [])
    logger.info(f"    Keyword exclude check: {keywords_exclude}")
    if keywords_exclude:
        _handle_keywords_exclude(page, keywords_exclude)


def _handle_keywords_exclude(page: Page, keywords_exclude: list):
    """Add exclude keywords via the bulk add exclude UI.

    TJ has separate include/exclude keyword sections. The exclude section
    uses the same bulk-add pattern but with data-type='exclude' attributes.
    If the separate exclude UI isn't available, fall back to the select2 approach.
    """
    import time

    try:
        # Scroll to keyword exclude section
        page.evaluate('''() => {
            const section = document.querySelector('#campaign_keywordTargeting, #keywordExclude');
            if (section) section.scrollIntoView({block: "center"});
        }''')
        time.sleep(0.5)

        # Remove existing exclude keywords
        page.evaluate('''() => {
            const removeAll = document.querySelector('a.removeAllKeywords[data-selection-type="exclude"]');
            if (removeAll) removeAll.click();
        }''')
        time.sleep(0.5)

        # Build bulk text (all exact for excludes)
        bulk_text = "\n".join(keywords_exclude)

        # Add exclude keywords one-by-one via select2 #keyword_exclude
        added = 0
        for kw in keywords_exclude:
            try:
                # Open the exclude keyword select2 (ID: keyword_exclude)
                page.evaluate('''() => {
                    const sel = document.querySelector("#keyword_exclude");
                    if (sel) { $(sel).select2("open"); return; }
                    const s2 = document.querySelector('#select2-keyword_exclude-container');
                    if (s2) s2.click();
                }''')
                time.sleep(0.5)

                # Type keyword in search
                search = page.locator('.select2-container--open .select2-search__field')
                search.fill(kw)
                time.sleep(1.5)

                # Click first matching result
                page.locator('li.select2-results__option').first.click(timeout=5000)
                time.sleep(0.5)
                added += 1
            except Exception as e:
                logger.warning(f"    Could not add exclude keyword '{kw}': {e}")
                try:
                    page.keyboard.press("Escape")
                except Exception:
                    pass
                time.sleep(0.3)

        logger.info(f"    Excluded {added}/{len(keywords_exclude)} keywords via select2")

        logger.info(f"    Excluded {len(keywords_exclude)} keywords")
    except Exception as e:
        logger.warning(f"    Could not configure keyword excludes: {e}")

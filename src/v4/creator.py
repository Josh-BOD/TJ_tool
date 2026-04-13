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

    def clone_from_template(
        self,
        config: V4CampaignConfig,
        variant: str,
        csv_dir: str,
    ) -> Tuple[str, str]:
        """
        Clone a campaign from template_campaign_id, then update all fields from config.

        Applies: name, group, labels, gender, content_category, content_rating (step 1),
        geos (step 2), trackers + source_selection (step 3),
        frequency_cap + daily_budget (step 4).

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
        logger.info(f"  Cloned to draft: {new_id}")

        # Cloned campaigns are LIVE (not drafts) — use live edit URLs
        # URL patterns: /campaign/{id}#section_basicSettings
        #               /campaign/{id}/audience#section_audienceTargeting
        #               /campaign/{id}/tracking-spots-rules
        #               /campaign/{id}/schedule-budget

        # ── Step 1: Basic Settings ───────────────────────────
        if not check_session(self.page):
            raise V4CreationError("Session expired after clone", orphan_id=new_id)

        self.page.goto(
            f"{BASE_URL}/campaign/{new_id}#section_basicSettings",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        _t.sleep(5)
        dismiss_modals(self.page)

        # Update campaign name
        try:
            name_input = self.page.query_selector('input[name="name"]')
            if name_input:
                name_input.fill("")
                name_input.fill(campaign_name)
                logger.info(f"    Name: {campaign_name}")
        except Exception as e:
            logger.warning(f"    Could not set name: {e}")

        # Auto-generate labels from keyword_name if not explicitly set with niche
        labels = list(config.labels) if config.labels else []
        if config.keyword_name:
            # Extract niche from keyword_name (e.g. "Big Tits" → "BigTits")
            niche = config.keyword_name.replace("KEY-", "").replace("INT-", "").replace(" ", "")
            if niche and niche not in labels:
                labels.append(niche)

        # Update labels (clears old ones first)
        if labels:
            step1._set_labels(self.page, labels)

        # Group
        if config.group:
            try:
                step1._select_or_create_group(self.page, config.group)
                logger.info(f"    Group: {config.group}")
            except Exception as e:
                logger.warning(f"    Could not set group: {e}")

        # Gender
        if config.gender:
            try:
                from .utils import set_radio
                gen_val = GENDER_MAP.get(config.gender.lower(), "1")
                set_radio(self.page, "demographic_targeting_id", gen_val)
                logger.info(f"    Gender: {config.gender}")
            except Exception as e:
                logger.warning(f"    Could not set gender: {e}")

        # Content category
        if config.content_category:
            try:
                from .utils import set_radio
                cat = config.content_category.lower()
                if cat not in ("straight", "gay", "trans"):
                    cat = "straight"
                set_radio(self.page, "content_category_id", cat)
                logger.info(f"    Content category: {cat}")
            except Exception as e:
                logger.warning(f"    Could not set content_category: {e}")

        # Content rating
        if config.content_rating:
            try:
                rating = config.content_rating.lower()
                try:
                    self.page.click(f'label:has(input[value="{rating}"])', timeout=3000)
                except Exception:
                    self.page.click(f'label:has-text("{config.content_rating}")', timeout=2000)
                logger.info(f"    Content rating: {config.content_rating}")
            except Exception as e:
                logger.warning(f"    Could not set content_rating: {e}")

        # Ad dimensions
        if config.ad_dimensions:
            try:
                from .steps.step1_basic_settings import DIMENSION_MAP
                dim_norm = config.ad_dimensions.lower().replace(" ", "")
                dim_val = DIMENSION_MAP.get(dim_norm, "9")
                set_radio(self.page, "ad_dimension_id", dim_val)
                logger.info(f"    Dimensions: {config.ad_dimensions}")
            except Exception as e:
                logger.warning(f"    Could not set ad_dimensions: {e}")

        # Save step 1
        self._save_draft_step(self.page)
        logger.info(f"  [Nav] Step 1 saved")

        # ── Step 2: Geo & Audience ───────────────────────────
        self.page.goto(
            f"{BASE_URL}/campaign/{new_id}/audience#section_audienceTargeting",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        _t.sleep(5)
        dismiss_modals(self.page)

        # Update geos if config differs from template (always apply to be safe)
        if config.geo:
            try:
                step2._add_geos(self.page, config.geo)
                logger.info(f"    Geos: {config.geo}")
            except Exception as e:
                logger.warning(f"    Could not set geos: {e}")

        # Update keywords if set
        if config.keywords:
            _handle_keywords(self.page, config)

        self._save_draft_step(self.page)
        logger.info(f"  [Nav] Step 2 saved")

        # ── Step 3: Tracking & Sources ───────────────────────
        self.page.goto(
            f"{BASE_URL}/campaign/{new_id}/tracking-spots-rules",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        _t.sleep(5)
        dismiss_modals(self.page)

        # Trackers
        if config.tracker_id:
            from .utils import select2_choose
            sep = ";" if ";" in config.tracker_id else ","
            trackers = [t.strip() for t in config.tracker_id.split(sep) if t.strip()]
            for tracker_name in trackers:
                try:
                    select2_choose(
                        self.page,
                        '#campaignTrackerId + .select2-container, '
                        'span[id*="campaignTrackerId"]',
                        tracker_name,
                    )
                    logger.info(f"    Tracker: {tracker_name}")
                except Exception as e:
                    logger.warning(f"    Could not set tracker '{tracker_name}': {e}")

        # Dismiss any alerts that appeared during tracker setup
        dismiss_modals(self.page)
        _t.sleep(1)

        # Source selection
        if config.source_selection:
            try:
                ss = config.source_selection.strip()
                if ss and ss.upper() != "ALL":
                    from .steps.step3_tracking_sources import _select_manual_sources, _include_matching_sources, _refresh_sources
                    _select_manual_sources(self.page)
                    terms = [t.strip() for t in ss.split(";") if t.strip()]
                    for term in terms:
                        _include_matching_sources(self.page, term)
                    _refresh_sources(self.page)
                    logger.info(f"    Source selection: {ss}")
            except Exception as e:
                logger.warning(f"    Could not set source_selection: {e}")

        self._save_draft_step(self.page)
        logger.info(f"  [Nav] Step 3 saved")

        # ── Step 4: Schedule & Budget ────────────────────────
        self.page.goto(
            f"{BASE_URL}/campaign/{new_id}/schedule-budget",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        _t.sleep(5)
        dismiss_modals(self.page)

        # Frequency cap
        if config.frequency_cap:
            try:
                self.page.fill('input#frequency_cap_times', "")
                self.page.fill('input#frequency_cap_times', str(config.frequency_cap))
                logger.info(f"    Frequency cap: {config.frequency_cap}")
            except Exception as e:
                logger.warning(f"    Could not set frequency_cap: {e}")

        if config.frequency_cap_every:
            try:
                self.page.fill('input#frequency_cap_every', "")
                self.page.fill('input#frequency_cap_every', str(config.frequency_cap_every))
                logger.info(f"    Frequency cap every: {config.frequency_cap_every}")
            except Exception as e:
                logger.warning(f"    Could not set frequency_cap_every: {e}")

        # Daily budget
        if config.daily_budget:
            try:
                self.page.fill('input#daily_budget', "")
                self.page.fill('input#daily_budget', str(config.daily_budget))
                logger.info(f"    Daily budget: {config.daily_budget}")
            except Exception as e:
                logger.warning(f"    Could not set daily_budget: {e}")

        self._save_draft_step(self.page)
        logger.info(f"  [Nav] Step 4 saved")

        # Step 5 skipped — clone inherits ads from template

        logger.info(f"  Campaign cloned: {campaign_name} (ID: {new_id})")
        return new_id, campaign_name

    @staticmethod
    def _save_draft_step(page: Page):
        """Save the current draft step by clicking any available save button."""
        import time as _t
        saved = page.evaluate('''() => {
            // Try all save button variants
            const selectors = [
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

    # ── Helpers ───────────────────────────────────────────────────

    def _build_name(self, config: V4CampaignConfig, variant: str) -> str:
        """Generate the campaign name using the shared naming function."""
        # Determine ad_format for naming (NATIVE / INSTREAM)
        ad_format_name_map = {"display": "NATIVE", "instream": "INSTREAM", "pop": "POP"}
        ad_format = ad_format_name_map.get(config.ad_format_type, "NATIVE")
        ad_format_name = "PREROLL" if ad_format == "INSTREAM" else ad_format

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

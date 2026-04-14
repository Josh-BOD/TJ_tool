"""
Campaign creator using Playwright for UI automation (SYNC version).

Handles creating campaigns via TrafficJunky UI since the API doesn't support it.
Uses sync Playwright to match existing tool architecture.
"""

import time
import logging
from pathlib import Path
from typing import Optional, Tuple, List
from playwright.sync_api import Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeout

from .models import CampaignDefinition, Keyword, MatchType

# Import from parent src directory
import sys
sys_path = Path(__file__).parent.parent
if str(sys_path) not in sys.path:
    sys.path.insert(0, str(sys_path))

from campaign_templates import (
    generate_campaign_name, 
    DEFAULT_SETTINGS, 
    TEMPLATE_CAMPAIGNS,
    REMARKETING_TEMPLATES,
    get_templates
)

# Setup logger
logger = logging.getLogger(__name__)


class CampaignCreationError(Exception):
    """Raised when campaign creation fails."""
    def __init__(self, message: str, orphan_id: str = None):
        self.orphan_id = orphan_id
        if orphan_id:
            message = f"{message} [ORPHAN CAMPAIGN ID: {orphan_id} - delete manually]"
        super().__init__(message)


class CampaignCreator:
    """Creates campaigns via TrafficJunky UI automation."""
    
    BASE_URL = "https://advertiser.trafficjunky.com"
    
    def __init__(self, page: Page, ad_format: str = "NATIVE", campaign_type: str = "Standard", content_category: str = "straight", keep_ads: bool = False):
        """
        Initialize campaign creator.

        Args:
            page: Playwright page object (already logged in)
            ad_format: Ad format - "NATIVE" or "INSTREAM" (default: NATIVE)
            campaign_type: Campaign type - "Standard" or "Remarketing" (default: Standard)
            content_category: Content category - "straight", "gay", or "trans" (default: straight)
            keep_ads: If True, never delete inherited ads (SHORTS flow)
        """
        self.page = page
        self.ad_format = ad_format.upper()
        self.campaign_type = campaign_type.title()
        self.content_category = content_category.lower()
        self.keep_ads = keep_ads

        # Get templates for this format, campaign type, and content category
        self.templates = get_templates(self.ad_format, self.campaign_type, self.content_category)

        # Track if this is a remarketing campaign
        self.is_remarketing = self.campaign_type.lower() == "remarketing"
    
    def create_desktop_campaign(
        self,
        campaign: CampaignDefinition,
        geo: str
    ) -> Tuple[str, str]:
        """
        Create a Desktop campaign from template.
        
        Args:
            campaign: Campaign definition
            geo: Geo code (e.g., "US") or first geo if multiple
            
        Returns:
            Tuple of (campaign_id, campaign_name)
            
        Raises:
            CampaignCreationError: If creation fails
        """
        template_id = self.templates["desktop"]["id"]
        keyword = campaign.primary_keyword if campaign.keywords else "Broad"

        # Use name override if provided, otherwise auto-generate
        if campaign.campaign_name_override:
            # Replace device suffix for desktop variant
            campaign_name = campaign.campaign_name_override.replace("_iOS_", "_DESK_").replace("_AND_", "_DESK_")
        else:
            campaign_name = generate_campaign_name(
                geo=campaign.geo,
                language=campaign.settings.language,
                ad_format=self.ad_format,
                bid_type=campaign.settings.bid_type,
                source=DEFAULT_SETTINGS["source"],
                keyword=keyword,
                device="desktop",
                gender=campaign.settings.gender,
                test_number=campaign.test_number,
                campaign_type=campaign.settings.campaign_type,
                geo_name=campaign.settings.geo_name,
                content_category=self.content_category
            )

        campaign_id = None
        try:
            # Navigate to campaigns page
            self.page.goto(f"{self.BASE_URL}/campaigns")
            self.page.wait_for_load_state("networkidle")

            # Clone template
            campaign_id = self._clone_campaign(template_id)

            # Configure campaign
            self._configure_basic_settings(campaign_name, campaign.group, campaign.settings.gender, campaign.settings.labels)
            self._configure_geo(campaign.geo)  # Pass full geo list
            self._set_browser_language(campaign.settings.language)

            # Configure keywords, negative keywords, interests, and negative interests
            self._configure_keyword_page(campaign)

            if self.keep_ads:
                # SHORTS flow: save audience page and stop (tracking/budget inherited from template)
                logger.info("  SHORTS: saving audience page — tracking/budget inherited from template")
                # No need for Save & Continue to tracking — the audience save is enough
                # The campaign is ready as a clone with template bids/budget/ads
                logger.info(f"  ✓ SHORTS campaign configured: {campaign_name} (ID: {campaign_id})")
            else:
                self._configure_tracking_and_bids(campaign)
                self._configure_schedule_and_budget(campaign)

                if campaign.csv_file:
                    self._delete_all_ads()
                else:
                    logger.info("  Keeping template ads (no csv_file — template-only campaign)")

                self._configure_ad_rotation("autopilot", "ctr")

            # Pause the campaign (user requested all created as paused)
            try:
                self.page.evaluate('''() => {
                    // Look for pause/disable toggle on current page
                    const toggle = document.querySelector('input[name="enabled"], input[name="status"]');
                    if (toggle && toggle.checked) { toggle.click(); return "paused"; }
                    return "no_toggle";
                }''')
            except Exception:
                pass

            return campaign_id, campaign_name

        except Exception as e:
            if campaign_id:
                logger.error(f"  ✗ ORPHANED CAMPAIGN: {campaign_id} (failed during configuration - delete manually)")
            raise CampaignCreationError(f"Failed to create desktop campaign: {str(e)}", orphan_id=campaign_id)
    
    def create_ios_campaign(
        self,
        campaign: CampaignDefinition,
        geo: str
    ) -> Tuple[str, str]:
        """
        Create an iOS campaign from template.
        
        Args:
            campaign: Campaign definition
            geo: Geo code
            
        Returns:
            Tuple of (campaign_id, campaign_name)
        """
        template_id = self.templates["ios"]["id"]
        keyword = campaign.primary_keyword if campaign.keywords else "Broad"

        # Use name override if provided
        if campaign.campaign_name_override:
            campaign_name = campaign.campaign_name_override
        else:
            campaign_name = generate_campaign_name(
                geo=campaign.geo,
                language=campaign.settings.language,
                ad_format=self.ad_format,
                bid_type=campaign.settings.bid_type,
                source=DEFAULT_SETTINGS["source"],
                keyword=keyword,
                device="ios",
                gender=campaign.settings.gender,
                mobile_combined=campaign.mobile_combined,
                test_number=campaign.test_number,
                campaign_type=campaign.settings.campaign_type,
                geo_name=campaign.settings.geo_name,
                content_category=self.content_category
            )

        campaign_id = None
        try:
            self.page.goto(f"{self.BASE_URL}/campaigns")
            self.page.wait_for_load_state("networkidle")

            campaign_id = self._clone_campaign(template_id)

            self._configure_basic_settings(campaign_name, campaign.group, campaign.settings.gender, campaign.settings.labels)
            self._configure_geo(campaign.geo)  # Pass full geo list
            self._set_browser_language(campaign.settings.language)

            # If mobile_combined, configure both iOS and Android OS targeting
            if campaign.mobile_combined:
                self._configure_os_targeting(
                    ["iOS", "Android"],
                    campaign.settings.ios_version,
                    campaign.settings.android_version
                )
            else:
                # Configure iOS OS targeting with version constraint only
                self._configure_os_targeting(["iOS"], campaign.settings.ios_version)

            # Configure keywords, negative keywords, interests, and negative interests
            self._configure_keyword_page(campaign)

            if self.keep_ads:
                # SHORTS flow: save audience page and stop (tracking/budget inherited from template)
                logger.info("  SHORTS: saving audience page — tracking/budget inherited from template")
                logger.info(f"  ✓ SHORTS campaign configured: {campaign_name} (ID: {campaign_id})")
            else:
                self._configure_tracking_and_bids(campaign)
                self._configure_schedule_and_budget(campaign)

                if campaign.csv_file:
                    self._delete_all_ads()
                else:
                    logger.info("  Keeping template ads (no csv_file — template-only campaign)")

                self._configure_ad_rotation("autopilot", "ctr")

            return campaign_id, campaign_name

        except Exception as e:
            if campaign_id:
                logger.error(f"  ✗ ORPHANED CAMPAIGN: {campaign_id} (failed during configuration - delete manually)")
            raise CampaignCreationError(f"Failed to create iOS campaign: {str(e)}", orphan_id=campaign_id)
    
    def create_android_campaign(
        self,
        campaign: CampaignDefinition,
        geo: str,
        ios_campaign_id: str
    ) -> Tuple[str, str]:
        """
        Create an Android campaign by cloning iOS campaign.
        
        Args:
            campaign: Campaign definition
            geo: Geo code
            ios_campaign_id: ID of iOS campaign to clone from
            
        Returns:
            Tuple of (campaign_id, campaign_name)
        """
        keyword = campaign.primary_keyword if campaign.keywords else "Broad"

        # Use name override if provided, swap iOS→AND for android variant
        if campaign.campaign_name_override:
            campaign_name = campaign.campaign_name_override.replace("_iOS_", "_AND_")
        else:
            campaign_name = generate_campaign_name(
                geo=campaign.geo,
                language=campaign.settings.language,
                ad_format=self.ad_format,
                bid_type=campaign.settings.bid_type,
                source=DEFAULT_SETTINGS["source"],
                keyword=keyword,
                device="android",
                gender=campaign.settings.gender,
                mobile_combined=campaign.mobile_combined,
                test_number=campaign.test_number,
                campaign_type=campaign.settings.campaign_type,
                geo_name=campaign.settings.geo_name,
                content_category=self.content_category
            )

        campaign_id = None
        try:
            self.page.goto(f"{self.BASE_URL}/campaigns")
            self.page.wait_for_load_state("networkidle")

            # Clone iOS campaign
            campaign_id = self._clone_campaign(ios_campaign_id)

            # Update name
            self._update_campaign_name(campaign_name)

            # Update OS targeting (remove iOS, add Android with version constraint)
            self._configure_os_targeting(["Android"], android_version=campaign.settings.android_version)

            # Continue through remaining steps (inherited from iOS)
            self._click_save_and_continue()  # Keywords
            self._click_save_and_continue()  # Tracking
            self._click_save_and_continue()  # Budget

            if self.keep_ads:
                logger.info("  Keeping template ads (--keep-ads flag, shorts flow)")
                logger.info("  Keeping template ad rotation (--keep-ads flag)")
            else:
                if campaign.csv_file:
                    self._delete_all_ads()
                else:
                    logger.info("  Keeping template ads (no csv_file — template-only campaign)")

                self._configure_ad_rotation("autopilot", "ctr")

            return campaign_id, campaign_name

        except Exception as e:
            if campaign_id:
                logger.error(f"  ✗ ORPHANED CAMPAIGN: {campaign_id} (failed during configuration - delete manually)")
            raise CampaignCreationError(f"Failed to create Android campaign: {str(e)}", orphan_id=campaign_id)
    
    def create_all_mobile_campaign(
        self,
        campaign: CampaignDefinition,
        geo: str
    ) -> Tuple[str, str]:
        """
        Create an All Mobile campaign (combined iOS + Android) from template.
        
        This is primarily used for remarketing campaigns where we have a dedicated
        "all_mobile" template that already targets both iOS and Android.
        
        Args:
            campaign: Campaign definition
            geo: Geo code
            
        Returns:
            Tuple of (campaign_id, campaign_name)
        """
        # Use all_mobile template if available, otherwise fall back to ios template
        if "all_mobile" in self.templates:
            template_id = self.templates["all_mobile"]["id"]
        else:
            template_id = self.templates["ios"]["id"]
        
        keyword = campaign.primary_keyword if campaign.keywords else "Broad"
        
        campaign_name = generate_campaign_name(
            geo=campaign.geo,  # Pass full geo list for multi-geo naming
            language=campaign.settings.language,
            ad_format=self.ad_format,  # Use the format passed to creator
            bid_type=campaign.settings.bid_type,  # Use campaign's bid type
            source=DEFAULT_SETTINGS["source"],
            keyword=keyword,
            device="all_mobile",  # Will be converted to MOB_ALL
            gender=campaign.settings.gender,
            mobile_combined=True,  # Always true for all_mobile
            test_number=campaign.test_number,
            campaign_type=campaign.settings.campaign_type,
            geo_name=campaign.settings.geo_name,
            content_category=self.content_category
        )
        
        campaign_id = None
        try:
            self.page.goto(f"{self.BASE_URL}/campaigns")
            self.page.wait_for_load_state("networkidle")

            campaign_id = self._clone_campaign(template_id)

            self._configure_basic_settings(campaign_name, campaign.group, campaign.settings.gender, campaign.settings.labels)
            self._configure_geo(campaign.geo)  # Pass full geo list
            self._set_browser_language(campaign.settings.language)

            # Skip OS targeting for remarketing - templates already have iOS/Android configured
            if not self.is_remarketing:
                # Ensure both iOS and Android OS targeting for standard campaigns
                self._configure_os_targeting(
                    ["iOS", "Android"],
                    campaign.settings.ios_version,
                    campaign.settings.android_version
                )

            # Configure keywords, negative keywords, interests, and negative interests
            self._configure_keyword_page(campaign)

            if self.keep_ads:
                logger.info("  SHORTS: saving audience page — tracking/budget inherited from template")
            else:
                self._configure_tracking_and_bids(campaign)
                self._configure_schedule_and_budget(campaign)

                if campaign.csv_file:
                    self._delete_all_ads()
                else:
                    logger.info("  Keeping template ads (no csv_file — template-only campaign)")

                self._configure_ad_rotation("autopilot", "ctr")

            return campaign_id, campaign_name

        except Exception as e:
            if campaign_id:
                logger.error(f"  ✗ ORPHANED CAMPAIGN: {campaign_id} (failed during configuration - delete manually)")
            raise CampaignCreationError(f"Failed to create all mobile campaign: {str(e)}", orphan_id=campaign_id)
    
    # =========================================================================
    # V3 From-Scratch Campaign Creation
    # =========================================================================
    
    def create_campaign_from_scratch(
        self,
        campaign: CampaignDefinition,
        device_variant: str = "desktop"
    ) -> Tuple[str, str]:
        """
        Create a campaign from scratch (not from template).
        
        This allows full control over all first-page settings that are locked
        when cloning from a template.
        
        Args:
            campaign: Campaign definition with settings
            device_variant: "desktop", "ios", "android", or "all_mobile" (for naming)
            
        Returns:
            Tuple of (campaign_id, campaign_name)
            
        Raises:
            CampaignCreationError: If creation fails
        """
        keyword = campaign.primary_keyword if campaign.keywords else "Broad"
        settings = campaign.settings

        # Use name override if provided, otherwise auto-generate
        if campaign.campaign_name_override:
            # Swap device suffix for the current variant
            campaign_name = campaign.campaign_name_override
            if device_variant == "android":
                campaign_name = campaign_name.replace("_iOS_", "_AND_")
            elif device_variant == "desktop":
                campaign_name = campaign_name.replace("_iOS_", "_DESK_").replace("_AND_", "_DESK_")
        else:
            campaign_name = generate_campaign_name(
                geo=campaign.geo,
                language=campaign.settings.language,
                ad_format=self.ad_format,
                bid_type=settings.bid_type,
                source=DEFAULT_SETTINGS["source"],
                keyword=keyword,
                device=device_variant,
                gender=settings.gender,
                mobile_combined=campaign.mobile_combined,
                test_number=campaign.test_number,
                campaign_type=settings.campaign_type,
                geo_name=settings.geo_name,
                content_category=self.content_category
            )
        
        campaign_id = None
        try:
            # Navigate to create campaign page
            logger.info(f"Navigating to create campaign page...")
            self.page.goto(f"{self.BASE_URL}/campaign/drafts/bid/create")
            self.page.wait_for_load_state("networkidle")
            time.sleep(1)

            # Step 1: Configure all first-page settings
            logger.info(f"Configuring basic settings...")
            self._configure_first_page_settings(campaign_name, campaign, device_variant)

            # Extract campaign ID from URL after save
            # URL patterns: /campaign/1234567/2 or /campaign/drafts/1234567/2
            url_path = self.page.url.split("/campaign/")[1] if "/campaign/" in self.page.url else ""
            parts = [p for p in url_path.split("/") if p and p != "drafts" and p.isdigit()]
            campaign_id = parts[0] if parts else self.page.url.split("/")[-2]
            logger.info(f"Campaign created with ID: {campaign_id} (URL: {self.page.url})")

            # Step 2: Audience page (all targeting on one page for drafts)
            is_draft = "/drafts/" in self.page.url

            logger.info(f"Configuring geo targeting...")
            self._configure_geo(campaign.geo)
            self._set_browser_language(campaign.settings.language)

            # Step 2b: Configure OS targeting for mobile
            variant_lower = device_variant.lower().strip()
            if variant_lower in ("ios", "android", "mobile", "all mobile"):
                logger.info(f"Configuring OS targeting...")
                if campaign.mobile_combined or variant_lower in ("mobile", "all mobile"):
                    self._configure_os_targeting(
                        ["iOS", "Android"],
                        settings.ios_version,
                        settings.android_version
                    )
                elif variant_lower == "ios":
                    self._configure_os_targeting(["iOS"], settings.ios_version)
                elif variant_lower == "android":
                    self._configure_os_targeting(["Android"], android_version=settings.android_version)

            if is_draft:
                # Draft flow: geo + OS + keywords all on same audience page
                # Configure keywords/interests on this page (no separate save needed)
                logger.info(f"Configuring keywords and targeting (same page)...")
                self._configure_keyword_page_no_save(campaign)

                # Save audience page via "Save Changes" button (not Save & Continue)
                logger.info(f"Saving draft audience settings...")
                self.page.evaluate('''() => {
                    const btns = document.querySelectorAll("button");
                    for (const btn of btns) {
                        if (btn.textContent.includes("Save Changes") && btn.offsetParent !== null) {
                            btn.click();
                            return true;
                        }
                    }
                    // Fallback: click Save & Continue
                    const sc = document.querySelector("button.confirmAudience.saveAndContinue");
                    if (sc) { sc.click(); return true; }
                    return false;
                }''')
                time.sleep(3)

                # Campaign saved as draft — skip tracking/schedule (will be configured later)
                logger.info(f"✓ Draft campaign saved: {campaign_name} (ID: {campaign_id})")
                logger.info(f"  Note: Tracking, budget, and ads need to be configured separately")
            else:
                # Clone flow: geo/OS page → Save → keywords page → tracking → budget
                self._click_save_and_continue()

                logger.info(f"Configuring keywords and targeting...")
                self._configure_keyword_page(campaign)

                logger.info(f"Configuring tracking and bids...")
                self._configure_tracking_and_bids(campaign)

                logger.info(f"Configuring schedule and budget...")
                self._configure_schedule_and_budget(campaign)

            # Now on ads page - ready for CSV upload
            logger.info(f"✓ Campaign {campaign_name} created successfully")

            return campaign_id, campaign_name

        except Exception as e:
            if campaign_id:
                logger.error(f"  ✗ ORPHANED CAMPAIGN: {campaign_id} (failed during configuration - delete manually)")
            raise CampaignCreationError(f"Failed to create campaign from scratch: {str(e)}", orphan_id=campaign_id)
    
    def _configure_first_page_settings(
        self,
        campaign_name: str,
        campaign: CampaignDefinition,
        device_variant: str
    ):
        """
        Configure all settings on the first page (Basic Settings).
        
        This is for V3 from-scratch creation where we have full control.
        """
        settings = campaign.settings
        
        # 1. Campaign Name
        logger.info(f"  Setting campaign name: {campaign_name}")
        self.page.fill('input[name="name"]', campaign_name)
        time.sleep(0.3)
        
        # 2. Content Rating - Always NSFW
        logger.info(f"  Setting content rating: NSFW")
        try:
            # Click NSFW radio button label
            self.page.click('label:has(input[value="nsfw"])')
        except:
            # Try alternate selector
            try:
                self.page.click('label:has-text("NSFW")')
            except:
                logger.warning("Could not set NSFW - may already be selected")
        time.sleep(0.3)
        
        # 3. Group
        logger.info(f"  Setting group: {campaign.group}")
        self._select_or_create_group(campaign.group)
        
        # 4. Labels (if any)
        if settings.labels:
            logger.info(f"  Setting labels: {settings.labels}")
            self._set_labels(settings.labels)
        
        # 5. Device (All / Desktop / Mobile)
        device_setting = settings.device
        # Override based on device_variant if needed
        variant_lower = device_variant.lower().strip()
        if variant_lower == "desktop":
            device_setting = "desktop"
        elif variant_lower in ("ios", "android", "mobile", "all mobile"):
            device_setting = "mobile"

        logger.info(f"  Setting device: {device_setting}")
        self._set_device(device_setting)
        
        # 6. Ad Format (Display / In-Stream Video / Pop)
        logger.info(f"  Setting ad format type: {settings.ad_format_type}")
        self._set_ad_format_type(settings.ad_format_type)
        time.sleep(0.5)  # Wait for dependent fields to update
        
        # 7. Format Type (Banner / Native) - only for Display
        if settings.ad_format_type == "display":
            logger.info(f"  Setting format type: {settings.format_type}")
            self._set_format_type(settings.format_type)
            time.sleep(0.3)
        
        # 8. Ad Type
        logger.info(f"  Setting ad type: {settings.ad_type}")
        self._set_ad_type(settings.ad_type)
        time.sleep(0.3)
        
        # 9. Ad Dimensions
        logger.info(f"  Setting ad dimensions: {settings.ad_dimensions}")
        self._set_ad_dimensions(settings.ad_dimensions)
        time.sleep(0.3)
        
        # 10. Content Category (Straight / Gay / Trans)
        logger.info(f"  Setting content category: {settings.content_category}")
        self._set_content_category(settings.content_category)
        
        # 11. Gender (Demographic Targeting)
        logger.info(f"  Setting gender: {settings.gender}")
        self._set_gender(settings.gender)
        
        # Save & Continue to next step
        logger.info(f"  Saving basic settings...")
        self._click_save_and_continue()
    
    def _set_labels(self, labels: List[str]):
        """Set campaign labels (multi-select). Removes inherited labels first."""
        try:
            # Step 1: Remove all existing labels (custom div.labelBox chips, NOT select2)
            # The X button is div.deleteLabel inside div.labelBox
            removed = 0
            for _ in range(20):  # Max 20 labels to remove
                delete_btn = self.page.locator(".deleteLabel").first
                if delete_btn.count() > 0 and delete_btn.is_visible():
                    try:
                        delete_btn.click(timeout=1000)
                        time.sleep(0.3)
                        removed += 1
                    except:
                        break
                else:
                    break
            if removed:
                logger.info(f"  Removed {removed} inherited label(s)")

            # Step 2: Add new labels via select2 (select#selectLabel)
            labels_input = self.page.locator('input.select2-search__field[placeholder="Select or Input a Label"]')
            labels_input.click()
            time.sleep(0.5)

            for label in labels:
                labels_input.fill(label)
                time.sleep(0.5)

                try:
                    option = self.page.locator('li.select2-results__option').first
                    option.wait_for(state='visible', timeout=2000)
                    option.click()
                    time.sleep(0.3)
                except:
                    self.page.keyboard.press("Enter")
                    logger.info(f"  Created new label: {label}")
                    time.sleep(0.3)

            # Close dropdown
            self.page.keyboard.press("Escape")
            time.sleep(0.3)
            logger.info(f"  ✓ Labels set: {labels}")
        except Exception as e:
            logger.warning(f"Could not set labels: {e}")
    
    def _set_device(self, device: str):
        """Set device targeting (All / Desktop / Mobile)."""
        # Maps to: input[name="platform_id"] with value 1=All, 2=Desktop, 3=Mobile
        device_map = {
            "all": "1",
            "desktop": "2",
            "mobile": "3"
        }
        
        value = device_map.get(device.lower(), "2")  # Default to desktop
        selector = f'input[name="platform_id"][value="{value}"]'
        
        try:
            # Wait for the element to be present
            self.page.wait_for_selector(selector, timeout=5000)
            time.sleep(0.3)
            
            # Click the parent span/label since radio inputs can be hidden
            element = self.page.locator(selector)
            element.click(force=True)
            logger.info(f"  ✓ Set device: {device}")
        except Exception as e:
            logger.warning(f"Could not set device to {device}: {e}")
    
    def _set_ad_format_type(self, ad_format_type: str):
        """Set ad format type (Display / In-Stream Video / Pop)."""
        # Maps to: input[name="ad_format_id"] with value 1=Display, 2=In-Stream Video, 3=Pop
        format_map = {
            "display": "1",
            "instream": "2",
            "pop": "3"
        }
        
        value = format_map.get(ad_format_type.lower(), "1")  # Default to Display
        selector = f'input[name="ad_format_id"][value="{value}"]'
        
        try:
            self.page.wait_for_selector(selector, timeout=5000)
            time.sleep(0.3)
            self.page.locator(selector).click(force=True)
            logger.info(f"  ✓ Set ad format type: {ad_format_type}")
            time.sleep(0.5)  # Wait for dependent fields to update
        except Exception as e:
            logger.warning(f"Could not set ad format type to {ad_format_type}: {e}")
    
    def _set_format_type(self, format_type: str):
        """Set format type (Banner / Native) - for Display ads only."""
        # Maps to: input[name="format_type_id"] with value 4=Banner, 5=Native
        format_map = {
            "banner": "4",
            "native": "5"
        }
        
        value = format_map.get(format_type.lower(), "5")  # Default to Native
        selector = f'input[name="format_type_id"][value="{value}"]'
        
        try:
            self.page.wait_for_selector(selector, timeout=5000)
            time.sleep(0.3)
            self.page.locator(selector).click(force=True)
            logger.info(f"  ✓ Set format type: {format_type}")
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"Could not set format type to {format_type}: {e}")
    
    def _set_ad_type(self, ad_type: str):
        """Set ad type (Static Banner / Video Banner / Rollover / Video File)."""
        # Maps to: input[name="ad_type_id"]
        # 1=Static Banner, 2=Video Banner, 5=Video File (PreRoll), 9=Rollover (Native)
        type_map = {
            "static_banner": "1",
            "video_banner": "2",
            "video_file": "5",
            "rollover": "9"
        }
        
        value = type_map.get(ad_type.lower(), "9")  # Default to Rollover
        selector = f'input[name="ad_type_id"][value="{value}"]'
        
        try:
            self.page.wait_for_selector(selector, timeout=5000)
            time.sleep(0.3)
            self.page.locator(selector).click(force=True)
            logger.info(f"  ✓ Set ad type: {ad_type}")
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"Could not set ad type to {ad_type}: {e}")
    
    def _set_ad_dimensions(self, ad_dimensions: str):
        """Set ad dimensions."""
        # Maps to: input[name="ad_dimension_id"]
        # Normalize input to lowercase without spaces
        dim_normalized = ad_dimensions.lower().replace(" ", "").replace("x", "x")
        
        dimension_map = {
            "300x250": "9",
            "950x250": "5",
            "468x60": "25",
            "305x99": "55",
            "300x100": "80",
            "970x90": "221",
            "320x480": "9771",
            "640x360": "9731",  # Native Rollover/Static Banner
            "9:16": "9781",    # Shorties In-Stream 9:16
        }
        
        value = dimension_map.get(dim_normalized, "9")  # Default to 300x250
        selector = f'input[name="ad_dimension_id"][value="{value}"]'
        
        try:
            self.page.wait_for_selector(selector, timeout=5000)
            time.sleep(0.3)
            self.page.locator(selector).click(force=True)
            logger.info(f"  ✓ Set ad dimensions: {ad_dimensions}")
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"Could not set ad dimensions to {ad_dimensions}: {e}")
    
    def _set_content_category(self, content_category: str):
        """Set content category (Straight / Gay / Trans)."""
        # Maps to: input[name="content_category_id"] with value straight/gay/trans
        value = content_category.lower()
        if value not in ["straight", "gay", "trans"]:
            value = "straight"  # Default
        
        selector = f'input[name="content_category_id"][value="{value}"]'
        
        try:
            self.page.wait_for_selector(selector, timeout=5000)
            time.sleep(0.3)
            self.page.locator(selector).click(force=True)
            logger.info(f"  ✓ Set content category: {content_category}")
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"Could not set content category to {content_category}: {e}")
    
    # =========================================================================
    # Internal helper methods
    # =========================================================================
    
    def _clone_campaign(self, template_id: str) -> str:
        """Clone a campaign and return new campaign ID.

        Updated flow (TJ UI 2026):
        1. Navigate to campaigns page
        2. Click "Filters" button to open side panel
        3. Search for campaign in select#campaign select2
        4. Hover over the campaign row → click inline clone icon
        5. Extract new campaign ID from redirect URL
        """
        # Navigate to campaigns page
        try:
            self.page.goto(f"{self.BASE_URL}/campaigns", wait_until='domcontentloaded', timeout=15000)
        except Exception as e:
            print(f"    ⚠ Navigation warning: {e}")
            time.sleep(2)

        time.sleep(2)

        # Open the Filters side panel
        filters_btn = self.page.locator('button.toggleCampaignsFilter')
        filters_btn.click(timeout=5000)
        time.sleep(1)

        # Use the campaign select2 to search by template ID
        campaign_select = self.page.locator('#campaign + .select2-container, span[aria-labelledby="select2-campaign-container"]')
        campaign_select.click(timeout=5000)
        time.sleep(0.5)

        search_input = self.page.locator('.select2-container--open .select2-search__field')
        search_input.fill(template_id)
        time.sleep(2)

        # Click on the dropdown result
        self.page.locator('li.select2-results__option').first.click(timeout=5000)
        time.sleep(0.5)

        # Click "Apply" button
        self.page.locator('button#applyFilters').click(timeout=5000)
        time.sleep(3)

        # Hover over the campaign row to reveal the clone icon, then click it
        campaign_row = self.page.locator(f'tr:has(i.campaignIconAction.clone[data-campaign-id="{template_id}"])').first
        if campaign_row.count() == 0:
            campaign_row = self.page.locator('tr:has(i.campaignIconAction.clone)').first

        campaign_row.hover(timeout=5000)
        time.sleep(0.5)

        clone_icon = self.page.locator(f'i.campaignIconAction.clone[data-campaign-id="{template_id}"]')
        if clone_icon.count() == 0:
            clone_icon = self.page.locator('i.campaignIconAction.clone[data-action="clone"]').first

        clone_icon.first.click(force=True, no_wait_after=True, timeout=5000)
        time.sleep(2)

        # Wait for redirect to new campaign page
        self.page.wait_for_url(f"{self.BASE_URL}/campaign/**", timeout=30000)

        # Extract campaign ID from URL
        campaign_id = self.page.url.split("/campaign/")[1].split("?")[0].split("/")[0]

        return campaign_id
    
    def _configure_basic_settings(
        self,
        campaign_name: str,
        group_name: str,
        gender: str,
        labels: Optional[List[str]] = None
    ):
        """Configure basic campaign settings (Step 1)."""
        # Dismiss any modals left over from cloning
        self._dismiss_modals()

        # Update campaign name
        self.page.fill('input[name="name"]', "")
        self.page.fill('input[name="name"]', campaign_name)

        # Select or create group
        self._select_or_create_group(group_name)

        # Set labels if provided
        if labels:
            self._set_labels(labels)

        # Set gender
        self._set_gender(gender)

        # Save & Continue
        self._click_save_and_continue()
    
    def _update_campaign_name(self, campaign_name: str):
        """Update campaign name only (for Android cloning)."""
        self.page.fill('input[name="name"]', "")
        self.page.fill('input[name="name"]', campaign_name)
        self._click_save_and_continue()
    
    def _select_or_create_group(self, group_name: str):
        """Select existing group or create new one."""
        # Skip if General - it's pre-selected by default
        if group_name.lower() == "general":
            logger.info(f"  ✓ Group: General (pre-selected)")
            return

        try:
            # Open group dropdown
            self.page.click('span.select2-selection[aria-labelledby="select2-group_id-container"]')
            time.sleep(0.5)

            # Search for group
            search_field = self.page.locator('.select2-container--open input.select2-search__field')
            search_field.fill(group_name)
            time.sleep(1)

            # Check if group exists in dropdown results
            no_results = self.page.query_selector('li.select2-results__message')

            if no_results:
                # Create new group
                self.page.click('a#showNewGroupFormButton')

                input_field = self.page.locator('input#new_group_name')
                input_field.fill(group_name)
                input_field.evaluate('(el) => el.dispatchEvent(new Event("input", { bubbles: true }))')

                try:
                    self.page.wait_for_function(
                        'document.querySelector("button#confirmNewGroupButton") && document.querySelector("button#confirmNewGroupButton").disabled === false',
                        timeout=3000
                    )
                except:
                    time.sleep(0.5)
                    self.page.evaluate('document.querySelector("button#confirmNewGroupButton").disabled = false')

                self.page.click('button#confirmNewGroupButton')
                time.sleep(0.5)
                logger.info(f"  ✓ Created new group: {group_name}")
            else:
                # Click the exact matching option
                option = self.page.locator('li.select2-results__option').filter(has_text=group_name).first
                if option.count() > 0:
                    option.click()
                else:
                    self.page.keyboard.press("Enter")
                time.sleep(0.5)
                logger.info(f"  ✓ Selected group: {group_name}")
        except Exception as e:
            logger.warning(f"  Could not set group: {e}")
            try:
                self.page.keyboard.press("Escape")
            except:
                pass
    
    def _set_gender(self, gender: str):
        """Set gender/demographic targeting (All / Male / Female)."""
        # Maps to: input[name="demographic_targeting_id"] with value 1=All, 2=Male, 3=Female
        gender_map = {
            "all": "1",
            "male": "2",
            "female": "3"
        }
        
        value = gender_map.get(gender.lower(), "1")  # Default to All
        selector = f'input[name="demographic_targeting_id"][value="{value}"]'
        
        try:
            self.page.wait_for_selector(selector, timeout=5000)
            time.sleep(0.3)
            self.page.locator(selector).click(force=True)
            logger.info(f"  ✓ Set gender: {gender}")
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"Could not set gender to {gender}: {e}")
    
    def _configure_geo(self, geo_list: List[str]):
        """
        Configure geo targeting (Step 2).

        Args:
            geo_list: List of country codes (e.g., ["US", "CA"])
        """
        # Wait for geo page to fully load — draft pages can be slow to render
        logger.info(f"  Waiting for geo page: {self.page.url}")
        time.sleep(3)  # Hard wait for page render after navigation

        # Wait for page to be fully loaded (jQuery/select2 ready)
        try:
            self.page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        time.sleep(2)

        # Remove existing geo if needed
        self.page.evaluate('() => { const r = document.querySelector("a.removeTargetedLocation"); if (r) r.click(); }')
        time.sleep(0.5)

        # Map ambiguous 2-letter codes to full names for accurate search
        GEO_SEARCH_MAP = {
            "AU": "Australia", "AT": "Austria", "AD": "Andorra",
            "AE": "United Arab Emirates", "AF": "Afghanistan",
            "GB": "United Kingdom", "GE": "Georgia", "GD": "Grenada",
            "GG": "Guernsey", "GL": "Greenland",
            "CA": "Canada", "CR": "Costa Rica", "CW": "Curacao",
            "CY": "Cyprus", "CZ": "Czech",
            "US": "United States",
            "IE": "Ireland", "IM": "Isle of Man", "ID": "Indonesia",
            "IN": "India", "IL": "Israel",
            "DE": "Germany", "DK": "Denmark",
            "ES": "Spain", "EE": "Estonia",
            "FR": "France", "FI": "Finland", "FO": "Faroe", "FJ": "Fiji",
            "HK": "Hong Kong", "HU": "Hungary", "HR": "Croatia",
            "JE": "Jersey", "JP": "Japan",
            "KR": "Korea", "KY": "Cayman",
            "LA": "Laos", "LB": "Lebanon", "LC": "Saint Lucia",
            "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia",
            "MC": "Monaco", "MD": "Moldova", "MT": "Malta",
            "NL": "Netherlands", "NO": "Norway", "NZ": "New Zealand",
            "PA": "Panama", "PL": "Poland", "PT": "Portugal", "PR": "Puerto Rico",
            "RO": "Romania", "RS": "Serbia", "RU": "Russia",
            "SA": "Saudi Arabia", "SE": "Sweden", "SI": "Slovenia", "SK": "Slovakia",
            "TH": "Thailand", "TR": "Turkey", "TW": "Taiwan", "TN": "Tunisia",
            "UA": "Ukraine", "UY": "Uruguay",
            "VE": "Venezuela",
            "BB": "Barbados", "BE": "Belgium", "BG": "Bulgaria",
            "BM": "Bermuda", "BO": "Bolivia", "BS": "Bahamas", "BY": "Belarus", "BZ": "Belize",
            "CD": "Congo", "YE": "Yemen",
        }

        # Add each geo using Playwright clicks (not JS — JS doesn't trigger hidden field updates)
        added = 0
        for geo in geo_list:
            try:
                geo_select = self.page.locator('span[id="select2-geo_country-container"]')
                geo_select.scroll_into_view_if_needed(timeout=5000)
                geo_select.click(timeout=5000)
                time.sleep(0.5)

                search_term = GEO_SEARCH_MAP.get(geo, geo)
                search_input = self.page.locator('input.select2-search__field[placeholder="Type here to search"]')
                search_input.fill(search_term)
                time.sleep(0.8)

                option = self.page.locator('li.select2-results__option:not(.select2-results__message)')
                if option.count() > 0:
                    option.first.click()
                    time.sleep(0.3)

                    add_btn = self.page.locator('button#addLocation')
                    add_btn.click(timeout=5000)
                    time.sleep(0.5)
                    added += 1
                else:
                    logger.warning(f"  No geo result for: {geo} (searched: {search_term})")
                    self.page.keyboard.press("Escape")
                    time.sleep(0.3)
            except Exception as e:
                logger.warning(f"  Failed to add geo '{geo}': {e}")
                try:
                    self.page.keyboard.press("Escape")
                except Exception:
                    pass
                time.sleep(0.3)

        if added != len(geo_list):
            logger.warning(f"  Geo: added {added}/{len(geo_list)} countries")
        else:
            logger.info(f"  Geo: {added} countries added")
    
    LANGUAGE_MAP = {
        "EN": "English", "FR": "French", "DE": "German", "ES": "Spanish",
        "IT": "Italian", "PT": "Portuguese", "NL": "Dutch", "JA": "Japanese",
        "KO": "Korean", "ZH": "Chinese", "PL": "Polish", "RU": "Russian",
        "TR": "Turkish", "AR": "Arabic", "CS": "Czech", "SV": "Swedish",
        "DA": "Danish", "NO": "Norwegian", "FI": "Finnish", "HU": "Hungarian",
        "RO": "Romanian", "TH": "Thai",
    }

    def _set_browser_language(self, language_code: str):
        """Change browser language targeting on the geo page (for cloned campaigns).

        If language_code is empty or "ALL", disable browser language targeting entirely.
        If "EN", keep template default (English). Otherwise set to the specified language.
        """
        if language_code and language_code.upper() == "EN":
            return  # Template already has English, no change needed

        # Empty or "ALL" = disable browser language targeting
        if not language_code or language_code.upper() == "ALL":
            try:
                self.page.evaluate('''() => {
                    const section = document.querySelector("#campaign_browserLanguageTargeting");
                    if (!section) return;
                    const checkbox = section.querySelector("input[type='checkbox']");
                    if (checkbox && checkbox.checked) {
                        checkbox.click();
                        checkbox.dispatchEvent(new Event("change", {bubbles: true}));
                    }
                }''')
                time.sleep(0.5)
                logger.info("  Browser language: ALL (targeting disabled)")
            except Exception as e:
                logger.warning(f"  Could not disable browser language targeting: {e}")
            return

        lang_name = self.LANGUAGE_MAP.get(language_code.upper(), language_code)
        try:
            section = self.page.locator("#campaign_browserLanguageTargeting")
            section.scroll_into_view_if_needed()
            time.sleep(0.5)

            # Ensure browser language targeting is toggled ON
            self.page.evaluate('''() => {
                const section = document.querySelector("#campaign_browserLanguageTargeting");
                if (!section) return;
                const checkbox = section.querySelector("input[type='checkbox']");
                if (checkbox && !checkbox.checked) {
                    checkbox.click();
                    checkbox.dispatchEvent(new Event("change", { bubbles: true }));
                }
            }''')
            time.sleep(1)

            # Remove ALL existing languages via their remove buttons
            removed = self.page.evaluate('''() => {
                let count = 0;
                // Method 1: Click all remove buttons in the browser language section
                const section = document.querySelector("#campaign_browserLanguageTargeting");
                if (section) {
                    const removeBtns = section.querySelectorAll(
                        "a.removeBtn, a.removeBrowserLanguage, a[class*='remove'], "
                        + "button[class*='remove'], .remove-browser-lang, "
                        + "a[data-action='remove']"
                    );
                    removeBtns.forEach(btn => { btn.click(); count++; });
                }
                // Method 2: Remove select2 choices
                const choices = section ? section.querySelectorAll(".select2-selection__choice__remove") : [];
                choices.forEach(btn => { btn.click(); count++; });
                return count;
            }''')
            time.sleep(0.5)

            # Also try clicking visible remove buttons via Playwright
            while True:
                remove_btn = section.locator("a[class*='remove'], .select2-selection__choice__remove").first
                if remove_btn.count() > 0 and remove_btn.is_visible():
                    try:
                        remove_btn.click(timeout=1000)
                        time.sleep(0.3)
                    except:
                        break
                else:
                    break

            if removed:
                logger.info(f"  Removed {removed} existing browser language(s)")

            # Click the select2 dropdown to open it
            select2 = section.locator(".select2-container").first
            select2.scroll_into_view_if_needed()
            time.sleep(0.3)
            select2.click()
            time.sleep(0.5)

            # Type and select the language
            search_input = self.page.locator(".select2-container--open .select2-search__field")
            search_input.fill(lang_name)
            time.sleep(0.5)
            self.page.locator(".select2-results__option").filter(has_text=lang_name).first.click()
            time.sleep(0.3)

            # Close dropdown if still open
            if self.page.locator(".select2-container--open").count() > 0:
                self.page.keyboard.press("Escape")
                time.sleep(0.3)

            logger.info(f"  ✓ Browser language set: {lang_name}")
        except Exception as e:
            logger.warning(f"  Could not set browser language: {e}")

    def _configure_os_targeting(self, operating_systems: List[str], ios_version=None, android_version=None):
        """
        Configure OS targeting with optional version constraints.
        
        Args:
            operating_systems: List of OS names (e.g., ["iOS"], ["Android"], or ["iOS", "Android"])
            ios_version: OSVersion object with iOS version constraint (optional)
            android_version: OSVersion object with Android version constraint (optional)
        """
        # Remove all existing OS first via JS (avoids visibility issues on draft pages)
        self.page.evaluate('''() => {
            const removeAll = document.querySelector('a.removeAll[data-selection="include"]');
            if (removeAll) { removeAll.click(); return; }
            document.querySelectorAll('a.removeOsTarget').forEach(btn => btn.click());
        }''')
        time.sleep(0.5)

        # Add each OS with its respective version constraint
        for os_name in operating_systems:
            logger.info(f"Adding OS: {os_name}")

            # Determine which version constraint to use for this OS
            os_version = None
            if os_name == "iOS" and ios_version:
                os_version = ios_version
            elif os_name == "Android" and android_version:
                os_version = android_version

            # Select OS via select2 programmatic API
            result = self.page.evaluate('''(osName) => {
                return new Promise((resolve) => {
                    const sel = document.getElementById("operating_systems_list_include");
                    if (!sel) { resolve("no_select"); return; }

                    $(sel).select2("open");
                    setTimeout(() => {
                        const options = document.querySelectorAll("li.select2-results__option");
                        for (const opt of options) {
                            if (opt.textContent.trim().includes(osName)) {
                                opt.dispatchEvent(new MouseEvent("mouseup", {bubbles: true}));
                                resolve("selected");
                                return;
                            }
                        }
                        resolve("not_found");
                    }, 500);
                });
            }''', os_name)
            time.sleep(0.5)

            if result != "selected":
                logger.warning(f"  OS '{os_name}': {result}")
                continue

            # Set version constraint if provided
            if os_version and hasattr(os_version, 'operator'):
                from .models import VersionOperator
                if os_version.operator != VersionOperator.ALL and os_version.version:
                    logger.info(f"Setting version constraint for {os_name}: {os_version}")
                    operator_text = {
                        VersionOperator.NEWER_THAN: "Newer than",
                        VersionOperator.OLDER_THAN: "Older than",
                        VersionOperator.EQUAL: "Equal to",
                    }.get(os_version.operator, "")

                    if operator_text:
                        # Select operator via select2
                        self.page.evaluate('''(opText) => {
                            const sel = document.getElementById("operating_system_selectors_include");
                            if (sel) {
                                $(sel).select2("open");
                                setTimeout(() => {
                                    const opts = document.querySelectorAll("li.select2-results__option");
                                    for (const o of opts) {
                                        if (o.textContent.includes(opText)) {
                                            o.dispatchEvent(new MouseEvent("mouseup", {bubbles: true}));
                                            break;
                                        }
                                    }
                                }, 300);
                            }
                        }''', operator_text)
                        time.sleep(1)

                        # Select version
                        self.page.evaluate('''(version) => {
                            const sel = document.getElementById("single_version_include");
                            if (sel) {
                                $(sel).select2("open");
                                setTimeout(() => {
                                    const input = document.querySelector(".select2-container--open .select2-search__field");
                                    if (input) {
                                        input.value = version;
                                        input.dispatchEvent(new Event("input", {bubbles: true}));
                                        setTimeout(() => {
                                            const opt = document.querySelector("li.select2-results__option--highlighted");
                                            if (opt) opt.dispatchEvent(new MouseEvent("mouseup", {bubbles: true}));
                                        }, 500);
                                    }
                                }, 300);
                            }
                        }''', os_version.version)
                        time.sleep(1)
                    logger.info(f"✓ Set version constraint for {os_name}: {os_version}")

            # Click Add button via JS
            self.page.evaluate('() => { const b = document.querySelector("button.addOsTarget[data-selection=\\"include\\"]"); if (b) b.click(); }')
            time.sleep(0.5)
            time.sleep(0.5)
            logger.info(f"✓ Added {os_name}")
            
            # Click outside to close any remaining dropdown
            self.page.click('body')
            time.sleep(0.3)
    
    def _configure_keyword_page_no_save(self, campaign: CampaignDefinition):
        """Configure keywords/interests on the keyword page WITHOUT saving (for draft pages where it's on the same page as geo)."""
        has_keywords = bool(campaign.keywords)
        has_negative_keywords = bool(campaign.negative_keywords)
        has_interests = bool(campaign.interests)
        has_negative_interests = bool(campaign.negative_interests)

        if not has_keywords and not has_negative_keywords and not has_interests and not has_negative_interests:
            logger.info("No keywords/interests to configure")
            return

        keyword_section_exists = self.page.locator('span[id="select2-keyword_select-container"]').count() > 0

        if has_keywords and keyword_section_exists:
            self._add_include_keywords(campaign.keywords)
        elif has_keywords and not keyword_section_exists:
            logger.warning("  Keyword section not found — format may not support it")

        if has_negative_keywords and keyword_section_exists:
            self._add_negative_keywords(campaign.negative_keywords)

        if has_interests:
            self._configure_segment_targeting(campaign.interests, "included")

        if has_negative_interests:
            self._configure_segment_targeting(campaign.negative_interests, "excluded")

    def _configure_keyword_page(self, campaign: CampaignDefinition):
        """Configure the full keyword/targeting page: keywords, negative keywords, interests, negative interests."""
        has_keywords = bool(campaign.keywords)
        has_negative_keywords = bool(campaign.negative_keywords)
        has_interests = bool(campaign.interests)
        has_negative_interests = bool(campaign.negative_interests)

        if not has_keywords and not has_negative_keywords and not has_interests and not has_negative_interests:
            logger.info("No keywords/interests to configure, skipping...")
            self._click_save_and_continue()
            return

        # Check if keyword section exists on this page (SHORTS/instream may not have it)
        keyword_section_exists = self.page.locator('span[id="select2-keyword_select-container"]').count() > 0

        # 1. Include keywords (or clear inherited ones)
        if has_keywords and keyword_section_exists:
            self._add_include_keywords(campaign.keywords)
        elif has_keywords and not keyword_section_exists:
            logger.warning("  Keyword section not found — skipping keyword targeting (format may not support it)")
        elif keyword_section_exists:
            # Clear any inherited keywords from template
            try:
                self.page.click('a.removeAllKeywords[data-selection-type="include"]')
                time.sleep(0.3)
            except Exception:
                pass

        # 2. Negative keywords (exclude)
        if has_negative_keywords and keyword_section_exists:
            self._add_negative_keywords(campaign.negative_keywords)
        elif has_negative_keywords and not keyword_section_exists:
            logger.warning("  Negative keyword section not found — skipping")

        # 3. Segment/interest targeting (include)
        if has_interests:
            self._configure_segment_targeting(campaign.interests, "included")

        # 4. Segment/interest targeting (exclude)
        if has_negative_interests:
            self._configure_segment_targeting(campaign.negative_interests, "excluded")

        # Save audience page — click Save & Continue and handle any modal that appears
        logger.info(f"  Saving audience page from {self.page.url}")
        url_before = self.page.url

        # Click Save & Continue via JS (avoids visibility issues with modals)
        self.page.evaluate('''() => {
            const btn = document.querySelector("button.confirmAudience.saveAndContinue");
            if (btn) btn.click();
        }''')

        # Poll for modal or URL change for up to 30 seconds
        for i in range(60):
            time.sleep(0.5)

            # Check if URL changed (save succeeded)
            try:
                current_url = self.page.url
            except Exception:
                logger.info(f"  Page navigated (context destroyed)")
                break
            if current_url != url_before and "sign-in" not in current_url:
                logger.info(f"  After save: {current_url}")
                break

            # Check for and accept any modal
            try:
                modal_result = self.page.evaluate('''() => {
                const modals = document.querySelectorAll(".modal");
                for (const modal of modals) {
                    if (modal.offsetHeight > 0 && modal.offsetWidth > 0) {
                        const buttons = modal.querySelectorAll("button");
                        for (const btn of buttons) {
                            const text = btn.textContent.trim();
                            if (text.includes("Match Suggested CPM") && btn.offsetHeight > 0) {
                                btn.click();
                                return "matched_cpm";
                            }
                        }
                        // Click any green/primary button
                        for (const btn of buttons) {
                            if (btn.offsetHeight > 0 && (btn.classList.contains("greenButton") || btn.classList.contains("btn-primary"))) {
                                btn.click();
                                return "clicked_" + btn.textContent.trim().substring(0, 20);
                            }
                        }
                        return "modal_visible_id=" + modal.id;
                    }
                }
                return "";
            }''')
            except Exception:
                logger.info(f"  Page navigated during modal check")
                break
            if modal_result:
                logger.info(f"  Modal: {modal_result}")
                time.sleep(3)
                try:
                    if self.page.url != url_before:
                        logger.info(f"  After modal accept: {self.page.url}")
                        break
                except Exception:
                    break
        else:
            try:
                logger.warning(f"  Save & Continue: no navigation after 30s (still on {self.page.url})")
            except Exception:
                pass

    def _configure_keywords(self, keywords: List[Keyword]):
        """Configure keyword targeting (legacy — prefer _configure_keyword_page)."""
        # If no keywords, just save and continue (for remarketing campaigns without keywords)
        if not keywords:
            logger.info("No keywords to configure, skipping...")
            self._click_save_and_continue()
            return

        self._add_include_keywords(keywords)

        # Save & Continue
        self._click_save_and_continue()

    def _add_include_keywords(self, keywords: List[Keyword]):
        """Add include keywords to the keyword page (does NOT save)."""
        # Wait for keyword page to load
        try:
            self.page.wait_for_selector('span[id="select2-keyword_select-container"]', timeout=15000)
        except Exception:
            logger.warning("  Keyword selector not found — page may still be loading")
            time.sleep(3)

        # Remove all existing keywords
        try:
            self.page.click('a.removeAllKeywords[data-selection-type="include"]')
            time.sleep(0.5)
        except Exception:
            pass

        added_keywords = []

        # Open keyword selector once
        self.page.click('span[id="select2-keyword_select-container"]')
        time.sleep(0.3)

        search_input = self.page.locator('input.select2-search__field[aria-controls="select2-keyword_select-results"]')

        for keyword in keywords:
            try:
                # Clear and type keyword in search field
                search_input.fill("") # Clear previous search
                search_input.fill(keyword.name)
                time.sleep(0.5) # Give time for results to load

                # Wait for any keyword item to appear (platform search is case-insensitive)
                # Check for both possible result types: keywordItem div or select2 results option
                keyword_item = None
                try:
                    # Try div.keywordItem first (some platforms use this)
                    keyword_item = self.page.locator('div.keywordItem').first
                    keyword_item.wait_for(state='visible', timeout=2000)
                except:
                    # Fallback to select2 results option (more common)
                    keyword_item = self.page.locator('li.select2-results__option').first
                    keyword_item.wait_for(state='visible', timeout=3000)

                # Click the keyword from results
                keyword_item.click()
                time.sleep(0.3)
                added_keywords.append(keyword)

            except PlaywrightTimeout:
                print(f"      ⚠ Skipping keyword '{keyword.name}' - not found after 5 seconds")
            except Exception as e:
                print(f"      ⚠ Error with keyword '{keyword.name}': {str(e)}")

        # Close keyword selector after all keywords are processed
        self.page.keyboard.press('Escape')
        time.sleep(0.5)

        if not added_keywords:
            print(f"      ⚠ WARNING: No keywords were added!")

        # All keywords added, now set match types
        # IMPORTANT: Click the LABEL, not the input (input is hidden)
        for keyword in added_keywords:
            if keyword.match_type == MatchType.BROAD:
                # Click the label for broad match type
                # The label wraps the hidden input
                # ID attributes convert spaces to underscores or use CSS escape
                # Try both approaches
                keyword_id = keyword.name.replace(" ", "_")
                try:
                    self.page.click(f'label[for="broad_{keyword_id}"]', timeout=5000)
                except:
                    # If that fails, try without replacement (exact match)
                    try:
                        # Use XPath for exact text match
                        label = self.page.locator(f'//label[@for="broad_{keyword.name}"]')
                        label.click(timeout=5000)
                    except:
                        print(f"      ⚠ Could not set broad match for '{keyword.name}', skipping")
                time.sleep(0.2)
            # If exact, leave it (it's the default)

        logger.info(f"  Keywords: {len(added_keywords)} added")

    def _add_negative_keywords(self, negative_keywords: List[Keyword]):
        """Add negative (exclude) keywords on the keyword page (does NOT save)."""
        try:
            # Open the exclude keyword selector
            exclude_select = self.page.locator('span[id="select2-keyword_select_excluded-container"]')
            if exclude_select.count() == 0:
                logger.warning("  Negative keyword selector not found")
                return

            exclude_select.click(timeout=5000)
            time.sleep(0.3)

            search_input = self.page.locator(
                'input.select2-search__field[aria-controls="select2-keyword_select_excluded-results"]'
            )

            added = 0
            for kw in negative_keywords:
                try:
                    search_input.fill("")
                    search_input.fill(kw.name)
                    time.sleep(0.5)

                    keyword_item = None
                    try:
                        keyword_item = self.page.locator('div.keywordItem').first
                        keyword_item.wait_for(state='visible', timeout=2000)
                    except Exception:
                        keyword_item = self.page.locator('li.select2-results__option').first
                        keyword_item.wait_for(state='visible', timeout=3000)

                    keyword_item.click()
                    time.sleep(0.3)
                    added += 1
                except Exception as e:
                    logger.warning(f"  Could not add negative keyword '{kw.name}': {e}")

            self.page.keyboard.press('Escape')
            time.sleep(0.3)
            logger.info(f"  Negative keywords: {added} added")
        except Exception as e:
            logger.warning(f"  Could not configure negative keywords: {e}")

    def _configure_segment_targeting(self, segments: List[str], targeting_type: str = "included"):
        """Configure segment/interest targeting using the proven V4 code.

        For "included": calls V4 _configure_segments directly.
        For "excluded": same logic but clicks the "excluded" link and "Exclude Segment" button.

        Args:
            segments: List of segment names (e.g., ["Intent to buy VOD-Hentai"])
            targeting_type: "included" or "excluded"
        """
        try:
            from v4.utils import enable_toggle

            if targeting_type == "included":
                # Use V4 code directly — proven to work
                from v4.steps.step2_geo_audience import _configure_segments
                from v4.models import V4CampaignConfig
                config = V4CampaignConfig(segment_targeting=";".join(segments))
                _configure_segments(self.page, config)

                # Deduplicate segments in the hidden field (V4 code can add duplicates)
                self.page.evaluate('''() => {
                    const el = document.getElementById("segments");
                    if (!el || !el.value) return;
                    try {
                        const data = JSON.parse(el.value);
                        if (data.included) {
                            const seen = new Set();
                            data.included = data.included.filter(s => {
                                if (seen.has(s.id)) return false;
                                seen.add(s.id);
                                return true;
                            });
                        }
                        el.value = JSON.stringify(data);
                    } catch(e) {}
                }''')
            else:
                # Excluded: same flow as V4 but with excluded selectors
                enable_toggle(self.page, "campaign_segmentTargeting")
                time.sleep(0.8)

                clicked = self.page.evaluate('''() => {
                    const section = document.querySelector("#campaign_segmentTargeting");
                    if (section) section.scrollIntoView({behavior: "instant", block: "center"});
                    const link = document.querySelector('a.openSegmentTargetingModal[data-targeting-segment-type="excluded"]');
                    if (link) { link.click(); return true; }
                    return false;
                }''')
                if not clicked:
                    logger.warning(f"  Segment 'excluded' link not found")
                    return
                time.sleep(2)

                # Wait for modal loading (same as V4)
                for _ in range(15):
                    loading = self.page.evaluate('''() => {
                        const modals = document.querySelectorAll('[class*="modal"]');
                        for (const m of modals) {
                            if (m.offsetHeight > 0 && m.innerText.includes("Loading")) return true;
                        }
                        return false;
                    }''')
                    if not loading:
                        break
                    time.sleep(1)
                time.sleep(1)

                search_input = self.page.locator('input[placeholder*="VOD"], input[placeholder*="Try"]').first

                for segment_name in segments:
                    search_input.fill("")
                    search_input.fill(segment_name)
                    time.sleep(1)

                    for _ in range(10):
                        loading = self.page.evaluate('''() => {
                            const modals = document.querySelectorAll('[class*="modal"]');
                            for (const m of modals) {
                                if (m.offsetHeight > 0 && m.innerText.includes("Loading")) return true;
                            }
                            return false;
                        }''')
                        if not loading:
                            break
                        time.sleep(1)
                    time.sleep(0.5)

                    checked = self.page.evaluate('''(name) => {
                        const items = document.querySelectorAll('label, li, [class*="segment"], [class*="Segment"]');
                        for (const item of items) {
                            if (item.textContent.includes(name)) {
                                const cb = item.querySelector('input[type="checkbox"]');
                                if (cb && !cb.checked) {
                                    cb.click();
                                    cb.dispatchEvent(new Event("change", {bubbles: true}));
                                    return "checked";
                                }
                                if (cb && cb.checked) return "already checked";
                            }
                        }
                        return "not found";
                    }''', segment_name)

                    if "checked" in checked:
                        logger.info(f"  ✓ Segment (excluded): {segment_name}")
                    else:
                        logger.warning(f"  Segment '{segment_name}' (excluded): {checked}")

                # Click "Exclude Segment" button
                self.page.evaluate('''() => {
                    const buttons = document.querySelectorAll('button');
                    for (const b of buttons) {
                        if (b.textContent.includes("Exclude Segment") && b.offsetHeight > 0) {
                            b.click();
                            return true;
                        }
                    }
                    return false;
                }''')
                time.sleep(1)

            logger.info(f"  Segment targeting ({targeting_type}): {len(segments)} segment(s) configured")

            # Dismiss Review Your Bids modal if it appeared after segment config
            time.sleep(1)
            self._dismiss_modals()

        except ImportError:
            logger.warning(f"  V4 segment code not available — cannot configure segments")
        except Exception as e:
            logger.warning(f"  Could not configure segment targeting ({targeting_type}): {e}")
    
    def _configure_tracking_and_bids(self, campaign: CampaignDefinition):
        """Configure tracking and bids (Step 3)."""
        settings = campaign.settings
        
        # Check if this is a CPM campaign
        if settings.is_cpm:
            logger.info("Configuring CPM bidding...")
            self._configure_cpm_bidding(campaign)
        else:
            # CPA bidding (default)
            logger.info("Configuring CPA bidding...")
            
            # Target CPA
            self.page.fill('input#target_cpa', "")
            self.page.fill('input#target_cpa', str(settings.target_cpa))
            
            # Per Source Test Budget
            self.page.fill('input#per_source_test_budget', "")
            self.page.fill('input#per_source_test_budget', str(settings.per_source_test_budget))
            
            # Max Bid
            self.page.fill('input#maximum_bid', "")
            self.page.fill('input#maximum_bid', str(settings.max_bid))
            
            # Include all sources (only for NATIVE, not for INSTREAM)
            try:
                source_checkbox = self.page.locator('input.checkUncheckAll[data-table="sourceSelectionTable"]')
                if source_checkbox.is_visible(timeout=2000):
                    self.page.check('input.checkUncheckAll[data-table="sourceSelectionTable"]')
                    time.sleep(0.3)
                    self.page.click('button.includeBtn[data-btn-action="include"]')
                    time.sleep(0.5)
            except:
                # INSTREAM campaigns don't have source selection
                pass
        
        # Save & Continue
        self._click_save_and_continue()
    
    def _configure_cpm_bidding(self, campaign: CampaignDefinition):
        """
        Configure CPM bidding by setting max bid based on highest suggested CPM.

        Keeps template sources as-is. Reads the highest suggested CPM from included
        sources and sets max bid to that value adjusted by the cpm_adjust percentage.
        """
        settings = campaign.settings
        cpm_adjust = settings.cpm_adjust

        logger.info("CPM bidding - keeping template sources")

        if cpm_adjust is not None:
            logger.info(f"Setting max bid from suggested CPM + {cpm_adjust}%...")
            self._set_max_bid_from_suggested(cpm_adjust)
        else:
            logger.info("Using template's CPM bids (no adjustment)")

    def _set_max_bid_from_suggested(self, percentage: int):
        """Set max bid to highest suggested CPM + percentage adjustment."""
        try:
            # Wait for sources table to load
            time.sleep(2)

            # Show all entries in included sources table
            try:
                page_length = self.page.query_selector('select[name="includedSourcesTable_length"]')
                if page_length:
                    self.page.select_option('select[name="includedSourcesTable_length"]', '100')
                    time.sleep(2)
            except:
                pass

            # Read highest suggested CPM from included sources
            highest_bid = self.page.evaluate('''() => {
                let highest = 0;
                // Try data-your-cpm attributes first
                const links = document.querySelectorAll("a[data-your-cpm]");
                for (const a of links) {
                    const val = parseFloat(a.getAttribute("data-your-cpm"));
                    if (!isNaN(val) && val > highest) highest = val;
                }
                // Fallback: read $ values from td cells
                if (highest === 0) {
                    document.querySelectorAll("td").forEach(td => {
                        const match = td.textContent.trim().match(/^\\$([\\d.]+)/);
                        if (match) {
                            const val = parseFloat(match[1]);
                            if (val > highest) highest = val;
                        }
                    });
                }
                return highest;
            }''')

            if highest_bid and highest_bid > 0:
                multiplier = 1 + (percentage / 100)
                max_bid = round(highest_bid * multiplier, 2)
                logger.info(f"  Highest suggested CPM: ${highest_bid} → Max bid: ${max_bid} (+{percentage}%)")
            else:
                max_bid = 0.3
                logger.info(f"  No suggested CPMs found, using default: ${max_bid}")

            # Set the max bid field
            bid_input = self.page.locator("#maximum_bid")
            bid_input.click()
            time.sleep(0.2)
            bid_input.fill(str(max_bid))
            time.sleep(0.3)
            logger.info(f"  ✓ Max bid set: ${max_bid}")

        except Exception as e:
            logger.warning(f"  Could not set max bid from suggested CPM: {e}")
    
    def _configure_schedule_and_budget(self, campaign: CampaignDefinition):
        """Configure schedule and budget (Step 4)."""
        settings = campaign.settings

        # Log current URL for debugging page flow
        current_url = self.page.url
        logger.info(f"  Budget page URL: {current_url}")

        # Wait for budget page to fully load
        self.page.wait_for_load_state("networkidle")
        time.sleep(1)

        # Dismiss any blocking modals first
        self._dismiss_modals()

        # Frequency cap — toggle via JS since it's a CSS onoffswitch
        if settings.frequency_cap == 0:
            # Disable frequency capping (uncheck the toggle)
            self.page.evaluate('''() => {
                const section = document.querySelector("#campaign_frequency_capping");
                if (section) {
                    const checkbox = section.querySelector("input[type='checkbox']");
                    if (checkbox && checkbox.checked) {
                        checkbox.click();
                    }
                }
            }''')
            time.sleep(0.3)
            logger.info("  ✓ Frequency capping disabled")
        else:
            # Enable frequency capping and set the value
            self.page.evaluate('''() => {
                const section = document.querySelector("#campaign_frequency_capping");
                if (section) {
                    const checkbox = section.querySelector("input[type='checkbox']");
                    if (checkbox && !checkbox.checked) {
                        checkbox.click();
                    }
                }
            }''')
            time.sleep(0.3)
            self.page.fill('input#frequency_cap_times', "")
            self.page.fill('input#frequency_cap_times', str(settings.frequency_cap))
            logger.info(f"  ✓ Frequency cap set to {settings.frequency_cap}")

        # Dismiss any blocking modals before budget section
        self._dismiss_modals()

        # Diagnose budget page state
        budget_diag = self.page.evaluate('''() => {
            const customRadio = document.getElementById("is_unlimited_budget_custom");
            const unlimitedRadio = document.getElementById("is_unlimited_budget");
            const budgetField = document.getElementById("daily_budget");
            return {
                customRadioExists: !!customRadio,
                customRadioChecked: customRadio ? customRadio.checked : null,
                unlimitedRadioExists: !!unlimitedRadio,
                unlimitedRadioChecked: unlimitedRadio ? unlimitedRadio.checked : null,
                budgetFieldExists: !!budgetField,
                budgetFieldVisible: budgetField ? (budgetField.offsetParent !== null) : null,
                budgetFieldValue: budgetField ? budgetField.value : null
            };
        }''')
        logger.info(f"  Budget state: custom={budget_diag.get('customRadioChecked')}, "
                     f"unlimited={budget_diag.get('unlimitedRadioChecked')}, "
                     f"field_exists={budget_diag.get('budgetFieldExists')}, "
                     f"field_visible={budget_diag.get('budgetFieldVisible')}, "
                     f"current_value={budget_diag.get('budgetFieldValue')}")

        # Select "Custom" budget option to make daily_budget field visible
        # Use JS with jQuery fallback — TJ uses jQuery for form handling
        self.page.evaluate('''() => {
            const input = document.getElementById("is_unlimited_budget_custom");
            if (input) {
                input.checked = true;
                input.click();
                input.dispatchEvent(new Event("change", {bubbles: true}));
                input.dispatchEvent(new Event("input", {bubbles: true}));
            }
            // Try jQuery trigger if available (TJ uses jQuery)
            if (typeof $ !== "undefined") {
                try { $("#is_unlimited_budget_custom").prop("checked", true).trigger("click").trigger("change"); } catch(e) {}
            }
            // Also try clicking the label
            const label = document.querySelector('label[for="is_unlimited_budget_custom"]');
            if (label) label.click();
        }''')
        time.sleep(1)

        # Wait for budget field to appear after clicking Custom radio
        for attempt in range(3):
            budget_field_ready = self.page.evaluate('''() => {
                const field = document.getElementById("daily_budget");
                return field && field.offsetParent !== null;
            }''')
            if budget_field_ready:
                break
            logger.info(f"  Waiting for budget field to appear (attempt {attempt + 1}/3)...")
            time.sleep(1)
            # Force-show if hidden
            self.page.evaluate('''() => {
                const budgetField = document.getElementById("daily_budget");
                if (budgetField) {
                    let parent = budgetField.closest("div[style*='display: none'], div.hidden, .custom-budget-section");
                    if (parent) parent.style.display = "";
                    budgetField.style.display = "";
                    budgetField.removeAttribute("disabled");
                }
            }''')

        # Max Daily Budget — use JS to set value
        budget_set = self.page.evaluate(f'''() => {{
            const field = document.getElementById("daily_budget");
            if (field) {{
                field.value = "";
                field.value = "{settings.max_daily_budget}";
                field.dispatchEvent(new Event("input", {{bubbles: true}}));
                field.dispatchEvent(new Event("change", {{bubbles: true}}));
                if (typeof $ !== "undefined") {{
                    try {{ $("#daily_budget").val("{settings.max_daily_budget}").trigger("input").trigger("change"); }} catch(e) {{}}
                }}
                return true;
            }}
            return false;
        }}''')
        if budget_set:
            logger.info(f"  ✓ Daily budget set to {settings.max_daily_budget}")
        else:
            # Fallback to Playwright fill with short timeout
            try:
                self.page.fill('input#daily_budget', "", timeout=5000)
                self.page.fill('input#daily_budget', str(settings.max_daily_budget), timeout=5000)
                logger.info(f"  ✓ Daily budget set to {settings.max_daily_budget} (fallback)")
            except Exception:
                logger.warning(f"  Could not set daily budget — template value will be used")

        # Save & Continue to ads page
        self._click_save_and_continue()

        # Verify we reached the ads page (URL should contain /ad-settings)
        time.sleep(1)
        self.page.wait_for_load_state("networkidle")
        ads_url = self.page.url
        if "/ad-settings" not in ads_url and "/ads" not in ads_url:
            logger.warning(f"  Expected ads page but got: {ads_url}")
            # Try Save & Continue again — maybe a validation error or modal blocked it
            self._dismiss_modals()
            time.sleep(1)
            try:
                self._click_save_and_continue()
                time.sleep(1)
                self.page.wait_for_load_state("networkidle")
                ads_url = self.page.url
                if "/ad-settings" not in ads_url and "/ads" not in ads_url:
                    logger.warning(f"  Still not on ads page after retry: {ads_url}")
                else:
                    logger.info(f"  ✓ Reached ads page on retry: {ads_url}")
            except Exception:
                logger.warning(f"  Could not navigate to ads page — continuing anyway")
        else:
            logger.info(f"  ✓ On ads page: {ads_url}")
    
    def _delete_all_ads(self):
        """Delete all existing ads (inherited from cloning)."""
        # Dismiss any modals blocking the ads page
        self._dismiss_modals()
        try:
            # Step 1: Set page length to 100 to ensure all ads are visible
            page_length_dropdown = self.page.query_selector('select[name="adsTable_length"]')
            if page_length_dropdown:
                self.page.select_option('select[name="adsTable_length"]', '100')
                time.sleep(1)
            
            # Step 2: Check if there are any ads to delete by looking for the select-all checkbox
            select_all_checkbox = self.page.query_selector('input[type="checkbox"].checkUncheckAll[data-table="adsTable"]')
            if not select_all_checkbox:
                # No ads table visible, nothing to delete
                logger.info("No ads to delete (checkbox not found)")
                return
            
            # Step 3: Select all ads by clicking the checkbox
            select_all_checkbox.click()
            time.sleep(0.5)
            
            # Step 4: Click Delete button
            delete_button = self.page.query_selector('button.massDeleteButton.redButton.smallButton')
            if delete_button and delete_button.is_visible():
                delete_button.click()
                time.sleep(0.5)
                
                # Step 5: Confirm deletion by clicking "Yes" in the modal
                try:
                    # Click the "Yes" button with the specific data-function attribute
                    yes_button = self.page.query_selector('a[data-function="adsManagement.deleteAds"].smallButton.greenButton')
                    if yes_button:
                        yes_button.click()
                        time.sleep(2)  # Wait for deletion to complete
                    else:
                        # Fallback to generic Yes button
                        self.page.click('button:has-text("Yes")', timeout=2000)
                        time.sleep(2)
                except Exception as e:
                    logger.warning(f"Error clicking Yes button: {e}")
                
                # Step 6: Wait until no ads show (table becomes empty or disappears)
                time.sleep(1)
                logger.info("✓ Deleted all inherited ads")
            
        except Exception as e:
            # If deletion fails, log but don't crash - the CSV upload will just add to existing ads
            logger.warning(f"Could not delete existing ads (may be none to delete): {e}")
    
    def _configure_ad_rotation(self, method: str = "autopilot", optimization: str = "ctr"):
        """
        Configure ad rotation settings on the Ads page.
        
        Args:
            method: "autopilot" or "manual" (default: autopilot)
            optimization: "ctr" or "cpa" when autopilot is selected (default: ctr)
        """
        try:
            logger.info(f"  Configuring ad rotation: {method} ({optimization})...")
            
            # Click the Autopilot radio button
            autopilot_selector = 'input[name="ad_rotation"][value="autopilot"]'
            autopilot_radio = self.page.query_selector(autopilot_selector)
            
            if autopilot_radio:
                # Click the label to ensure it's selected (radio might be hidden)
                label = self.page.query_selector('label[data-ad-rotation-trackers="autopilot"]')
                if label:
                    label.click()
                else:
                    autopilot_radio.click()
                time.sleep(0.5)
                
                # Now select CTR or CPA optimization
                if optimization.lower() == "ctr":
                    ctr_selector = 'input[name="ad_rotation_autopilot"][value="ctr"]'
                    ctr_radio = self.page.query_selector(ctr_selector)
                    if ctr_radio:
                        # Try clicking the label first
                        ctr_label = self.page.query_selector('label[for="ad_rotation_autopilot_ctr"]')
                        if ctr_label:
                            ctr_label.click()
                        else:
                            ctr_radio.click()
                        logger.info("  ✓ Ad rotation set to Autopilot (CTR)")
                    else:
                        logger.warning("  Could not find CTR radio button")
                elif optimization.lower() == "cpa":
                    cpa_selector = 'input[name="ad_rotation_autopilot"][value="cpa"]'
                    cpa_radio = self.page.query_selector(cpa_selector)
                    if cpa_radio:
                        cpa_label = self.page.query_selector('label[for="ad_rotation_autopilot_cpa"]')
                        if cpa_label:
                            cpa_label.click()
                        else:
                            cpa_radio.click()
                        logger.info("  ✓ Ad rotation set to Autopilot (CPA)")
                    else:
                        logger.warning("  Could not find CPA radio button")
            else:
                logger.warning("  Could not find Autopilot radio button")
                
        except Exception as e:
            logger.warning(f"  Could not configure ad rotation: {e}")
    
    def _dismiss_modals(self):
        """Dismiss any blocking modals (e.g., reviewYourBidsModal)."""
        try:
            # Check for reviewYourBidsModal or similar overlay modals
            dismissed = self.page.evaluate('''() => {
                let dismissed = false;
                // Handle reviewYourBidsModal — click "Match Suggested CPM" to accept bid changes
                const modal = document.querySelector("#reviewYourBidsModal");
                if (modal && (modal.classList.contains("show") || modal.offsetHeight > 0)) {
                    // Try "Match Suggested CPM" button first (green button — accepts the bid change)
                    const buttons = modal.querySelectorAll("button");
                    for (const btn of buttons) {
                        if (btn.textContent.includes("Match Suggested CPM") && btn.offsetHeight > 0) {
                            btn.click();
                            dismissed = true;
                            break;
                        }
                    }
                    // Fallback: close it
                    if (!dismissed) {
                        const closeBtn = modal.querySelector(".close, [data-dismiss='modal']");
                        if (closeBtn) { closeBtn.click(); dismissed = true; }
                    }
                    // Clean up backdrop
                    setTimeout(() => {
                        const backdrop = document.querySelector(".modal-backdrop");
                        if (backdrop) backdrop.remove();
                        document.body.classList.remove("modal-open");
                    }, 500);
                }
                // Close any visible Bootstrap modal
                const openModal = document.querySelector(".modal.in, .modal.show");
                if (openModal) {
                    const closeBtn = openModal.querySelector(".close, [data-dismiss='modal']");
                    if (closeBtn) { closeBtn.click(); dismissed = true; }
                }
                // Remove any modal backdrop
                const backdrop = document.querySelector(".modal-backdrop");
                if (backdrop) { backdrop.remove(); dismissed = true; }
                return dismissed;
            }''')
            if dismissed:
                time.sleep(2)  # Wait longer after modal dismiss (bid recalculation)
                logger.info("  Dismissed blocking modal (matched suggested CPM)")
        except Exception:
            pass

    def _click_save_and_continue(self):
        """Click Save & Continue button, verifying the page actually navigates or step changes."""
        url_before = self.page.url

        is_draft = "/drafts/" in url_before

        # For draft pages, detect step changes by page content (URL won't change)
        step_before = None
        if is_draft:
            step_before = self.page.evaluate(
                '() => { const a = document.querySelector(".wizard-step.active, .nav-link.active, [class*=\\"step\\"][class*=\\"active\\"]"); return a ? a.textContent.trim().substring(0, 30) : ""; }'
            )

        # Dismiss any modals that might be blocking
        self._dismiss_modals()

        # Try multiple possible selectors in order of specificity
        selectors = [
            'button.confirmAudience.saveAndContinue',  # Step 2 (keywords)
            'button.confirmtrackingAdSpotsRules.saveAndContinue',  # Step 3 (tracking)
            'button#addCampaign',  # Step 1 (basic settings)
            'button.saveAndContinue',  # Generic
            'button:has-text("Save & Continue")',  # Fallback by text
        ]

        for attempt in range(3):
            for selector in selectors:
                button = self.page.query_selector(selector)
                if button and button.is_visible():
                    button.click()

                    # Wait for either URL change or Review Your Bids modal (up to 10s)
                    for _ in range(20):
                        time.sleep(0.5)
                        # Check URL change
                        if self.page.url != url_before:
                            return
                        # Check for Review Your Bids modal
                        modal_handled = self.page.evaluate('''() => {
                            const modal = document.querySelector("#reviewYourBidsModal");
                            if (modal && (modal.classList.contains("show") || modal.offsetHeight > 0)) {
                                const buttons = modal.querySelectorAll("button");
                                for (const btn of buttons) {
                                    if (btn.textContent.includes("Match Suggested CPM") && btn.offsetHeight > 0) {
                                        btn.click();
                                        return "matched";
                                    }
                                }
                                // Fallback: click any visible button that isn't "close"
                                for (const btn of buttons) {
                                    if (btn.offsetHeight > 0 && !btn.classList.contains("close")) {
                                        btn.click();
                                        return "clicked_fallback";
                                    }
                                }
                            }
                            return "";
                        }''')
                        if modal_handled:
                            logger.info(f"  Review Your Bids modal: {modal_handled}")
                            time.sleep(3)  # Wait for bid recalculation and navigation
                            if self.page.url != url_before:
                                return
                            break

                    # Final check
                    self._dismiss_modals()
                    time.sleep(2)
                    if self.page.url != url_before:
                        return

                    # For draft pages: check if wizard step changed (URL stays same)
                    if is_draft:
                        step_after = self.page.evaluate(
                            '() => { const a = document.querySelector(".wizard-step.active, .nav-link.active, [class*=\\"step\\"][class*=\\"active\\"]"); return a ? a.textContent.trim().substring(0, 30) : ""; }'
                        )
                        if step_after and step_after != step_before:
                            logger.info(f"  Draft wizard: {step_before} → {step_after}")
                            return
                        time.sleep(2)
                        if self.page.url != url_before:
                            return

                    # URL didn't change — click may have been intercepted by modal
                    if attempt < 2:
                        logger.info(f"  Save & Continue clicked but page didn't navigate (attempt {attempt + 1}/3), retrying...")
                        # Aggressive modal cleanup
                        self.page.evaluate('''() => {
                            document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
                            document.querySelectorAll('.modal.in, .modal.show, .modal[style*="display: block"]').forEach(el => {
                                el.style.display = "none";
                                el.classList.remove("in", "show");
                            });
                            document.body.classList.remove('modal-open');
                            document.body.style.removeProperty('padding-right');
                            document.body.style.overflow = '';
                        }''')
                        time.sleep(1)
                        self.page.keyboard.press('Escape')
                        time.sleep(0.5)
                    break  # Found a button, break inner loop to retry
            else:
                # No button found at all
                if attempt < 2:
                    logger.info(f"  No Save & Continue button found (attempt {attempt + 1}/3), retrying...")
                    self._dismiss_modals()
                    time.sleep(1)
                    continue
                # Last resort: JS click any save button
                logger.warning(f"  No Save & Continue button visible after 3 attempts, trying JS click on {self.page.url}")
                clicked = self.page.evaluate('''() => {
                    const btns = document.querySelectorAll('button.saveAndContinue, button[type="submit"]');
                    for (const btn of btns) {
                        btn.click();
                        return btn.textContent.trim().substring(0, 40);
                    }
                    // Fallback: find any button containing "Save"
                    const allBtns = document.querySelectorAll('button');
                    for (const btn of allBtns) {
                        if (btn.textContent.includes("Save") && btn.offsetHeight > 0) {
                            btn.click();
                            return btn.textContent.trim().substring(0, 40);
                        }
                    }
                    return "";
                }''')
                if clicked:
                    logger.info(f"  JS clicked: {clicked}")
                    time.sleep(3)
                    if self.page.url != url_before:
                        return
                raise CampaignCreationError(f"Could not find Save & Continue button on {self.page.url}")

        # If we exhausted retries but URL hasn't changed, try JS click as last resort
        if self.page.url == url_before:
            logger.warning("  Save & Continue: page didn't navigate after 3 attempts, trying JS click...")
            clicked = self.page.evaluate('''() => {
                const btns = document.querySelectorAll('button.saveAndContinue, button[type="submit"]');
                for (const btn of btns) {
                    btn.click();
                    return true;
                }
                return false;
            }''')
            if clicked:
                time.sleep(3)
                self.page.wait_for_load_state("networkidle")
                self._dismiss_modals()
                if self.page.url != url_before:
                    logger.info("  ✓ JS click navigated successfully")
                    return
            logger.warning(f"  Save & Continue failed to navigate from {url_before}")


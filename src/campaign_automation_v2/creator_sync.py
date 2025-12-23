"""
Campaign creator using Playwright for UI automation (SYNC version).

Handles creating campaigns via TrafficJunky UI since the API doesn't support it.
Uses sync Playwright to match existing tool architecture.
"""

import time
import logging
from pathlib import Path
from typing import Optional, Tuple, List
from playwright.sync_api import Page, Browser, BrowserContext

from .models import CampaignDefinition, Keyword, MatchType

# Import from parent src directory
import sys
sys_path = Path(__file__).parent.parent
if str(sys_path) not in sys.path:
    sys.path.insert(0, str(sys_path))

from campaign_templates import generate_campaign_name, DEFAULT_SETTINGS, TEMPLATE_CAMPAIGNS

# Setup logger
logger = logging.getLogger(__name__)


class CampaignCreationError(Exception):
    """Raised when campaign creation fails."""
    pass


class CampaignCreator:
    """Creates campaigns via TrafficJunky UI automation."""
    
    BASE_URL = "https://advertiser.trafficjunky.com"
    
    def __init__(self, page: Page, ad_format: str = "NATIVE"):
        """
        Initialize campaign creator.
        
        Args:
            page: Playwright page object (already logged in)
            ad_format: Ad format - "NATIVE" or "INSTREAM" (default: NATIVE)
        """
        self.page = page
        self.ad_format = ad_format.upper()
        
        # Get templates for this format
        from campaign_templates import get_templates_for_format
        self.templates = get_templates_for_format(self.ad_format)
    
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
        keyword = campaign.primary_keyword
        
        # Generate campaign name with all geos
        campaign_name = generate_campaign_name(
            geo=campaign.geo,  # Pass full geo list for multi-geo naming
            language=DEFAULT_SETTINGS["language"],
            ad_format=self.ad_format,  # Use the format passed to creator
            bid_type=DEFAULT_SETTINGS["bid_type"],
            source=DEFAULT_SETTINGS["source"],
            keyword=keyword,
            device="desktop",
            gender=campaign.settings.gender,
            test_number=campaign.test_number
        )
        
        try:
            # Navigate to campaigns page
            self.page.goto(f"{self.BASE_URL}/campaigns")
            self.page.wait_for_load_state("networkidle")
            
            # Clone template
            campaign_id = self._clone_campaign(template_id)
            
            # Configure campaign
            self._configure_basic_settings(campaign_name, campaign.group, campaign.settings.gender)
            self._configure_geo(campaign.geo)  # Pass full geo list
            self._configure_keywords(campaign.keywords)
            self._configure_tracking_and_bids(campaign)
            self._configure_schedule_and_budget(campaign)
            
            # Delete any inherited ads before uploading new ones
            self._delete_all_ads()
            
            return campaign_id, campaign_name
            
        except Exception as e:
            raise CampaignCreationError(f"Failed to create desktop campaign: {str(e)}")
    
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
        keyword = campaign.primary_keyword
        
        campaign_name = generate_campaign_name(
            geo=campaign.geo,  # Pass full geo list for multi-geo naming
            language=DEFAULT_SETTINGS["language"],
            ad_format=self.ad_format,  # Use the format passed to creator
            bid_type=DEFAULT_SETTINGS["bid_type"],
            source=DEFAULT_SETTINGS["source"],
            keyword=keyword,
            device="ios",
            gender=campaign.settings.gender,
            mobile_combined=campaign.mobile_combined,
            test_number=campaign.test_number
        )
        
        try:
            self.page.goto(f"{self.BASE_URL}/campaigns")
            self.page.wait_for_load_state("networkidle")
            
            campaign_id = self._clone_campaign(template_id)
            
            self._configure_basic_settings(campaign_name, campaign.group, campaign.settings.gender)
            self._configure_geo(campaign.geo)  # Pass full geo list
            
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
            
            self._configure_keywords(campaign.keywords)
            self._configure_tracking_and_bids(campaign)
            self._configure_schedule_and_budget(campaign)
            
            # Delete any inherited ads before uploading new ones
            self._delete_all_ads()
            
            return campaign_id, campaign_name
            
        except Exception as e:
            raise CampaignCreationError(f"Failed to create iOS campaign: {str(e)}")
    
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
        keyword = campaign.primary_keyword
        
        campaign_name = generate_campaign_name(
            geo=campaign.geo,  # Pass full geo list for multi-geo naming
            language=DEFAULT_SETTINGS["language"],
            ad_format=self.ad_format,  # Use the format passed to creator
            bid_type=DEFAULT_SETTINGS["bid_type"],
            source=DEFAULT_SETTINGS["source"],
            keyword=keyword,
            device="android",
            gender=campaign.settings.gender,
            mobile_combined=campaign.mobile_combined,
            test_number=campaign.test_number
        )
        
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
            
            # Delete inherited ads before uploading new ones
            self._delete_all_ads()
            
            return campaign_id, campaign_name
            
        except Exception as e:
            raise CampaignCreationError(f"Failed to create Android campaign: {str(e)}")
    
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
            device_variant: "desktop", "ios", or "android" (for naming)
            
        Returns:
            Tuple of (campaign_id, campaign_name)
            
        Raises:
            CampaignCreationError: If creation fails
        """
        keyword = campaign.primary_keyword
        settings = campaign.settings
        
        # Generate campaign name
        campaign_name = generate_campaign_name(
            geo=campaign.geo,
            language=DEFAULT_SETTINGS["language"],
            ad_format=self.ad_format,
            bid_type=DEFAULT_SETTINGS["bid_type"],
            source=DEFAULT_SETTINGS["source"],
            keyword=keyword,
            device=device_variant,
            gender=settings.gender,
            mobile_combined=campaign.mobile_combined,
            test_number=campaign.test_number
        )
        
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
            campaign_id = self.page.url.split("/campaign/")[1].split("/")[0].split("?")[0]
            logger.info(f"Campaign created with ID: {campaign_id}")
            
            # Step 2: Configure geo targeting
            logger.info(f"Configuring geo targeting...")
            self._configure_geo(campaign.geo)
            
            # Step 2b: Configure OS targeting for mobile
            variant_lower = device_variant.lower().strip()
            if variant_lower in ("ios", "android", "mobile", "all mobile"):
                logger.info(f"Configuring OS targeting...")
                if campaign.mobile_combined or variant_lower in ("mobile", "all mobile"):
                    # Target both iOS and Android
                    self._configure_os_targeting(
                        ["iOS", "Android"],
                        settings.ios_version,
                        settings.android_version
                    )
                elif variant_lower == "ios":
                    self._configure_os_targeting(["iOS"], settings.ios_version)
                elif variant_lower == "android":
                    self._configure_os_targeting(["Android"], android_version=settings.android_version)
            
            # Step 2c: Save & Continue (geo/audience page)
            self._click_save_and_continue()
            
            # Step 3: Configure keywords
            logger.info(f"Configuring keywords...")
            self._configure_keywords(campaign.keywords)
            
            # Step 4: Configure tracking and bids
            logger.info(f"Configuring tracking and bids...")
            self._configure_tracking_and_bids(campaign)
            
            # Step 5: Configure schedule and budget
            logger.info(f"Configuring schedule and budget...")
            self._configure_schedule_and_budget(campaign)
            
            # Now on ads page - ready for CSV upload
            logger.info(f"✓ Campaign {campaign_name} created successfully")
            
            return campaign_id, campaign_name
            
        except Exception as e:
            raise CampaignCreationError(f"Failed to create campaign from scratch: {str(e)}")
    
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
        """Set campaign labels (multi-select)."""
        try:
            # Find and click the labels input field directly
            labels_input = self.page.locator('input.select2-search__field[placeholder="Select or Input a Label"]')
            labels_input.click()
            time.sleep(0.5)
            
            for label in labels:
                # Type label in search field
                labels_input.fill(label)
                time.sleep(0.5)
                
                # Click on matching result or press Enter to create new
                try:
                    # Wait for dropdown option to appear
                    option = self.page.locator('li.select2-results__option').first
                    option.wait_for(state='visible', timeout=2000)
                    option.click()
                    time.sleep(0.3)
                except:
                    # If no option found, press Enter to create the label
                    self.page.keyboard.press("Enter")
                    logger.info(f"Created new label: {label}")
                    time.sleep(0.3)
            
            # Close dropdown
            self.page.keyboard.press("Escape")
            time.sleep(0.3)
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
        """Clone a campaign and return new campaign ID."""
        # Navigate to campaigns page first
        try:
            self.page.goto(f"{self.BASE_URL}/campaigns", wait_until='domcontentloaded', timeout=15000)
        except Exception as e:
            print(f"    ⚠ Navigation warning: {e}")
            time.sleep(2)
        
        # Use the "All Campaigns" searchbox to filter by ID
        searchbox = self.page.locator('input.select2-search__field[placeholder="All Campaigns"]')
        searchbox.fill(template_id)
        time.sleep(1)
        
        # Click on the dropdown result
        self.page.click('li.select2-results__option')
        time.sleep(0.5)
        
        # Click "Apply Filters" button (as per your workflow doc)
        apply_filters_btn = self.page.query_selector('button:has-text("Apply Filters")')
        if apply_filters_btn:
            apply_filters_btn.click()
            time.sleep(1)
        
        # Select the campaign checkbox
        checkbox_selector = f'input[type="checkbox"][value="{template_id}"]'
        self.page.click(checkbox_selector)
        time.sleep(0.5)
        
        # Now the clone button should be visible in the action toolbar
        # It's a button with a copy icon, not an <a> tag
        # Wait for it to be visible and click it
        self.page.wait_for_selector('button:has(i.fa-copy)', state='visible', timeout=5000)
        self.page.click('button:has(i.fa-copy)')
        time.sleep(1)
        
        # Wait for redirect to new campaign page
        self.page.wait_for_url(f"{self.BASE_URL}/campaign/*")
        
        # Extract campaign ID from URL
        campaign_id = self.page.url.split("/campaign/")[1].split("?")[0]
        
        return campaign_id
    
    def _configure_basic_settings(
        self,
        campaign_name: str,
        group_name: str,
        gender: str
    ):
        """Configure basic campaign settings (Step 1)."""
        # Update campaign name
        self.page.fill('input[name="name"]', "")
        self.page.fill('input[name="name"]', campaign_name)
        
        # Select or create group
        self._select_or_create_group(group_name)
        
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
            self.page.fill('input.select2-search__field', group_name)
            time.sleep(0.5)
            
            # Check if group exists
            no_results = self.page.query_selector('li.select2-results__message')
            
            if no_results:
                # Create new group
                self.page.click('a#showNewGroupFormButton')
                
                # Fill the input and trigger events to enable the button
                input_field = self.page.locator('input#new_group_name')
                input_field.fill(group_name)
                
                # Trigger input event to enable button
                input_field.evaluate('(el) => el.dispatchEvent(new Event("input", { bubbles: true }))')
                
                # Wait for button to be enabled (try with retry)
                try:
                    self.page.wait_for_function(
                        'document.querySelector("button#confirmNewGroupButton") && document.querySelector("button#confirmNewGroupButton").disabled === false',
                        timeout=3000
                    )
                except:
                    # Force enable button if waiting fails
                    time.sleep(0.5)
                    self.page.evaluate('document.querySelector("button#confirmNewGroupButton").disabled = false')
                
                self.page.click('button#confirmNewGroupButton')
                time.sleep(0.5)
            else:
                # Select existing group
                self.page.keyboard.press("Enter")
                time.sleep(0.5)
        except Exception as e:
            print(f"    ⚠ Could not set group (non-critical): {e}")
            # Group is optional, try to close dropdown and continue
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
        # Remove existing geo if needed
        remove_link = self.page.query_selector('a.removeTargetedLocation')
        if remove_link:
            remove_link.click()
            time.sleep(0.5)
        
        # Add each geo
        for geo in geo_list:
            # Click to open the country dropdown
            self.page.click('span[id="select2-geo_country-container"]')
            time.sleep(0.5)
            
            # Type country name in the search field
            search_input = self.page.locator('input.select2-search__field[placeholder="Type here to search"]')
            search_input.fill(geo)
            time.sleep(0.5)
            
            # Click the first result
            self.page.click('li.select2-results__option')
            time.sleep(0.5)
            
            # Click Add button
            self.page.click('button#addLocation')
            time.sleep(0.5)
    
    def _configure_os_targeting(self, operating_systems: List[str], ios_version=None, android_version=None):
        """
        Configure OS targeting with optional version constraints.
        
        Args:
            operating_systems: List of OS names (e.g., ["iOS"], ["Android"], or ["iOS", "Android"])
            ios_version: OSVersion object with iOS version constraint (optional)
            android_version: OSVersion object with Android version constraint (optional)
        """
        # Remove all existing OS first - use "Remove All" button if available
        remove_all_btn = self.page.query_selector('a.removeAll[data-selection="include"]')
        if remove_all_btn:
            remove_all_btn.click()
            time.sleep(0.5)
            logger.info("Removed all existing OS")
        else:
            # Fallback: remove individually
            while True:
                remove_btn = self.page.query_selector('a.removeOsTarget')
                if not remove_btn:
                    break
                remove_btn.click()
                time.sleep(0.3)
        
        # Add each OS with its respective version constraint
        for os_name in operating_systems:
            logger.info(f"Adding OS: {os_name}")
            
            # Determine which version constraint to use for this OS
            os_version = None
            if os_name == "iOS" and ios_version:
                os_version = ios_version
            elif os_name == "Android" and android_version:
                os_version = android_version
            
            # Click to open OS dropdown
            self.page.click('span[id="select2-operating_systems_list_include-container"]')
            time.sleep(0.5)
            
            # Click on the OS option from the dropdown (don't type, just click)
            # Wait for dropdown to appear and click the matching option
            self.page.click(f'li.select2-results__option:has-text("{os_name}")')
            time.sleep(0.3)
            
            # Set version constraint if provided for this OS
            if os_version and hasattr(os_version, 'operator'):
                from .models import VersionOperator
                if os_version.operator != VersionOperator.ALL and os_version.version:
                    logger.info(f"Setting version constraint for {os_name}: {os_version}")
                    
                    # Click on the version selector to open operator dropdown
                    # First, need to click the "All Versions" selector
                    self.page.click('span[id="select2-operating_system_selectors_include-container"]')
                    time.sleep(0.5)
                    
                    # Select the operator based on version constraint
                    if os_version.operator == VersionOperator.NEWER_THAN:
                        self.page.click('li.select2-results__option:has-text("Newer than")')
                    elif os_version.operator == VersionOperator.OLDER_THAN:
                        self.page.click('li.select2-results__option:has-text("Older than")')
                    elif os_version.operator == VersionOperator.EQUAL:
                        self.page.click('li.select2-results__option:has-text("Equal to")')
                    time.sleep(0.5)
                    
                    # Click on the "Select Version" dropdown to open it
                    # This makes the search input visible
                    self.page.click('span[id="select2-single_version_include-container"]')
                    time.sleep(0.5)
                    
                    # Now type the version number in the search field that appears
                    # The search field selector is: input.select2-search__field with aria-controls="select2-single_version_include-results"
                    search_input = self.page.locator('input.select2-search__field[aria-controls="select2-single_version_include-results"]')
                    
                    # Type the version number slowly to trigger the dropdown
                    search_input.type(os_version.version, delay=100)
                    time.sleep(0.5)
                    
                    # Click on the highlighted option from the dropdown
                    # Wait for the highlighted option to appear
                    self.page.wait_for_selector('li.select2-results__option--highlighted', timeout=5000)
                    self.page.click('li.select2-results__option--highlighted')
                    time.sleep(0.3)
                    
                    logger.info(f"✓ Set version constraint for {os_name}: {os_version}")
            
            # Click Add button
            self.page.click('button.smallButton.greenButton.addOsTarget[data-selection="include"]')
            time.sleep(0.5)
            logger.info(f"✓ Added {os_name}")
            
            # Click outside to close any remaining dropdown
            self.page.click('body')
            time.sleep(0.3)
    
    def _configure_keywords(self, keywords: List[Keyword]):
        """Configure keyword targeting."""
        # Remove all existing keywords
        self.page.click('a.removeAllKeywords[data-selection-type="include"]')
        time.sleep(0.5)
        
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
        
        # Save & Continue
        self._click_save_and_continue()
    
    def _configure_tracking_and_bids(self, campaign: CampaignDefinition):
        """Configure tracking and bids (Step 3)."""
        settings = campaign.settings
        
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
    
    def _configure_schedule_and_budget(self, campaign: CampaignDefinition):
        """Configure schedule and budget (Step 4)."""
        settings = campaign.settings
        
        # Frequency cap
        self.page.fill('input#frequency_cap_times', "")
        self.page.fill('input#frequency_cap_times', str(settings.frequency_cap))
        
        # First, select "Custom" budget option to make daily_budget field visible
        # Click the label, not the input
        self.page.click('label:has(input#is_unlimited_budget_custom)')
        time.sleep(0.5)
        
        # Now the daily budget field should be visible
        # Max Daily Budget
        self.page.fill('input#daily_budget', "")
        self.page.fill('input#daily_budget', str(settings.max_daily_budget))
        
        # Save & Continue to ads page
        self._click_save_and_continue()
    
    def _delete_all_ads(self):
        """Delete all existing ads (inherited from cloning)."""
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
    
    def _click_save_and_continue(self):
        """Click Save & Continue button."""
        # Try multiple possible selectors in order of specificity
        selectors = [
            'button.confirmAudience.saveAndContinue',  # Step 2 (keywords)
            'button.confirmtrackingAdSpotsRules.saveAndContinue',  # Step 3 (tracking)
            'button#addCampaign',  # Step 1 (basic settings)
            'button.saveAndContinue',  # Generic
            'button:has-text("Save & Continue")',  # Fallback by text
        ]
        
        for selector in selectors:
            button = self.page.query_selector(selector)
            if button and button.is_visible():
                button.click()
                time.sleep(2)  # Wait for page transition
                return
        
        raise CampaignCreationError("Could not find Save & Continue button")


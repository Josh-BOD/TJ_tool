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
            geo: Geo code (e.g., "US")
            
        Returns:
            Tuple of (campaign_id, campaign_name)
            
        Raises:
            CampaignCreationError: If creation fails
        """
        template_id = self.templates["desktop"]["id"]
        keyword = campaign.primary_keyword
        
        # Generate campaign name
        campaign_name = generate_campaign_name(
            geo=geo,
            language=DEFAULT_SETTINGS["language"],
            ad_format=self.ad_format,  # Use the format passed to creator
            bid_type=DEFAULT_SETTINGS["bid_type"],
            source=DEFAULT_SETTINGS["source"],
            keyword=keyword,
            device="desktop",
            gender=campaign.settings.gender
        )
        
        try:
            # Navigate to campaigns page
            self.page.goto(f"{self.BASE_URL}/campaigns")
            self.page.wait_for_load_state("networkidle")
            
            # Clone template
            campaign_id = self._clone_campaign(template_id)
            
            # Configure campaign
            self._configure_basic_settings(campaign_name, campaign.group, campaign.settings.gender)
            self._configure_geo(geo)
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
            geo=geo,
            language=DEFAULT_SETTINGS["language"],
            ad_format=self.ad_format,  # Use the format passed to creator
            bid_type=DEFAULT_SETTINGS["bid_type"],
            source=DEFAULT_SETTINGS["source"],
            keyword=keyword,
            device="ios",
            gender=campaign.settings.gender
        )
        
        try:
            self.page.goto(f"{self.BASE_URL}/campaigns")
            self.page.wait_for_load_state("networkidle")
            
            campaign_id = self._clone_campaign(template_id)
            
            self._configure_basic_settings(campaign_name, campaign.group, campaign.settings.gender)
            self._configure_geo(geo)
            # Configure iOS OS targeting with version constraint
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
            geo=geo,
            language=DEFAULT_SETTINGS["language"],
            ad_format=self.ad_format,  # Use the format passed to creator
            bid_type=DEFAULT_SETTINGS["bid_type"],
            source=DEFAULT_SETTINGS["source"],
            keyword=keyword,
            device="android",
            gender=campaign.settings.gender
        )
        
        try:
            self.page.goto(f"{self.BASE_URL}/campaigns")
            self.page.wait_for_load_state("networkidle")
            
            # Clone iOS campaign
            campaign_id = self._clone_campaign(ios_campaign_id)
            
            # Update name
            self._update_campaign_name(campaign_name)
            
            # Update OS targeting (remove iOS, add Android with version constraint)
            self._configure_os_targeting(["Android"], campaign.settings.android_version)
            
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
    # Internal helper methods
    # =========================================================================
    
    def _clone_campaign(self, template_id: str) -> str:
        """Clone a campaign and return new campaign ID."""
        # Navigate to campaigns page first
        self.page.goto(f"{self.BASE_URL}/campaigns")
        self.page.wait_for_load_state("networkidle")
        
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
            
            # Wait for button to be enabled
            self.page.wait_for_function(
                'document.querySelector("button#confirmNewGroupButton").disabled === false',
                timeout=5000
            )
            
            self.page.click('button#confirmNewGroupButton')
            time.sleep(0.5)
        else:
            # Select existing group
            self.page.keyboard.press("Enter")
            time.sleep(0.5)
    
    def _set_gender(self, gender: str):
        """Set gender targeting."""
        gender_map = {
            "male": "demographic_male",
            "female": "demographic_female",
            "all": "demographic_all"
        }
        
        gender_id = gender_map.get(gender.lower(), "demographic_male")
        # Click the label instead of the input (label wraps the input)
        self.page.click(f'label:has(input#{gender_id})')
    
    def _configure_geo(self, geo: str):
        """Configure geo targeting (Step 2)."""
        # Remove existing geo if needed
        remove_link = self.page.query_selector('a.removeTargetedLocation')
        if remove_link:
            remove_link.click()
            time.sleep(0.5)
        
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
    
    def _configure_os_targeting(self, operating_systems: List[str], os_version=None):
        """
        Configure OS targeting with optional version constraints.
        
        Args:
            operating_systems: List of OS names (e.g., ["iOS"], ["Android"])
            os_version: OSVersion object with version constraint (optional)
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
        
        # Add each OS
        for os_name in operating_systems:
            logger.info(f"Adding OS: {os_name}")
            
            # Click to open OS dropdown
            self.page.click('span[id="select2-operating_systems_list_include-container"]')
            time.sleep(0.5)
            
            # Click on the OS option from the dropdown (don't type, just click)
            # Wait for dropdown to appear and click the matching option
            self.page.click(f'li.select2-results__option:has-text("{os_name}")')
            time.sleep(0.3)
            
            # Set version constraint if provided
            if os_version and hasattr(os_version, 'operator'):
                from .models import VersionOperator
                if os_version.operator != VersionOperator.ALL and os_version.version:
                    logger.info(f"Setting version constraint: {os_version}")
                    
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
                    
                    logger.info(f"✓ Set version constraint: {os_version}")
            
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
        
        # Add each keyword
        for keyword in keywords:
            # Click to open keyword selector
            self.page.click('span[id="select2-keyword_select-container"]')
            time.sleep(0.3)
            
            # Type keyword in search field
            search_input = self.page.locator('input.select2-search__field[aria-controls="select2-keyword_select-results"]')
            search_input.fill(keyword.name)
            time.sleep(0.5)
            
            # Click the keyword from results (div.keywordItem)
            self.page.click(f'div.keywordItem[title="{keyword.name}"]')
            time.sleep(0.3)
            
            # Click outside to close the dropdown after each keyword
            self.page.click('body')
            time.sleep(0.3)
        
        # All keywords added, now set match types
        # IMPORTANT: Click the LABEL, not the input (input is hidden)
        for keyword in keywords:
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
                        print(f"Warning: Could not set broad match for '{keyword.name}', skipping")
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
        
        # Include all sources
        self.page.check('input.checkUncheckAll[data-table="sourceSelectionTable"]')
        time.sleep(0.3)
        self.page.click('button.includeBtn[data-btn-action="include"]')
        time.sleep(0.5)
        
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


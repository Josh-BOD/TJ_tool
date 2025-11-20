"""
Campaign creator using Playwright for UI automation.

Handles creating campaigns via TrafficJunky UI since the API doesn't support it.
"""

import asyncio
from pathlib import Path
from typing import Optional, Tuple, List
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from .models import CampaignDefinition, Keyword, MatchType

# Import from parent src directory
import sys
sys_path = Path(__file__).parent.parent
if str(sys_path) not in sys.path:
    sys.path.insert(0, str(sys_path))

from campaign_templates import generate_campaign_name, DEFAULT_SETTINGS, TEMPLATE_CAMPAIGNS
from auth import TJAuthenticator


class CampaignCreationError(Exception):
    """Raised when campaign creation fails."""
    pass


class CampaignCreator:
    """Creates campaigns via TrafficJunky UI automation."""
    
    BASE_URL = "https://advertiser.trafficjunky.com"
    
    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = True,
        slow_mo: int = 500
    ):
        """
        Initialize campaign creator.
        
        Args:
            username: TrafficJunky username
            password: TrafficJunky password
            headless: Run browser in headless mode
            slow_mo: Slow down operations by N milliseconds
        """
        self.username = username
        self.password = password
        self.headless = headless
        self.slow_mo = slow_mo
        
        self.playwright: Optional[any] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.authenticator: Optional[TJAuthenticator] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def start(self):
        """Start browser and login with fresh session."""
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo
        )
        
        # Always create fresh context - NEVER reuse old sessions
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        
        # Initialize authenticator
        self.authenticator = TJAuthenticator(self.username, self.password)
        
        # Login using existing auth system
        print("→ Logging in to TrafficJunky...")
        
        # Convert async page to sync for auth module
        # The auth module uses sync API, so we need to handle this
        # For now, use manual_login which handles reCAPTCHA
        success = self.authenticator.manual_login(self.page._sync, timeout=120)
        
        if not success:
            raise Exception("Login failed - please check credentials")
        
        print("✓ Successfully logged in")
    
    async def close(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()
        
        if self.playwright:
            await self.playwright.stop()
    
    async def create_desktop_campaign(
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
        template_id = TEMPLATE_CAMPAIGNS["desktop"]["id"]
        keyword = campaign.primary_keyword
        
        # Generate campaign name
        campaign_name = generate_campaign_name(
            geo=geo,
            language=DEFAULT_SETTINGS["language"],
            ad_format=DEFAULT_SETTINGS["ad_format"],
            bid_type=DEFAULT_SETTINGS["bid_type"],
            source=DEFAULT_SETTINGS["source"],
            keyword=keyword,
            device="desktop",
            gender=campaign.settings.gender
        )
        
        try:
            # Navigate to campaigns page
            await self.page.goto(f"{self.BASE_URL}/campaigns")
            await self.page.wait_for_load_state("networkidle")
            
            # Clone template
            campaign_id = await self._clone_campaign(template_id)
            
            # Configure campaign
            await self._configure_basic_settings(campaign_name, campaign.group, campaign.settings.gender)
            await self._configure_geo(geo)
            await self._configure_keywords(campaign.keywords)
            await self._configure_tracking_and_bids(campaign)
            await self._configure_schedule_and_budget(campaign)
            
            return campaign_id, campaign_name
            
        except Exception as e:
            raise CampaignCreationError(f"Failed to create desktop campaign: {str(e)}")
    
    async def create_ios_campaign(
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
        template_id = TEMPLATE_CAMPAIGNS["ios"]["id"]
        keyword = campaign.primary_keyword
        
        campaign_name = generate_campaign_name(
            geo=geo,
            language=DEFAULT_SETTINGS["language"],
            ad_format=DEFAULT_SETTINGS["ad_format"],
            bid_type=DEFAULT_SETTINGS["bid_type"],
            source=DEFAULT_SETTINGS["source"],
            keyword=keyword,
            device="ios",
            gender=campaign.settings.gender
        )
        
        try:
            await self.page.goto(f"{self.BASE_URL}/campaigns")
            await self.page.wait_for_load_state("networkidle")
            
            campaign_id = await self._clone_campaign(template_id)
            
            await self._configure_basic_settings(campaign_name, campaign.group, campaign.settings.gender)
            await self._configure_geo(geo)
            await self._configure_os_targeting(["iOS"])
            await self._configure_keywords(campaign.keywords)
            await self._configure_tracking_and_bids(campaign)
            await self._configure_schedule_and_budget(campaign)
            
            return campaign_id, campaign_name
            
        except Exception as e:
            raise CampaignCreationError(f"Failed to create iOS campaign: {str(e)}")
    
    async def create_android_campaign(
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
            ad_format=DEFAULT_SETTINGS["ad_format"],
            bid_type=DEFAULT_SETTINGS["bid_type"],
            source=DEFAULT_SETTINGS["source"],
            keyword=keyword,
            device="android",
            gender=campaign.settings.gender
        )
        
        try:
            await self.page.goto(f"{self.BASE_URL}/campaigns")
            await self.page.wait_for_load_state("networkidle")
            
            # Clone iOS campaign
            campaign_id = await self._clone_campaign(ios_campaign_id)
            
            # Update name
            await self._update_campaign_name(campaign_name)
            
            # Update OS targeting (remove iOS, add Android)
            await self._configure_os_targeting(["Android"])
            
            # Continue through remaining steps (inherited from iOS)
            await self._click_save_and_continue()  # Keywords
            await self._click_save_and_continue()  # Tracking
            await self._click_save_and_continue()  # Budget
            
            # Delete inherited ads before uploading new ones
            await self._delete_all_ads()
            
            return campaign_id, campaign_name
            
        except Exception as e:
            raise CampaignCreationError(f"Failed to create Android campaign: {str(e)}")
    
    # =========================================================================
    # Internal helper methods
    # =========================================================================
    
    async def _clone_campaign(self, template_id: str) -> str:
        """Clone a campaign and return new campaign ID."""
        # Filter by campaign ID
        await self.page.fill('input[name="id"]', template_id)
        await self.page.keyboard.press("Enter")
        await asyncio.sleep(1)
        
        # Click clone button
        clone_selector = f'a.cloneCampaign[data-campaign-id="{template_id}"]'
        await self.page.click(clone_selector)
        
        # Wait for redirect to new campaign page
        await self.page.wait_for_url(f"{self.BASE_URL}/campaign/*")
        
        # Extract campaign ID from URL
        campaign_id = self.page.url.split("/campaign/")[1].split("?")[0]
        
        return campaign_id
    
    async def _configure_basic_settings(
        self,
        campaign_name: str,
        group_name: str,
        gender: str
    ):
        """Configure basic campaign settings (Step 1)."""
        # Update campaign name
        await self.page.fill('input[name="name"]', "")
        await self.page.fill('input[name="name"]', campaign_name)
        
        # Select or create group
        await self._select_or_create_group(group_name)
        
        # Set gender
        await self._set_gender(gender)
        
        # Save & Continue
        await self._click_save_and_continue()
    
    async def _update_campaign_name(self, campaign_name: str):
        """Update campaign name only (for Android cloning)."""
        await self.page.fill('input[name="name"]', "")
        await self.page.fill('input[name="name"]', campaign_name)
        await self._click_save_and_continue()
    
    async def _select_or_create_group(self, group_name: str):
        """Select existing group or create new one."""
        # Open group dropdown
        await self.page.click('span.select2-selection[aria-labelledby="select2-group_id-container"]')
        await asyncio.sleep(0.5)
        
        # Search for group
        await self.page.fill('input.select2-search__field', group_name)
        await asyncio.sleep(0.5)
        
        # Check if group exists
        no_results = await self.page.query_selector('li.select2-results__message')
        
        if no_results:
            # Create new group
            await self.page.click('a#showNewGroupFormButton')
            await self.page.fill('input#new_group_name', group_name)
            await self.page.click('button#confirmNewGroupButton')
            await asyncio.sleep(0.5)
        else:
            # Select existing group
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(0.5)
    
    async def _set_gender(self, gender: str):
        """Set gender targeting."""
        gender_map = {
            "male": "demographic_male",
            "female": "demographic_female",
            "all": "demographic_all"
        }
        
        gender_id = gender_map.get(gender.lower(), "demographic_male")
        await self.page.click(f'input#{gender_id}')
    
    async def _configure_geo(self, geo: str):
        """Configure geo targeting (Step 2)."""
        # Remove existing geo if needed
        remove_link = await self.page.query_selector('a.removeTargetedLocation')
        if remove_link:
            await remove_link.click()
            await asyncio.sleep(0.5)
        
        # Select country dropdown
        await self.page.click('span[id="select2-geo_country-container"]')
        await asyncio.sleep(0.5)
        
        # Type country name
        await self.page.fill('input.select2-search__field', geo)
        await asyncio.sleep(0.5)
        
        # Select from results
        await self.page.keyboard.press("Enter")
        await asyncio.sleep(0.5)
        
        # Click Add button
        await self.page.click('button#addLocation')
        await asyncio.sleep(0.5)
    
    async def _configure_os_targeting(self, operating_systems: List[str]):
        """Configure OS targeting."""
        # Remove all existing OS first
        while True:
            remove_btn = await self.page.query_selector('a.removeOsTarget')
            if not remove_btn:
                break
            await remove_btn.click()
            await asyncio.sleep(0.3)
        
        # Add each OS
        for os_name in operating_systems:
            await self.page.click('span[id="select2-operating_systems_list_include-container"]')
            await asyncio.sleep(0.3)
            
            await self.page.fill('input.select2-search__field', os_name)
            await asyncio.sleep(0.3)
            
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(0.3)
            
            await self.page.click('button.addOsTarget[data-selection="include"]')
            await asyncio.sleep(0.3)
    
    async def _configure_keywords(self, keywords: List[Keyword]):
        """Configure keyword targeting."""
        # Remove all existing keywords
        await self.page.click('a.removeAllKeywords[data-selection-type="include"]')
        await asyncio.sleep(0.5)
        
        # Add each keyword
        for keyword in keywords:
            await self.page.click('span[id="select2-keyword_select-container"]')
            await asyncio.sleep(0.3)
            
            await self.page.fill('input.select2-search__field', keyword.name)
            await asyncio.sleep(0.5)
            
            # Click the keyword from results
            await self.page.click(f'div.keywordItem[title="{keyword.name}"]')
            await asyncio.sleep(0.3)
        
        # Close keyword selector
        await self.page.click('body')
        await asyncio.sleep(0.5)
        
        # Set match types
        for keyword in keywords:
            if keyword.match_type == MatchType.BROAD:
                # Click broad radio button
                await self.page.click(f'input#broad_{keyword.name}')
                await asyncio.sleep(0.2)
        
        # Save & Continue
        await self._click_save_and_continue()
    
    async def _configure_tracking_and_bids(self, campaign: CampaignDefinition):
        """Configure tracking and bids (Step 3)."""
        settings = campaign.settings
        
        # Target CPA
        await self.page.fill('input#target_cpa', "")
        await self.page.fill('input#target_cpa', str(settings.target_cpa))
        
        # Per Source Test Budget
        await self.page.fill('input#per_source_test_budget', "")
        await self.page.fill('input#per_source_test_budget', str(settings.per_source_test_budget))
        
        # Max Bid
        await self.page.fill('input#maximum_bid', "")
        await self.page.fill('input#maximum_bid', str(settings.max_bid))
        
        # Include all sources
        await self.page.check('input.checkUncheckAll[data-table="sourceSelectionTable"]')
        await asyncio.sleep(0.3)
        await self.page.click('button.includeBtn[data-btn-action="include"]')
        await asyncio.sleep(0.5)
        
        # Save & Continue
        await self._click_save_and_continue()
    
    async def _configure_schedule_and_budget(self, campaign: CampaignDefinition):
        """Configure schedule and budget (Step 4)."""
        settings = campaign.settings
        
        # Frequency cap
        await self.page.fill('input#frequency_cap_times', "")
        await self.page.fill('input#frequency_cap_times', str(settings.frequency_cap))
        
        # Max Daily Budget
        await self.page.fill('input#daily_budget', "")
        await self.page.fill('input#daily_budget', str(settings.max_daily_budget))
        
        # Save & Continue to ads page
        await self._click_save_and_continue()
    
    async def _delete_all_ads(self):
        """Delete all existing ads (for Android after cloning iOS)."""
        # Check for "Created Ad(s)" section
        created_ads_section = await self.page.query_selector('h5:text("Created Ad(s)")')
        if not created_ads_section:
            return  # No ads to delete
        
        # Click "Remove All" link
        remove_all = await self.page.query_selector('a.removeAll')
        if remove_all:
            await remove_all.click()
            await asyncio.sleep(0.5)
            
            # Confirm removal if dialog appears
            try:
                await self.page.click('button:text("Yes")', timeout=2000)
                await asyncio.sleep(0.5)
            except:
                pass
    
    async def _click_save_and_continue(self):
        """Click Save & Continue button."""
        # Try multiple possible selectors
        selectors = [
            'button.saveAndContinue',
            'button.confirmAudience.saveAndContinue',
            'button.confirmtrackingAdSpotsRules.saveAndContinue',
            'button#addCampaign'
        ]
        
        for selector in selectors:
            button = await self.page.query_selector(selector)
            if button:
                await button.click()
                await asyncio.sleep(1)
                return
        
        raise CampaignCreationError("Could not find Save & Continue button")


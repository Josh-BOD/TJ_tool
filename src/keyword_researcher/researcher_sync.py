"""
Synchronous keyword research with Playwright browser automation.

Searches keywords in TrafficJunky's keyword selector dropdown and captures
all suggested keywords.
"""

import logging
import time
from pathlib import Path
from typing import List, Optional, Set
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .models import ResearchResult

logger = logging.getLogger(__name__)


class KeywordResearcher:
    """Discovers related keywords via TrafficJunky's keyword search dropdown."""
    
    BASE_URL = "https://advertiser.trafficjunky.com"
    
    # Default campaign ID to use for accessing keyword dropdown
    # Can be overridden in __init__
    DEFAULT_CAMPAIGN_ID = "1013085241"
    
    def __init__(
        self,
        page: Page,
        campaign_id: Optional[str] = None,
        delay_between_searches: float = 2.0,
        take_screenshots: bool = False,
        screenshot_dir: Optional[Path] = None
    ):
        """
        Initialize keyword researcher.
        
        Args:
            page: Playwright page object (already logged in)
            campaign_id: Campaign ID to use for keyword research (any existing campaign)
            delay_between_searches: Seconds to wait between keyword searches
            take_screenshots: If True, take screenshots of key steps
            screenshot_dir: Directory to save screenshots
        """
        self.page = page
        self.campaign_id = campaign_id or self.DEFAULT_CAMPAIGN_ID
        self.delay_between_searches = delay_between_searches
        self.take_screenshots = take_screenshots
        self.screenshot_dir = screenshot_dir or Path('./data/screenshots')
        self.retry_attempts = 3
        self.retry_delay_base = 1.0
        
        if self.take_screenshots:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    def navigate_to_keyword_selector(self) -> bool:
        """
        Navigate to an existing campaign's audience page to access keyword selector.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Navigating to campaign {self.campaign_id} audience page...")
            
            # Navigate directly to the campaign's audience section
            url = f"{self.BASE_URL}/campaign/{self.campaign_id}/audience#section_advancedTargeting"
            self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            self.page.wait_for_timeout(2000)
            
            # Dismiss any popups
            self._dismiss_popups()
            
            # Wait for keyword selector to be available
            logger.info("Waiting for keyword selector...")
            self.page.wait_for_selector('span[id="select2-keyword_select-container"]', timeout=15000)
            
            logger.info("✓ Successfully navigated to keyword selector")
            
            if self.take_screenshots:
                self._take_screenshot("keyword_selector_ready")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to keyword selector: {e}")
            return False
    
    def research_keyword(self, seed_keyword: str, existing_keywords: Set[str] = None) -> ResearchResult:
        """
        Search for a keyword and capture all suggested keywords.
        
        Args:
            seed_keyword: The keyword to search for
            existing_keywords: Set of existing keywords to exclude (lowercase)
            
        Returns:
            ResearchResult with discovered keywords
        """
        existing_keywords = existing_keywords or set()
        start_time = time.time()
        
        result = ResearchResult(seed_keyword=seed_keyword)
        
        try:
            logger.info(f"Researching keyword: '{seed_keyword}'")
            
            # Click to open keyword selector dropdown
            keyword_container = self.page.locator('span[id="select2-keyword_select-container"]').first
            
            if not keyword_container.is_visible(timeout=5000):
                result.status = 'failed'
                result.error = "Keyword selector not visible"
                result.time_taken = time.time() - start_time
                return result
            
            keyword_container.click()
            self.page.wait_for_timeout(500)
            
            # Type the seed keyword in search field
            search_input = self.page.locator(
                'input.select2-search__field[aria-controls="select2-keyword_select-results"]'
            ).first
            
            if not search_input.is_visible(timeout=3000):
                # Try alternative selector
                search_input = self.page.locator('input.select2-search__field').first
            
            # Clear and type
            search_input.fill("")
            self.page.wait_for_timeout(200)
            search_input.fill(seed_keyword)
            
            # Wait for results to load
            logger.info("Waiting for keyword suggestions...")
            self.page.wait_for_timeout(1500)  # Give time for AJAX to complete
            
            # Try to wait for results to appear
            try:
                self.page.wait_for_selector('div.keywordItem', timeout=5000)
            except:
                logger.warning(f"No keyword suggestions found for '{seed_keyword}'")
            
            # Capture all keyword items
            keyword_items = self.page.locator('div.keywordItem').all()
            
            logger.info(f"Found {len(keyword_items)} keyword suggestions")
            
            discovered = []
            for item in keyword_items:
                try:
                    # Get keyword name from title attribute
                    keyword_name = item.get_attribute('title')
                    
                    if not keyword_name:
                        # Try to get text content
                        keyword_name = item.text_content()
                    
                    if keyword_name:
                        keyword_name = keyword_name.strip()
                        
                        # Skip if it's the same as seed or already exists
                        if keyword_name.lower() == seed_keyword.lower():
                            continue
                        if keyword_name.lower() in existing_keywords:
                            continue
                        
                        discovered.append(keyword_name)
                        
                except Exception as e:
                    logger.debug(f"Error extracting keyword: {e}")
                    continue
            
            # Close the dropdown
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(300)
            
            # Also click body to ensure dropdown is closed
            self.page.click('body')
            self.page.wait_for_timeout(300)
            
            result.discovered_keywords = discovered
            result.status = 'success'
            
            logger.info(f"✓ Discovered {len(discovered)} new keywords for '{seed_keyword}'")
            
            if self.take_screenshots:
                self._take_screenshot(f"keyword_{seed_keyword[:20]}")
            
        except Exception as e:
            logger.error(f"Error researching keyword '{seed_keyword}': {e}")
            result.status = 'failed'
            result.error = str(e)
        
        result.time_taken = time.time() - start_time
        
        # Wait before next search
        time.sleep(self.delay_between_searches)
        
        return result
    
    def research_keywords_batch(
        self,
        seed_keywords: List[str],
        existing_keywords: Set[str] = None
    ) -> List[ResearchResult]:
        """
        Research multiple keywords in batch.
        
        Args:
            seed_keywords: List of seed keywords to research
            existing_keywords: Set of existing keywords to exclude
            
        Returns:
            List of ResearchResult objects
        """
        existing_keywords = existing_keywords or set()
        results = []
        
        # Add seed keywords to existing set
        all_existing = existing_keywords | {k.lower() for k in seed_keywords}
        
        for i, seed in enumerate(seed_keywords, 1):
            logger.info(f"\n[{i}/{len(seed_keywords)}] Researching: {seed}")
            
            result = self.research_keyword(seed, all_existing)
            results.append(result)
            
            # Add discovered keywords to existing set to avoid duplicates
            for keyword in result.discovered_keywords:
                all_existing.add(keyword.lower())
            
            # Print progress
            if result.status == 'success':
                logger.info(f"  ✓ Found {len(result.discovered_keywords)} keywords ({result.time_taken:.1f}s)")
            else:
                logger.warning(f"  ✗ Failed: {result.error}")
        
        return results
    
    def _click_save_and_continue(self) -> bool:
        """Click Save & Continue button."""
        try:
            # Try different button variations
            selectors = [
                'button:has-text("Save & Continue")',
                'button:has-text("Save and Continue")',
                'button.saveAndContinue',
                'button[type="submit"]:has-text("Continue")',
                'a:has-text("Save & Continue")',
            ]
            
            for selector in selectors:
                try:
                    btn = self.page.locator(selector).first
                    if btn.is_visible(timeout=2000):
                        btn.click()
                        self.page.wait_for_timeout(2000)
                        return True
                except:
                    continue
            
            logger.warning("Could not find Save & Continue button")
            return False
            
        except Exception as e:
            logger.error(f"Error clicking Save & Continue: {e}")
            return False
    
    def _dismiss_popups(self):
        """Dismiss any popups that might appear."""
        try:
            # Pendo popup
            close_btn = self.page.locator('button.pendo-close-guide, div._pendo-close-guide_').first
            if close_btn.is_visible(timeout=1000):
                close_btn.click()
                self.page.wait_for_timeout(300)
        except:
            pass
        
        try:
            # Generic close buttons
            close_btn = self.page.locator('button[aria-label="Close"], button.close').first
            if close_btn.is_visible(timeout=500):
                close_btn.click()
                self.page.wait_for_timeout(300)
        except:
            pass
    
    def _take_screenshot(self, name: str):
        """Take a screenshot with timestamp."""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{name}.png"
            filepath = self.screenshot_dir / filename
            
            self.page.screenshot(path=str(filepath))
            logger.info(f"Screenshot saved: {filename}")
        except Exception as e:
            logger.warning(f"Failed to take screenshot: {e}")


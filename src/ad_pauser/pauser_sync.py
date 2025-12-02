"""Synchronous ad pausing with Playwright browser automation."""

import logging
import time
from pathlib import Path
from typing import Set, List, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .models import PauseResult

logger = logging.getLogger(__name__)


class AdPauser:
    """Handles pausing of ads in TrafficJunky campaigns using browser automation."""
    
    def __init__(
        self, 
        page: Page, 
        dry_run: bool = False, 
        take_screenshots: bool = False,
        screenshot_dir: Optional[Path] = None
    ):
        """
        Initialize ad pauser.
        
        Args:
            page: Playwright page object
            dry_run: If True, don't actually pause ads (preview only)
            take_screenshots: If True, take screenshots of key steps
            screenshot_dir: Directory to save screenshots (default: ./data/screenshots)
        """
        self.page = page
        self.dry_run = dry_run
        self.take_screenshots = take_screenshots
        self.screenshot_dir = screenshot_dir or Path('./data/screenshots')
        self.retry_attempts = 3
        self.retry_delay_base = 1.0  # Base delay in seconds for exponential backoff
        
        if self.take_screenshots:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Screenshots will be saved to: {self.screenshot_dir}")
    
    def pause_ads_in_campaign(
        self, 
        campaign_id: str, 
        creative_ids: Set[str],
        campaign_name: str = ""
    ) -> PauseResult:
        """
        Navigate to campaign ad page and pause specified creative IDs.
        
        Handles pagination, retries, and error tracking.
        
        Args:
            campaign_id: Campaign ID to process
            creative_ids: Set of Creative IDs to pause
            campaign_name: Optional campaign name for logging
            
        Returns:
            PauseResult with statistics and status
        """
        start_time = time.time()
        
        result = PauseResult(
            campaign_id=campaign_id,
            campaign_name=campaign_name or campaign_id
        )
        
        try:
            logger.info(f"Processing campaign {campaign_id}")
            
            # Navigate to campaign ads page
            url = f"https://advertiser.trafficjunky.com/campaign/{campaign_id}/overview/ads"
            logger.info(f"Navigating to: {url}")
            
            if not self._navigate_with_retry(url):
                result.status = 'failed'
                result.errors.append("Failed to navigate to campaign ads page")
                result.time_taken = time.time() - start_time
                return result
            
            # FASTER METHOD: Use filters to narrow down results
            # 1. Set Ad Status to "Active" only
            logger.info("Setting Ad Status filter to 'Active' only...")
            if not self._set_ad_status_filter_to_active():
                logger.warning("Could not set Ad Status filter, continuing anyway...")
            
            # 2. Use Banner Name/ID search to filter to specific Creative IDs
            logger.info(f"Filtering to {len(creative_ids)} Creative ID(s) using Banner search...")
            if not self._filter_by_banner_ids(creative_ids):
                logger.warning("Could not set Banner ID filter, continuing with manual search...")
            else:
                logger.info("✓ Filters applied - table now shows only active ads with target Creative IDs")
            
            # Set pagination to 100
            if not self._set_pagination_to_100():
                logger.warning("Could not set pagination to 100, continuing with default")
                # Not a fatal error, continue anyway
            
            # Get total pages (should be much fewer now due to filters!)
            total_pages = self._get_total_pages()
            logger.info(f"Found {total_pages} page(s) to process (after filtering)")
            
            # Track found and paused ads
            found_ids = []
            paused_ids = []
            
            # Strategy: Go through ALL pages, pause active ads, then repeat until no more active ads found
            max_rounds = 10  # Safety limit - maximum rounds through all pages
            round_num = 0
            
            while round_num < max_rounds:
                round_num += 1
                logger.info(f"Starting round {round_num} - checking all pages")
                
                paused_this_round = 0
                
                # Process each page in this round
                for page_num in range(1, total_pages + 1):
                    logger.info(f"Processing page {page_num}/{total_pages} (round {round_num})")
                    
                    found_before = len(paused_ids)
                    
                    if not self._process_page(page_num, creative_ids, found_ids, paused_ids):
                        result.errors.append(f"Failed to process page {page_num} in round {round_num}")
                        continue
                    
                    result.pages_processed += 1
                    
                    # Count how many paused on this page
                    paused_on_page = len(paused_ids) - found_before
                    if paused_on_page > 0:
                        paused_this_round += paused_on_page
                        logger.info(f"✓ Paused {paused_on_page} ad(s) on page {page_num}")
                        
                        # After pausing, recalculate total pages (might have changed)
                        if not self.dry_run:
                            self.page.wait_for_timeout(2000)
                            total_pages = self._get_total_pages()
                            logger.info(f"Pages after pause: {total_pages}")
                            
                            # If we paused ads, the pagination may have changed
                            # Break out of page loop and start a new round
                            break
                    
                    # Navigate to next page if not the last page
                    if page_num < total_pages:
                        if not self._go_to_next_page(page_num + 1):
                            logger.warning(f"Could not navigate to page {page_num + 1}, ending this round")
                            break
                
                # If we didn't pause anything this round, we're done
                if paused_this_round == 0:
                    logger.info(f"No more active matching ads found after round {round_num}")
                    break
                else:
                    logger.info(f"Round {round_num} complete: paused {paused_this_round} ad(s). Starting next round...")
                    # Navigate back to page 1 for next round
                    if round_num < max_rounds and not self.dry_run:
                        logger.info("Navigating back to page 1...")
                        # Click First button: <a href="#" class="page-link first" aria-label="First">First</a>
                        try:
                            first_button = self.page.locator('a.page-link.first').first
                            if first_button.is_visible(timeout=3000):
                                first_button.click()
                                self.page.wait_for_timeout(2000)
                                logger.info("✓ Clicked First button, back to page 1")
                            else:
                                # Fallback: reload the page
                                url = f"https://advertiser.trafficjunky.com/campaign/{campaign_id}/overview/ads"
                                self._navigate_with_retry(url)
                                self._set_pagination_to_100()
                        except Exception as e:
                            logger.warning(f"Could not click First button: {e}, reloading page...")
                            url = f"https://advertiser.trafficjunky.com/campaign/{campaign_id}/overview/ads"
                            self._navigate_with_retry(url)
                            self._set_pagination_to_100()
                        self.page.wait_for_timeout(1000)
            
            # Calculate what wasn't found
            result.ads_found = found_ids
            result.ads_paused = paused_ids
            result.ads_not_found = [cid for cid in creative_ids if cid not in found_ids]
            
            # Determine status
            if len(paused_ids) == len(creative_ids):
                result.status = 'success'
            elif len(paused_ids) > 0:
                result.status = 'partial'
            else:
                result.status = 'failed'
                if not result.errors:
                    result.errors.append("No ads were paused")
            
        except Exception as e:
            logger.error(f"Unexpected error processing campaign {campaign_id}: {e}")
            logger.exception("Exception details:")
            result.status = 'failed'
            result.errors.append(f"Unexpected error: {str(e)}")
        
        result.time_taken = time.time() - start_time
        return result
    
    def _navigate_with_retry(self, url: str) -> bool:
        """Navigate to URL with retry logic."""
        for attempt in range(self.retry_attempts):
            try:
                self.page.goto(url, wait_until='networkidle', timeout=30000)
                self.page.wait_for_timeout(1000)  # Extra settling time
                return True
            except Exception as e:
                delay = self.retry_delay_base * (2 ** attempt)
                logger.warning(f"Navigation attempt {attempt + 1}/{self.retry_attempts} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"Navigation failed after {self.retry_attempts} attempts")
        return False
    
    def _set_pagination_to_100(self) -> bool:
        """
        Set pagination dropdown to show 100 items per page.
        
        Returns:
            True if successful, False otherwise
        """
        for attempt in range(self.retry_attempts):
            try:
                logger.info("Setting pagination to 100...")
                
                # Click the pagination dropdown
                # Selector: span#select2-dt-length-0-container
                dropdown = self.page.locator('span#select2-dt-length-0-container').first
                
                if not dropdown.is_visible(timeout=5000):
                    logger.warning("Pagination dropdown not found")
                    return False
                
                dropdown.click()
                self.page.wait_for_timeout(500)
                
                # Click the "100" option
                option_100 = self.page.locator('li.select2-results__option:has-text("100")').first
                
                if not option_100.is_visible(timeout=3000):
                    logger.warning("Option '100' not found in dropdown")
                    return False
                
                option_100.click()
                self.page.wait_for_timeout(2000)  # Wait for table to reload
                
                logger.info("✓ Pagination set to 100")
                
                if self.take_screenshots:
                    self._take_screenshot("pagination_set")
                
                return True
                
            except Exception as e:
                delay = self.retry_delay_base * (2 ** attempt)
                logger.warning(f"Pagination attempt {attempt + 1}/{self.retry_attempts} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to set pagination after {self.retry_attempts} attempts")
        
        return False
    
    def _get_total_pages(self) -> int:
        """
        Detect total number of pages by checking pagination controls.
        
        Returns:
            Number of pages (1 if no pagination)
        """
        try:
            # Wait a moment for pagination to load
            self.page.wait_for_timeout(1000)
            
            # Look for the pagination info text: "Showing X to Y of Z entries"
            # This tells us the total number of ads
            try:
                info_text = self.page.locator('#adsTable_info').first.text_content()
                logger.info(f"Pagination info: {info_text}")
                
                # Parse: "Showing 1 to 100 of 118 entries" -> 118 total, 100 per page = 2 pages
                if 'of' in info_text and 'entries' in info_text:
                    import re
                    match = re.search(r'of\s+(\d+)\s+entries', info_text)
                    if match:
                        total_entries = int(match.group(1))
                        # Assuming 100 per page (what we set)
                        total_pages = (total_entries + 99) // 100  # Ceiling division
                        logger.info(f"Calculated {total_pages} page(s) from {total_entries} total entries")
                        return max(1, total_pages)
            except Exception as e:
                logger.debug(f"Could not parse pagination info text: {e}")
            
            # Fallback: Look for pagination buttons
            pagination_buttons = self.page.locator('.paginate_button').count()
            
            if pagination_buttons <= 2:  # Only "Previous" and "Next" buttons
                return 1
            
            # Count numbered page buttons (exclude Previous/Next)
            page_numbers = self.page.locator('.paginate_button:not(.previous):not(.next)').all_text_contents()
            
            if not page_numbers:
                return 1
            
            # Filter out empty strings and convert to int
            page_nums = [int(p.strip()) for p in page_numbers if p.strip().isdigit()]
            
            if page_nums:
                max_page = max(page_nums)
                logger.info(f"Detected {max_page} page(s) from pagination buttons")
                return max_page
            
            return 1
            
        except Exception as e:
            logger.warning(f"Could not detect pagination: {e}")
            return 1
    
    def _process_page(
        self, 
        page_num: int, 
        creative_ids_to_find: Set[str],
        found_ids: List[str],
        paused_ids: List[str]
    ) -> bool:
        """
        Process current page: find, select, and pause matching creative IDs.
        
        Args:
            page_num: Current page number (for logging)
            creative_ids_to_find: Set of creative IDs to look for
            found_ids: List to append found creative IDs to
            paused_ids: List to append paused creative IDs to
            
        Returns:
            True if successful, False on error
        """
        for attempt in range(self.retry_attempts):
            try:
                logger.info(f"Scanning page {page_num} for creative IDs...")
                
                # Wait for table to be visible
                self.page.wait_for_selector('table#adsTable tbody', state='visible', timeout=10000)
                self.page.wait_for_timeout(1000)  # Extra settling
                
                # Find all table rows in the ads table
                rows = self.page.locator('table#adsTable tbody tr').all()
                
                logger.info(f"Found {len(rows)} rows on page")
                
                # Track which checkboxes to select
                checkboxes_to_select = []
                found_on_this_page = []
                
                for row in rows:
                    try:
                        # Look for the Creative ID in the dtc_bannerId cell
                        banner_id_cell = row.locator('td.dtc_bannerId').first
                        
                        if not banner_id_cell.is_visible():
                            continue
                        
                        # Get the Creative ID from the cell text
                        creative_id = banner_id_cell.text_content().strip()
                        
                        if not creative_id:
                            continue
                        
                        # Check if this creative ID is in our list
                        if creative_id in creative_ids_to_find:
                            # If filters worked, all ads shown should be active already
                            # But we'll still check status as a safety measure
                            status_div = row.locator('div.campaignAdBidStatus').first
                            
                            try:
                                status_text = status_div.text_content().strip().lower()
                            except Exception as e:
                                logger.debug(f"  Could not get status for Creative ID {creative_id}: {e}")
                                status_text = "active"  # Assume active if filter worked
                            
                            # Only select if status is "active"
                            if status_text != "active":
                                logger.info(f"  Skipping Creative ID {creative_id} - status: '{status_text}' (not active)")
                                continue
                            
                            logger.info(f"  ✓ Found Creative ID: {creative_id} (active)")
                            
                            # Find the checkbox in this row
                            checkbox = row.locator('input.tableCheckbox[type="checkbox"]').first
                            
                            if checkbox.is_visible():
                                checkboxes_to_select.append(checkbox)
                                found_on_this_page.append(creative_id)
                                
                                # Add to found list if not already there
                                if creative_id not in found_ids:
                                    found_ids.append(creative_id)
                            else:
                                logger.warning(f"  Checkbox not found for Creative ID: {creative_id}")
                    
                    except Exception as e:
                        logger.warning(f"Error checking row: {e}")
                        continue
                
                # If we found any, select them and pause
                if checkboxes_to_select:
                    logger.info(f"Selecting {len(checkboxes_to_select)} checkbox(es)...")
                    
                    # Check all the boxes
                    for checkbox in checkboxes_to_select:
                        try:
                            checkbox.check()
                            self.page.wait_for_timeout(200)  # Small delay between checks
                        except Exception as e:
                            logger.warning(f"Failed to check checkbox: {e}")
                    
                    if self.take_screenshots:
                        self._take_screenshot(f"page_{page_num}_selected")
                    
                    # Click the pause button
                    if self._click_pause_button(len(checkboxes_to_select)):
                        # Add to paused list
                        paused_ids.extend(found_on_this_page)
                        logger.info(f"✓ Paused {len(found_on_this_page)} ad(s) on page {page_num}")
                    else:
                        logger.error(f"Failed to pause ads on page {page_num}")
                        return False
                else:
                    logger.info(f"No matching creative IDs found on page {page_num}")
                
                return True
                
            except Exception as e:
                delay = self.retry_delay_base * (2 ** attempt)
                logger.warning(f"Page processing attempt {attempt + 1}/{self.retry_attempts} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to process page after {self.retry_attempts} attempts")
        
        return False
    
    def _click_pause_button(self, selected_count: int) -> bool:
        """
        Click the pause button to pause selected ads.
        
        Args:
            selected_count: Number of ads selected (for logging)
            
        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would pause {selected_count} ad(s)")
            return True
        
        for attempt in range(self.retry_attempts):
            try:
                logger.info(f"Clicking pause button for {selected_count} ad(s)...")
                
                # Find the BULK pause button: <i class="fal fa-pause"></i>
                # NOT the individual action button: <i class="actionBtn fal fa-pause">
                # The button is the parent of the icon
                pause_button = self.page.locator('i.fa-pause:not(.actionBtn)').locator('..').first
                
                if not pause_button.is_visible(timeout=3000):
                    logger.error("Pause button not found or not visible")
                    return False
                
                # Click the pause button
                pause_button.click()
                logger.info("Pause button clicked, waiting for confirmation modal...")
                self.page.wait_for_timeout(1000)
                
                # CRITICAL: Click "Yes" in the confirmation modal
                # Modal HTML: <a href="javascript:;" data-function="adsFunctions.playPauseAds" class="smallButton greenButton pauseCampaigns">Yes</a>
                try:
                    # Wait for the modal to appear
                    yes_button = self.page.locator('a.pauseCampaigns:has-text("Yes")').first
                    if yes_button.is_visible(timeout=5000):
                        logger.info("Clicking 'Yes' in confirmation modal...")
                        yes_button.click()
                        logger.info("✓ Confirmed pause action")
                        self.page.wait_for_timeout(1000)
                    else:
                        logger.warning("Confirmation modal 'Yes' button not found")
                        return False
                except Exception as e:
                    logger.error(f"Failed to click 'Yes' in confirmation modal: {e}")
                    return False
                
                # CRITICAL: Wait for the page to reload/refresh after pausing
                # The page usually reloads to show the updated status
                logger.info("Waiting for page to reload after pause...")
                try:
                    # Wait for the table to reload (up to 10 seconds)
                    self.page.wait_for_load_state('networkidle', timeout=10000)
                except:
                    logger.warning("Network didn't go idle, waiting 5 seconds...")
                    self.page.wait_for_timeout(5000)
                
                # Additional wait to ensure pause is processed
                self.page.wait_for_timeout(3000)
                
                if self.take_screenshots:
                    self._take_screenshot("after_pause")
                
                logger.info("✓ Pause button clicked and page reloaded successfully")
                return True
                
            except Exception as e:
                delay = self.retry_delay_base * (2 ** attempt)
                logger.warning(f"Pause click attempt {attempt + 1}/{self.retry_attempts} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to click pause button after {self.retry_attempts} attempts")
        
        return False
    
    def _go_to_next_page(self, page_num: int) -> bool:
        """
        Navigate to the next page in pagination.
        
        Args:
            page_num: Target page number
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Navigating to page {page_num}...")
            
            # First, try to dismiss any popups/overlays that might be blocking
            try:
                # Close Pendo badge if it's in the way
                pendo_close = self.page.locator('button[aria-label*="Close"]').first
                if pendo_close.is_visible(timeout=1000):
                    pendo_close.click()
                    self.page.wait_for_timeout(500)
            except:
                pass
            
            # Check if Next button exists and is NOT disabled
            next_button = self.page.locator('a.page-link.next').first
            
            # Check if the parent li has class "disabled"
            try:
                parent_li = next_button.locator('..').first
                parent_class = parent_li.get_attribute('class')
                if parent_class and 'disabled' in parent_class:
                    logger.info(f"Next button is disabled - we're on the last page")
                    return False
            except:
                pass
            
            if next_button.is_visible(timeout=3000):
                try:
                    # Try normal click first
                    next_button.click(timeout=5000)
                    self.page.wait_for_timeout(2000)  # Wait for table to reload
                    logger.info(f"✓ Clicked Next button, now on page {page_num}")
                    return True
                except Exception as e:
                    logger.warning(f"Normal click failed: {e}, trying force click...")
                    # Try force click as fallback (ignores overlays)
                    try:
                        next_button.click(force=True, timeout=5000)
                        self.page.wait_for_timeout(2000)
                        logger.info(f"✓ Force clicked Next button, now on page {page_num}")
                        return True
                    except Exception as e2:
                        logger.error(f"Force click also failed: {e2}")
                        return False
            else:
                logger.warning(f"Next button not visible for page {page_num}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to navigate to page {page_num}: {e}")
            return False
    
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
    
    def _set_ad_status_filter_to_active(self) -> bool:
        """
        Set the Ad Status filter to 'Active' only.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Click the Ad Status dropdown
            status_dropdown = self.page.locator('#select2-adStatus-container').first
            status_dropdown.click()
            self.page.wait_for_timeout(500)
            
            # Find and click "Active" option
            active_option = self.page.locator('li.select2-results__option:has-text("Active")').first
            active_option.click()
            self.page.wait_for_timeout(500)
            
            logger.info("✓ Ad Status set to 'Active'")
            return True
        except Exception as e:
            logger.error(f"Failed to set Ad Status filter: {e}")
            return False
    
    def _filter_by_banner_ids(self, creative_ids: Set[str]) -> bool:
        """
        Use the Banner Name/ID search to filter to specific Creative IDs.
        
        Args:
            creative_ids: Set of Creative IDs to filter to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Click the Banner search input to activate it
            banner_search = self.page.locator('input.select2-search__field[placeholder="All Banners"]').first
            banner_search.click()
            self.page.wait_for_timeout(500)
            
            # Enter each Creative ID
            for creative_id in creative_ids:
                logger.info(f"  Adding Creative ID {creative_id} to filter...")
                
                # Type the Creative ID
                banner_search.type(creative_id, delay=50)
                self.page.wait_for_timeout(800)  # Wait for dropdown to populate
                
                # Click the matching option from dropdown
                # The option shows as "NAME - [CREATIVE_ID]"
                try:
                    option = self.page.locator(f'li.select2-results__option:has-text("[{creative_id}]")').first
                    if option.is_visible(timeout=2000):
                        option.click()
                        self.page.wait_for_timeout(300)
                        logger.info(f"    ✓ Selected Creative ID {creative_id}")
                    else:
                        logger.warning(f"    Could not find option for Creative ID {creative_id}")
                except Exception as e:
                    logger.warning(f"    Error selecting Creative ID {creative_id}: {e}")
                    continue
                
                # Click back into search field for next ID
                banner_search.click()
                self.page.wait_for_timeout(200)
            
            # Click "Apply Filters" button
            logger.info("Clicking 'Apply Filters' button...")
            apply_button = self.page.locator('button:has-text("Apply Filters")').first
            if apply_button.is_visible(timeout=3000):
                apply_button.click()
                self.page.wait_for_timeout(2000)  # Wait for table to reload
                logger.info("✓ Filters applied")
                return True
            else:
                logger.warning("Apply Filters button not found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to set Banner ID filters: {e}")
            return False


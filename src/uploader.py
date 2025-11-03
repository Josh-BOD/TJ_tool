"""Main CSV upload automation module."""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class TJUploader:
    """Handles CSV upload to TrafficJunky campaigns."""
    
    def __init__(self, dry_run: bool = True, take_screenshots: bool = True):
        """
        Initialize uploader.
        
        Args:
            dry_run: If True, simulate but don't actually upload
            take_screenshots: If True, take screenshots at each step
        """
        self.dry_run = dry_run
        self.take_screenshots = take_screenshots
        self.screenshot_counter = 0
    
    def upload_to_campaign(
        self, 
        page: Page, 
        campaign_id: str, 
        csv_path: Path,
        screenshot_dir: Optional[Path] = None
    ) -> Dict:
        """
        Upload CSV to a specific campaign.
        
        Args:
            page: Playwright page object
            campaign_id: TrafficJunky campaign ID
            csv_path: Path to CSV file
            screenshot_dir: Directory to save screenshots
            
        Returns:
            Dictionary with upload results
        """
        result = {
            'campaign_id': campaign_id,
            'status': 'failed',
            'ads_created': 0,
            'error': None,
            'invalid_creatives': []
        }
        
        try:
            logger.info(f"Processing campaign {campaign_id}...")
            
            # Step 1: Navigate to campaign ad settings
            if not self._navigate_to_campaign(page, campaign_id):
                result['error'] = "Failed to navigate to campaign"
                return result
            
            self._take_screenshot(page, f"01_campaign_{campaign_id}_loaded", screenshot_dir)
            
            # Step 2: Count existing ads
            existing_ads = self._count_existing_ads(page)
            logger.info(f"Campaign has {existing_ads} existing ads")
            
            # Step 3: Select "Mass create with CSV"
            if not self._select_mass_csv(page):
                result['error'] = "Failed to select Mass CSV upload"
                return result
            
            self._take_screenshot(page, f"02_mass_csv_selected", screenshot_dir)
            
            # Step 4: Upload CSV
            if self.dry_run:
                logger.info(f"DRY RUN: Would upload {csv_path}")
                result['status'] = 'dry_run_success'
                return result
            
            if not self._upload_csv_file(page, csv_path):
                result['error'] = "Failed to upload CSV file"
                return result
            
            self._take_screenshot(page, f"03_csv_uploaded", screenshot_dir)
            
            # Step 5: Wait and check for preview/errors
            time.sleep(2)  # Give it time to process
            
            # Step 6: Handle validation errors
            if self._has_validation_errors(page):
                logger.warning("Validation errors detected")
                invalid_ids = self._extract_invalid_creatives(page)
                result['invalid_creatives'] = invalid_ids
                result['error'] = f"Validation errors: {len(invalid_ids)} invalid creative IDs"
                self._take_screenshot(page, f"04_validation_errors", screenshot_dir)
                # Note: CSV cleaning and retry will be handled by campaign_manager
                return result
            
            # Step 7: Click create preview (if button exists)
            self._click_create_preview(page)
            time.sleep(2)
            
            self._take_screenshot(page, f"05_preview_created", screenshot_dir)
            
            # Step 8: Click create ads
            if not self._click_create_ads(page):
                result['error'] = "Failed to click create ads button"
                return result
            
            # Step 9: Wait for processing
            time.sleep(3)
            
            self._take_screenshot(page, f"06_ads_created", screenshot_dir)
            
            # Step 10: Verify success
            new_ad_count = self._count_existing_ads(page)
            ads_created = new_ad_count - existing_ads
            
            if ads_created > 0:
                logger.info(f"✓ Successfully created {ads_created} ads")
                result['status'] = 'success'
                result['ads_created'] = ads_created
            else:
                logger.warning("No new ads detected")
                result['error'] = "No new ads created"
            
            return result
            
        except Exception as e:
            logger.error(f"✗ Upload failed for campaign {campaign_id}: {e}")
            result['error'] = str(e)
            self._take_screenshot(page, f"ERROR_campaign_{campaign_id}", screenshot_dir)
            return result
    
    def _navigate_to_campaign(self, page: Page, campaign_id: str) -> bool:
        """Navigate to campaign ad settings page."""
        try:
            url = f"https://advertiser.trafficjunky.com/campaign/{campaign_id}/ad-settings#section_adSpecs"
            logger.info(f"Navigating to {url}")
            
            page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Wait for page to load
            page.wait_for_selector('text=STEP 5. CREATE YOUR AD', state='visible', timeout=10000)
            
            return True
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    def _count_existing_ads(self, page: Page) -> int:
        """Count existing ads in the campaign."""
        try:
            # Look for the ads table
            table = page.locator('table').first
            if table.is_visible():
                rows = table.locator('tbody tr').count()
                # Subtract header row if counted
                return max(0, rows)
            return 0
        except:
            return 0
    
    def _select_mass_csv(self, page: Page) -> bool:
        """Select 'Mass create with CSV' radio button."""
        try:
            logger.info("Selecting 'Mass create with CSV'...")
            
            # Click the radio button
            radio = page.locator('text=Mass create with CSV').first
            radio.click()
            
            # Wait for file upload interface to appear
            page.wait_for_selector('#massAdsCsv', state='visible', timeout=5000)
            
            logger.info("✓ Mass CSV option selected")
            return True
        except Exception as e:
            logger.error(f"Failed to select Mass CSV: {e}")
            return False
    
    def _upload_csv_file(self, page: Page, csv_path: Path) -> bool:
        """Upload CSV file."""
        try:
            logger.info(f"Uploading CSV: {csv_path}")
            
            # Use set_input_files on the file input
            file_input = page.locator('#massAdsCsv')
            file_input.set_input_files(str(csv_path))
            
            logger.info("✓ CSV file uploaded")
            return True
        except Exception as e:
            logger.error(f"Failed to upload CSV: {e}")
            return False
    
    def _has_validation_errors(self, page: Page) -> bool:
        """Check if validation errors are present."""
        try:
            return page.locator('text=At least one issue was detected').is_visible(timeout=2000)
        except:
            return False
    
    def _extract_invalid_creatives(self, page: Page) -> List[str]:
        """Extract invalid creative IDs from error message."""
        try:
            # Look for error text containing creative IDs
            error_element = page.locator('text=The following creatives are not valid').first
            if error_element.is_visible():
                error_text = error_element.text_content()
                
                # Extract numbers that look like creative IDs (10+ digits)
                import re
                creative_ids = re.findall(r'\d{10,}', error_text)
                
                logger.warning(f"Found {len(creative_ids)} invalid creative IDs: {creative_ids}")
                return creative_ids
        except Exception as e:
            logger.debug(f"Could not extract invalid creatives: {e}")
        
        return []
    
    def _click_create_preview(self, page: Page) -> bool:
        """Click 'Create CSV Preview' button if it exists."""
        try:
            # Look for the button
            preview_btn = page.locator('text=Create CSV Preview').first
            if preview_btn.is_visible(timeout=2000):
                logger.info("Clicking 'Create CSV Preview'...")
                preview_btn.click()
                time.sleep(2)
                return True
            else:
                logger.debug("No 'Create CSV Preview' button found - may not be needed")
                return True
        except Exception as e:
            logger.debug(f"Create preview step: {e}")
            return True  # Not critical if button doesn't exist
    
    def _click_create_ads(self, page: Page) -> bool:
        """Click 'Create ad(s)' button."""
        try:
            logger.info("Looking for 'Create ad(s)' button...")
            
            # Find the create ads button by class
            create_btn = page.locator('button.create-ads-from-csv-button')
            
            # Wait for button to be visible
            logger.info("Waiting for button to be visible...")
            create_btn.wait_for(state='visible', timeout=10000)
            
            # Scroll the button into view
            logger.info("Scrolling button into view...")
            create_btn.scroll_into_view_if_needed()
            
            # Wait a moment for any animations
            page.wait_for_timeout(1000)
            
            # Click the button
            logger.info("Clicking 'Create ad(s)' button...")
            create_btn.click(timeout=10000)
            
            logger.info("✓ Create ads button clicked")
            return True
        except Exception as e:
            logger.error(f"Failed to click create ads: {e}")
            # Try to get a screenshot for debugging
            try:
                page.screenshot(path='./screenshots/create_ads_error.png')
                logger.error("Screenshot saved to: ./screenshots/create_ads_error.png")
            except:
                pass
            return False
    
    def _take_screenshot(self, page: Page, name: str, screenshot_dir: Optional[Path]):
        """Take a screenshot if enabled."""
        if not self.take_screenshots or not screenshot_dir:
            return
        
        try:
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            self.screenshot_counter += 1
            filename = f"{self.screenshot_counter:02d}_{name}.png"
            filepath = screenshot_dir / filename
            page.screenshot(path=str(filepath))
            logger.debug(f"Screenshot saved: {filename}")
        except Exception as e:
            logger.debug(f"Screenshot failed: {e}")


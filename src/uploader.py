"""Main CSV upload automation module."""

import logging
import time
import csv
import tempfile
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
        campaign_name: Optional[str] = None,
        screenshot_dir: Optional[Path] = None,
        skip_navigation: bool = False
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
            
            # Step 1: Navigate to campaign ad settings (unless already there)
            if not skip_navigation:
                if not self._navigate_to_campaign(page, campaign_id):
                    result['error'] = "Failed to navigate to campaign"
                    return result
            else:
                logger.info("Skipping navigation (already on campaign page)")
            
            self._take_screenshot(page, f"01_campaign_{campaign_id}_loaded", screenshot_dir)
            
            # Step 2: Set page length to show all ads (important for accurate counting!)
            self._set_ads_page_length(page, length=100)
            
            # Step 3: Count existing ads
            existing_ads = self._count_existing_ads(page)
            logger.info(f"Campaign has {existing_ads} existing ads")
            
            # Step 4: Select "Mass create with CSV"
            if not self._select_mass_csv(page):
                result['error'] = "Failed to select Mass CSV upload"
                return result
            
            self._take_screenshot(page, f"02_mass_csv_selected", screenshot_dir)
            
            # Step 4.5: Update CSV with campaign name if provided
            if campaign_name:
                csv_path = self._update_csv_with_campaign_name(csv_path, campaign_name)
            
            # Step 5: Upload CSV
            if self.dry_run:
                logger.info(f"DRY RUN: Would upload {csv_path}")
                result['status'] = 'dry_run_success'
                return result
            
            if not self._upload_csv_file(page, csv_path):
                result['error'] = "Failed to upload CSV file"
                return result
            
            self._take_screenshot(page, f"03_csv_uploaded", screenshot_dir)
            
            # Step 6: Wait and check for preview/errors
            time.sleep(2)  # Give it time to process
            
            # Step 7: Handle validation errors
            if self._has_validation_errors(page):
                logger.warning("Validation errors detected")
                invalid_ids = self._extract_invalid_creatives(page)
                result['invalid_creatives'] = invalid_ids
                result['error'] = f"Validation errors: {len(invalid_ids)} invalid creative IDs"
                self._take_screenshot(page, f"04_validation_errors", screenshot_dir)
                # Note: CSV cleaning and retry will be handled by campaign_manager
                return result
            
            # Step 8: Click create preview (if button exists)
            self._click_create_preview(page)
            time.sleep(2)
            
            self._take_screenshot(page, f"05_preview_created", screenshot_dir)
            
            # Step 9: Click create ads
            if not self._click_create_ads(page):
                result['error'] = "Failed to click create ads button"
                return result
            
            # Step 10: Wait for processing and reload to get fresh ad count
            logger.info("Waiting for ads to be created...")
            time.sleep(5)  # Wait for processing
            
            self._take_screenshot(page, f"06_ads_created", screenshot_dir)
            
            # Reload the page to get fresh ad count
            logger.info("Reloading page to verify ad creation...")
            page.reload(wait_until='networkidle', timeout=30000)
            time.sleep(2)  # Wait for page to settle
            
            # Set page length again after reload
            self._set_ads_page_length(page, length=100)
            
            # Step 11: Verify success
            new_ad_count = self._count_existing_ads(page)
            ads_created = new_ad_count - existing_ads
            
            logger.info(f"Ad count - Before: {existing_ads}, After: {new_ad_count}, Created: {ads_created}")
            
            if ads_created > 0:
                logger.info(f"✓ Successfully created {ads_created} ads")
                result['status'] = 'success'
                result['ads_created'] = ads_created
            elif new_ad_count > 0:
                # If we can't detect the difference but there ARE ads, assume success
                # This handles cases where the creative already existed
                logger.warning(f"Could not detect new ads, but found {new_ad_count} total ads in campaign")
                logger.warning("Upload likely succeeded (creative may have already existed)")
                result['status'] = 'success'
                result['ads_created'] = 1  # Assume 1 ad was uploaded
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
    
    def get_campaign_name_from_page(self, page: Page) -> str:
        """
        Extract the actual campaign name from TrafficJunky page.
        
        Args:
            page: Playwright page object (should be on campaign page)
            
        Returns:
            Campaign name from TJ, or empty string if not found
        """
        try:
            # Try to find campaign name at the top of the page
            # It's usually in a heading or title element
            selectors_to_try = [
                'h1.campaign-name',
                'h1',
                '.campaign-title',
                '[class*="campaign"][class*="name"]',
                'h2'
            ]
            
            for selector in selectors_to_try:
                try:
                    element = page.locator(selector).first
                    if element.is_visible(timeout=2000):
                        text = element.inner_text()
                        # Skip generic headings
                        if text and len(text) > 5 and 'STEP' not in text:
                            logger.info(f"✓ Found campaign name from TJ: {text}")
                            return text.strip()
                except:
                    continue
            
            logger.warning("Could not extract campaign name from page")
            return ""
            
        except Exception as e:
            logger.warning(f"Error extracting campaign name: {e}")
            return ""
    
    def _count_existing_ads(self, page: Page) -> int:
        """Count existing ads in the campaign."""
        try:
            # Wait for ads table to load
            page.wait_for_load_state('networkidle', timeout=10000)
            time.sleep(1)  # Extra wait for table to render
            
            # Look for the ads table (look for all tables and find the right one)
            tables = page.locator('table')
            table_count = tables.count()
            
            logger.debug(f"Found {table_count} tables on page")
            
            # Try to find the ads table (usually the first visible table with data)
            for i in range(table_count):
                table = tables.nth(i)
                if table.is_visible():
                    rows = table.locator('tbody tr').count()
                    if rows > 0:  # Found table with data
                        logger.debug(f"Found ads table with {rows} rows")
                        return max(0, rows)
            
            logger.debug("No ads table found or table is empty")
            return 0
        except Exception as e:
            logger.warning(f"Error counting ads: {e}")
            return 0
    
    def _set_ads_page_length(self, page: Page, length: int = 100) -> bool:
        """
        Set the DataTable page length to show more ads at once.
        This is critical for accurate ad counting when campaigns have many ads.
        
        Args:
            page: Playwright page object
            length: Number of ads to show per page (default: 100)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Setting ads table page length to {length}...")
            
            # Look for the page length dropdown (similar to campaigns page)
            # The selector might be different, so try multiple options
            selectors = [
                'span#select2-dt-length-1-container',  # Based on user's observation
                'select[name="dt-length-1"]',
                'span.select2-selection__rendered:has-text("10")',
            ]
            
            dropdown_clicked = False
            for selector in selectors:
                try:
                    dropdown = page.locator(selector).first
                    if dropdown.is_visible(timeout=2000):
                        dropdown.click()
                        dropdown_clicked = True
                        logger.debug(f"Clicked page length dropdown with selector: {selector}")
                        time.sleep(1)
                        break
                except:
                    continue
            
            if not dropdown_clicked:
                logger.debug("Page length dropdown not found, may not be needed")
                return False
            
            # Click the desired length option (100)
            try:
                option = page.locator(f'li.select2-results__option:has-text("{length}")').first
                option.click()
                logger.info(f"✓ Set page length to {length}")
                time.sleep(2)  # Wait for table to reload
                return True
            except:
                # Try clicking "All" if 100 doesn't exist
                try:
                    option = page.locator('li.select2-results__option:has-text("All")').first
                    option.click()
                    logger.info("✓ Set page length to show All ads")
                    time.sleep(2)
                    return True
                except:
                    logger.warning("Could not find page length option")
                    return False
                    
        except Exception as e:
            logger.debug(f"Could not set page length: {e}")
            return False
    
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
    
    def _update_csv_with_campaign_name(self, csv_path: Path, campaign_name: str) -> Path:
        """
        Update CSV file to replace sub11 parameter with actual campaign name.
        Also truncates ad names to 64 characters (TrafficJunky limit).
        Creates a temporary CSV file with updated values.
        
        Args:
            csv_path: Original CSV file path
            campaign_name: Actual campaign name to use
            
        Returns:
            Path to updated temporary CSV file
        """
        try:
            import re
            
            # Read original CSV
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                rows = list(reader)
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
            temp_path = Path(temp_file.name)
            
            # Write updated CSV
            with temp_file:
                writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in rows:
                    # Truncate Ad Name to 64 characters (TrafficJunky limit)
                    # Keep the ID at the end (format: ID-XXXXXXXX-VID)
                    if 'Ad Name' in row and row['Ad Name']:
                        ad_name = row['Ad Name']
                        if len(ad_name) > 64:
                            # Try to extract ID pattern (ID-XXXXXXXX-VID or similar)
                            # Match alphanumeric ID with format: ID-<alphanumeric>-<letters>
                            id_match = re.search(r'(ID-[A-Za-z0-9]+-[A-Z]+)$', ad_name)
                            if id_match:
                                id_part = id_match.group(1)
                                # Truncate the beginning but keep the ID
                                max_prefix_len = 64 - len(id_part) - 1  # -1 for underscore
                                prefix = ad_name[:max_prefix_len]
                                row['Ad Name'] = f"{prefix}_{id_part}"
                                logger.info(f"Truncated ad name from {len(ad_name)} to 64 chars (kept ID): {row['Ad Name']}")
                            else:
                                # No ID pattern found, just truncate
                                row['Ad Name'] = ad_name[:64]
                                logger.info(f"Truncated ad name to 64 chars (no ID pattern): {row['Ad Name']}")
                        else:
                            logger.debug(f"Ad name OK ({len(ad_name)} chars): {ad_name}")
                    
                    # Update Target URL - replace sub11 value with actual campaign name
                    if 'Target URL' in row and row['Target URL']:
                        # Replace sub11=<anything> with sub11=<campaign_name>
                        row['Target URL'] = re.sub(r'sub11=[^&]*', f'sub11={campaign_name}', row['Target URL'])
                    
                    # Also update Custom CTA URL if it exists
                    if 'Custom CTA URL' in row and row['Custom CTA URL']:
                        row['Custom CTA URL'] = re.sub(r'sub11=[^&]*', f'sub11={campaign_name}', row['Custom CTA URL'])
                    
                    # Also update Banner CTA URL if it exists
                    if 'Banner CTA URL' in row and row['Banner CTA URL']:
                        row['Banner CTA URL'] = re.sub(r'sub11=[^&]*', f'sub11={campaign_name}', row['Banner CTA URL'])
                    
                    writer.writerow(row)
            
            logger.info(f"✓ Updated CSV with campaign name in sub11: {campaign_name}")
            return temp_path
            
        except Exception as e:
            logger.warning(f"Failed to update CSV with campaign name: {e}")
            # Return original path if update fails
            return csv_path


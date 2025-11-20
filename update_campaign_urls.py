"""
One-time Campaign URL Updater Script
Updates all ad URLs in a campaign to include the correct campaign name in sub11 parameter
"""

import sys
import time
import argparse
import re
import pandas as pd
from pathlib import Path
from playwright.sync_api import sync_playwright

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from src.auth import TJAuthenticator
from src.utils import setup_logger, print_success, print_error, print_warning, print_info


def load_campaigns_from_csv(csv_path: Path) -> list:
    """Load campaign IDs, names, and template URLs from CSV file."""
    try:
        df = pd.read_csv(csv_path)
        
        # Check required columns
        if 'Campaign ID' not in df.columns or 'Campaign Name' not in df.columns or 'Template URL' not in df.columns:
            print_error("CSV must have 'Campaign ID', 'Campaign Name', and 'Template URL' columns")
            return []
        
        campaigns = []
        for _, row in df.iterrows():
            campaign_id = str(row['Campaign ID']).strip()
            campaign_name = str(row['Campaign Name']).strip()
            template_url = str(row['Template URL']).strip()
            
            if campaign_id and campaign_name and template_url:
                campaigns.append({
                    'id': campaign_id,
                    'name': campaign_name,
                    'template_url': template_url
                })
        
        return campaigns
        
    except Exception as e:
        print_error(f"Error reading CSV: {e}")
        return []


def update_urls_with_sub11(url: str, campaign_name: str) -> str:
    """Update URL to replace sub11 parameter with campaign name."""
    if not url:
        return url
    
    # Replace sub11=anything with sub11=campaign_name
    updated_url = re.sub(
        r'sub11=[^&]*',
        f'sub11={campaign_name}',
        url
    )
    
    return updated_url


def update_campaign_urls(page, campaign_id: str, campaign_name: str, template_url: str) -> bool:
    """Update all ad URLs in a campaign with the correct sub11 parameter."""
    try:
        print_info(f"Updating URLs for campaign {campaign_id}...")
        print_info(f"  Template URL: {template_url[:80]}...")
        
        # Make sure we're on the ad settings page
        current_url = page.url
        if f"campaign/{campaign_id}" not in current_url or "ad-settings" not in current_url:
            url = f"https://advertiser.trafficjunky.com/campaign/{campaign_id}/ad-settings#section_adSpecs"
            page.goto(url, wait_until='networkidle', timeout=30000)
            time.sleep(2)
        
        # Step 1: Set page length to 100 to see all ads
        print_info("  Setting table to show 100 ads...")
        try:
            # Click the dropdown for page length
            page_length_dropdown = page.locator('span#select2-dt-length-1-container').first
            if page_length_dropdown.is_visible(timeout=3000):
                page_length_dropdown.click()
                time.sleep(0.5)
                
                # Select 100
                option_100 = page.locator('li.select2-results__option:has-text("100")').first
                if option_100.is_visible(timeout=2000):
                    option_100.click()
                    print_success("  ✓ Set to show 100 ads")
                    time.sleep(2)  # Wait for table to reload
                else:
                    print_warning("  Could not find 100 option, continuing anyway...")
            else:
                print_warning("  Page length dropdown not found, continuing anyway...")
        except Exception as e:
            print_warning(f"  Could not set page length: {e}")
        
        # Step 2: Count how many ads are in the table
        ad_rows = page.locator('table#adsTable tbody tr').count()
        print_info(f"  Found {ad_rows} ads in campaign")
        
        if ad_rows == 0:
            print_warning("  No ads found in campaign")
            return False
        
        # Step 3: Select all ads by checking the "check all" checkbox
        print_info("  Selecting all ads...")
        check_all = page.locator('input.checkUncheckAll[data-table="adsTable"]').first
        
        if not check_all.is_visible(timeout=5000):
            print_error("  'Select All' checkbox not found")
            return False
        
        check_all.click()
        time.sleep(0.5)
        print_success(f"  ✓ Selected all {ad_rows} ads")
        
        # Step 4: Click "Edit Selected URLs" button
        print_info("  Clicking 'Edit Selected URLs'...")
        edit_urls_btn = page.locator('button.massUrlModifyButton').first
        
        if not edit_urls_btn.is_visible(timeout=5000):
            print_error("  'Edit Selected URLs' button not found")
            return False
        
        edit_urls_btn.click()
        
        # Wait longer for modal to appear
        print_info("  Waiting for modal to appear...")
        time.sleep(3)  # Increased wait time for modal animation
        
        # Wait for modal dialog to appear
        try:
            page.wait_for_selector('.modal.show', timeout=10000)
            print_success("  ✓ Modal dialog appeared")
        except Exception as e:
            print_error(f"  Modal did not appear: {e}")
            return False
        
        # The modal has TWO inputs with same id="mass_target_source_url":
        # 1. One with d-none class (hidden) for static/banner/native ads
        # 2. One WITHOUT d-none for video_file ads (the one we want!)
        # We need to find the one with data-ad-type-mass="video_file" that's NOT disabled
        
        time.sleep(2)  # Wait for dynamic fields to show
        
        # Find the video_file input (not the hidden one)
        modal_input = page.locator('input#mass_target_source_url[data-ad-type-mass="video_file"]:not([disabled])').first
        
        try:
            modal_input.wait_for(state='visible', timeout=5000)
            print_success("  ✓ Found video file URL input field")
        except Exception as e:
            print_error(f"  Could not find video file URL input: {e}")
            # Take a screenshot for debugging
            try:
                page.screenshot(path="debug_modal_error.png")
                print_info("  Screenshot saved to debug_modal_error.png")
            except:
                pass
            return False
        
        # Step 5: Use the template URL from CSV (already has correct structure)
        # Just update the sub11 parameter with the campaign name
        new_url = update_urls_with_sub11(template_url, campaign_name)
        print_info(f"  New URL: {new_url[:80]}...")
        
        # Set the new URL using character-by-character typing to trigger validation
        print_info("  Setting new URL in modal...")
        modal_input.click()
        time.sleep(0.3)
        
        # Type the new URL to trigger all validation events
        modal_input.type(new_url, delay=10)
        time.sleep(1)  # Give validation time to run
        
        print_success(f"  ✓ URL set with sub11={campaign_name}")
        
        # Step 6: Click Save button in modal
        print_info("  Clicking 'Save' button...")
        save_btn = page.locator('button#massAdModifyApply').first
        
        if not save_btn.is_visible(timeout=5000):
            print_error("  'Save' button not found")
            return False
        
        save_btn.click()
        
        # Wait for modal to close and changes to be saved
        print_info("  Waiting for changes to be saved...")
        time.sleep(3)
        
        # Wait for page to update
        page.wait_for_load_state('networkidle', timeout=10000)
        time.sleep(2)
        
        print_success(f"  ✓ URLs updated successfully for {ad_rows} ads!")
        return True
        
    except Exception as e:
        print_error(f"  Error updating URLs: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Update campaign ad URLs with correct sub11 parameter (one-time script)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
CSV Format (URL_Update.csv):
  Campaign ID,Campaign Name,Template URL
  1012927662,OLD_CPA_Global_Video-IS_excl._iOS_OTH5,https://track.redtrack.com/click?...&sub11=CAMPAIGN_NAME
  1012927663,OLD_CPA_Global_Video-IS_excl._iOS_OTH6,https://track.redtrack.com/click?...&sub11=CAMPAIGN_NAME
        """
    )
    
    parser.add_argument(
        '--csv',
        type=Path,
        default=Path('data/input/URL_Update.csv'),
        help='Path to CSV file with campaigns (default: data/input/URL_Update.csv)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without actually changing'
    )
    
    args = parser.parse_args()
    
    # Load campaigns from CSV
    if not args.csv.exists():
        print_error(f"CSV file not found: {args.csv}")
        print_info("Please create a CSV file with columns: Campaign ID, Campaign Name, Template URL")
        return 1
    
    campaigns = load_campaigns_from_csv(args.csv)
    
    if not campaigns:
        print_error("No valid campaigns found in CSV")
        return 1
    
    print("\n" + "="*60)
    print("Campaign URL Updater - One-Time Script")
    print("="*60)
    print(f"CSV file: {args.csv}")
    print(f"Campaigns to process: {len(campaigns)}")
    if args.dry_run:
        print_warning("DRY RUN MODE - No changes will be made")
    print("="*60 + "\n")
    
    # Setup logging
    log_file = Config.LOG_DIR / f"campaign_url_update_{time.strftime('%Y%m%d_%H%M%S')}.txt"
    logger = setup_logger('url_update', log_file, 'INFO', True, True)
    
    # Validate config
    config_errors = Config.validate()
    if config_errors:
        print_error("Configuration errors:")
        for error in config_errors:
            print_error(f"  - {error}")
        return 1
    
    results = []
    
    try:
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(
                headless=False,
                slow_mo=Config.SLOW_MO
            )
            
            print_success("Browser launched")
            
            # Initialize authenticator
            authenticator = TJAuthenticator(Config.TJ_USERNAME, Config.TJ_PASSWORD)
            
            # ALWAYS do a fresh manual login (don't use saved sessions)
            print_warning("⚠️  Manual login required - browser window will open")
            logger.info("Starting fresh login session...")
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            page.set_default_timeout(Config.TIMEOUT)
            
            if not authenticator.manual_login(page, timeout=120):
                print_error("Authentication failed or timed out")
                browser.close()
                return 1
            
            print_success("Logged into TrafficJunky")
            
            # Process each campaign
            print("\n" + "="*60)
            print("Processing Campaigns")
            print("="*60 + "\n")
            
            for campaign in campaigns:
                campaign_id = campaign['id']
                campaign_name = campaign['name']
                template_url = campaign['template_url']
                
                print(f"\nCampaign {campaign_id}:")
                print_info(f"  Campaign Name: {campaign_name}")
                
                if args.dry_run:
                    new_url = update_urls_with_sub11(template_url, campaign_name)
                    print_warning(f"  [DRY RUN] Would update URLs to:")
                    print_warning(f"  {new_url[:100]}...")
                    results.append({
                        'campaign_id': campaign_id,
                        'campaign_name': campaign_name,
                        'status': 'dry_run'
                    })
                else:
                    # Update URLs
                    success = update_campaign_urls(page, campaign_id, campaign_name, template_url)
                    results.append({
                        'campaign_id': campaign_id,
                        'campaign_name': campaign_name,
                        'status': 'success' if success else 'failed'
                    })
            
            # Close browser
            browser.close()
            print_success("\nBrowser closed")
            
    except KeyboardInterrupt:
        print_warning("\nProcess interrupted by user")
        return 130
    except Exception as e:
        logger.exception("Fatal error during execution")
        print_error(f"Fatal error: {e}")
        return 1
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    failed_count = sum(1 for r in results if r['status'] == 'failed')
    
    print(f"Total campaigns: {len(results)}")
    print(f"✓ Updated: {success_count}")
    print(f"✗ Failed: {failed_count}")
    
    if failed_count > 0:
        print("\nFailed campaigns:")
        for r in results:
            if r['status'] == 'failed':
                error = r.get('error', 'Unknown error')
                print(f"  ✗ {r['campaign_id']}: {error}")
    
    print("="*60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())


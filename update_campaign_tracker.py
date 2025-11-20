"""
One-time Campaign Tracker Updater Script
Ensures "Redtrack - Purchase" tracker is enabled for all specified campaigns
"""

import sys
import time
import argparse
import pandas as pd
from pathlib import Path
from playwright.sync_api import sync_playwright

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from src.auth import TJAuthenticator
from src.utils import setup_logger, print_success, print_error, print_warning, print_info


def load_campaigns_from_csv(csv_path: Path) -> list:
    """Load campaign IDs from CSV file."""
    try:
        df = pd.read_csv(csv_path)
        
        # Check required columns
        if 'Campaign ID' not in df.columns:
            print_error("CSV must have 'Campaign ID' column")
            return []
        
        campaigns = []
        for _, row in df.iterrows():
            campaign_id = str(row['Campaign ID']).strip()
            
            if campaign_id:
                campaigns.append(campaign_id)
        
        return campaigns
        
    except Exception as e:
        print_error(f"Error reading CSV: {e}")
        return []


def check_tracker_enabled(page, campaign_id: str) -> bool:
    """Check if Redtrack - Purchase tracker is already enabled."""
    try:
        # Look for the enabled tracker element
        tracker_element = page.locator('div.labelText[title="Redtrack - Purchase"]')
        
        if tracker_element.count() > 0 and tracker_element.first.is_visible(timeout=2000):
            return True
        
        return False
        
    except Exception as e:
        return False


def enable_redtrack_tracker(page, campaign_id: str) -> bool:
    """Enable Redtrack - Purchase tracker for a campaign."""
    try:
        print_info(f"Processing campaign {campaign_id}...")
        
        # Step 1: Navigate to the conversion tracker page
        tracker_url = f"https://advertiser.trafficjunky.com/campaign/{campaign_id}/tracking-spots-rules"
        print_info(f"  Navigating to tracker settings...")
        page.goto(tracker_url, wait_until='networkidle', timeout=30000)
        time.sleep(3)
        
        # Take a screenshot for debugging
        try:
            screenshot_path = f"data/debug/tracker_page_{campaign_id}.png"
            page.screenshot(path=screenshot_path)
            print_info(f"  Screenshot saved to {screenshot_path}")
        except:
            pass
        
        # Check if tracker is already enabled
        print_info("  Checking if tracker is already enabled...")
        if check_tracker_enabled(page, campaign_id):
            print_success("  ✓ Redtrack - Purchase is already enabled")
            return True
        
        print_info("  Tracker not enabled, proceeding to enable it...")
        
        # Step 2: Open the selector dropdown
        print_info("  Opening tracker selector...")
        
        # Wait a bit more for the page to fully load
        time.sleep(2)
        
        # Find the select2 container and click it to open the dropdown
        # The selector might be inside the form, let's try multiple approaches
        selector_container = page.locator('span.select2-selection.select2-selection--multiple').first
        
        if not selector_container.is_visible(timeout=10000):
            print_error("  Tracker selector not found")
            # Take another screenshot
            try:
                page.screenshot(path=f"data/debug/tracker_error_{campaign_id}.png")
                print_info(f"  Error screenshot saved")
            except:
                pass
            return False
        
        selector_container.click()
        time.sleep(1)  # Wait for dropdown to open
        print_success("  ✓ Opened tracker selector")
        
        # Step 3: Select "Redtrack - Purchase" option
        print_info("  Selecting 'Redtrack - Purchase'...")
        
        # Wait for the dropdown results to appear
        try:
            page.wait_for_selector('li.select2-results__option', timeout=5000)
        except Exception as e:
            print_error(f"  Dropdown options did not appear: {e}")
            return False
        
        # Find and click the "Redtrack - Purchase" option
        redtrack_option = page.locator('li.select2-results__option:has-text("Redtrack - Purchase")').first
        
        if not redtrack_option.is_visible(timeout=3000):
            print_error("  'Redtrack - Purchase' option not found in dropdown")
            return False
        
        redtrack_option.click()
        time.sleep(1)
        print_success("  ✓ Selected 'Redtrack - Purchase'")
        
        # Step 4: Verify the tracker has been added
        print_info("  Verifying tracker was added...")
        time.sleep(1)  # Give the UI time to update
        
        if not check_tracker_enabled(page, campaign_id):
            print_error("  Tracker selection did not persist")
            return False
        
        print_success("  ✓ Tracker successfully added to UI")
        
        # Step 5: Click "Save & Continue" button
        print_info("  Saving changes...")
        save_btn = page.locator('button.saveAndContinue[data-gtm-index="saveContinueStepThree"]').first
        
        if not save_btn.is_visible(timeout=5000):
            print_error("  'Save & Continue' button not found")
            return False
        
        save_btn.click()
        
        # Wait for save to complete
        print_info("  Waiting for changes to save...")
        time.sleep(3)
        
        # Wait for navigation
        page.wait_for_load_state('networkidle', timeout=10000)
        time.sleep(2)
        
        print_success(f"  ✓ Redtrack - Purchase tracker enabled successfully!")
        return True
        
    except Exception as e:
        print_error(f"  Error enabling tracker: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Enable Redtrack - Purchase tracker for campaigns (one-time script)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
CSV Format (Campaign_TrackerUpdate.csv):
  Campaign ID
  1012927662
  1012927663
        """
    )
    
    parser.add_argument(
        '--csv',
        type=Path,
        default=Path('data/input/Campaign_TrackerUpdate.csv'),
        help='Path to CSV file with campaign IDs (default: data/input/Campaign_TrackerUpdate.csv)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what campaigns would be processed without actually changing'
    )
    
    args = parser.parse_args()
    
    # Load campaigns from CSV
    if not args.csv.exists():
        print_error(f"CSV file not found: {args.csv}")
        print_info("Please create a CSV file with column: Campaign ID")
        return 1
    
    campaign_ids = load_campaigns_from_csv(args.csv)
    
    if not campaign_ids:
        print_error("No valid campaign IDs found in CSV")
        return 1
    
    print("\n" + "="*60)
    print("Campaign Tracker Updater - One-Time Script")
    print("="*60)
    print(f"CSV file: {args.csv}")
    print(f"Campaigns to process: {len(campaign_ids)}")
    print(f"Tracker to enable: Redtrack - Purchase")
    if args.dry_run:
        print_warning("DRY RUN MODE - No changes will be made")
    print("="*60 + "\n")
    
    # Setup logging
    log_file = Config.LOG_DIR / f"campaign_tracker_update_{time.strftime('%Y%m%d_%H%M%S')}.txt"
    logger = setup_logger('tracker_update', log_file, 'INFO', True, True)
    
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
            
            # Create fresh browser context and login
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            page.set_default_timeout(Config.TIMEOUT)
            
            logger.info("Manual login required...")
            print_warning("⚠️  Manual login required - browser window will open")
            
            if not authenticator.manual_login(page, timeout=120):
                print_error("Authentication failed or timed out")
                browser.close()
                return 1
            
            print_success("Logged into TrafficJunky")
            
            # Process each campaign
            print("\n" + "="*60)
            print("Processing Campaigns")
            print("="*60 + "\n")
            
            for campaign_id in campaign_ids:
                print(f"\nCampaign {campaign_id}:")
                
                if args.dry_run:
                    print_warning("  [DRY RUN] Would check and enable Redtrack - Purchase tracker")
                    results.append({
                        'campaign_id': campaign_id,
                        'status': 'dry_run'
                    })
                else:
                    # Enable the tracker
                    success = enable_redtrack_tracker(page, campaign_id)
                    results.append({
                        'campaign_id': campaign_id,
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
    print(f"✓ Tracker enabled: {success_count}")
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


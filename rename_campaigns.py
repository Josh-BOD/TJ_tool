"""
One-time Campaign Name Renamer Script
Updates campaign names from format: "CPA - Global - Video-IS - excl. iOS - OTH5"
To format: "OLD_CPA_Global_Video-IS_excl.iOS_OTH5"
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


def convert_campaign_name(old_name: str) -> str:
    """
    Convert campaign name from old format to new format.
    
    Example: "CPA - Global - Video-IS - excl. iOS - OTH5" 
    -> "OLD_CPA_Global_Video-IS_excl.iOS_OTH5"
    """
    # Add OLD_ prefix if not already there
    if not old_name.startswith("OLD_"):
        new_name = "OLD_" + old_name
    else:
        new_name = old_name
    
    # Replace " - " with "_"
    new_name = new_name.replace(" - ", "_")
    
    # Replace remaining spaces with underscores
    new_name = new_name.replace(" ", "_")
    
    return new_name


def get_campaign_name(page, campaign_id: str) -> str:
    """Get current campaign name from the campaign edit page."""
    try:
        # Navigate directly to the edit page (section_basicSettings)
        url = f"https://advertiser.trafficjunky.com/campaign/{campaign_id}#section_basicSettings"
        print_info(f"Navigating to campaign {campaign_id} edit page...")
        page.goto(url, wait_until='networkidle', timeout=30000)
        
        # Wait for page to load
        time.sleep(2)
        
        # Get the campaign name from the input field: input[name="name"]
        try:
            name_input = page.locator('input[name="name"]').first
            if name_input.is_visible(timeout=5000):
                old_name = name_input.input_value()
                print_info(f"  Found name: {old_name}")
                return old_name
        except Exception as e:
            print_error(f"  Could not find name input: {e}")
        
        print_warning(f"  Could not find campaign name")
        return ""
        
    except Exception as e:
        print_error(f"Error getting campaign name: {e}")
        return ""


def update_campaign_name(page, campaign_id: str, old_name: str, new_name: str) -> bool:
    """Update campaign name on TrafficJunky following the exact steps."""
    try:
        print_info(f"Updating to: {new_name}")
        
        # Make sure we're on the edit page
        current_url = page.url
        if f"campaign/{campaign_id}" not in current_url or "section_basicSettings" not in current_url:
            url = f"https://advertiser.trafficjunky.com/campaign/{campaign_id}#section_basicSettings"
            page.goto(url, wait_until='networkidle', timeout=30000)
            time.sleep(2)
        
        # Find the campaign name input field: input[name="name"]
        name_input = page.locator('input[name="name"]').first
        
        if not name_input.is_visible(timeout=5000):
            print_error("  Campaign name input field not found")
            return False
        
        # Use JavaScript to set the value directly (most reliable)
        print_info("  Setting new campaign name using JavaScript...")
        page.evaluate(f"""
            const input = document.querySelector('input[name="name"]');
            if (input) {{
                input.value = "{new_name}";
                // Trigger input event so the form knows it changed
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        """)
        time.sleep(0.5)  # 500ms
        
        print_success(f"  ✓ Name set to: {new_name}")
        
        # Click "Save & Continue" button: button#addCampaign
        print_info("  Clicking 'Save & Continue'...")
        save_btn = page.locator('button#addCampaign').first
        
        if not save_btn.is_visible(timeout=5000):
            print_error("  Save & Continue button not found")
            return False
        
        save_btn.click()
        
        # Wait for navigation to next screen
        print_info("  Waiting for page to save and navigate...")
        time.sleep(3)
        
        # Wait for URL to change (should move to next section)
        page.wait_for_load_state('networkidle', timeout=10000)
        time.sleep(2)
        
        print_success(f"  ✓ Campaign name updated successfully!")
        return True
        
    except Exception as e:
        print_error(f"  Error updating campaign name: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Rename TrafficJunky campaigns (one-time script)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
CSV Format (Campaign_Rename.csv):
  Campaign ID
  1012927662
  1012927663
        """
    )
    
    parser.add_argument(
        '--csv',
        type=Path,
        default=Path('data/input/Campaign_Rename.csv'),
        help='Path to CSV file with campaign IDs (default: data/input/Campaign_Rename.csv)'
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
        print_info("Please create a CSV file with column: Campaign ID")
        return 1
    
    campaign_ids = load_campaigns_from_csv(args.csv)
    
    if not campaign_ids:
        print_error("No valid campaign IDs found in CSV")
        return 1
    
    print("\n" + "="*60)
    print("Campaign Name Renamer - One-Time Script")
    print("="*60)
    print(f"CSV file: {args.csv}")
    print(f"Campaigns to process: {len(campaign_ids)}")
    if args.dry_run:
        print_warning("DRY RUN MODE - No changes will be made")
    print("="*60 + "\n")
    
    # Setup logging
    log_file = Config.LOG_DIR / f"campaign_rename_{time.strftime('%Y%m%d_%H%M%S')}.txt"
    logger = setup_logger('rename', log_file, 'INFO', True, True)
    
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
            
            # Try to load saved session first
            context = authenticator.load_session(browser)
            
            if context:
                page = context.new_page()
                page.set_default_timeout(Config.TIMEOUT)
                
                logger.info("Checking if saved session is still valid...")
                page.goto('https://advertiser.trafficjunky.com/campaigns', wait_until='domcontentloaded')
                
                if authenticator.is_logged_in(page):
                    print_success("Logged in using saved session")
                else:
                    logger.warning("Saved session expired, need to login again")
                    context.close()
                    context = None
            
            # If no valid session, do manual login
            if not context:
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080}
                )
                page = context.new_page()
                page.set_default_timeout(Config.TIMEOUT)
                
                logger.info("No valid session found, manual login required...")
                print_warning("⚠️  Manual login required - browser window will open")
                
                if not authenticator.manual_login(page, timeout=120):
                    print_error("Authentication failed or timed out")
                    browser.close()
                    return 1
                
                authenticator.save_session(context)
                print_success("Logged into TrafficJunky (session saved)")
            
            # Process each campaign
            print("\n" + "="*60)
            print("Processing Campaigns")
            print("="*60 + "\n")
            
            for campaign_id in campaign_ids:
                print(f"\nCampaign {campaign_id}:")
                
                # Get current name
                old_name = get_campaign_name(page, campaign_id)
                
                if not old_name:
                    print_error(f"  Skipping - could not get current name")
                    results.append({
                        'campaign_id': campaign_id,
                        'status': 'failed',
                        'error': 'Could not get name'
                    })
                    continue
                
                # Convert to new format
                new_name = convert_campaign_name(old_name)
                
                print_info(f"  Old: {old_name}")
                print_info(f"  New: {new_name}")
                
                if old_name == new_name:
                    print_warning("  No change needed - name already in correct format")
                    results.append({
                        'campaign_id': campaign_id,
                        'old_name': old_name,
                        'new_name': new_name,
                        'status': 'skipped'
                    })
                    continue
                
                if args.dry_run:
                    print_warning("  [DRY RUN] Would update name")
                    results.append({
                        'campaign_id': campaign_id,
                        'old_name': old_name,
                        'new_name': new_name,
                        'status': 'dry_run'
                    })
                else:
                    # Update the name (pass old_name for backspacing)
                    success = update_campaign_name(page, campaign_id, old_name, new_name)
                    results.append({
                        'campaign_id': campaign_id,
                        'old_name': old_name,
                        'new_name': new_name,
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
    skipped_count = sum(1 for r in results if r['status'] == 'skipped')
    
    print(f"Total campaigns: {len(results)}")
    print(f"✓ Updated: {success_count}")
    print(f"✗ Failed: {failed_count}")
    print(f"⊘ Skipped: {skipped_count}")
    
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


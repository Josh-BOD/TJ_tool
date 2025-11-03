#!/usr/bin/env python3
"""
Campaign Fetcher for TrafficJunky

Fetches campaign IDs and names from TJ web interface and generates
a campaign_mapping.csv for bulk creative uploads.

Based on the working main.py upload tool.

Usage:
    python fetch_campaigns.py --csv-file data/input/preroll_creatives.csv --output data/input/preroll_mapping.csv
"""

import argparse
import logging
import sys
import csv
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from config.config import Config
from src.auth import TJAuthenticator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_header():
    """Print tool header."""
    print("\n" + "="*70)
    print("TrafficJunky Campaign Fetcher")
    print("="*70 + "\n")


def print_success(msg):
    """Print success message."""
    print(f"✓ {msg}")


def print_warning(msg):
    """Print warning message."""
    print(f"⚠️  {msg}")


def print_error(msg):
    """Print error message."""
    print(f"❌ {msg}")


def apply_ad_format_filter(page, ad_format: str):
    """
    Automatically apply the Ad Format filter using Select2 dropdown.
    
    Args:
        page: Playwright page object
        ad_format: Ad format to filter by (e.g., "In-Stream Video")
        
    Returns:
        True if filter was applied successfully
    """
    import time
    
    try:
        logger.info(f"Attempting to apply Ad Format filter: {ad_format}")
        
        # Wait for the filter section to load
        time.sleep(2)
        
        # Find the Ad Format Select2 dropdown container
        # The input field you provided is inside a Select2 container
        ad_format_container = page.query_selector('input.select2-search__field[placeholder*="Ad Format"]')
        
        if not ad_format_container:
            logger.warning("Could not find Ad Format dropdown")
            return False
        
        # Click on the Select2 container to open dropdown
        logger.info("Opening Ad Format dropdown...")
        
        # Find the parent Select2 container and click it
        # Select2 dropdowns typically have a parent with class select2-selection
        parent_selector = page.query_selector('span.select2-selection:has(input[placeholder*="Ad Format"])')
        if parent_selector:
            parent_selector.click()
        else:
            # Try clicking the input itself
            ad_format_container.click()
        
        time.sleep(1)
        
        # Type the ad format into the search field
        logger.info(f"Typing '{ad_format}' into search...")
        ad_format_container.fill(ad_format)
        
        time.sleep(1)
        
        # Wait for results and click the matching option
        # Select2 results appear in a separate dropdown
        result_selector = f'li.select2-results__option:has-text("{ad_format}")'
        result_option = page.wait_for_selector(result_selector, timeout=5000)
        
        if result_option:
            logger.info(f"Clicking option: {ad_format}")
            result_option.click()
            time.sleep(1)
            
            # Click away from the dropdown to close it
            logger.info("Clicking away from dropdown...")
            page.click('body')
            time.sleep(1)
            
            # Find and click the "Apply Filters" button
            logger.info("Looking for Apply Filters button...")
            apply_button_selectors = [
                'button:has-text("Apply Filters")',
                'button.apply-filters',
                'input[value="Apply Filters"]',
                'button[type="submit"]:has-text("Apply")'
            ]
            
            apply_button = None
            for selector in apply_button_selectors:
                try:
                    apply_button = page.query_selector(selector)
                    if apply_button:
                        logger.info(f"Found Apply Filters button with selector: {selector}")
                        break
                except:
                    continue
            
            if apply_button:
                logger.info("Clicking Apply Filters button...")
                apply_button.click()
                time.sleep(3)  # Wait for campaigns to reload
                logger.info("✓ Filter applied successfully")
                return True
            else:
                logger.warning("Could not find Apply Filters button")
                return False
        else:
            logger.warning(f"Could not find option for: {ad_format}")
            return False
            
    except Exception as e:
        logger.error(f"Error applying filter: {e}")
        return False


def wait_for_user_filter(wait_seconds: int = 30):
    """
    Display instructions and wait for user to apply filter.
    
    Args:
        wait_seconds: How long to wait
    """
    print("\n" + "="*70)
    print("📋 FILTER INSTRUCTIONS")
    print("="*70)
    print("\nIn the browser window:")
    print("  1. Find and click the 'Ad Format' dropdown/filter")
    print("  2. Select your desired format (e.g., 'In-Stream Video')")
    print("  3. Wait for the campaigns list to update")
    print("  4. Make sure all pages are loaded (scroll if needed)")
    print(f"\nThis script will continue in {wait_seconds} seconds...")
    print("="*70 + "\n")
    
    import time
    for i in range(wait_seconds, 0, -1):
        print(f"  Continuing in {i} seconds... (the browser will stay open)", end='\r')
        time.sleep(1)
    print("\n")


def extract_campaigns_from_page(page):
    """
    Extract campaign IDs and names from the current page.
    
    Args:
        page: Playwright page object
        
    Returns:
        List of dicts with campaign_id and campaign_name
    """
    logger.info("Extracting campaigns from page...")
    
    campaigns = []
    
    try:
        # Debug: Try different selectors
        selectors_to_try = [
            'a[href*="/campaign/overview/"]',
            'a[href*="/campaign/"]',
            'tr[data-campaign-id]',
            '.campaign-row',
            '[class*="campaign"]'
        ]
        
        for selector in selectors_to_try:
            elements = page.query_selector_all(selector)
            if elements:
                logger.info(f"Found {len(elements)} elements with selector: {selector}")
        
        # Find all campaign links
        campaign_links = page.query_selector_all('a[href*="/campaign/overview/"]')
        
        logger.info(f"Found {len(campaign_links)} campaign links with main selector")
        
        seen_ids = set()
        
        for link in campaign_links:
            try:
                href = link.get_attribute('href')
                if not href or '/campaign/overview/' not in href:
                    continue
                
                # Extract campaign ID
                campaign_id = href.split('/campaign/overview/')[-1].strip('/')
                
                # Skip duplicates
                if campaign_id in seen_ids:
                    continue
                seen_ids.add(campaign_id)
                
                # Extract campaign name
                campaign_name = link.inner_text().strip()
                
                if campaign_id and campaign_name:
                    campaigns.append({
                        'campaign_id': campaign_id,
                        'campaign_name': campaign_name
                    })
                    
            except Exception as e:
                logger.debug(f"Error extracting campaign: {e}")
                continue
        
        logger.info(f"✓ Extracted {len(campaigns)} unique campaigns")
        return campaigns
        
    except Exception as e:
        logger.error(f"Error extracting campaigns: {e}")
        return []


def save_mapping_csv(campaigns, csv_file_path, output_path, enabled=True):
    """
    Save campaigns to mapping CSV.
    
    Args:
        campaigns: List of campaign dicts
        csv_file_path: Path to creative CSV
        output_path: Where to save mapping
        enabled: Whether campaigns are enabled
    """
    if not campaigns:
        print_error("No campaigns to save!")
        return False
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['campaign_id', 'campaign_name', 'csv_file', 'enabled'])
        
        for campaign in campaigns:
            writer.writerow([
                campaign['campaign_id'],
                campaign['campaign_name'],
                csv_file_path,
                'true' if enabled else 'false'
            ])
    
    print_success(f"Saved {len(campaigns)} campaigns to: {output_path}")
    return True


def preview_campaigns(campaigns, limit=10):
    """Preview campaigns."""
    print("\n" + "="*70)
    print("CAMPAIGN PREVIEW")
    print("="*70 + "\n")
    
    for i, campaign in enumerate(campaigns[:limit], 1):
        print(f"{i}. {campaign['campaign_name']}")
        print(f"   ID: {campaign['campaign_id']}\n")
    
    if len(campaigns) > limit:
        print(f"... and {len(campaigns) - limit} more campaigns\n")
    
    print("="*70 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Fetch campaigns from TJ and generate mapping CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch In-Stream Video campaigns (automatic filtering)
  python fetch_campaigns.py --ad-format "In-Stream Video" --csv-file data/input/preroll_creatives.csv --output data/input/instream_mapping.csv
  
  # Fetch Native campaigns
  python fetch_campaigns.py --ad-format "Native" --csv-file data/input/native_creatives.csv --output data/input/native_mapping.csv
  
  # Manual filtering (no --ad-format)
  python fetch_campaigns.py --csv-file data/input/preroll_creatives.csv --output data/input/manual_mapping.csv
  
  # Preview only
  python fetch_campaigns.py --ad-format "In-Stream Video" --csv-file data/input/preroll_creatives.csv --preview-only
  
  # Save as disabled
  python fetch_campaigns.py --ad-format "In-Stream Video" --csv-file data/input/preroll_creatives.csv --output data/input/instream_mapping.csv --disabled

Workflow:
  1. Script opens browser and logs into TrafficJunky
  2. If --ad-format provided: Script automatically applies filter
     If not provided: You manually apply filters (wait time provided)
  3. Script extracts all visible campaigns
  4. Script generates mapping CSV
        """
    )
    
    parser.add_argument(
        '--ad-format',
        type=str,
        default=None,
        help='Ad format to filter by (e.g., "In-Stream Video", "Native", "Popunder"). If not provided, will wait for manual filtering.'
    )
    
    parser.add_argument(
        '--csv-file',
        type=str,
        required=True,
        help='Path to creative CSV file (e.g., data/input/preroll_creatives.csv)'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Output path for mapping CSV (default: auto-generated name)'
    )
    
    parser.add_argument(
        '--disabled',
        action='store_true',
        help='Set campaigns as disabled in mapping'
    )
    
    parser.add_argument(
        '--preview-only',
        action='store_true',
        help='Preview campaigns without saving file'
    )
    
    parser.add_argument(
        '--wait-time',
        type=int,
        default=30,
        help='Seconds to wait for manual filtering (default: 30)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (not recommended)'
    )
    
    args = parser.parse_args()
    
    # Auto-generate output filename if not provided
    if not args.output and not args.preview_only:
        args.output = Path('data/input/campaign_mapping_generated.csv')
    
    print_header()
    
    try:
        # Validate config
        logger.info("Validating configuration...")
        Config.validate()
        print_success("Configuration valid")
        
        # Start browser
        logger.info("Starting browser...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=args.headless,
                slow_mo=Config.SLOW_MO if not args.headless else 0
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
                
                import time
                time.sleep(2)  # Wait for any redirects
                
                # Check if we're still on the campaigns page (not redirected to login)
                current_url = page.url
                if 'sign-in' in current_url.lower() or 'login' in current_url.lower():
                    logger.warning("Session expired - redirected to login")
                    context.close()
                    context = None
                elif authenticator.is_logged_in(page):
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
                print_warning("Manual login required - browser window will open")
                
                if not authenticator.manual_login(page, timeout=120):
                    print_error("Authentication failed or timed out")
                    browser.close()
                    return 1
                
                authenticator.save_session(context)
                print_success("Logged into TrafficJunky (session saved)")
            
            # Navigate to campaigns page
            logger.info("Navigating to campaigns page...")
            page.goto('https://advertiser.trafficjunky.com/campaigns', wait_until='domcontentloaded')
            
            import time
            time.sleep(2)  # Let page settle
            
            print_success("On campaigns page")
            
            # First, change the page size to 100 campaigns (default is 10)
            logger.info("Changing page size to 100 campaigns...")
            try:
                # Find the page length dropdown (DataTable length selector)
                length_selector = page.query_selector('span#select2-dt-length-0-container')
                
                if length_selector:
                    logger.info("Clicking page length dropdown...")
                    length_selector.click()
                    time.sleep(1)
                    
                    # Click the "100" option
                    hundred_option = page.wait_for_selector('li.select2-results__option:has-text("100")', timeout=5000)
                    if hundred_option:
                        logger.info("Selecting 100 campaigns per page...")
                        hundred_option.click()
                        time.sleep(2)  # Wait for page to reload with 100 items
                        print_success("Page size set to 100 campaigns")
                    else:
                        logger.warning("Could not find 100 option")
                else:
                    logger.warning("Could not find page length dropdown, continuing anyway...")
            except Exception as e:
                logger.warning(f"Error setting page size: {e}, continuing anyway...")
            
            # Set date range to Last 7 Days
            logger.info("Setting date range to Last 7 Days...")
            try:
                # Click the date range input to open the dropdown
                daterange_input = page.query_selector('input#daterange')
                
                if daterange_input:
                    logger.info("Clicking date range picker...")
                    daterange_input.click()
                    time.sleep(1)
                    
                    # Click "Last 7 Days" shortcut
                    last_7_days = page.wait_for_selector('a[shortcut="custom"]:has-text("Last 7 Days")', timeout=5000)
                    if last_7_days:
                        logger.info("Selecting Last 7 Days...")
                        last_7_days.click()
                        time.sleep(1)
                        
                        # Click Close button to apply the date range
                        close_button_selectors = [
                            'input.apply-btn[value="Close"]',
                            'button:has-text("Close")',
                            'button.close-date-picker',
                            'button[data-dismiss="daterangepicker"]'
                        ]
                        
                        close_button = None
                        for selector in close_button_selectors:
                            try:
                                close_button = page.query_selector(selector)
                                if close_button:
                                    logger.info(f"Found Close button with selector: {selector}")
                                    break
                            except:
                                continue
                        
                        if close_button:
                            logger.info("Clicking Close to apply date range...")
                            close_button.click()
                            time.sleep(2)  # Wait for data to reload
                            print_success("Date range set to Last 7 Days")
                        else:
                            logger.warning("Could not find Close button, date range may not be applied")
                    else:
                        logger.warning("Could not find Last 7 Days option")
                else:
                    logger.warning("Could not find date range picker, continuing anyway...")
            except Exception as e:
                logger.warning(f"Error setting date range: {e}, continuing anyway...")
            
            # Apply Ad Format filter (automatic or manual)
            if args.ad_format:
                print(f"\n🔍 Automatically filtering by: {args.ad_format}")
                filter_applied = apply_ad_format_filter(page, args.ad_format)
                
                if not filter_applied:
                    print_warning("Automatic filtering failed, waiting for manual filtering...")
                    wait_for_user_filter(args.wait_time)
                else:
                    print_success(f"Filter applied: {args.ad_format}")
                    time.sleep(3)  # Extra wait for campaigns to load
            else:
                # Wait for user to apply filters manually
                wait_for_user_filter(args.wait_time)
            
            # Sort by Cost descending (highest spend first)
            logger.info("Sorting campaigns by Cost (descending)...")
            try:
                # Find the Cost column header - try multiple selectors
                # The th element is what actually triggers the sort
                cost_header_selectors = [
                    'th:has(span.dt-column-title:has-text("Cost"))',  # Try th parent first
                    'span.dt-column-title:has-text("Cost")',  # Fallback to span
                ]
                
                cost_header = None
                for selector in cost_header_selectors:
                    cost_header = page.query_selector(selector)
                    if cost_header:
                        logger.info(f"Found Cost column with selector: {selector}")
                        break
                
                if cost_header:
                    logger.info("Clicking Cost column to sort by cost (descending)...")
                    cost_header.click()
                    logger.info("Waiting for table to re-render with cost descending...")
                    time.sleep(12)  # Wait for sort to complete
                    print_success("Sorted by Cost (descending) - highest spend first")
                else:
                    logger.warning("Could not find Cost column, continuing anyway...")
            except Exception as e:
                logger.warning(f"Error sorting by Cost: {e}, continuing anyway...")
            
            # Take screenshot for debugging
            screenshot_path = Path('data/debug/campaigns_page.png')
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot_path))
            logger.info(f"Screenshot saved to: {screenshot_path}")
            
            # Extract campaigns
            campaigns = extract_campaigns_from_page(page)
            
            if not campaigns:
                print_error("No campaigns found! Make sure:")
                print("  - The campaigns page has loaded")
                print("  - You've applied the correct filters")
                print("  - Campaigns are visible on the page")
                print(f"\nDebug screenshot saved to: {screenshot_path}")
                print("Check the screenshot to see what the page looks like.")
                browser.close()
                return 1
            
            # Preview
            preview_campaigns(campaigns, limit=20)
            
            # Save or preview
            if args.preview_only:
                print_warning("Preview mode - no file saved")
            else:
                if save_mapping_csv(campaigns, args.csv_file, args.output, enabled=not args.disabled):
                    print("\n" + "="*70)
                    print("✅ SUCCESS!")
                    print("="*70)
                    print(f"\nMapping file: {args.output}")
                    print(f"Total campaigns: {len(campaigns)}")
                    print(f"\nNext steps:")
                    print(f"1. Review: {args.output}")
                    print(f"2. Ensure creative CSV exists: {args.csv_file}")
                    print(f"3. Run upload tool:")
                    print(f"   python main.py --dry-run")
                    print(f"   python main.py --live")
                    print()
            
            # Keep browser open briefly
            print("\nClosing browser in 3 seconds...")
            time.sleep(3)
            browser.close()
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        return 1
    except Exception as e:
        logger.exception("Fatal error")
        print_error(f"Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())


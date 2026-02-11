"""
One-time Campaign URL Updater Script
Updates all ad URLs in a campaign to include the correct campaign name in sub11 parameter.

Supports:
- Preroll ads (video_file)
- Native ads (rollover)

IMPORTANT: Only updates URL fields - does NOT modify headline/brand text fields.
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
        
        # Support both "Campaign ID" and "ID" column names
        id_column = None
        if 'Campaign ID' in df.columns:
            id_column = 'Campaign ID'
        elif 'ID' in df.columns:
            id_column = 'ID'
        else:
            print_error("CSV must have 'Campaign ID' or 'ID' column")
            return []
        
        # Check required columns
        if 'Campaign Name' not in df.columns or 'Template URL' not in df.columns:
            print_error("CSV must have 'Campaign Name' and 'Template URL' columns")
            return []
        
        campaigns = []
        for _, row in df.iterrows():
            campaign_id = str(row[id_column]).strip()
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
    """
    Update URL to replace sub11 parameter with campaign name.
    
    If the template URL already has {CampaignName} macro, it will be preserved.
    Otherwise, replaces sub11 with the actual campaign name.
    """
    if not url:
        return url
    
    # Check if sub11 already has a macro (like {CampaignName}, {campaignName}, etc.)
    macro_pattern = r'sub11=[^&]*\{[^}]+\}[^&]*'
    if re.search(macro_pattern, url):
        # Already has a macro - keep it as-is (TrafficJunky will auto-replace it)
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
        
        # The modal has multiple inputs with same id="mass_target_source_url":
        # 1. One for video_file ads (Preroll) - data-ad-type-mass="video_file"
        # 2. One for rollover ads (Native) - data-ad-type-mass="rollover"
        # 3. Hidden ones for other ad types
        # We need to find the visible one that matches the ad type
        
        time.sleep(2)  # Wait for dynamic fields to show
        
        # Try to find Preroll (video_file) input first
        modal_input = None
        ad_type = None
        
        try:
            # Try Preroll/video_file ads
            video_input = page.locator('input#mass_target_source_url[data-ad-type-mass="video_file"]:not([disabled])').first
            if video_input.is_visible(timeout=2000):
                modal_input = video_input
                ad_type = "Preroll"
                print_success("  ✓ Found Preroll (video_file) URL input field")
        except:
            pass
        
        # If not Preroll, try Native (rollover) ads
        if not modal_input:
            try:
                rollover_input = page.locator('input#mass_target_source_url[data-ad-type-mass="rollover"]:not([disabled])').first
                if rollover_input.is_visible(timeout=2000):
                    modal_input = rollover_input
                    ad_type = "Native"
                    print_success("  ✓ Found Native (rollover) URL input field")
            except:
                pass
        
        # If still not found, try any visible URL input
        if not modal_input:
            try:
                any_input = page.locator('input#mass_target_source_url:not([disabled]):not(.d-none)').first
                if any_input.is_visible(timeout=2000):
                    modal_input = any_input
                    ad_type = "Unknown"
                    print_warning("  ⚠ Found URL input but ad type unknown")
            except:
                pass
        
        if not modal_input:
            print_error("  Could not find URL input field for any ad type")
            # Take a screenshot for debugging
            try:
                page.screenshot(path="debug_modal_error.png")
                print_info("  Screenshot saved to debug_modal_error.png")
            except:
                pass
            return False
        
        # Step 5: Use the template URL from CSV (replace entire URL with new template)
        # If template has {CampaignName} macro, use it as-is (TrafficJunky will auto-replace)
        # Otherwise, replace sub11 with actual campaign name
        new_url = update_urls_with_sub11(template_url, campaign_name)
        
        if new_url == template_url:
            print_info(f"  Using template URL with {{CampaignName}} macro (TrafficJunky will auto-replace)")
        else:
            print_info(f"  Using template URL with sub11 replaced with campaign name")
        
        print_info(f"  New URL: {new_url[:80]}...")
        
        # Update Target URL field
        print_info(f"  Setting Target URL in modal ({ad_type} ads)...")
        modal_input.click()
        time.sleep(0.3)
        modal_input.fill("")  # Clear first
        modal_input.fill(new_url)  # Paste the URL
        # Click outside the input to trigger validation and enable save button
        try:
            page.locator('.modal.show .modal-header, .modal.show .modal-body').first.click()
            time.sleep(0.5)
        except:
            # Fallback: press Tab to blur the input
            page.keyboard.press('Tab')
            time.sleep(0.5)
        print_success(f"  ✓ Target URL set")
        
        # Step 5b: Also update Custom CTA URL if it exists (for Preroll ads)
        if ad_type == "Preroll":
            print_info(f"  Looking for Custom CTA URL field...")
            custom_cta_input = None
            
            # Try multiple selector strategies for Custom CTA URL
            selectors_to_try = [
                ('input#mass_custom_cta_url[data-ad-type-mass="video_file"]:not([disabled])', "ID: mass_custom_cta_url"),
                ('input[name="mass_custom_cta_url"][data-ad-type-mass="video_file"]:not([disabled])', "Name: mass_custom_cta_url"),
                ('input[name*="custom_cta"][data-ad-type-mass="video_file"]:not([disabled])', "Name contains: custom_cta"),
                ('input[data-ad-type-mass="video_file"]:not([disabled])', "Any video_file input (will check label)"),
            ]
            
            for selector, description in selectors_to_try:
                try:
                    test_input = page.locator(selector).first
                    if test_input.is_visible(timeout=1000):
                        # If using the generic selector, verify it's the Custom CTA URL by checking nearby text
                        if "Any video_file input" in description:
                            # Check if there's a label nearby that says "Custom CTA"
                            try:
                                # Get the input's parent or nearby elements to check for label
                                input_id = test_input.get_attribute('id') or ""
                                if 'custom' in input_id.lower() or 'cta' in input_id.lower():
                                    custom_cta_input = test_input
                                    print_info(f"    Found by {description}")
                                    break
                            except:
                                pass
                        else:
                            custom_cta_input = test_input
                            print_info(f"    Found by {description}")
                            break
                except:
                    continue
            
            # If still not found, try finding by label text (with data-ad-type-mass)
            if not custom_cta_input:
                try:
                    # Look for any label containing "Custom CTA" or "CTA URL"
                    labels = page.locator('label').all()
                    for label in labels:
                        label_text = label.inner_text().lower()
                        if 'custom cta' in label_text and 'url' in label_text:
                            for_id = label.get_attribute('for')
                            if for_id:
                                try:
                                    found_input = page.locator(f'input#{for_id}[data-ad-type-mass="video_file"]:not([disabled])').first
                                    if found_input.is_visible(timeout=1000):
                                        custom_cta_input = found_input
                                        print_info(f"    Found by label text: {label.inner_text()}")
                                        break
                                except:
                                    pass
                except Exception as e:
                    print_warning(f"    Error searching by label: {e}")
            
            # Fallback: Try without data-ad-type-mass attribute
            if not custom_cta_input:
                try:
                    # Try by ID without the data-ad-type-mass filter
                    fallback_input = page.locator('input#mass_custom_cta_url:not([disabled])').first
                    if fallback_input.is_visible(timeout=1000):
                        custom_cta_input = fallback_input
                        print_info(f"    Found by ID without data-ad-type-mass filter")
                except:
                    pass
            
            # Final fallback: Search all inputs in modal and match by label
            if not custom_cta_input:
                try:
                    # Get all visible inputs in the modal
                    all_inputs = page.locator('.modal.show input[type="text"], .modal.show input[type="url"]').all()
                    for inp in all_inputs:
                        try:
                            inp_id = inp.get_attribute('id') or ''
                            # Check if this input has a label that says "Custom CTA URL"
                            if inp_id:
                                # Try to find label with matching 'for' attribute
                                label = page.locator(f'label[for="{inp_id}"]').first
                                if label.is_visible(timeout=500):
                                    label_text = label.inner_text().lower()
                                    if 'custom cta' in label_text and 'url' in label_text:
                                        if inp.is_visible(timeout=500):
                                            custom_cta_input = inp
                                            print_info(f"    Found by matching label to input ID: {inp_id}")
                                            break
                        except:
                            continue
                except Exception as e:
                    print_warning(f"    Error in final fallback search: {e}")
            
            if custom_cta_input:
                try:
                    print_info(f"  Setting Custom CTA URL...")
                    custom_cta_input.click()
                    time.sleep(0.3)
                    custom_cta_input.fill("")  # Clear first
                    custom_cta_input.fill(new_url)  # Paste the URL
                    # Click outside the input to trigger validation
                    try:
                        page.locator('.modal.show .modal-header, .modal.show .modal-body').first.click()
                        time.sleep(0.5)
                    except:
                        page.keyboard.press('Tab')
                        time.sleep(0.5)
                    print_success(f"  ✓ Custom CTA URL set")
                except Exception as e:
                    print_warning(f"  Could not set Custom CTA URL: {e}")
                    print_warning(f"    Error details: {str(e)}")
            else:
                print_warning(f"  ⚠ Custom CTA URL field not found - trying to list all URL inputs for debugging...")
                try:
                    # Debug: List all URL inputs in modal
                    all_inputs = page.locator('.modal.show input[type="text"], .modal.show input[type="url"]').all()
                    print_info(f"    Found {len(all_inputs)} text/url inputs in modal")
                    for i, inp in enumerate(all_inputs[:5]):  # Show first 5
                        try:
                            inp_id = inp.get_attribute('id') or 'no-id'
                            inp_name = inp.get_attribute('name') or 'no-name'
                            inp_placeholder = inp.get_attribute('placeholder') or 'no-placeholder'
                            print_info(f"      Input {i+1}: id={inp_id}, name={inp_name}, placeholder={inp_placeholder}")
                        except:
                            pass
                except:
                    pass
            
            # Step 5c: Also update Banner CTA URL if it exists (for Preroll ads)
            print_info(f"  Looking for Banner CTA URL field...")
            banner_cta_input = None
            
            # Try multiple selector strategies for Banner CTA URL
            selectors_to_try = [
                ('input#mass_banner_cta_url[data-ad-type-mass="video_file"]:not([disabled])', "ID: mass_banner_cta_url"),
                ('input[name="mass_banner_cta_url"][data-ad-type-mass="video_file"]:not([disabled])', "Name: mass_banner_cta_url"),
                ('input[name*="banner_cta"][data-ad-type-mass="video_file"]:not([disabled])', "Name contains: banner_cta"),
            ]
            
            for selector, description in selectors_to_try:
                try:
                    test_input = page.locator(selector).first
                    if test_input.is_visible(timeout=1000):
                        banner_cta_input = test_input
                        print_info(f"    Found by {description}")
                        break
                except:
                    continue
            
            # If still not found, try finding by label text
            if not banner_cta_input:
                try:
                    # Look for any label containing "Banner CTA" or "Banner CTA URL"
                    labels = page.locator('label').all()
                    for label in labels:
                        label_text = label.inner_text().lower()
                        if 'banner cta' in label_text and 'url' in label_text:
                            for_id = label.get_attribute('for')
                            if for_id:
                                try:
                                    found_input = page.locator(f'input#{for_id}[data-ad-type-mass="video_file"]:not([disabled])').first
                                    if found_input.is_visible(timeout=1000):
                                        banner_cta_input = found_input
                                        print_info(f"    Found by label text: {label.inner_text()}")
                                        break
                                except:
                                    pass
                except Exception as e:
                    print_warning(f"    Error searching by label: {e}")
            
            if banner_cta_input:
                try:
                    print_info(f"  Setting Banner CTA URL...")
                    banner_cta_input.click()
                    time.sleep(0.3)
                    banner_cta_input.fill("")  # Clear first
                    banner_cta_input.fill(new_url)  # Paste the URL
                    # Click outside the input to trigger validation
                    try:
                        page.locator('.modal.show .modal-header, .modal.show .modal-body').first.click()
                        time.sleep(0.5)
                    except:
                        page.keyboard.press('Tab')
                        time.sleep(0.5)
                    print_success(f"  ✓ Banner CTA URL set")
                except Exception as e:
                    print_warning(f"  Could not set Banner CTA URL: {e}")
                    print_warning(f"    Error details: {str(e)}")
            else:
                print_info(f"  Banner CTA URL field not found (ads may not have Banner CTA)")
        
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
        
        print_success(f"  ✓ URLs updated successfully for {ad_rows} {ad_type} ads! (URLs only, text fields unchanged)")
        return True
        
    except Exception as e:
        print_error(f"  Error updating URLs: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Update campaign ad URLs with correct sub11 parameter (one-time script)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supports both Preroll and Native ads. Only updates URL fields - does NOT modify text/headline fields.

CSV Format (URL_Update.csv):
  Campaign ID,Campaign Name,Template URL
  1012927662,US_EN_PREROLL_CPA_ALL_KEY-INDIAN_ALL_M_JB,https://track.redtrack.com/click?...&sub11=CAMPAIGN_NAME
  1012927663,US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB,https://track.redtrack.com/click?...&sub11=CAMPAIGN_NAME
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


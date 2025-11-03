"""
TrafficJunky Automation Tool - Main Entry Point

Automates bulk ad creative uploads to TrafficJunky campaigns.
"""

import argparse
import sys
import time
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright

from config import Config
from src.utils import (
    setup_logger,
    print_banner,
    print_success,
    print_error,
    print_warning,
    print_info,
    format_duration
)
from src.auth import TJAuthenticator
from src.uploader import TJUploader
from src.csv_processor import CSVProcessor
from src.campaign_manager import CampaignManager


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='TrafficJunky Automation Tool - Upload ads via CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (default - no actual uploads)
  python main.py
  
  # Live mode (actual uploads)
  python main.py --live
  
  # Process specific campaigns
  python main.py --campaigns 1013017411,1013017412
  
  # Verbose output
  python main.py --verbose
  
  # Headless mode (no browser window)
  python main.py --headless
        """
    )
    
    parser.add_argument(
        '--live',
        action='store_true',
        help='Disable dry-run mode and perform actual uploads (default: dry-run)'
    )
    
    parser.add_argument(
        '--campaigns',
        type=str,
        help='Comma-separated list of campaign IDs to process (overrides mapping file)'
    )
    
    parser.add_argument(
        '--csv',
        type=str,
        help='Path to CSV file (used with --campaigns for single campaign)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose (DEBUG) logging'
    )
    
    parser.add_argument(
        '--no-screenshots',
        action='store_true',
        help='Disable screenshot capture'
    )
    
    return parser.parse_args()


def main():
    """Main execution function."""
    start_time = time.time()
    
    # Parse arguments
    args = parse_arguments()
    
    # Print banner
    print_banner()
    
    # Setup logging
    log_level = 'DEBUG' if args.verbose else Config.LOG_LEVEL
    log_file = Config.LOG_DIR / f"upload_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    logger = setup_logger('main', log_file, log_level, Config.LOG_TO_CONSOLE, Config.LOG_TO_FILE)
    
    logger.info("="*60)
    logger.info("TrafficJunky Automation Tool Started")
    logger.info("="*60)
    
    # Validate configuration
    logger.info("Validating configuration...")
    config_errors = Config.validate()
    if config_errors:
        print_error("Configuration errors:")
        for error in config_errors:
            print_error(f"  - {error}")
        return 1
    
    print_success("Configuration validated")
    
    # Display configuration
    if args.verbose:
        Config.display_config()
    
    # Override config with args
    dry_run = not args.live if args.live else Config.DRY_RUN
    headless = args.headless if args.headless else Config.HEADLESS_MODE
    take_screenshots = not args.no_screenshots
    
    if dry_run:
        print_warning("DRY RUN MODE: Will navigate but NOT actually upload")
    else:
        print_info("LIVE MODE: Will perform actual uploads")
    
    # Initialize campaign manager
    logger.info("Loading campaigns...")
    campaign_manager = CampaignManager(
        mapping_file=Config.CSV_INPUT_DIR / 'campaign_mapping.csv',
        csv_input_dir=Config.CSV_INPUT_DIR
    )
    
    if not campaign_manager.load_campaigns():
        print_error("Failed to load campaigns")
        return 1
    
    if len(campaign_manager.campaigns) == 0:
        print_error("No campaigns found in mapping file")
        return 1
    
    print_success(f"Loaded {len(campaign_manager.campaigns)} campaigns")
    
    # Start browser automation
    logger.info("Starting browser automation...")
    
    try:
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(
                headless=headless,
                slow_mo=Config.SLOW_MO if not headless else 0
            )
            
            print_success("Browser launched")
            
            # Initialize authenticator
            authenticator = TJAuthenticator(Config.TJ_USERNAME, Config.TJ_PASSWORD)
            
            # Try to load saved session first
            context = authenticator.load_session(browser)
            
            if context:
                # Session loaded, verify it's still valid
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
                # Create new context
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080}
                )
                page = context.new_page()
                page.set_default_timeout(Config.TIMEOUT)
                
                # Manual login (user solves reCAPTCHA)
                logger.info("No valid session found, manual login required...")
                print_warning("⚠️  Manual login required - browser window will open")
                
                if not authenticator.manual_login(page, timeout=120):
                    print_error("Authentication failed or timed out")
                    browser.close()
                    return 1
                
                # Save session for future use
                authenticator.save_session(context)
                print_success("Logged into TrafficJunky (session saved)")
            else:
                print_success("Using saved session (no login needed)")
            
            # Initialize uploader
            uploader = TJUploader(
                dry_run=dry_run,
                take_screenshots=take_screenshots
            )
            
            # Process each campaign
            campaign = campaign_manager.get_next_campaign()
            while campaign:
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing campaign: {campaign.campaign_id} ({campaign.campaign_name})")
                logger.info(f"{'='*60}")
                
                # Get CSV path
                csv_path = campaign_manager.get_csv_path(campaign)
                
                # Validate CSV
                is_valid, errors = CSVProcessor.validate_csv(csv_path)
                if not is_valid:
                    error_msg = f"CSV validation failed: {'; '.join(errors)}"
                    campaign_manager.mark_failed(campaign, error_msg)
                    campaign = campaign_manager.get_next_campaign()
                    continue
                
                # Navigate to campaign first to get actual campaign name
                logger.info("Navigating to campaign to get actual name from TJ...")
                if not uploader._navigate_to_campaign(page, campaign.campaign_id):
                    campaign_manager.mark_failed(campaign, "Failed to navigate to campaign")
                    campaign = campaign_manager.get_next_campaign()
                    continue
                
                # Get actual campaign name from TrafficJunky page
                tj_campaign_name = uploader.get_campaign_name_from_page(page)
                if not tj_campaign_name:
                    logger.warning("Could not get campaign name from TJ, using mapping name")
                    tj_campaign_name = campaign.campaign_name
                
                # Update URLs with actual TJ campaign name (sub11 parameter)
                logger.info(f"Updating URLs with TJ campaign name: {tj_campaign_name}")
                csv_path = CSVProcessor.update_campaign_name_in_urls(csv_path, tj_campaign_name)
                
                # Upload (navigation already done above)
                result = uploader.upload_to_campaign(
                    page=page,
                    campaign_id=campaign.campaign_id,
                    csv_path=csv_path,
                    screenshot_dir=Config.SCREENSHOT_DIR,
                    skip_navigation=True  # We already navigated
                )
                
                # Handle result
                if result['status'] == 'success':
                    campaign_manager.mark_success(campaign, result['ads_created'])
                elif result['status'] == 'dry_run_success':
                    campaign_manager.mark_success(campaign, 0)
                elif result.get('invalid_creatives'):
                    # Handle validation errors - clean CSV and retry
                    logger.warning("Attempting to clean CSV and retry...")
                    try:
                        cleaned_csv, removed_rows = CSVProcessor.remove_invalid_creatives(
                            csv_path,
                            result['invalid_creatives']
                        )
                        
                        # Retry with cleaned CSV
                        result = uploader.upload_to_campaign(
                            page=page,
                            campaign_id=campaign.campaign_id,
                            csv_path=cleaned_csv,
                            screenshot_dir=Config.SCREENSHOT_DIR
                        )
                        
                        if result['status'] == 'success':
                            campaign_manager.mark_success(campaign, result['ads_created'])
                            campaign.invalid_creatives = result.get('invalid_creatives', [])
                        else:
                            campaign_manager.mark_failed(
                                campaign,
                                result.get('error', 'Unknown error'),
                                result.get('invalid_creatives', [])
                            )
                    except Exception as e:
                        campaign_manager.mark_failed(campaign, f"Cleanup failed: {e}")
                else:
                    campaign_manager.mark_failed(
                        campaign,
                        result.get('error', 'Unknown error'),
                        result.get('invalid_creatives', [])
                    )
                
                # Get next campaign
                campaign = campaign_manager.get_next_campaign()
            
            # Close browser
            browser.close()
            print_success("Browser closed")
            
    except KeyboardInterrupt:
        print_warning("\nProcess interrupted by user")
        return 130
    except Exception as e:
        logger.exception("Fatal error during execution")
        print_error(f"Fatal error: {e}")
        return 1
    
    # Generate reports
    logger.info("\n" + "="*60)
    logger.info("Generating reports...")
    logger.info("="*60)
    
    summary_report = campaign_manager.generate_summary_report(Config.CSV_OUTPUT_DIR)
    if summary_report:
        print_success(f"Summary report: {summary_report}")
    
    invalid_report = campaign_manager.generate_invalid_creatives_report(Config.CSV_OUTPUT_DIR)
    if invalid_report:
        print_warning(f"Invalid creatives report: {invalid_report}")
    
    # Print summary
    campaign_manager.print_summary()
    
    # Calculate duration
    duration = time.time() - start_time
    logger.info(f"Total execution time: {format_duration(duration)}")
    
    print_success(f"Process completed in {format_duration(duration)}")
    logger.info("="*60)
    logger.info("TrafficJunky Automation Tool Finished")
    logger.info("="*60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())


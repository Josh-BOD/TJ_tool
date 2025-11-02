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
            
            # Create context and page
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            page.set_default_timeout(Config.TIMEOUT)
            
            print_success("Browser launched")
            
            # Authenticate
            logger.info("Authenticating...")
            authenticator = TJAuthenticator(Config.TJ_USERNAME, Config.TJ_PASSWORD)
            
            if not authenticator.login(page):
                print_error("Authentication failed")
                browser.close()
                return 1
            
            print_success("Logged into TrafficJunky")
            
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
                
                # Upload
                result = uploader.upload_to_campaign(
                    page=page,
                    campaign_id=campaign.campaign_id,
                    csv_path=csv_path,
                    screenshot_dir=Config.SCREENSHOT_DIR
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


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
from tqdm import tqdm

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


def cleanup_wip_folder():
    """Prompt user to clean up WIP folder with temporary CSV files."""
    import shutil
    
    # Check if WIP folder has files
    wip_files = list(Config.WIP_DIR.glob('*'))
    if not wip_files:
        return
    
    print("\n" + "="*60)
    print_info(f"WIP Folder Cleanup")
    print("="*60)
    print_info(f"Found {len(wip_files)} temporary file(s) in: {Config.WIP_DIR}")
    print_info("These are modified CSV files created during the upload process.")
    print("")
    
    # Show first few files as examples
    for f in wip_files[:5]:
        print(f"  - {f.name}")
    if len(wip_files) > 5:
        print(f"  ... and {len(wip_files) - 5} more")
    
    print("")
    
    # Check if stdin is available (not running in background)
    import sys
    if sys.stdin.isatty():
        response = input("Do you want to delete these temporary files? [y/N]: ").strip().lower()
        
        if response == 'y':
            try:
                shutil.rmtree(Config.WIP_DIR)
                Config.WIP_DIR.mkdir(parents=True, exist_ok=True)
                print_success(f"✓ Cleaned up {len(wip_files)} file(s) from WIP folder")
            except Exception as e:
                print_error(f"Failed to clean up WIP folder: {e}")
        else:
            print_info("Skipped cleanup - files remain in WIP folder")
    else:
        # Running in background or stdin not available
        print_info("ℹ Running in background mode - skipping cleanup prompt")
        print_info("ℹ You can manually delete files from data/wip/ or run the tool again in foreground")
    
    print("="*60 + "\n")


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
  
  # Resume from previous interrupted session
  python main.py --live
  
  # Start fresh (ignore previous checkpoint)
  python main.py --live --fresh
  
  # Retry previously failed campaigns
  python main.py --live --retry-failed
  
  # Process specific campaigns
  python main.py --campaigns 1013017411,1013017412
  
  # Verbose output
  python main.py --verbose
  
  # Headless mode (no browser window)
  python main.py --headless

Checkpoint/Resume:
  By default, the tool saves progress after each campaign. If interrupted,
  simply run the tool again and it will resume where it left off, skipping
  campaigns that were already successful.
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
    
    parser.add_argument(
        '--fresh',
        action='store_true',
        help='Start fresh, ignore any existing checkpoint (default: resume from checkpoint)'
    )
    
    parser.add_argument(
        '--retry-failed',
        action='store_true',
        help='Retry previously failed campaigns'
    )
    
    return parser.parse_args()


def main():
    """Main execution function."""
    start_time = time.time()
    
    # Parse arguments
    args = parse_arguments()
    
    # Check if checkpoint exists (before deleting session)
    checkpoint_exists = (Config.BASE_DIR / 'data' / 'session' / 'upload_checkpoint.json').exists()
    
    # Delete old session to force fresh login (but not if resuming from checkpoint)
    if args.fresh or not checkpoint_exists:
        try:
            session_file = Config.BASE_DIR / 'data' / 'session' / 'tj_session.json'
            if session_file.exists():
                session_file.unlink()
                print("🔄 Deleted old session - fresh login required")
        except Exception as e:
            print(f"⚠️  Could not delete old session: {e}")
    else:
        print("📋 Resuming from checkpoint - keeping existing session")
    
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
    checkpoint_file = Config.BASE_DIR / 'data' / 'session' / 'upload_checkpoint.json'
    campaign_manager = CampaignManager(
        mapping_file=Config.CSV_INPUT_DIR / 'campaign_mapping.csv',
        csv_input_dir=Config.CSV_INPUT_DIR,
        checkpoint_file=checkpoint_file
    )
    
    if not campaign_manager.load_campaigns():
        print_error("Failed to load campaigns")
        return 1
    
    if len(campaign_manager.campaigns) == 0:
        print_error("No campaigns found in mapping file")
        return 1
    
    print_success(f"Loaded {len(campaign_manager.campaigns)} campaigns")
    
    # Handle checkpoint
    session_id = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if args.fresh:
        campaign_manager.clear_checkpoint()
        print_warning("Starting fresh - cleared previous checkpoint")
    
    # Initialize checkpoint (will resume if checkpoint exists)
    campaign_manager.initialize_checkpoint(session_id, use_existing=not args.fresh)
    
    # Set retry failed flag
    if args.retry_failed:
        campaign_manager.set_retry_failed(True)
    
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
            
            # ALWAYS do a fresh manual login (don't use saved sessions)
            print_warning("⚠️  Manual login required - browser window will open")
            logger.info("Starting fresh login session...")
                # Create new context
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            page.set_default_timeout(Config.TIMEOUT)
            
            # Manual login (user solves reCAPTCHA)
            if not authenticator.manual_login(page, timeout=120):
                print_error("Authentication failed or timed out")
                browser.close()
                return 1
            
            print_success("Logged into TrafficJunky")
            
            # Initialize uploader
            uploader = TJUploader(
                dry_run=dry_run,
                take_screenshots=take_screenshots
            )
            
            # Initialize progress tracking
            campaign_manager.start_tracking()
            
            # Get enabled campaigns for progress bar
            enabled_campaigns = [c for c in campaign_manager.campaigns if c.enabled]
            total_campaigns = len(enabled_campaigns)
            
            logger.info(f"Starting upload of {total_campaigns} campaigns...")
            
            # Create progress bar
            with tqdm(
                total=total_campaigns,
                desc="Uploading campaigns",
                unit="campaign",
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
                ncols=100
            ) as pbar:
                
                # Process each campaign
                campaign = campaign_manager.get_next_campaign()
                while campaign:
                    campaign_start = time.time()
                    
                    # Update progress bar description with current campaign
                    campaign_display = campaign.campaign_name[:20] if campaign.campaign_name else campaign.campaign_id[:10]
                    pbar.set_description(f"Processing {campaign_display}")
                    
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
                        
                        # Record time and update progress
                        campaign_duration = time.time() - campaign_start
                        campaign_manager.record_campaign_time(campaign_duration)
                        stats = campaign_manager.get_progress_stats()
                        pbar.set_postfix({
                            'speed': f"{stats['speed_cpm']:.1f} c/m",
                            'eta': f"{int(stats['eta_seconds']//60)}m {int(stats['eta_seconds']%60)}s" if stats['eta_seconds'] > 0 else "calculating...",
                            'remaining': stats['remaining']
                        })
                        pbar.update(1)
                        
                        campaign = campaign_manager.get_next_campaign()
                        continue
                    
                    # Navigate to campaign first to get actual campaign name
                    logger.info("Navigating to campaign to get actual name from TJ...")
                    if not uploader._navigate_to_campaign(page, campaign.campaign_id):
                        campaign_manager.mark_failed(campaign, "Failed to navigate to campaign")
                        
                        # Record time and update progress
                        campaign_duration = time.time() - campaign_start
                        campaign_manager.record_campaign_time(campaign_duration)
                        stats = campaign_manager.get_progress_stats()
                        pbar.set_postfix({
                            'speed': f"{stats['speed_cpm']:.1f} c/m",
                            'eta': f"{int(stats['eta_seconds']//60)}m {int(stats['eta_seconds']%60)}s" if stats['eta_seconds'] > 0 else "calculating...",
                            'remaining': stats['remaining']
                        })
                        pbar.update(1)
                        
                        campaign = campaign_manager.get_next_campaign()
                        continue
                    
                    # Get actual campaign name from TrafficJunky page
                    tj_campaign_name = uploader.get_campaign_name_from_page(page)
                    if not tj_campaign_name:
                        logger.warning("Could not get campaign name from TJ, using mapping name")
                        tj_campaign_name = campaign.campaign_name
                    
                    # Update campaign object with actual TJ name for reporting
                    campaign.campaign_name = tj_campaign_name
                    
                    # Update URLs with actual TJ campaign name (sub11 parameter)
                    logger.info(f"Updating URLs with TJ campaign name: {tj_campaign_name}")
                    csv_path = CSVProcessor.update_campaign_name_in_urls(csv_path, tj_campaign_name, Config.WIP_DIR)
                    
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
                    
                    # Record time and update progress
                    campaign_duration = time.time() - campaign_start
                    campaign_manager.record_campaign_time(campaign_duration)
                    
                    # Get stats for custom postfix
                    stats = campaign_manager.get_progress_stats()
                    
                    # Update progress bar with ETA
                    pbar.set_postfix({
                        'speed': f"{stats['speed_cpm']:.1f} c/m",
                        'eta': f"{int(stats['eta_seconds']//60)}m {int(stats['eta_seconds']%60)}s" if stats['eta_seconds'] > 0 else "calculating...",
                        'remaining': stats['remaining']
                    })
                    pbar.update(1)
                    
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
    
    # Offer to clean up WIP folder
    cleanup_wip_folder()
    
    logger.info("="*60)
    logger.info("TrafficJunky Automation Tool Finished")
    logger.info("="*60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())


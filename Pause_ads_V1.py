#!/usr/bin/env python3
"""
Pause_ads_V1.py - Mass Ad Pausing Tool

Pauses specific Creative IDs across multiple TrafficJunky campaigns.
Uses browser automation with the same authentication as V2 campaign creation.

Usage:
    # Dry run (preview only, don't actually pause)
    python Pause_ads_V1.py --creatives data/input/black_friday_creatives.csv \\
                           --campaigns data/input/all_campaigns.csv \\
                           --dry-run

    # Actually pause ads
    python Pause_ads_V1.py --creatives data/input/black_friday_creatives.csv \\
                           --campaigns data/input/all_campaigns.csv

    # With screenshots for debugging
    python Pause_ads_V1.py --creatives data/input/black_friday_creatives.csv \\
                           --campaigns data/input/all_campaigns.csv \\
                           --screenshots
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.sync_api import sync_playwright
from config import Config
from auth import TJAuthenticator
from ad_pauser import (
    parse_creative_ids_csv,
    parse_campaign_ids_csv,
    AdPauser,
    generate_pause_report,
    PauseBatch,
)
from ad_pauser.reporter import print_summary_to_console

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/pause_ads_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Mass Ad Pausing Tool - Pause specific Creative IDs across campaigns',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (preview only)
  %(prog)s --creatives creatives.csv --campaigns campaigns.csv --dry-run

  # Actually pause ads
  %(prog)s --creatives creatives.csv --campaigns campaigns.csv

  # With screenshots
  %(prog)s --creatives creatives.csv --campaigns campaigns.csv --screenshots
        """
    )
    
    parser.add_argument(
        '--creatives',
        required=True,
        type=Path,
        help='Path to Creative IDs CSV file (required column: Creative ID)'
    )
    
    parser.add_argument(
        '--campaigns',
        required=True,
        type=Path,
        help='Path to Campaign IDs CSV file (required column: Campaign ID)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview mode - show what would be paused without actually pausing'
    )
    
    parser.add_argument(
        '--screenshots',
        action='store_true',
        help='Take screenshots during the pausing process (saved to data/screenshots/)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (no visible window)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()
    
    print("="*70)
    print("PAUSE ADS V1 - MASS AD PAUSING TOOL")
    print("="*70)
    
    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No ads will actually be paused")
    
    print(f"\nCreative IDs CSV: {args.creatives}")
    print(f"Campaign IDs CSV: {args.campaigns}")
    
    # Validate CSV files exist
    if not args.creatives.exists():
        print(f"\n✗ Error: Creative IDs CSV not found: {args.creatives}")
        return 1
    
    if not args.campaigns.exists():
        print(f"\n✗ Error: Campaign IDs CSV not found: {args.campaigns}")
        return 1
    
    try:
        # Parse CSVs
        print(f"\nParsing CSV files...")
        creative_ids = parse_creative_ids_csv(args.creatives)
        campaign_list = parse_campaign_ids_csv(args.campaigns)
        
        print(f"✓ Loaded {len(creative_ids)} Creative IDs")
        print(f"✓ Loaded {len(campaign_list)} Campaign IDs")
        
        if len(creative_ids) == 0:
            print("\n✗ Error: No Creative IDs found in CSV")
            return 1
        
        if len(campaign_list) == 0:
            print("\n✗ Error: No Campaign IDs found in CSV")
            return 1
        
        # Initialize batch
        batch = PauseBatch(
            creative_ids=creative_ids,
            campaign_ids=[c['id'] for c in campaign_list],
            results=[],
            dry_run=args.dry_run,
            start_time=datetime.now()
        )
        
        # Start browser & authenticate
        print("\n" + "="*70)
        print("BROWSER AUTHENTICATION")
        print("="*70)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=args.headless,
                slow_mo=100  # Slow down for stability
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = context.new_page()
            page.set_default_timeout(30000)
            
            # Login (same as V2 campaign creation)
            authenticator = TJAuthenticator(Config.TJ_USERNAME, Config.TJ_PASSWORD)
            
            print("\nLogging in (solve reCAPTCHA manually if prompted)...")
            if not authenticator.manual_login(page, timeout=180):
                print("\n✗ Login failed!")
                browser.close()
                return 1
            
            authenticator.save_session(context)
            print("✓ Logged in successfully")
            
            # Initialize pauser
            screenshot_dir = Config.SCREENSHOT_DIR if args.screenshots else None
            pauser = AdPauser(
                page=page,
                dry_run=args.dry_run,
                take_screenshots=args.screenshots,
                screenshot_dir=screenshot_dir
            )
            
            # Process each campaign
            print("\n" + "="*70)
            print("PROCESSING CAMPAIGNS")
            print("="*70)
            
            for i, campaign in enumerate(campaign_list, 1):
                campaign_id = campaign['id']
                campaign_name = campaign.get('name', campaign_id)
                
                print(f"\n[{i}/{len(campaign_list)}] Processing: {campaign_name}")
                print(f"Campaign ID: {campaign_id}")
                
                # Pause ads in this campaign
                result = pauser.pause_ads_in_campaign(
                    campaign_id=campaign_id,
                    creative_ids=creative_ids,
                    campaign_name=campaign_name
                )
                
                batch.results.append(result)
                
                # Print immediate summary
                if result.status == 'success':
                    print(f"  ✓ SUCCESS - Paused {len(result.ads_paused)}/{len(creative_ids)} ads")
                elif result.status == 'partial':
                    print(f"  ⚠ PARTIAL - Paused {len(result.ads_paused)}/{len(result.ads_found)} ads")
                    print(f"  Note: {len(result.ads_not_found)} Creative IDs not found in this campaign")
                else:
                    print(f"  ✗ FAILED - {result.errors[0] if result.errors else 'Unknown error'}")
                
                print(f"  Time: {result.time_taken:.1f}s | Pages: {result.pages_processed}")
            
            browser.close()
        
        # Mark batch end time
        batch.end_time = datetime.now()
        
        # Generate report
        print("\n" + "="*70)
        print("GENERATING REPORT")
        print("="*70)
        
        # Save reports to Ad_Pause subfolder
        ad_pause_reports_dir = Config.REPORT_OUTPUT_DIR / "Ad_Pause"
        ad_pause_reports_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = generate_pause_report(batch, ad_pause_reports_dir)
        print(f"\n✓ Report saved to: {report_path}")
        
        # Print console summary
        print_summary_to_console(batch)
        
        # Return success if at least some ads were paused
        if batch.total_ads_paused > 0:
            return 0
        else:
            print("\n⚠️  Warning: No ads were paused")
            return 1
    
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        return 130
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.exception("Exception details:")
        print(f"\n✗ Error: {e}")
        return 1


if __name__ == "__main__":
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    # Run main
    sys.exit(main() or 0)


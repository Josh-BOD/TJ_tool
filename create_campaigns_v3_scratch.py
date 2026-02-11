#!/usr/bin/env python3
"""
Campaign Creation Tool V3 - From Scratch (Single Worker)

Creates campaigns from scratch instead of cloning from templates.
This allows full control over first-page settings like:
- Labels
- Device (All/Desktop/Mobile)
- Ad Format (Display/In-Stream Video/Pop)
- Format Type (Banner/Native)
- Ad Type (Static Banner/Video Banner/Rollover)
- Ad Dimensions
- Content Category (Straight/Gay/Trans)

Input folder: data/input/Blank_Campaign_Creation/
Output folder: data/output/Blank_Campaign_Creation/

Usage:
    python create_campaigns_v3_scratch.py <csv_file>
    python create_campaigns_v3_scratch.py data/input/Blank_Campaign_Creation/my_campaigns.csv
    
    # Dry run (validate CSV without creating campaigns)
    python create_campaigns_v3_scratch.py <csv_file> --dry-run
"""

import sys
import os
import time
import csv
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.sync_api import sync_playwright

from config import Config
from auth import TJAuthenticator
from campaign_automation_v2.csv_parser import parse_csv, CSVParseError
from campaign_automation_v2.validator import validate_batch
from campaign_automation_v2.models import CampaignBatch, CampaignDefinition
from campaign_automation_v2.creator_sync import CampaignCreator
from campaign_templates import generate_campaign_name, DEFAULT_SETTINGS
from native_uploader import NativeUploader
from uploader import TJUploader

# Default paths
INPUT_DIR = Path(__file__).parent / "data" / "input" / "Blank_Campaign_Creation"
OUTPUT_DIR = Path(__file__).parent / "data" / "output" / "Blank_Campaign_Creation"
# Ad CSVs are now in the same folder as campaign definition CSVs

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - [V3] %(message)s'
)
logger = logging.getLogger(__name__)


def upload_csv_to_campaign(page, csv_path: Path, campaign_name: str, ad_format: str = "NATIVE"):
    """Upload CSV file to create ads in campaign using proper uploader."""
    try:
        # Use the appropriate uploader based on ad format
        if ad_format.upper() == "NATIVE":
            uploader = NativeUploader(dry_run=False)
            result = uploader.upload_to_campaign(
                page=page,
                campaign_id="current",  # Already on campaign page
                csv_path=csv_path,
                campaign_name=campaign_name,
                skip_navigation=True  # Already on ads page
            )
        else:
            # INSTREAM uses TJUploader
            uploader = TJUploader(dry_run=False)
            result = uploader.upload_to_campaign(
                page=page,
                campaign_id="current",
                csv_path=csv_path,
                campaign_name=campaign_name,
                skip_navigation=True
            )
        
        if result.get('status') == 'success':
            ads_created = result.get('ads_created', 0)
            logger.info(f"✓ CSV uploaded successfully - {ads_created} ads created")
            return True
        else:
            error = result.get('error', 'Unknown error')
            logger.error(f"✗ CSV upload failed: {error}")
            return False
        
    except Exception as e:
        logger.error(f"✗ CSV upload failed: {e}")
        return False


def create_campaign_from_scratch(page, campaign: CampaignDefinition, csv_dir: Path):
    """
    Create campaign(s) from scratch for all variants.
    
    Unlike V2 which clones from templates, V3 creates campaigns from scratch
    giving full control over all first-page settings.
    """
    ad_format = campaign.settings.ad_format
    content_category = campaign.settings.content_category
    creator = CampaignCreator(page, ad_format=ad_format, content_category=content_category)
    
    csv_path = csv_dir / campaign.csv_file
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return []
    
    created_campaigns = []
    
    for variant in campaign.variants:
        # Skip Android if mobile_combined (iOS campaign handles both)
        if campaign.mobile_combined and variant == "android":
            logger.info(f"  Skipping {variant} (mobile_combined mode - iOS handles both)")
            continue
        
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Creating from scratch: {campaign.group} - {variant.upper()}")
            logger.info(f"{'='*60}")
            
            # Create campaign from scratch
            campaign_id, campaign_name = creator.create_campaign_from_scratch(
                campaign=campaign,
                device_variant=variant
            )
            
            logger.info(f"✓ Created campaign: {campaign_name}")
            logger.info(f"  ID: {campaign_id}")
            
            # Upload CSV with campaign name for tracking URL replacement
            upload_csv_to_campaign(page, csv_path, campaign_name, ad_format)
            
            created_campaigns.append((campaign_id, campaign_name, variant))
            
        except Exception as e:
            logger.error(f"✗ Failed to create {variant} campaign: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return created_campaigns


def save_report(results: list, csv_path: Path, total_created: int, total_failed: int):
    """Save a CSV report of created campaigns to the output folder."""
    # Create output directory if it doesn't exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate report filename based on input file and timestamp
    input_name = csv_path.stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = OUTPUT_DIR / f"{input_name}_report_{timestamp}.csv"
    
    try:
        with open(report_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(['Campaign ID', 'Campaign Name', 'Variant', 'Status'])
            
            # Results
            for campaign_id, campaign_name, variant in results:
                writer.writerow([campaign_id, campaign_name, variant, 'Created'])
        
        logger.info(f"✓ Report saved to: {report_path}")
        return report_path
        
    except Exception as e:
        logger.error(f"Failed to save report: {e}")
        return None


def validate_csv_only(csv_path: Path):
    """Validate CSV file without creating campaigns (dry run)."""
    logger.info(f"Validating CSV: {csv_path}")
    logger.info("=" * 60)
    
    try:
        batch = parse_csv(csv_path)
        enabled = batch.enabled_campaigns
        
        logger.info(f"✓ CSV parsed successfully")
        logger.info(f"  Total rows: {batch.total_campaigns}")
        logger.info(f"  Enabled campaigns: {len(enabled)}")
        logger.info(f"  Total variants to create: {batch.total_variants}")
        logger.info("")
        
        # Show summary of each campaign
        for i, campaign in enumerate(enabled, 1):
            settings = campaign.settings
            logger.info(f"Campaign {i}: {campaign.group}")
            logger.info(f"  Keywords: {', '.join([k.name for k in campaign.keywords])}")
            logger.info(f"  Geo: {', '.join(campaign.geo)}")
            logger.info(f"  Variants: {', '.join(campaign.variants)}")
            logger.info(f"  CSV File: {campaign.csv_file}")
            logger.info(f"  V3 Settings:")
            logger.info(f"    - Device: {settings.device}")
            logger.info(f"    - Ad Format Type: {settings.ad_format_type}")
            logger.info(f"    - Format Type: {settings.format_type}")
            logger.info(f"    - Ad Type: {settings.ad_type}")
            logger.info(f"    - Ad Dimensions: {settings.ad_dimensions}")
            logger.info(f"    - Content Category: {settings.content_category}")
            logger.info(f"    - Labels: {settings.labels if settings.labels else '(none)'}")
            logger.info(f"    - Gender: {settings.gender}")
            logger.info("")
        
        logger.info("=" * 60)
        logger.info("✓ Dry run complete - CSV is valid")
        return True
        
    except CSVParseError as e:
        logger.error(f"✗ CSV parse error: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_v3(csv_path: Path, dry_run: bool = False, headless: bool = False, slow_mo: int = 500):
    """Main runner for V3 from-scratch campaign creation."""
    logger.info("=" * 60)
    logger.info("Campaign Creation V3 - From Scratch")
    logger.info("=" * 60)
    logger.info(f"CSV File: {csv_path}")
    
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return
    
    # Dry run mode - just validate
    if dry_run:
        validate_csv_only(csv_path)
        return
    
    # Parse CSV
    try:
        batch = parse_csv(csv_path)
        enabled = batch.enabled_campaigns
    except CSVParseError as e:
        logger.error(f"CSV parse error: {e}")
        return
    
    if not enabled:
        logger.warning("No enabled campaigns found in CSV")
        return
    
    logger.info(f"Found {len(enabled)} enabled campaigns")
    logger.info(f"Total variants to create: {batch.total_variants}")
    
    # Ad CSVs are in the same folder as the campaign definition CSV
    csv_dir = csv_path.parent
    logger.info(f"Looking for ad CSVs in: {csv_dir}")
    
    # Launch browser & authenticate
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            slow_mo=slow_mo
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = context.new_page()
        page.set_default_timeout(30000)
        
        # Login using TJAuthenticator
        authenticator = TJAuthenticator(Config.TJ_USERNAME, Config.TJ_PASSWORD)
        
        logger.info("Logging in (solve reCAPTCHA manually if prompted)...")
        if not authenticator.manual_login(page, timeout=180):
            logger.error("Login failed!")
            browser.close()
            return
        
        authenticator.save_session(context)
        logger.info("✓ Logged in successfully")
        
        # Track results
        total_created = 0
        total_failed = 0
        results = []
        
        # Process each campaign
        for i, campaign in enumerate(enabled, 1):
            logger.info(f"\n{'#'*60}")
            logger.info(f"Processing {i}/{len(enabled)}: {campaign.group}")
            logger.info(f"  Keywords: {campaign.primary_keyword}")
            logger.info(f"  Variants: {', '.join(campaign.variants)}")
            logger.info(f"{'#'*60}")
            
            try:
                created = create_campaign_from_scratch(page, campaign, csv_dir)
                total_created += len(created)
                results.extend(created)
                
            except Exception as e:
                logger.error(f"Error with {campaign.group}: {e}")
                import traceback
                traceback.print_exc()
                total_failed += 1
                continue
        
        browser.close()
    
    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Campaigns created: {total_created}")
    logger.info(f"Campaigns failed: {total_failed}")
    
    if results:
        logger.info("\nCreated campaigns:")
        for campaign_id, campaign_name, variant in results:
            logger.info(f"  [{variant}] {campaign_name} (ID: {campaign_id})")
        
        # Save report to output folder
        save_report(results, csv_path, total_created, total_failed)
    
    logger.info("\n✓ V3 Campaign creation complete!")


def main():
    """Parse arguments and run."""
    parser = argparse.ArgumentParser(
        description='Create TrafficJunky campaigns from scratch (V3)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_campaigns_v3_scratch.py data/input/Blank_Campaign_Creation/my_campaigns.csv
  python create_campaigns_v3_scratch.py data/input/Blank_Campaign_Creation/test.csv --dry-run

Input:  data/input/Blank_Campaign_Creation/
Output: data/output/Blank_Campaign_Creation/
        """
    )
    
    parser.add_argument(
        'csv_file',
        type=str,
        help='Path to CSV file with campaign definitions'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate CSV without creating campaigns'
    )

    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode'
    )

    parser.add_argument(
        '--slow-mo',
        type=int,
        default=500,
        help='Slow motion delay in ms (default: 500)'
    )

    args = parser.parse_args()

    csv_path = Path(args.csv_file)
    run_v3(csv_path, dry_run=args.dry_run, headless=args.headless, slow_mo=args.slow_mo)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Campaign Creation Tool V2 - SYNC Version for Parallel Workers

This script is used by run_parallel_launcher.py to run multiple browser instances.
Uses the same authentication pattern as Pause_ads_V1.py (manual login per worker).
"""

import sys
import os
import time
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
from campaign_templates import generate_campaign_name, DEFAULT_SETTINGS, get_templates_for_format
from native_uploader import NativeUploader
from uploader import TJUploader

# Setup logging
worker_id = os.environ.get('WORKER_ID', '1')
logging.basicConfig(
    level=logging.INFO, 
    format=f'%(asctime)s - [Worker {worker_id}] %(message)s'
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


def create_campaign_set(page, campaign: CampaignDefinition, csv_dir: Path):
    """Create all variants for a campaign definition."""
    ad_format = campaign.settings.ad_format
    campaign_type = campaign.settings.campaign_type
    content_category = campaign.settings.content_category
    creator = CampaignCreator(page, ad_format=ad_format, campaign_type=campaign_type, content_category=content_category)
    
    csv_path = csv_dir / campaign.csv_file
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return
    
    geo = campaign.geo[0] if campaign.geo else "US"
    created_campaigns = []
    
    for variant in campaign.variants:
        # Skip Android if mobile_combined and not using all_mobile variant (iOS campaign handles both)
        if campaign.mobile_combined and variant == "android" and "all_mobile" not in campaign.variants:
            continue
        
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Creating: {campaign.group} - {variant.upper()}")
            logger.info(f"{'='*60}")
            
            if variant == "desktop":
                campaign_id, campaign_name = creator.create_desktop_campaign(campaign, geo)
            elif variant == "all_mobile":
                # Use dedicated all_mobile template (mainly for remarketing)
                campaign_id, campaign_name = creator.create_all_mobile_campaign(campaign, geo)
            elif variant == "ios":
                campaign_id, campaign_name = creator.create_ios_campaign(campaign, geo)
            elif variant == "android":
                # Clone from iOS campaign if we have one
                ios_id = next((c[0] for c in created_campaigns if "ios" in c[1].lower()), None)
                if ios_id:
                    campaign_id, campaign_name = creator.create_android_campaign(campaign, geo, ios_id)
                else:
                    logger.warning("No iOS campaign to clone from for Android")
                    continue
            else:
                logger.warning(f"Unknown variant: {variant}")
                continue
            
            logger.info(f"✓ Created campaign: {campaign_name}")
            logger.info(f"  ID: {campaign_id}")
            
            # Upload CSV — don't replace sub11, TJ fills {CampaignName} dynamically
            upload_csv_to_campaign(page, csv_path, None, ad_format)
            
            created_campaigns.append((campaign_id, campaign_name))
            
        except Exception as e:
            logger.error(f"✗ Failed to create {variant} campaign: {e}")
            continue
    
    return created_campaigns


def run_sync():
    """Main sync runner — accepts --input or falls back to temp batch file for parallel launcher."""
    parser = argparse.ArgumentParser(description="Campaign Creation V2 Sync")
    parser.add_argument("--input", type=str, help="Path to campaign CSV file")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't create campaigns")
    parser.add_argument("--no-headless", action="store_true", default=True, help="Show browser (default)")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--slow-mo", type=int, default=500, help="Slow motion delay in ms")
    # Parallel worker args
    parser.add_argument("--window-position", type=str, help="Chromium window position as X,Y (e.g. '0,0')")
    parser.add_argument("--window-size", type=str, help="Chromium window size as W,H (e.g. '960,540')")
    parser.add_argument("--use-session", action="store_true", help="Load saved session instead of manual login")
    parser.add_argument("--session-file", type=str, default="data/session/tj_session.json", help="Path to session JSON file")
    args = parser.parse_args()

    # Determine input file: --input flag takes priority, else temp batch file
    if args.input:
        input_file = Path(args.input)
    else:
        worker_id = os.environ.get('WORKER_ID', '1')
        input_file = Path(f"data/temp/temp_batch_{worker_id}.csv")

    logger.info(f"Starting...")
    logger.info(f"Using CSV: {input_file}")

    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        return

    # Parse CSV
    batch = parse_csv(input_file)
    enabled = batch.enabled_campaigns

    logger.info(f"Found {len(enabled)} enabled campaigns")

    if args.dry_run:
        logger.info("\n=== DRY RUN — previewing campaigns ===")
        for i, campaign in enumerate(enabled, 1):
            ad_format = campaign.settings.ad_format
            campaign_type = campaign.settings.campaign_type
            content_category = campaign.settings.content_category
            lang = campaign.settings.language
            geo = campaign.geo[0] if campaign.geo else "US"
            csv_file = campaign.csv_file
            logger.info(f"  {i}. [{content_category}] {geo}_{lang}_{ad_format}_{campaign.settings.bid_type}_{campaign_type} — variants: {campaign.variants}")
            logger.info(f"     group: {campaign.group} | csv: {csv_file}")
        logger.info(f"\nTotal: {len(enabled)} campaigns")
        return

    # Resolve csv_dir: use input file's parent directory so relative csv_file paths work
    csv_dir = input_file.parent
    
    # Launch browser & authenticate (same pattern as Pause_ads_V1.py)
    with sync_playwright() as p:
        # Build Chromium args for window positioning (parallel workers)
        chromium_args = []
        if args.window_position:
            chromium_args.append(f'--window-position={args.window_position}')
        if args.window_size:
            chromium_args.append(f'--window-size={args.window_size}')

        browser = p.chromium.launch(
            headless=args.headless,
            slow_mo=args.slow_mo,
            args=chromium_args if chromium_args else None,
        )

        # Derive viewport from window size (subtract ~80px for chrome UI)
        vp_w, vp_h = 1920, 1080
        if args.window_size:
            parts = args.window_size.split(',')
            vp_w, vp_h = int(parts[0]), int(parts[1]) - 80

        context_kwargs = {'viewport': {'width': vp_w, 'height': vp_h}}
        if args.use_session and Path(args.session_file).exists():
            context_kwargs['storage_state'] = args.session_file
        context = browser.new_context(**context_kwargs)

        page = context.new_page()
        page.set_default_timeout(30000)

        # Login using TJAuthenticator (solve CAPTCHA manually if prompted)
        authenticator = TJAuthenticator(Config.TJ_USERNAME, Config.TJ_PASSWORD)

        if args.use_session:
            # Try loading session — fall back to manual login if expired
            page.goto('https://advertiser.trafficjunky.com/', wait_until='domcontentloaded')
            page.wait_for_timeout(3000)
            if authenticator.is_logged_in(page):
                logger.info("✓ Session loaded successfully")
            else:
                logger.warning("Session expired, falling back to manual login...")
                if not authenticator.manual_login(page, timeout=180):
                    logger.error("Login failed!")
                    browser.close()
                    return
                authenticator.save_session(context)
        else:
            logger.info("Logging in (solve reCAPTCHA manually if prompted)...")
            if not authenticator.manual_login(page, timeout=180):
                logger.error("Login failed!")
                browser.close()
                return
            authenticator.save_session(context)
        logger.info("✓ Logged in successfully")
        
        # Process each campaign
        for i, campaign in enumerate(enabled, 1):
            logger.info(f"Processing {i}/{len(enabled)}: {campaign.group} - {campaign.keywords[0].name if campaign.keywords else 'N/A'}")
            
            try:
                create_campaign_set(page, campaign, csv_dir)
            except Exception as e:
                logger.error(f"Error with {campaign.group}: {e}")
                continue
        
        browser.close()
    
    logger.info(f"✓ Complete!")


if __name__ == "__main__":
    run_sync()


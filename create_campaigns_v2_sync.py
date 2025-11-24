#!/usr/bin/env python3
"""
Campaign Creation Tool V2 - SYNC version that actually works!

Uses SYNC playwright like native_main.py.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.sync_api import sync_playwright
from config import Config
from auth import TJAuthenticator
from campaign_automation_v2.csv_parser import parse_csv
from campaign_automation_v2.creator_sync import CampaignCreator
from native_uploader import NativeUploader
from uploader import TJUploader

def main():
    input_file = Path("data/input/ExoCampaignUpload_V2.csv")
    
    print("="*65)
    print("CAMPAIGN CREATION V2 - SYNC VERSION")
    print("="*65)
    
    # Parse campaigns
    print(f"\nParsing {input_file}...")
    batch = parse_csv(input_file)
    print(f"✓ Found {len(batch.campaigns)} campaigns")
    
    # Start browser
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)  # Always visible
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        page.set_default_timeout(30000)
        
        # Auto login with credentials (gives you time for reCAPTCHA)
        authenticator = TJAuthenticator(Config.TJ_USERNAME, Config.TJ_PASSWORD)
        print("Logging in (solve reCAPTCHA if needed)...")
        if not authenticator.login(page):
            print("✗ Login failed!")
            browser.close()
            return 1
        
        authenticator.save_session(context)
        print("✓ Logged in")
        
        # Create campaigns and upload ads
        # Initialize uploaders
        native_uploader = NativeUploader(dry_run=False, take_screenshots=False)
        instream_uploader = TJUploader(dry_run=False, take_screenshots=False)
        
        # Track results
        results = {'success': [], 'failed': []}
        
        for i, campaign in enumerate(batch.campaigns, 1):
            if not campaign.is_enabled:
                continue
            
            print(f"\n[{i}/{len(batch.campaigns)}] Processing: {campaign.group} ({campaign.settings.ad_format})")
            
            try:
                # Create campaign creator with correct ad_format for this campaign
                creator = CampaignCreator(page, ad_format=campaign.settings.ad_format)
                
                geo = campaign.geo[0] if campaign.geo else "US"
                
                # Choose uploader based on ad format
                uploader = native_uploader if campaign.settings.ad_format.upper() == "NATIVE" else instream_uploader
                
                # Get CSV path
                csv_path = Config.CSV_INPUT_DIR / campaign.csv_file if campaign.csv_file else None
                
                # Track iOS campaign ID for Android cloning
                ios_campaign_id = None
                variants_created = []
                
                for variant in campaign.variants:
                    try:
                        if variant == "desktop":
                            campaign_id, campaign_name = creator.create_desktop_campaign(campaign, geo)
                            
                            # Upload ads immediately
                            if csv_path and csv_path.exists():
                                print(f"  → Uploading ads to campaign {campaign_id}...")
                                result = uploader.upload_to_campaign(
                                    page=page,
                                    campaign_id=campaign_id,
                                    csv_path=csv_path,
                                    campaign_name=campaign_name,
                                    screenshot_dir=Config.SCREENSHOT_DIR
                                )
                                
                                if result['status'] == 'success':
                                    ads = result.get('ads_created', 0)
                                    print(f"    ✓ Uploaded {ads} ads")
                                    variants_created.append(f"Desktop ({ads} ads)")
                                else:
                                    print(f"    ✗ Upload failed: {result.get('error', 'Unknown error')}")
                                    variants_created.append(f"Desktop (upload failed)")
                            
                        elif variant == "ios":
                            campaign_id, campaign_name = creator.create_ios_campaign(campaign, geo)
                            ios_campaign_id = campaign_id  # Save for Android cloning
                            
                            # Upload ads immediately
                            if csv_path and csv_path.exists():
                                print(f"  → Uploading ads to campaign {campaign_id}...")
                                result = uploader.upload_to_campaign(
                                    page=page,
                                    campaign_id=campaign_id,
                                    csv_path=csv_path,
                                    campaign_name=campaign_name,
                                    screenshot_dir=Config.SCREENSHOT_DIR
                                )
                                
                                if result['status'] == 'success':
                                    ads = result.get('ads_created', 0)
                                    print(f"    ✓ Uploaded {ads} ads")
                                    variants_created.append(f"iOS ({ads} ads)")
                                else:
                                    print(f"    ✗ Upload failed: {result.get('error', 'Unknown error')}")
                                    variants_created.append(f"iOS (upload failed)")
                        
                        elif variant == "android":
                            if not ios_campaign_id:
                                print(f"    ⚠ Skipping Android - no iOS campaign to clone from")
                                continue
                            
                            campaign_id, campaign_name = creator.create_android_campaign(campaign, geo, ios_campaign_id)
                            
                            # Upload ads immediately
                            if csv_path and csv_path.exists():
                                print(f"  → Uploading ads to campaign {campaign_id}...")
                                result = uploader.upload_to_campaign(
                                    page=page,
                                    campaign_id=campaign_id,
                                    csv_path=csv_path,
                                    campaign_name=campaign_name,
                                    screenshot_dir=Config.SCREENSHOT_DIR
                                )
                                
                                if result['status'] == 'success':
                                    ads = result.get('ads_created', 0)
                                    print(f"    ✓ Uploaded {ads} ads")
                                    variants_created.append(f"Android ({ads} ads)")
                                else:
                                    print(f"    ✗ Upload failed: {result.get('error', 'Unknown error')}")
                                    variants_created.append(f"Android (upload failed)")
                    
                    except Exception as e:
                        print(f"  ✗ Failed {variant}: {str(e)}")
                        variants_created.append(f"{variant} (FAILED)")
                
                # Record success
                results['success'].append({
                    'group': campaign.group,
                    'geo': geo,
                    'format': campaign.settings.ad_format,
                    'variants': ', '.join(variants_created)
                })
            
            except Exception as e:
                print(f"  ✗ FAILED: {str(e)}")
                results['failed'].append({
                    'group': campaign.group,
                    'geo': geo if 'geo' in locals() else 'N/A',
                    'error': str(e)
                })
        
        browser.close()
        
        # Print summary
        print("\n" + "="*65)
        print("SUMMARY")
        print("="*65)
        
        if results['success']:
            print(f"\n✓ Successfully created {len(results['success'])} campaign groups:")
            for r in results['success']:
                print(f"  • {r['group']} ({r['geo']}) - {r['format']}: {r['variants']}")
        
        if results['failed']:
            print(f"\n✗ Failed to create {len(results['failed'])} campaign groups:")
            for r in results['failed']:
                print(f"  • {r['group']} ({r['geo']}): {r['error']}")
        
        print(f"\n✓ Done! {len(results['success'])} successful, {len(results['failed'])} failed")


if __name__ == "__main__":
    sys.exit(main() or 0)

#!/usr/bin/env python3
"""
Full workflow test: Create campaigns and upload ads.

This will:
1. Parse a test CSV
2. Create Desktop campaign
3. Create iOS campaign  
4. Create Android campaign (cloning iOS)
5. Upload ads to each
6. Show you the campaign names to pause
"""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import Config
from auth import TJAuthenticator
from campaign_automation.creator_sync import CampaignCreator
from campaign_automation.csv_parser import parse_csv
from campaign_templates import generate_campaign_name, DEFAULT_SETTINGS
from native_uploader import NativeUploader
from native_csv_processor import NativeCSVProcessor

def main():
    print("\n" + "="*65)
    print("FULL CAMPAIGN CREATION TEST")
    print("="*65 + "\n")
    
    # Parse test CSV
    csv_path = Path("data/input/example_campaigns.csv")
    if not csv_path.exists():
        print(f"✗ Test CSV not found: {csv_path}")
        return 1
    
    print(f"→ Parsing CSV: {csv_path}")
    batch = parse_csv(csv_path)
    
    # Get first enabled campaign
    test_campaign = None
    for campaign in batch.campaigns:
        if campaign.is_enabled and len(campaign.variants) >= 1:
            test_campaign = campaign
            break
    
    if not test_campaign:
        print("✗ No enabled campaigns found in CSV")
        return 1
    
    print(f"✓ Found test campaign: {test_campaign.group}")
    print(f"  Keywords: {', '.join(kw.name for kw in test_campaign.keywords)}")
    print(f"  Variants: {', '.join(test_campaign.variants)}")
    print(f"  CSV: {test_campaign.csv_file}")
    print(f"  Geo: {', '.join(test_campaign.geo)}")
    
    csv_file_path = Path("data/input") / test_campaign.csv_file
    if not csv_file_path.exists():
        print(f"✗ Ad CSV not found: {csv_file_path}")
        return 1
    
    print(f"✓ Ad CSV exists: {csv_file_path}")
    
    # Confirm with user
    print("\n" + "-"*65)
    print("⚠️  THIS WILL CREATE REAL CAMPAIGNS ⚠️")
    print("-"*65)
    print("\nWhat will be created:")
    
    geo = test_campaign.geo[0]
    created_campaigns = []
    
    for variant in test_campaign.variants:
        campaign_name = generate_campaign_name(
            geo=geo,
            language=DEFAULT_SETTINGS["language"],
            ad_format=DEFAULT_SETTINGS["ad_format"],
            bid_type=DEFAULT_SETTINGS["bid_type"],
            source=DEFAULT_SETTINGS["source"],
            keyword=test_campaign.primary_keyword,
            device=variant,
            gender=test_campaign.settings.gender
        )
        print(f"  - {campaign_name}")
    
    # Skip confirmation in non-interactive mode
    if sys.stdin.isatty():
        print("\nPress Ctrl+C to cancel, or Enter to continue...")
        try:
            input()
        except KeyboardInterrupt:
            print("\n✗ Cancelled by user")
            return 0
    else:
        print("\n→ Running in non-interactive mode, proceeding automatically...")
    
    # Start browser
    print("\n" + "="*65)
    print("STARTING CAMPAIGN CREATION")
    print("="*65 + "\n")
    
    with sync_playwright() as p:
        # Use persistent context with your actual Chrome profile
        # This will use your real Chrome with all cookies and history
        print("→ Launching Chrome with your profile...")
        context = p.chromium.launch_persistent_context(
            user_data_dir="/tmp/playwright-chrome-profile",  # Temporary profile
            channel="chrome",    # Use installed Chrome
            headless=False,
            slow_mo=500,
            viewport={'width': 1920, 'height': 1080},
            args=[
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(60000)
        
        print("✓ Browser launched (using Chrome with persistent context)")
        
        # Login using existing pattern
        authenticator = TJAuthenticator(Config.TJ_USERNAME, Config.TJ_PASSWORD)
        
        # Add script to hide automation markers
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)
        
        print("→ Logging in with manual_login...")
        if not authenticator.manual_login(page):
            print("✗ Login failed")
            context.close()
            return 1
        
        print("✓ Login successful")
        # Note: persistent context handles session automatically
        print("✓ Session saved")
        
        # Create campaigns
        try:
            creator = CampaignCreator(page)
            uploader = NativeUploader(dry_run=False, take_screenshots=True)
            
            ios_campaign_id = None
            
            for variant in test_campaign.variants:
                print("\n" + "-"*65)
                print(f"Creating {variant.upper()} campaign...")
                print("-"*65)
                
                if variant == "desktop":
                    campaign_id, campaign_name = creator.create_desktop_campaign(
                        test_campaign, geo
                    )
                    print(f"✓ Created Desktop campaign")
                    print(f"  ID: {campaign_id}")
                    print(f"  Name: {campaign_name}")
                    
                elif variant == "ios":
                    campaign_id, campaign_name = creator.create_ios_campaign(
                        test_campaign, geo
                    )
                    ios_campaign_id = campaign_id
                    print(f"✓ Created iOS campaign")
                    print(f"  ID: {campaign_id}")
                    print(f"  Name: {campaign_name}")
                    
                elif variant == "android":
                    if not ios_campaign_id:
                        print("✗ iOS campaign must be created first!")
                        continue
                    
                    campaign_id, campaign_name = creator.create_android_campaign(
                        test_campaign, geo, ios_campaign_id
                    )
                    print(f"✓ Created Android campaign (cloned from iOS)")
                    print(f"  ID: {campaign_id}")
                    print(f"  Name: {campaign_name}")
                
                # Update sub11 in CSV with actual campaign name
                print(f"\n→ Updating sub11 in CSV with campaign name...")
                updated_csv_path = NativeCSVProcessor.update_campaign_name_in_urls(
                    csv_file_path, 
                    campaign_name, 
                    Config.WIP_DIR
                )
                print(f"✓ Updated CSV: {updated_csv_path.name}")
                
                # Upload ads
                print(f"\n→ Uploading ads from {updated_csv_path.name}...")
                result = uploader.upload_to_campaign(
                    page,
                    campaign_id,
                    updated_csv_path,
                    skip_navigation=True  # Already on campaign page
                )
                
                if result['status'] == 'success':
                    print(f"✓ Uploaded {result['ads_created']} ads")
                else:
                    print(f"✗ Upload failed: {result.get('error', 'Unknown error')}")
                
                # Save campaign
                print("→ Saving campaign...")
                save_btn = page.query_selector('button:text("Save Campaign")')
                if save_btn:
                    save_btn.click()
                    page.wait_for_timeout(2000)
                    print("✓ Campaign saved")
                
                created_campaigns.append({
                    'variant': variant,
                    'id': campaign_id,
                    'name': campaign_name,
                    'ads': result.get('ads_created', 0)
                })
            
            # Summary
            print("\n" + "="*65)
            print("✓ CAMPAIGN CREATION COMPLETE")
            print("="*65)
            print("\nCreated Campaigns:")
            for camp in created_campaigns:
                print(f"\n{camp['variant'].upper()}:")
                print(f"  Name: {camp['name']}")
                print(f"  ID: {camp['id']}")
                print(f"  Ads: {camp['ads']}")
            
            print("\n" + "-"*65)
            print("⚠️  ACTION REQUIRED: PAUSE THESE CAMPAIGNS")
            print("-"*65)
            print("\nGo to TrafficJunky and pause:")
            for camp in created_campaigns:
                print(f"  - {camp['name']}")
            
            print("\nBrowser will stay open so you can pause them...")
            if sys.stdin.isatty():
                input("\nPress Enter when done to close browser...")
            else:
                print("\n→ Non-interactive mode: Browser will close in 30 seconds...")
                page.wait_for_timeout(30000)
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
            if sys.stdin.isatty():
                input("\nPress Enter to close browser...")
            else:
                print("\n→ Error occurred, browser will close in 10 seconds...")
                page.wait_for_timeout(10000)
            return 1
        finally:
            context.close()
    
    print("\n✓ Test completed!\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())


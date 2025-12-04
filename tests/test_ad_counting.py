"""
Quick test script to verify ad counting works correctly on a specific campaign.
"""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

from config import Config
from src.auth import TJAuthenticator
from src.uploader import TJUploader
from src.utils import setup_logger, print_info, print_success, print_error

def test_ad_counting(campaign_id: str):
    """Test ad counting on a specific campaign."""
    
    print_info(f"Testing ad counting on campaign: {campaign_id}")
    print_info("="*60)
    
    # Setup logger
    logger = setup_logger('test', None, 'INFO', True, False)
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        
        # Try to load saved session
        authenticator = TJAuthenticator(Config.TJ_USERNAME, Config.TJ_PASSWORD)
        context = authenticator.load_session(browser)
        
        if context:
            # Check if session is still valid
            page = context.pages[0] if context.pages else context.new_page()
            page.set_default_timeout(Config.TIMEOUT)
            print_success("✓ Loaded saved session")
            
            # Quick test - try to navigate to campaigns page
            try:
                page.goto('https://advertiser.trafficjunky.com/campaigns', timeout=15000)
                if 'sign-in' in page.url or 'login' in page.url:
                    print_info("Session expired, need to login...")
                    context = None
                else:
                    print_success("✓ Session is valid")
            except:
                print_info("Session may be expired...")
                context = None
        
        if not context:
            # Create new context and login
            print_info("Manual login required...")
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = context.new_page()
            page.set_default_timeout(Config.TIMEOUT)
            
            if not authenticator.manual_login(page, timeout=120):
                print_error("Authentication failed or timed out")
                browser.close()
                return
            
            # Save session for future use
            authenticator.save_session(context)
            print_success("✓ Logged in and session saved")
        
        # Get the page (ensure we have one)
        if not page:
            page = context.pages[0] if context.pages else context.new_page()
            page.set_default_timeout(Config.TIMEOUT)
        
        # Navigate to campaign
        url = f"https://advertiser.trafficjunky.com/campaign/{campaign_id}/ad-settings"
        print_info(f"Navigating to: {url}")
        page.goto(url, wait_until='networkidle', timeout=30000)
        
        # Wait for page to load
        page.wait_for_selector('text=STEP 5. CREATE YOUR AD', state='visible', timeout=10000)
        print_success("✓ Page loaded")
        
        # Initialize uploader (to use its counting methods)
        uploader = TJUploader(dry_run=True, take_screenshots=False)
        
        # Test 1: Count ads WITHOUT setting page length
        print_info("\n" + "="*60)
        print_info("TEST 1: Counting ads WITHOUT changing page length")
        print_info("="*60)
        count_without = uploader._count_existing_ads(page)
        print_success(f"Ads found: {count_without}")
        
        # Test 2: Set page length to 100 and count again
        print_info("\n" + "="*60)
        print_info("TEST 2: Setting page length to 100 and counting again")
        print_info("="*60)
        uploader._set_ads_page_length(page, length=100)
        count_with = uploader._count_existing_ads(page)
        print_success(f"Ads found: {count_with}")
        
        # Test 3: Try "All" option if available
        print_info("\n" + "="*60)
        print_info("TEST 3: Testing page reload and recount")
        print_info("="*60)
        page.reload(wait_until='networkidle', timeout=30000)
        uploader._set_ads_page_length(page, length=100)
        count_after_reload = uploader._count_existing_ads(page)
        print_success(f"Ads found after reload: {count_after_reload}")
        
        # Summary
        print_info("\n" + "="*60)
        print_info("SUMMARY")
        print_info("="*60)
        print_info(f"Count without page length change: {count_without}")
        print_info(f"Count with page length = 100:     {count_with}")
        print_info(f"Count after reload:                {count_after_reload}")
        
        if count_with > count_without:
            print_success(f"\n✅ Page length fix WORKS! Found {count_with - count_without} more ads!")
        elif count_with == count_without:
            print_info(f"\n⚠️  Same count ({count_with}) - campaign may have ≤10 ads, or page length already set")
        
        # Keep browser open for inspection
        print_info("\n" + "="*60)
        print_info("Browser will stay open for 10 seconds for inspection...")
        print_info("="*60)
        import time
        time.sleep(10)
        
        browser.close()


if __name__ == '__main__':
    campaign_id = sys.argv[1] if len(sys.argv) > 1 else '1013013571'
    test_ad_counting(campaign_id)


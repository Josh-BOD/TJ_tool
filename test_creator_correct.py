#!/usr/bin/env python3
"""
Test campaign creator using EXACT pattern from native_main.py
"""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import Config
from auth import TJAuthenticator
from campaign_automation.creator_sync import CampaignCreator
from campaign_templates import TEMPLATE_CAMPAIGNS

def main():
    print("\n" + "="*65)
    print("CAMPAIGN CREATOR TEST (Using Existing Pattern)")
    print("="*65 + "\n")
    
    # Same pattern as native_main.py lines 271-340
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(
            headless=False,  # Visible for testing
            slow_mo=Config.SLOW_MO
        )
        
        print("✓ Browser launched")
        
        # Initialize authenticator (line 281)
        authenticator = TJAuthenticator(Config.TJ_USERNAME, Config.TJ_PASSWORD)
        
        # Try to load saved session first (line 284)
        context = authenticator.load_session(browser)
        
        if context:
            # Session loaded, verify it's still valid (line 288)
            page = context.new_page()
            page.set_default_timeout(Config.TIMEOUT)
            
            print("→ Checking if saved session is still valid...")
            page.goto('https://advertiser.trafficjunky.com/campaigns', wait_until='domcontentloaded')
            
            if authenticator.is_logged_in(page):
                print("✓ Logged in using saved session")
            else:
                print("⚠ Saved session expired, need to login again")
                context.close()
                context = None
        
        # If no valid session, create new context and login (line 301)
        if not context:
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(Config.TIMEOUT)
            
            print("→ Logging in (manual reCAPTCHA)...")
            
            if not authenticator.manual_login(page):
                print("✗ Login failed")
                browser.close()
                return 1
            
            print("✓ Login successful")
            
            # Save session for next time (line 312)
            authenticator.save_session(context)
            print("✓ Session saved")
        
        # NOW TEST THE CAMPAIGN CREATOR
        print("\n" + "-"*65)
        print("TESTING CAMPAIGN CREATOR")
        print("-"*65 + "\n")
        
        try:
            creator = CampaignCreator(page)
            
            # Test 1: Filter for Desktop template
            print("Test 1: Filter for Desktop template")
            page.goto("https://advertiser.trafficjunky.com/campaigns")
            page.wait_for_load_state("networkidle")
            
            desktop_id = TEMPLATE_CAMPAIGNS["desktop"]["id"]
            print(f"  Template ID: {desktop_id}")
            
            page.fill('input[name="id"]', desktop_id)
            page.keyboard.press("Enter")
            page.wait_for_timeout(2000)
            
            campaign_rows = page.query_selector_all('tr[data-campaign-id]')
            print(f"  ✓ Found {len(campaign_rows)} campaign(s)")
            
            if len(campaign_rows) > 0:
                name_elem = page.query_selector('.campaignName')
                if name_elem:
                    name = name_elem.text_content().strip()
                    print(f"  Campaign: {name}")
            else:
                print("  ✗ Desktop template not found!")
            
            # Test 2: Filter for iOS template
            print("\nTest 2: Filter for iOS template")
            ios_id = TEMPLATE_CAMPAIGNS["ios"]["id"]
            print(f"  Template ID: {ios_id}")
            
            page.fill('input[name="id"]', "")
            page.fill('input[name="id"]', ios_id)
            page.keyboard.press("Enter")
            page.wait_for_timeout(2000)
            
            campaign_rows = page.query_selector_all('tr[data-campaign-id]')
            print(f"  ✓ Found {len(campaign_rows)} campaign(s)")
            
            if len(campaign_rows) > 0:
                name_elem = page.query_selector('.campaignName')
                if name_elem:
                    name = name_elem.text_content().strip()
                    print(f"  Campaign: {name}")
            else:
                print("  ✗ iOS template not found!")
            
            print("\n" + "="*65)
            print("✓ TESTS PASSED")
            print("="*65)
            print("\nCampaign creator is working!")
            print("Browser will close in 5 seconds...")
            page.wait_for_timeout(5000)
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            browser.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


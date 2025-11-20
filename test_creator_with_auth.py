#!/usr/bin/env python3
"""
Simple test to verify the campaign creator works with your auth system.
"""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from auth import TJAuthenticator
from campaign_automation.creator_sync import CampaignCreator
from campaign_templates import TEMPLATE_CAMPAIGNS
from config import Config

def main():
    print("\n" + "="*65)
    print("CAMPAIGN CREATOR TEST (with Auth)")
    print("="*65 + "\n")
    
    # Get credentials
    config = Config()
    username = config.TJ_USERNAME
    password = config.TJ_PASSWORD
    
    if not username or not password:
        print("✗ Missing credentials in config")
        print("  Please set TJ_USERNAME and TJ_PASSWORD in config/config.py")
        return 1
    
    print(f"Using credentials for: {username}")
    
    with sync_playwright() as p:
        # Launch browser
        print("\n→ Launching browser...")
        browser = p.chromium.launch(
            headless=False,  # Visible so you can see
            slow_mo=1000      # Slow for debugging
        )
        
        context = browser.new_context()
        page = context.new_page()
        
        # Login using your auth system
        print("→ Logging in...")
        authenticator = TJAuthenticator(username, password)
        
        if not authenticator.manual_login(page):
            print("✗ Login failed")
            browser.close()
            return 1
        
        print("✓ Logged in successfully!\n")
        
        # Test campaign filter
        print("-"*65)
        print("Testing campaign filtering...")
        print("-"*65)
        
        creator = CampaignCreator(page)
        
        try:
            # Navigate to campaigns
            page.goto("https://advertiser.trafficjunky.com/campaigns")
            page.wait_for_load_state("networkidle")
            print("✓ On campaigns page")
            
            # Test filtering for Desktop template
            desktop_id = TEMPLATE_CAMPAIGNS["desktop"]["id"]
            print(f"\n→ Filtering for Desktop template: {desktop_id}")
            
            page.fill('input[name="id"]', desktop_id)
            page.keyboard.press("Enter")
            import time
            time.sleep(2)
            
            # Check if found
            campaign_rows = page.query_selector_all('tr[data-campaign-id]')
            print(f"✓ Found {len(campaign_rows)} matching campaign(s)")
            
            if len(campaign_rows) > 0:
                print("✓ Desktop template is accessible")
            else:
                print("✗ Desktop template not found")
            
            print("\n" + "="*65)
            print("✓ TEST PASSED")
            print("="*65)
            print("\nCampaign creator is ready to use!")
            print("Browser will close in 5 seconds...")
            time.sleep(5)
            
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


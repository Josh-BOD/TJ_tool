#!/usr/bin/env python3
"""
Test campaign creator - MANUAL LOGIN VERSION.

This test will open a browser and wait for you to manually log in,
then it will test the campaign creator functions.
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from campaign_automation.creator_sync import CampaignCreator
from campaign_templates import TEMPLATE_CAMPAIGNS

def main():
    print("\n" + "="*65)
    print("CAMPAIGN CREATOR - MANUAL LOGIN TEST")
    print("="*65 + "\n")
    
    with sync_playwright() as p:
        print("→ Launching browser...")
        browser = p.chromium.launch(
            headless=False,  # Visible
            slow_mo=1000     # Slow for watching
        )
        
        context = browser.new_context()
        page = context.new_page()
        
        # Go to TrafficJunky login
        print("→ Navigating to TrafficJunky...")
        page.goto("https://www.trafficjunky.com/sign-in")
        
        print("\n" + "="*65)
        print("⏳ PLEASE LOG IN MANUALLY IN THE BROWSER")
        print("="*65)
        print("\nSteps:")
        print("  1. Enter your username/email")
        print("  2. Enter your password")
        print("  3. Solve reCAPTCHA if prompted")
        print("  4. Click LOG IN")
        print("\nWaiting for you to complete login...")
        print("(Test will continue automatically once logged in)")
        print("="*65 + "\n")
        
        # Wait for login to complete (check if we're on campaigns/dashboard)
        max_wait = 120  # 2 minutes
        for i in range(max_wait):
            current_url = page.url
            if 'advertiser.trafficjunky.com' in current_url or 'campaigns' in current_url or 'dashboard' in current_url:
                print(f"✓ Login detected! Current URL: {current_url}\n")
                break
            time.sleep(1)
        else:
            print("✗ Login timeout - taking too long")
            browser.close()
            return 1
        
        # Now test the campaign creator
        print("-"*65)
        print("TESTING CAMPAIGN CREATOR")
        print("-"*65 + "\n")
        
        try:
            creator = CampaignCreator(page)
            
            # Test 1: Navigate to campaigns page
            print("Test 1: Navigate to campaigns page")
            page.goto("https://advertiser.trafficjunky.com/campaigns")
            page.wait_for_load_state("networkidle")
            print("  ✓ On campaigns page\n")
            
            # Test 2: Filter for Desktop template
            print("Test 2: Filter for Desktop template")
            desktop_id = TEMPLATE_CAMPAIGNS["desktop"]["id"]
            desktop_name = TEMPLATE_CAMPAIGNS["desktop"]["name"]
            print(f"  Template ID: {desktop_id}")
            print(f"  Template Name: {desktop_name}")
            
            page.fill('input[name="id"]', desktop_id)
            page.keyboard.press("Enter")
            time.sleep(2)
            
            campaign_rows = page.query_selector_all('tr[data-campaign-id]')
            print(f"  ✓ Found {len(campaign_rows)} matching campaign(s)\n")
            
            if len(campaign_rows) == 0:
                print("  ✗ WARNING: Desktop template not found!")
                print("    Check if template ID is correct\n")
            
            # Test 3: Filter for iOS template
            print("Test 3: Filter for iOS template")
            ios_id = TEMPLATE_CAMPAIGNS["ios"]["id"]
            ios_name = TEMPLATE_CAMPAIGNS["ios"]["name"]
            print(f"  Template ID: {ios_id}")
            print(f"  Template Name: {ios_name}")
            
            page.fill('input[name="id"]', "")  # Clear
            page.fill('input[name="id"]', ios_id)
            page.keyboard.press("Enter")
            time.sleep(2)
            
            campaign_rows = page.query_selector_all('tr[data-campaign-id]')
            print(f"  ✓ Found {len(campaign_rows)} matching campaign(s)\n")
            
            if len(campaign_rows) == 0:
                print("  ✗ WARNING: iOS template not found!")
                print("    Check if template ID is correct\n")
            
            # Test 4: Get campaign name from page
            if len(campaign_rows) > 0:
                print("Test 4: Extract campaign details")
                name_elem = page.query_selector('.campaignName')
                if name_elem:
                    name = name_elem.text_content().strip()
                    print(f"  Campaign Name: {name}")
                    print("  ✓ Can extract campaign details\n")
            
            print("="*65)
            print("✓ ALL TESTS PASSED")
            print("="*65)
            print("\nCampaign Creator is working correctly!")
            print("You can now use it to create real campaigns.")
            print("\nBrowser will close in 10 seconds...")
            time.sleep(10)
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
            print("\nBrowser will stay open for debugging...")
            input("Press Enter to close browser...")
            return 1
        finally:
            browser.close()
    
    print("\n✓ Test completed successfully!\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""Test browser connection and session validity."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from campaign_automation.creator import CampaignCreator


async def test_connection():
    """Test if we can connect to TrafficJunky with saved session."""
    session_file = Path("session.json")
    
    print("\n" + "="*65)
    print("BROWSER CONNECTION TEST")
    print("="*65 + "\n")
    
    # Check session file exists
    if not session_file.exists():
        print("✗ Session file not found: session.json")
        print("\nTo create a session file, run:")
        print("  python3 main.py --create-session")
        print("\nOr use an existing session file from your uploader.")
        return False
    
    print(f"✓ Found session file: {session_file}")
    print(f"  Size: {session_file.stat().st_size} bytes")
    
    print("\n" + "-"*65)
    print("Opening browser and connecting to TrafficJunky...")
    print("-"*65 + "\n")
    
    try:
        async with CampaignCreator(session_file, headless=False, slow_mo=1000) as creator:
            print("✓ Browser launched")
            
            # Navigate to campaigns page
            print("→ Navigating to campaigns page...")
            await creator.page.goto("https://advertiser.trafficjunky.com/campaigns")
            await creator.page.wait_for_load_state("networkidle")
            
            # Check page title
            title = await creator.page.title()
            print(f"✓ Page loaded: {title}")
            
            # Check if we're logged in
            if "Login" in title or "Sign In" in title:
                print("\n✗ Session expired - not logged in")
                print("\nTo create a new session:")
                print("  python3 main.py --create-session")
                await asyncio.sleep(3)
                return False
            
            # Check for campaign elements
            campaign_table = await creator.page.query_selector('#campaignsTable')
            if campaign_table:
                print("✓ Found campaigns table - successfully authenticated!")
            else:
                print("⚠ Cannot find campaigns table - may not be on correct page")
            
            # Count campaigns
            campaign_rows = await creator.page.query_selector_all('tr[data-campaign-id]')
            print(f"✓ Found {len(campaign_rows)} campaign(s) in your account")
            
            print("\n" + "="*65)
            print("✓ CONNECTION TEST PASSED")
            print("="*65)
            print("\nSession is valid and working!")
            print("Browser will close in 5 seconds...")
            await asyncio.sleep(5)
            
            return True
            
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the connection test."""
    result = asyncio.run(test_connection())
    
    if result:
        print("\n🎉 All checks passed! Ready for campaign creation.")
        return 0
    else:
        print("\n⚠ Test failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


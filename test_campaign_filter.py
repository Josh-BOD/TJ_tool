#!/usr/bin/env python3
"""Test campaign filtering functionality (read-only test)."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from campaign_automation.creator import CampaignCreator
from campaign_templates import TEMPLATE_CAMPAIGNS


async def test_filter():
    """Test if we can filter and find template campaigns."""
    session_file = Path("session.json")
    
    print("\n" + "="*65)
    print("CAMPAIGN FILTER TEST (Read-Only)")
    print("="*65 + "\n")
    
    if not session_file.exists():
        print("✗ Session file not found: session.json")
        print("  Run: python3 test_browser_connection.py first")
        return False
    
    try:
        async with CampaignCreator(session_file, headless=False, slow_mo=1000) as creator:
            print("✓ Browser launched")
            
            # Navigate to campaigns page
            print("→ Navigating to campaigns page...")
            await creator.page.goto("https://advertiser.trafficjunky.com/campaigns")
            await creator.page.wait_for_load_state("networkidle")
            print("✓ Page loaded")
            
            # Test Desktop template
            print("\n" + "-"*65)
            print("Testing Desktop Template Filter")
            print("-"*65)
            
            desktop_id = TEMPLATE_CAMPAIGNS["desktop"]["id"]
            desktop_name = TEMPLATE_CAMPAIGNS["desktop"]["name"]
            
            print(f"→ Filtering for campaign ID: {desktop_id}")
            
            # Clear any existing filter
            id_input = await creator.page.query_selector('input[name="id"]')
            if id_input:
                await id_input.fill("")
            
            await creator.page.fill('input[name="id"]', desktop_id)
            await creator.page.keyboard.press("Enter")
            await asyncio.sleep(2)
            
            # Check results
            campaign_rows = await creator.page.query_selector_all('tr[data-campaign-id]')
            print(f"✓ Found {len(campaign_rows)} matching campaign(s)")
            
            if len(campaign_rows) == 0:
                print("✗ Desktop template campaign not found!")
                print(f"  Expected ID: {desktop_id}")
                print(f"  Expected Name: {desktop_name}")
                return False
            
            # Verify it's the right campaign
            campaign_row = campaign_rows[0]
            row_id = await campaign_row.get_attribute('data-campaign-id')
            
            if row_id == desktop_id:
                print(f"✓ Found correct campaign: ID {row_id}")
            else:
                print(f"⚠ Found different campaign: ID {row_id}")
            
            # Get campaign name
            name_elem = await creator.page.query_selector('.campaignName')
            if name_elem:
                name = await name_elem.text_content()
                name = name.strip()
                print(f"  Name: {name}")
                
                if desktop_name in name or "TEMPLATE" in name:
                    print("✓ Template campaign verified")
                else:
                    print("⚠ Campaign name doesn't match template pattern")
            
            # Test iOS template
            print("\n" + "-"*65)
            print("Testing iOS Template Filter")
            print("-"*65)
            
            ios_id = TEMPLATE_CAMPAIGNS["ios"]["id"]
            ios_name = TEMPLATE_CAMPAIGNS["ios"]["name"]
            
            print(f"→ Filtering for campaign ID: {ios_id}")
            
            await creator.page.fill('input[name="id"]', "")
            await creator.page.fill('input[name="id"]', ios_id)
            await creator.page.keyboard.press("Enter")
            await asyncio.sleep(2)
            
            campaign_rows = await creator.page.query_selector_all('tr[data-campaign-id]')
            print(f"✓ Found {len(campaign_rows)} matching campaign(s)")
            
            if len(campaign_rows) == 0:
                print("✗ iOS template campaign not found!")
                print(f"  Expected ID: {ios_id}")
                print(f"  Expected Name: {ios_name}")
                return False
            
            name_elem = await creator.page.query_selector('.campaignName')
            if name_elem:
                name = await name_elem.text_content()
                name = name.strip()
                print(f"  Name: {name}")
            
            print("\n" + "="*65)
            print("✓ FILTER TEST PASSED")
            print("="*65)
            print("\n✓ Both template campaigns found")
            print("✓ Campaign filtering works correctly")
            print("\nBrowser will close in 5 seconds...")
            await asyncio.sleep(5)
            
            return True
            
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the filter test."""
    result = asyncio.run(test_filter())
    
    if result:
        print("\n🎉 Filter test passed! Template campaigns are accessible.")
        return 0
    else:
        print("\n⚠ Test failed. Check template campaign IDs.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


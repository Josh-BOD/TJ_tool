#!/usr/bin/env python3
"""
Quick test of the ad_pauser module components.
Tests CSV parsing and model creation without browser automation.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ad_pauser import (
    parse_creative_ids_csv,
    parse_campaign_ids_csv,
    PauseBatch,
    PauseResult
)

def test_csv_parsing():
    """Test CSV parsing functions."""
    print("="*70)
    print("Testing CSV Parsing")
    print("="*70)
    
    # Test Creative IDs CSV
    creative_csv = Path("Example_docs/Creative_IDs_Template.csv")
    print(f"\nParsing Creative IDs CSV: {creative_csv}")
    
    creative_ids = parse_creative_ids_csv(creative_csv)
    print(f"✓ Loaded {len(creative_ids)} Creative IDs:")
    for cid in sorted(creative_ids):
        print(f"  - {cid}")
    
    # Test Campaign IDs CSV
    campaign_csv = Path("Example_docs/Campaign_IDs_Template.csv")
    print(f"\nParsing Campaign IDs CSV: {campaign_csv}")
    
    campaigns = parse_campaign_ids_csv(campaign_csv)
    print(f"✓ Loaded {len(campaigns)} Campaign IDs:")
    for camp in campaigns:
        print(f"  - {camp['id']}: {camp['name']}")
    
    return creative_ids, campaigns


def test_models(creative_ids, campaigns):
    """Test data models."""
    print("\n" + "="*70)
    print("Testing Data Models")
    print("="*70)
    
    # Create a batch
    batch = PauseBatch(
        creative_ids=creative_ids,
        campaign_ids=[c['id'] for c in campaigns],
        dry_run=True
    )
    
    print(f"\n✓ Created PauseBatch:")
    print(f"  - Creative IDs: {len(batch.creative_ids)}")
    print(f"  - Campaign IDs: {len(batch.campaign_ids)}")
    print(f"  - Dry Run: {batch.dry_run}")
    
    # Create a test result
    result = PauseResult(
        campaign_id="1012927602",
        campaign_name="Desktop-Stepmom-US",
        ads_found=["2212936201", "2212936202"],
        ads_paused=["2212936201", "2212936202"],
        ads_not_found=["2212936203", "2212936204"],
        pages_processed=2,
        time_taken=45.2,
        status='partial'
    )
    
    batch.results.append(result)
    
    print(f"\n✓ Created PauseResult:")
    print(f"  - Campaign: {result.campaign_name}")
    print(f"  - Status: {result.status}")
    print(f"  - Found: {len(result.ads_found)}")
    print(f"  - Paused: {len(result.ads_paused)}")
    print(f"  - Not Found: {len(result.ads_not_found)}")
    
    print(f"\n✓ Batch Statistics:")
    print(f"  - Total Ads Paused: {batch.total_ads_paused}")
    print(f"  - Successful Campaigns: {batch.successful_campaigns}")
    print(f"  - Partial Campaigns: {batch.partial_campaigns}")
    print(f"  - Failed Campaigns: {batch.failed_campaigns}")
    
    return batch


def main():
    """Run tests."""
    print("\n" + "="*70)
    print("AD PAUSER MODULE TESTS")
    print("="*70)
    print()
    
    try:
        # Test CSV parsing
        creative_ids, campaigns = test_csv_parsing()
        
        # Test models
        batch = test_models(creative_ids, campaigns)
        
        # Success
        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED")
        print("="*70)
        print("\nThe ad_pauser module is ready to use!")
        print("\nNext step: Run with --dry-run to test browser automation:")
        print("  python Pause_ads_V1.py --creatives Example_docs/Creative_IDs_Template.csv \\")
        print("                         --campaigns Example_docs/Campaign_IDs_Template.csv \\")
        print("                         --dry-run")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""
Test script for campaign creation tool.

Tests the core functionality without actually creating campaigns.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from campaign_automation.csv_parser import parse_csv, CSVParseError
from campaign_automation.validator import validate_batch
from campaign_automation.models import CampaignStatus
from campaign_templates import generate_campaign_name, DEFAULT_SETTINGS


def test_csv_parsing():
    """Test CSV parsing."""
    print("\n" + "="*65)
    print("TEST 1: CSV Parsing")
    print("="*65)
    
    try:
        csv_path = Path("data/input/example_campaigns.csv")
        batch = parse_csv(csv_path)
        
        print(f"✓ Parsed {batch.total_campaigns} campaigns")
        print(f"✓ Session ID: {batch.session_id}")
        print(f"✓ Enabled campaigns: {len(batch.enabled_campaigns)}")
        print(f"✓ Total variants: {batch.total_variants}")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_validation():
    """Test validation."""
    print("\n" + "="*65)
    print("TEST 2: Validation")
    print("="*65)
    
    try:
        csv_path = Path("data/input/example_campaigns.csv")
        csv_dir = Path("data/input")
        batch = parse_csv(csv_path)
        
        is_valid, errors, warnings = validate_batch(batch, csv_dir)
        
        print(f"✓ Validation completed")
        print(f"  Valid: {is_valid}")
        print(f"  Errors: {len(errors)}")
        print(f"  Warnings: {len(warnings)}")
        
        return is_valid
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_campaign_naming():
    """Test campaign naming."""
    print("\n" + "="*65)
    print("TEST 3: Campaign Naming")
    print("="*65)
    
    try:
        test_cases = [
            ("US", "Milfs", "desktop", "male", "US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB"),
            ("US", "Milfs", "ios", "male", "US_EN_NATIVE_CPA_ALL_KEY-Milfs_iOS_M_JB"),
            ("US", "Milfs", "android", "male", "US_EN_NATIVE_CPA_ALL_KEY-Milfs_AND_M_JB"),
            ("CA", "Cougars", "desktop", "female", "CA_EN_NATIVE_CPA_ALL_KEY-Cougars_DESK_F_JB"),
        ]
        
        for geo, keyword, device, gender, expected in test_cases:
            result = generate_campaign_name(
                geo=geo,
                language=DEFAULT_SETTINGS["language"],
                ad_format=DEFAULT_SETTINGS["ad_format"],
                bid_type=DEFAULT_SETTINGS["bid_type"],
                source=DEFAULT_SETTINGS["source"],
                keyword=keyword,
                device=device,
                gender=gender
            )
            
            if result == expected:
                print(f"✓ {device:8s} | {result}")
            else:
                print(f"✗ {device:8s} | Expected: {expected}")
                print(f"           | Got:      {result}")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_data_models():
    """Test data models."""
    print("\n" + "="*65)
    print("TEST 4: Data Models")
    print("="*65)
    
    try:
        csv_path = Path("data/input/example_campaigns.csv")
        batch = parse_csv(csv_path)
        
        # Get first enabled campaign
        campaign = batch.enabled_campaigns[0]
        
        print(f"✓ Campaign: {campaign.group}")
        print(f"  Primary keyword: {campaign.primary_keyword}")
        print(f"  Variants: {', '.join(campaign.variants)}")
        print(f"  Enabled: {campaign.is_enabled}")
        print(f"  Completed: {campaign.is_completed}")
        
        # Test variant status
        campaign.update_variant_status(
            "desktop",
            CampaignStatus.COMPLETED,
            campaign_id="1234567890",
            campaign_name="Test Campaign"
        )
        
        variant_status = campaign.get_variant_status("desktop")
        print(f"\n✓ Variant status update:")
        print(f"  Status: {variant_status.status.value}")
        print(f"  Campaign ID: {variant_status.campaign_id}")
        print(f"  Campaign Name: {variant_status.campaign_name}")
        
        # Test serialization
        data = campaign.to_dict()
        print(f"\n✓ Serialization: {len(data)} fields")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_checkpoint():
    """Test checkpoint manager."""
    print("\n" + "="*65)
    print("TEST 5: Checkpoint Manager")
    print("="*65)
    
    try:
        from campaign_automation.checkpoint import CheckpointManager
        
        csv_path = Path("data/input/example_campaigns.csv")
        batch = parse_csv(csv_path)
        
        checkpoint_dir = Path("data/test_checkpoints")
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        mgr = CheckpointManager(checkpoint_dir)
        
        # Save checkpoint
        mgr.save(batch)
        print(f"✓ Saved checkpoint: {batch.session_id}")
        
        # Load checkpoint
        data = mgr.load(batch.session_id)
        print(f"✓ Loaded checkpoint: {len(data)} fields")
        
        # List checkpoints
        checkpoints = mgr.list_checkpoints()
        print(f"✓ Found {len(checkpoints)} checkpoint(s)")
        
        # Clean up
        mgr.delete(batch.session_id)
        checkpoint_dir.rmdir()
        print(f"✓ Cleaned up test checkpoint")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*65)
    print("CAMPAIGN CREATION TOOL - TEST SUITE")
    print("="*65)
    
    tests = [
        ("CSV Parsing", test_csv_parsing),
        ("Validation", test_validation),
        ("Campaign Naming", test_campaign_naming),
        ("Data Models", test_data_models),
        ("Checkpoint Manager", test_checkpoint),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*65)
    print("TEST SUMMARY")
    print("="*65)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8s} | {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())


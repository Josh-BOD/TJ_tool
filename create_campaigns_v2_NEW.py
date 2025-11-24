#!/usr/bin/env python3
"""
Campaign Creation Tool - CLI Interface

Automated end-to-end campaign creation for TrafficJunky Native campaigns.
"""

import sys
import argparse
import asyncio
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from campaign_automation.csv_parser import parse_csv, CSVParseError
from campaign_automation.validator import validate_batch
from campaign_automation.models import CampaignBatch
from campaign_automation.orchestrator import create_campaigns
from campaign_automation.checkpoint import CheckpointManager
from campaign_templates import generate_campaign_name, DEFAULT_SETTINGS


def print_header(text: str):
    """Print a section header."""
    print("\n" + "=" * 65)
    print(text)
    print("=" * 65)


def print_subheader(text: str):
    """Print a subsection header."""
    print("\n" + "-" * 65)
    print(text)
    print("-" * 65)


def print_success(text: str):
    """Print success message."""
    print(f"✓ {text}")


def print_error(text: str):
    """Print error message."""
    print(f"✗ {text}")


def print_warning(text: str):
    """Print warning message."""
    print(f"⚠ {text}")


def dry_run(batch: CampaignBatch, csv_dir: Path):
    """
    Perform dry-run validation and preview.
    
    Args:
        batch: CampaignBatch to preview
        csv_dir: Directory containing CSV ad files
    """
    print_header("DRY-RUN MODE - No campaigns will be created")
    
    # Parse info
    print(f"\nInput file: {batch.input_file}")
    print(f"Session ID: {batch.session_id}")
    print(f"Total campaigns defined: {batch.total_campaigns}")
    print(f"Enabled campaigns: {len(batch.enabled_campaigns)}")
    
    if batch.total_campaigns != len(batch.enabled_campaigns):
        disabled = batch.total_campaigns - len(batch.enabled_campaigns)
        print(f"Disabled campaigns: {disabled}")
    
    # Validate
    print_subheader("VALIDATION CHECKS")
    
    is_valid, errors, warnings = validate_batch(batch, csv_dir)
    
    if errors:
        print_error(f"Found {len(errors)} error(s):")
        for error in errors:
            print(f"  • {error}")
    else:
        print_success("No errors found")
    
    if warnings:
        print_warning(f"Found {len(warnings)} warning(s):")
        for warning in warnings:
            print(f"  • {warning}")
    else:
        print_success("No warnings")
    
    if not is_valid:
        print_subheader("VALIDATION FAILED")
        print("\n✗ Please fix the errors above before running.")
        return False
    
    # Show what would be created
    print_subheader("CAMPAIGNS TO BE CREATED")
    
    campaign_num = 0
    total_variants = 0
    
    for campaign in batch.campaigns:
        if not campaign.is_enabled:
            campaign_num += 1
            print(f"\nCampaign {campaign_num}: {campaign.group} (SKIPPED - disabled)")
            continue
        
        campaign_num += 1
        print(f"\nCampaign Set {campaign_num}: {campaign.group}")
        print(f"  Geo: {', '.join(campaign.geo)}")
        print(f"  Keywords: {', '.join(str(kw) for kw in campaign.keywords)}")
        print(f"  CSV: {campaign.csv_file}")
        print(f"  Settings:")
        print(f"    - Target CPA: ${campaign.settings.target_cpa}")
        print(f"    - Per Source Budget: ${campaign.settings.per_source_test_budget}")
        print(f"    - Max Bid: ${campaign.settings.max_bid}")
        print(f"    - Frequency Cap: {campaign.settings.frequency_cap} time(s)/day")
        print(f"    - Max Daily Budget: ${campaign.settings.max_daily_budget}")
        print(f"    - Gender: {campaign.settings.gender}")
        
        print(f"\n  Will create {len(campaign.variants)} campaign(s):")
        
        for variant in campaign.variants:
            geo = campaign.geo[0] if campaign.geo else "US"
            keyword = campaign.primary_keyword
            
            campaign_name = generate_campaign_name(
                geo=geo,
                language=DEFAULT_SETTINGS["language"],
                ad_format=DEFAULT_SETTINGS["ad_format"],
                bid_type=DEFAULT_SETTINGS["bid_type"],
                source=DEFAULT_SETTINGS["source"],
                keyword=keyword,
                device=variant,
                gender=campaign.settings.gender
            )
            
            template_info = ""
            if variant == "desktop":
                template_info = "Clone from Desktop template (1013076141)"
            elif variant == "ios":
                template_info = "Clone from iOS template (1013076221)"
            elif variant == "android":
                template_info = "Clone from iOS campaign (created above)"
            
            print(f"    {total_variants + 1}. {campaign_name}")
            print(f"       └─ {template_info}")
            print(f"       └─ Upload CSV: {campaign.csv_file}")
            
            total_variants += 1
    
    # Summary
    print_subheader("DRY-RUN SUMMARY")
    
    print(f"\nTotal campaign sets: {batch.total_campaigns}")
    print(f"  ✓ Enabled: {len(batch.enabled_campaigns)}")
    if batch.total_campaigns != len(batch.enabled_campaigns):
        print(f"  ⊗ Disabled: {batch.total_campaigns - len(batch.enabled_campaigns)}")
    
    print(f"\nTotal campaigns that would be created: {total_variants}")
    
    # Count by variant type
    desktop_count = sum(
        1 for c in batch.enabled_campaigns 
        for v in c.variants if v == "desktop"
    )
    ios_count = sum(
        1 for c in batch.enabled_campaigns 
        for v in c.variants if v == "ios"
    )
    android_count = sum(
        1 for c in batch.enabled_campaigns 
        for v in c.variants if v == "android"
    )
    
    print(f"  - Desktop campaigns: {desktop_count}")
    print(f"  - iOS campaigns: {ios_count}")
    print(f"  - Android campaigns: {android_count}")
    
    # Time estimate
    desktop_time = desktop_count * 5
    ios_time = ios_count * 5
    android_time = android_count * 3
    total_time = desktop_time + ios_time + android_time
    
    print(f"\nEstimated time: ~{total_time} minutes")
    print(f"  (Desktop: ~5min, iOS: ~5min, Android: ~3min per campaign)")
    
    print_subheader("NEXT STEPS")
    print("\n✓ Validation passed - ready to create campaigns!")
    print("\nTo create these campaigns for real:")
    print(f"  python create_campaigns.py --input {batch.input_file}")
    print("\nTo modify the configuration:")
    print(f"  1. Edit: {batch.input_file}")
    print(f"  2. Run dry-run again to verify changes")
    print(f"  3. Run without --dry-run when ready")
    
    print("\n" + "=" * 65 + "\n")
    
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated TrafficJunky Native Campaign Creation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry-run (validate and preview)
  python create_campaigns.py --input campaigns.csv --dry-run
  
  # Create campaigns
  python create_campaigns.py --input campaigns.csv
  
  # Resume from checkpoint
  python create_campaigns.py --input campaigns.csv --resume SESSION_ID
  
  # Specify CSV directory and session file
  python create_campaigns.py --input campaigns.csv --csv-dir data/input/ --session session.json
  
  # Visible browser (not headless)
  python create_campaigns.py --input campaigns.csv --no-headless
        """
    )
    
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input CSV file with campaign definitions"
    )
    
    parser.add_argument(
        "--csv-dir",
        type=Path,
        default=Path("data/input"),
        help="Directory containing CSV ad files (default: data/input/)"
    )
    
    parser.add_argument(
        "--session",
        type=Path,
        default=Path("session.json"),
        help="Browser session file (default: session.json)"
    )
    
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=Path("data/checkpoints"),
        help="Directory for checkpoint files (default: data/checkpoints/)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and preview without creating campaigns"
    )
    
    parser.add_argument(
        "--resume",
        type=str,
        metavar="SESSION_ID",
        help="Resume from checkpoint with given session ID"
    )
    
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in visible mode (not headless)"
    )
    
    parser.add_argument(
        "--slow-mo",
        type=int,
        default=500,
        help="Slow down browser operations by N milliseconds (default: 500)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not args.input.exists():
        print_error(f"Input file not found: {args.input}")
        return 1
    
    # Validate CSV directory
    if not args.csv_dir.exists():
        print_error(f"CSV directory not found: {args.csv_dir}")
        return 1
    
    try:
        # Parse CSV
        print(f"Parsing input file: {args.input}")
        batch = parse_csv(args.input)
        print_success("File parsed successfully")
        
        # Check for resume
        if args.resume:
            checkpoint_mgr = CheckpointManager(args.checkpoint_dir)
            checkpoint_data = checkpoint_mgr.load(args.resume)
            
            if checkpoint_data:
                print_success(f"Loaded checkpoint: {args.resume}")
                checkpoint_mgr.restore_batch(batch, checkpoint_data)
            else:
                print_warning(f"Checkpoint not found: {args.resume}")
                print("Starting fresh...")
        
        # Dry-run mode
        if args.dry_run:
            success = dry_run(batch, args.csv_dir)
            return 0 if success else 1
        
        # Validate before running
        print("\nValidating configuration...")
        is_valid, errors, warnings = validate_batch(batch, args.csv_dir)
        
        if errors:
            print_error(f"Validation failed with {len(errors)} error(s)")
            for error in errors:
                print(f"  • {error}")
            return 1
        
        if warnings:
            print_warning(f"Found {len(warnings)} warning(s)")
            for warning in warnings:
                print(f"  • {warning}")
        
        print_success("Validation passed")
        
        # Check if session file exists
        if not args.session.exists():
            print_error(f"Session file not found: {args.session}")
            print("\nPlease ensure you have a valid session file.")
            print("You can create one by logging in to TrafficJunky with Playwright.")
            return 1
        
        # Run campaign creation
        headless = not args.no_headless
        
        asyncio.run(create_campaigns(
            batch=batch,
            csv_dir=args.csv_dir,
            session_file=args.session,
            checkpoint_dir=args.checkpoint_dir,
            headless=headless,
            slow_mo=args.slow_mo,
            verbose=args.verbose
        ))
        
        return 0
        
    except CSVParseError as e:
        print_error(f"CSV parsing failed: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        print("Progress has been saved. Use --resume to continue.")
        return 130
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())


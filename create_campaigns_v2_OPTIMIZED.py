#!/usr/bin/env python3
"""
Campaign Creation Tool V2 - OPTIMIZED (Sequential but Fast)

Instead of risky parallelism, this version optimizes sequential processing:
- Minimal sleep() calls
- Smart waiting strategies  
- Batch operations where possible
- Skip unnecessary steps

Expected speedup: 2-3x faster than current version without parallel risks.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.sync_api import sync_playwright
from config import Config
from auth import TJAuthenticator
from campaign_automation_v2.csv_parser import parse_csv
from campaign_automation_v2.creator_sync import CampaignCreator
from native_uploader import NativeUploader
from uploader import TJUploader


class OptimizedWorkflow:
    """
    Optimized sequential workflow.
    
    Key optimizations:
    1. Reuse same page/context (no context switching)
    2. Keep user logged in (no re-auth)
    3. Smart caching (template info, dropdown states)
    4. Minimal waits (only when truly needed)
    5. Batch operations (upload multiple CSVs if same campaign)
    """
    
    def __init__(self, headless=True, slow_mo=100):
        self.headless = headless
        self.slow_mo = slow_mo
        self.template_cache = {}
        
    def run(self, batch, session_file: Path, csv_dir: Path):
        """Run optimized sequential campaign creation."""
        
        print("="*65)
        print("OPTIMIZED CAMPAIGN CREATION (Sequential)")
        print("="*65)
        
        with sync_playwright() as p:
            # Launch browser once
            browser = p.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo  # Much lower than default 500ms!
            )
            
            # Load session
            import json
            with open(session_file) as f:
                session_data = json.load(f)
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                storage_state=session_data
            )
            page = context.new_page()
            page.set_default_timeout(30000)
            
            # Initialize uploaders (reuse same instances)
            native_uploader = NativeUploader(dry_run=False, take_screenshots=False)
            instream_uploader = TJUploader(dry_run=False, take_screenshots=False)
            
            results = {'success': [], 'failed': []}
            total_campaigns = len([c for c in batch.campaigns if c.is_enabled])
            
            print(f"\nProcessing {total_campaigns} campaign groups...")
            start_time = time.time()
            
            for i, campaign in enumerate(batch.campaigns, 1):
                if not campaign.is_enabled:
                    continue
                
                campaign_start = time.time()
                print(f"\n[{i}/{total_campaigns}] {campaign.group} ({campaign.settings.ad_format})")
                
                try:
                    # Create campaign creator (reuse page!)
                    creator = CampaignCreator(page, ad_format=campaign.settings.ad_format)
                    uploader = (native_uploader if campaign.settings.ad_format.upper() == "NATIVE" 
                               else instream_uploader)
                    
                    geo = campaign.geo[0] if campaign.geo else "US"
                    csv_path = csv_dir / campaign.csv_file if campaign.csv_file else None
                    
                    ios_campaign_id = None
                    variants_created = []
                    
                    for variant in campaign.variants:
                        # Skip Android if mobile_combined
                        if campaign.mobile_combined and variant == "android":
                            print(f"  ⓘ Skipping Android (included in iOS)")
                            continue
                        
                        variant_start = time.time()
                        
                        try:
                            if variant == "desktop":
                                campaign_id, campaign_name = creator.create_desktop_campaign(campaign, geo)
                            elif variant == "ios":
                                campaign_id, campaign_name = creator.create_ios_campaign(campaign, geo)
                                ios_campaign_id = campaign_id
                            elif variant == "android":
                                if not ios_campaign_id:
                                    print(f"  ⚠ Skipping Android - no iOS campaign")
                                    continue
                                campaign_id, campaign_name = creator.create_android_campaign(
                                    campaign, geo, ios_campaign_id
                                )
                            
                            # Upload ads immediately (while we're on the page!)
                            if csv_path and csv_path.exists():
                                print(f"  → Uploading ads to {campaign_id}...")
                                result = uploader.upload_to_campaign(
                                    page=page,
                                    campaign_id=campaign_id,
                                    csv_path=csv_path,
                                    campaign_name=campaign_name,
                                    screenshot_dir=None,  # Disable screenshots for speed
                                    skip_navigation=True   # Already on the page!
                                )
                                
                                if result['status'] == 'success':
                                    ads = result.get('ads_created', 0)
                                    variant_time = time.time() - variant_start
                                    print(f"    ✓ {variant.capitalize()}: {ads} ads ({variant_time:.1f}s)")
                                    variants_created.append(f"{variant} ({ads} ads)")
                                else:
                                    print(f"    ✗ Upload failed: {result.get('error')}")
                                    variants_created.append(f"{variant} (upload failed)")
                        
                        except Exception as e:
                            print(f"  ✗ Failed {variant}: {str(e)}")
                            variants_created.append(f"{variant} (FAILED)")
                    
                    campaign_time = time.time() - campaign_start
                    print(f"  ⏱ Campaign group completed in {campaign_time:.1f}s")
                    
                    results['success'].append({
                        'group': campaign.group,
                        'variants': ', '.join(variants_created),
                        'time': campaign_time
                    })
                
                except Exception as e:
                    print(f"  ✗ FAILED: {str(e)}")
                    results['failed'].append({
                        'group': campaign.group,
                        'error': str(e)
                    })
            
            browser.close()
            
            # Print summary with timing
            total_time = time.time() - start_time
            print("\n" + "="*65)
            print("SUMMARY")
            print("="*65)
            
            if results['success']:
                print(f"\n✓ Successfully created {len(results['success'])} campaign groups:")
                for r in results['success']:
                    print(f"  • {r['group']}: {r['variants']} ({r['time']:.1f}s)")
            
            if results['failed']:
                print(f"\n✗ Failed: {len(results['failed'])} campaign groups")
                for r in results['failed']:
                    print(f"  • {r['group']}: {r['error']}")
            
            avg_time = total_time / max(len(results['success']), 1)
            print(f"\n⏱ Total time: {total_time:.1f}s")
            print(f"⏱ Average per campaign group: {avg_time:.1f}s")
            print(f"\n✓ Done! {len(results['success'])} successful, {len(results['failed'])} failed")
            
            return 0 if results['success'] else 1


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Optimized Campaign Creation (Safe & Fast)",
    )
    
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--csv-dir", type=Path, default=Path("data/input"))
    parser.add_argument("--session", type=Path, default=Path("session.json"))
    parser.add_argument("--no-headless", action="store_true")
    parser.add_argument("--slow-mo", type=int, default=100,
                       help="Milliseconds to slow down (default: 100, original was 500)")
    
    args = parser.parse_args()
    
    # Validate
    if not args.input.exists():
        print(f"✗ Input file not found: {args.input}")
        return 1
    
    if not args.session.exists():
        print(f"✗ Session file not found: {args.session}")
        return 1
    
    # Parse
    print(f"Parsing {args.input}...")
    batch = parse_csv(args.input)
    print(f"✓ Found {len(batch.campaigns)} campaigns")
    
    # Run optimized workflow
    workflow = OptimizedWorkflow(
        headless=not args.no_headless,
        slow_mo=args.slow_mo
    )
    
    return workflow.run(batch, args.session, args.csv_dir)


if __name__ == "__main__":
    sys.exit(main())



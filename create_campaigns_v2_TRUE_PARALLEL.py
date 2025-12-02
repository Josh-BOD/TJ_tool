#!/usr/bin/env python3
"""
Campaign Creation Tool V2 - TRUE PARALLEL VERSION

Uses multiple browser INSTANCES (not contexts) for parallel processing.
Based on real-world testing: 2-3 instances work without rate limiting.

Architecture:
- Each worker = separate browser process
- Each browser = independent session (different fingerprint)
- ProcessPoolExecutor for true parallelism
- Each worker processes campaigns independently
"""

import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.sync_api import sync_playwright
from config import Config
from auth import TJAuthenticator
from campaign_automation_v2.csv_parser import parse_csv
from campaign_automation_v2.creator_sync import CampaignCreator
from campaign_automation_v2.models import CampaignDefinition
from native_uploader import NativeUploader
from uploader import TJUploader

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Worker %(process)d] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class WorkerTask:
    """Task for a worker to process."""
    campaign_index: int
    campaign_group: str
    campaign_data: dict  # Serializable campaign data
    csv_dir: str
    session_file: str
    slow_mo: int
    headless: bool


def worker_process_campaign(task: WorkerTask) -> Dict:
    """
    Process a single campaign in a separate process.
    
    This function runs in its own process with its own browser instance.
    Each browser instance is completely independent.
    
    Args:
        task: WorkerTask with campaign and config
        
    Returns:
        Result dictionary
    """
    worker_id = task.campaign_index
    logger.info(f"Worker {worker_id} starting: {task.campaign_group}")
    
    result = {
        'worker_id': worker_id,
        'campaign_group': task.campaign_group,
        'status': 'failed',
        'variants': [],
        'error': None,
        'duration': 0
    }
    
    start_time = time.time()
    
    try:
        # Recreate campaign object from serialized data
        from campaign_automation_v2.models import CampaignDefinition
        campaign = CampaignDefinition.from_dict(task.campaign_data)
        
        # Launch SEPARATE browser instance for this worker
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=task.headless,
                slow_mo=task.slow_mo
            )
            
            try:
                # Try to load existing session, or login if needed
                context = browser.new_context(viewport={'width': 1920, 'height': 1080})
                page = context.new_page()
                page.set_default_timeout(30000)
                
                # Try to load session from file
                session_loaded = False
                if Path(task.session_file).exists():
                    try:
                        with open(task.session_file) as f:
                            session_data = json.load(f)
                        # Close old context and create new one with session
                        page.close()
                        context.close()
                        context = browser.new_context(
                            viewport={'width': 1920, 'height': 1080},
                            storage_state=session_data
                        )
                        page = context.new_page()
                        page.set_default_timeout(30000)
                        session_loaded = True
                        logger.info(f"Worker {worker_id}: Loaded session from file")
                    except Exception as e:
                        logger.warning(f"Worker {worker_id}: Could not load session: {e}")
                
                # If no session loaded and this is worker 1, do manual login
                if not session_loaded and worker_id <= 1:
                    logger.info(f"Worker {worker_id}: No session found, performing login...")
                    authenticator = TJAuthenticator(Config.TJ_USERNAME, Config.TJ_PASSWORD)
                    if authenticator.manual_login(page, timeout=180):
                        authenticator.save_session(context)
                        logger.info(f"Worker {worker_id}: Login successful, session saved")
                    else:
                        raise Exception("Login failed")
                elif not session_loaded:
                    # Worker > 1 should wait for worker 1 to create session
                    import time
                    logger.info(f"Worker {worker_id}: Waiting for session file...")
                    for _ in range(60):  # Wait up to 60 seconds
                        time.sleep(1)
                        if Path(task.session_file).exists():
                            with open(task.session_file) as f:
                                session_data = json.load(f)
                            page.close()
                            context.close()
                            context = browser.new_context(
                                viewport={'width': 1920, 'height': 1080},
                                storage_state=session_data
                            )
                            page = context.new_page()
                            page.set_default_timeout(30000)
                            logger.info(f"Worker {worker_id}: Loaded session after wait")
                            break
                    else:
                        raise Exception("Session file never created")
                
                # Initialize tools
                creator = CampaignCreator(page, ad_format=campaign.settings.ad_format)
                
                if campaign.settings.ad_format.upper() == "NATIVE":
                    uploader = NativeUploader(dry_run=False, take_screenshots=False)
                else:
                    uploader = TJUploader(dry_run=False, take_screenshots=False)
                
                # Process campaign
                geo = campaign.geo[0] if campaign.geo else "US"
                csv_path = Path(task.csv_dir) / campaign.csv_file if campaign.csv_file else None
                
                ios_campaign_id = None
                variants_created = []
                
                for variant in campaign.variants:
                    # Skip Android if mobile_combined
                    if campaign.mobile_combined and variant == "android":
                        logger.info(f"Worker {worker_id}: Skipping Android (mobile_combined)")
                        continue
                    
                    try:
                        logger.info(f"Worker {worker_id}: Creating {variant} campaign...")
                        
                        if variant == "desktop":
                            campaign_id, campaign_name = creator.create_desktop_campaign(campaign, geo)
                        elif variant == "ios":
                            campaign_id, campaign_name = creator.create_ios_campaign(campaign, geo)
                            ios_campaign_id = campaign_id
                        elif variant == "android":
                            if not ios_campaign_id:
                                logger.warning(f"Worker {worker_id}: Skipping Android - no iOS campaign")
                                continue
                            campaign_id, campaign_name = creator.create_android_campaign(
                                campaign, geo, ios_campaign_id
                            )
                        
                        # Upload ads
                        if csv_path and csv_path.exists():
                            logger.info(f"Worker {worker_id}: Uploading ads to {campaign_id}...")
                            upload_result = uploader.upload_to_campaign(
                                page=page,
                                campaign_id=campaign_id,
                                csv_path=csv_path,
                                campaign_name=campaign_name,
                                screenshot_dir=None,
                                skip_navigation=True
                            )
                            
                            if upload_result['status'] == 'success':
                                ads = upload_result.get('ads_created', 0)
                                logger.info(f"Worker {worker_id}: ✓ {variant} - {ads} ads created")
                                variants_created.append({
                                    'variant': variant,
                                    'campaign_id': campaign_id,
                                    'ads_created': ads,
                                    'status': 'success'
                                })
                            else:
                                logger.warning(f"Worker {worker_id}: ✗ {variant} upload failed")
                                variants_created.append({
                                    'variant': variant,
                                    'campaign_id': campaign_id,
                                    'ads_created': 0,
                                    'status': 'upload_failed',
                                    'error': upload_result.get('error')
                                })
                    
                    except Exception as e:
                        logger.error(f"Worker {worker_id}: ✗ {variant} failed: {e}")
                        variants_created.append({
                            'variant': variant,
                            'status': 'failed',
                            'error': str(e)
                        })
                
                result['status'] = 'success' if variants_created else 'failed'
                result['variants'] = variants_created
                result['duration'] = time.time() - start_time
                
                logger.info(f"Worker {worker_id}: ✓ Completed in {result['duration']:.1f}s")
                
            finally:
                browser.close()
    
    except Exception as e:
        result['error'] = str(e)
        result['duration'] = time.time() - start_time
        logger.error(f"Worker {worker_id}: ✗ Failed: {e}")
    
    return result


class TrueParallelCreator:
    """
    Creates campaigns in parallel using multiple browser INSTANCES.
    
    Based on real-world testing: 2-3 browser instances work without issues.
    """
    
    def __init__(
        self,
        max_workers: int = 2,
        headless: bool = True,
        slow_mo: int = 100
    ):
        """
        Initialize parallel creator.
        
        Args:
            max_workers: Number of parallel browser instances (recommended: 2-3)
            headless: Run browsers in headless mode
            slow_mo: Milliseconds to slow down operations
        """
        self.max_workers = max_workers
        self.headless = headless
        self.slow_mo = slow_mo
    
    def create_campaigns(
        self,
        batch,
        session_file: Path,
        csv_dir: Path
    ) -> Dict:
        """
        Create campaigns in parallel using ProcessPoolExecutor.
        
        Args:
            batch: CampaignBatch from CSV parser
            session_file: Authenticated session file
            csv_dir: Directory containing CSV files
            
        Returns:
            Dictionary with results
        """
        print("="*70)
        print(f"TRUE PARALLEL CAMPAIGN CREATION - {self.max_workers} Workers")
        print("="*70)
        
        # Build task list
        tasks = []
        for i, campaign in enumerate(batch.campaigns, 1):
            if not campaign.is_enabled:
                continue
            
            # Serialize campaign data (ProcessPoolExecutor requires picklable data)
            task = WorkerTask(
                campaign_index=i,
                campaign_group=campaign.group,
                campaign_data=campaign.to_dict(),  # Need to add this method
                csv_dir=str(csv_dir),
                session_file=str(session_file),
                slow_mo=self.slow_mo,
                headless=self.headless
            )
            tasks.append(task)
        
        print(f"Total campaigns to process: {len(tasks)}")
        print(f"Processing {self.max_workers} campaigns at a time...\n")
        
        # Process campaigns in parallel
        results = []
        start_time = time.time()
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(worker_process_campaign, task): task 
                for task in tasks
            }
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_task):
                completed += 1
                task = future_to_task[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    status = "✓" if result['status'] == 'success' else "✗"
                    print(f"[{completed}/{len(tasks)}] {status} {result['campaign_group']} "
                          f"({result['duration']:.1f}s)")
                    
                except Exception as e:
                    print(f"[{completed}/{len(tasks)}] ✗ {task.campaign_group} - EXCEPTION: {e}")
                    results.append({
                        'campaign_group': task.campaign_group,
                        'status': 'exception',
                        'error': str(e)
                    })
        
        total_time = time.time() - start_time
        
        # Print summary
        return self._print_summary(results, total_time)
    
    def _print_summary(self, results: List[Dict], total_time: float) -> Dict:
        """Print summary of results."""
        print("\n" + "="*70)
        print("PARALLEL CREATION SUMMARY")
        print("="*70)
        
        success = [r for r in results if r['status'] == 'success']
        failed = [r for r in results if r['status'] != 'success']
        
        if success:
            print(f"\n✓ Successfully created {len(success)} campaign groups:")
            for r in success:
                variants_summary = ', '.join(
                    f"{v['variant']} ({v.get('ads_created', 0)} ads)" 
                    for v in r.get('variants', [])
                )
                print(f"  • {r['campaign_group']}: {variants_summary} ({r['duration']:.1f}s)")
        
        if failed:
            print(f"\n✗ Failed {len(failed)} campaign groups:")
            for r in failed:
                error = r.get('error', 'Unknown error')
                print(f"  • {r['campaign_group']}: {error}")
        
        avg_time = total_time / max(len(results), 1)
        sequential_estimate = sum(r.get('duration', 0) for r in results)
        speedup = sequential_estimate / total_time if total_time > 0 else 1
        
        print(f"\n⏱ Total wall time: {total_time:.1f}s")
        print(f"⏱ Sequential would take: ~{sequential_estimate:.1f}s")
        print(f"🚀 Speedup: {speedup:.1f}x faster")
        print(f"\n✓ Done! {len(success)} successful, {len(failed)} failed")
        
        return {
            'total': len(results),
            'success': len(success),
            'failed': len(failed),
            'total_time': total_time,
            'speedup': speedup,
            'results': results
        }


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="True Parallel Campaign Creation (Multiple Browser Instances)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Safe parallel (2 workers)
  python create_campaigns_v2_TRUE_PARALLEL.py --input campaigns.csv --workers 2
  
  # Faster (3 workers - tested to work)
  python create_campaigns_v2_TRUE_PARALLEL.py --input campaigns.csv --workers 3
  
  # Watch it work (visible browsers)
  python create_campaigns_v2_TRUE_PARALLEL.py --input campaigns.csv --workers 2 --no-headless

Performance Notes:
  - 2 workers = ~2x speedup (safest)
  - 3 workers = ~2.5x speedup (tested, works)
  - 4+ workers = diminishing returns + risk of rate limiting
  
  Each worker uses ~200-300MB RAM, plan accordingly.
        """
    )
    
    parser.add_argument("--input", type=Path, required=True,
                       help="Input CSV file with campaign definitions")
    parser.add_argument("--csv-dir", type=Path, default=Path("data/input"),
                       help="Directory containing CSV ad files")
    parser.add_argument("--session", type=Path, default=Path("session.json"),
                       help="Browser session file")
    parser.add_argument("--workers", type=int, default=2, choices=range(1, 6),
                       help="Number of parallel workers (1-5, recommended: 2-3)")
    parser.add_argument("--slow-mo", type=int, default=100,
                       help="Slow down operations by N milliseconds")
    parser.add_argument("--no-headless", action="store_true",
                       help="Run browsers in visible mode")
    
    args = parser.parse_args()
    
    # Validate
    if not args.input.exists():
        print(f"✗ Input file not found: {args.input}")
        return 1
    
    if not args.session.exists():
        print(f"✗ Session file not found: {args.session}")
        return 1
    
    # Parse campaigns
    print(f"Parsing {args.input}...")
    batch = parse_csv(args.input)
    enabled = len([c for c in batch.campaigns if c.is_enabled])
    print(f"✓ Found {enabled} enabled campaigns")
    
    # Create parallel processor
    creator = TrueParallelCreator(
        max_workers=args.workers,
        headless=not args.no_headless,
        slow_mo=args.slow_mo
    )
    
    # Run parallel creation
    try:
        summary = creator.create_campaigns(
            batch=batch,
            session_file=args.session,
            csv_dir=args.csv_dir
        )
        
        return 0 if summary['success'] > 0 else 1
        
    except KeyboardInterrupt:
        print("\n⚠ Interrupted by user")
        return 130
    except Exception as e:
        print(f"✗ Parallel creation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())


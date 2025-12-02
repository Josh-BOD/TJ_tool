#!/usr/bin/env python3
"""
Campaign Creation Tool V2 - SIMPLE PARALLEL VERSION

Uses threading with multiple browser instances (simpler than ProcessPoolExecutor).
Easier to control and stop.
"""

import sys
import time
import logging
import threading
from pathlib import Path
from typing import List, Dict
from queue import Queue

sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.sync_api import sync_playwright
from config import Config
from auth import TJAuthenticator
from campaign_automation_v2.csv_parser import parse_csv
from campaign_automation_v2.creator_sync import CampaignCreator
from native_uploader import NativeUploader
from uploader import TJUploader

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Worker %(thread)d] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleParallelCreator:
    """Simple parallel creator using threading."""
    
    def __init__(self, num_workers=2, headless=True, slow_mo=100):
        self.num_workers = num_workers
        self.headless = headless
        self.slow_mo = slow_mo
        self.results = []
        self.stop_requested = False
    
    def worker_thread(self, worker_id: int, campaign_queue: Queue, session_file: Path, csv_dir: Path):
        """Worker thread that processes campaigns from queue."""
        logger.info(f"Worker {worker_id} starting...")
        
        try:
            with sync_playwright() as p:
                # Launch browser
                browser = p.chromium.launch(
                    headless=self.headless,
                    slow_mo=self.slow_mo
                )
                
                # Load or create session
                if session_file.exists():
                    import json
                    with open(session_file) as f:
                        session_data = json.load(f)
                    context = browser.new_context(
                        viewport={'width': 1920, 'height': 1080},
                        storage_state=session_data
                    )
                    logger.info(f"Worker {worker_id}: Loaded session")
                else:
                    # Only worker 1 does login
                    if worker_id == 1:
                        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
                        page = context.new_page()
                        logger.info(f"Worker {worker_id}: Logging in (solve CAPTCHA)...")
                        authenticator = TJAuthenticator(Config.TJ_USERNAME, Config.TJ_PASSWORD)
                        if authenticator.manual_login(page, timeout=180):
                            authenticator.save_session(context)
                            logger.info(f"Worker {worker_id}: Login successful, session saved")
                        else:
                            logger.error(f"Worker {worker_id}: Login failed")
                            browser.close()
                            return
                    else:
                        # Wait for worker 1 to create session
                        logger.info(f"Worker {worker_id}: Waiting for session...")
                        for _ in range(60):
                            time.sleep(1)
                            if session_file.exists():
                                break
                        
                        if not session_file.exists():
                            logger.error(f"Worker {worker_id}: No session file found")
                            browser.close()
                            return
                        
                        import json
                        with open(session_file) as f:
                            session_data = json.load(f)
                        context = browser.new_context(
                            viewport={'width': 1920, 'height': 1080},
                            storage_state=session_data
                        )
                
                page = context.new_page()
                page.set_default_timeout(30000)
                
                # Initialize uploaders
                native_uploader = NativeUploader(dry_run=False, take_screenshots=False)
                instream_uploader = TJUploader(dry_run=False, take_screenshots=False)
                
                # Process campaigns from queue
                while not self.stop_requested:
                    try:
                        # Get campaign from queue (timeout so we can check stop_requested)
                        item = campaign_queue.get(timeout=1)
                        if item is None:  # Sentinel value for shutdown
                            break
                        
                        campaign, campaign_num = item
                        start_time = time.time()
                        
                        logger.info(f"Worker {worker_id}: Processing campaign {campaign_num}: {campaign.group}")
                        
                        # Create campaign creator
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
                                continue
                            
                            try:
                                if variant == "desktop":
                                    campaign_id, campaign_name = creator.create_desktop_campaign(campaign, geo)
                                elif variant == "ios":
                                    campaign_id, campaign_name = creator.create_ios_campaign(campaign, geo)
                                    ios_campaign_id = campaign_id
                                elif variant == "android":
                                    if not ios_campaign_id:
                                        continue
                                    campaign_id, campaign_name = creator.create_android_campaign(
                                        campaign, geo, ios_campaign_id
                                    )
                                
                                # Upload ads
                                if csv_path and csv_path.exists():
                                    result = uploader.upload_to_campaign(
                                        page=page,
                                        campaign_id=campaign_id,
                                        csv_path=csv_path,
                                        campaign_name=campaign_name,
                                        screenshot_dir=None,
                                        skip_navigation=True
                                    )
                                    
                                    if result['status'] == 'success':
                                        ads = result.get('ads_created', 0)
                                        variants_created.append(f"{variant} ({ads} ads)")
                                    else:
                                        variants_created.append(f"{variant} (upload failed)")
                            
                            except Exception as e:
                                logger.error(f"Worker {worker_id}: {variant} failed: {e}")
                                variants_created.append(f"{variant} (FAILED)")
                        
                        duration = time.time() - start_time
                        self.results.append({
                            'worker': worker_id,
                            'campaign': campaign.group,
                            'variants': ', '.join(variants_created),
                            'duration': duration,
                            'status': 'success' if variants_created else 'failed'
                        })
                        
                        logger.info(f"Worker {worker_id}: ✓ Completed {campaign.group} in {duration:.1f}s")
                        
                        campaign_queue.task_done()
                    
                    except Exception as e:
                        if "Empty" not in str(e):
                            logger.error(f"Worker {worker_id}: Error: {e}")
                        continue
                
                browser.close()
                logger.info(f"Worker {worker_id}: Finished")
        
        except Exception as e:
            logger.error(f"Worker {worker_id}: Fatal error: {e}")
    
    def create_campaigns(self, batch, session_file: Path, csv_dir: Path):
        """Create campaigns using parallel workers."""
        print("="*70)
        print(f"SIMPLE PARALLEL CAMPAIGN CREATION - {self.num_workers} Workers")
        print("="*70)
        
        # Get enabled campaigns
        campaigns = [c for c in batch.campaigns if c.is_enabled]
        print(f"Total campaigns to process: {len(campaigns)}\n")
        
        # Create queue
        campaign_queue = Queue()
        
        # Add campaigns to queue
        for i, campaign in enumerate(campaigns, 1):
            campaign_queue.put((campaign, i))
        
        # Start workers
        workers = []
        start_time = time.time()
        
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self.worker_thread,
                args=(i + 1, campaign_queue, session_file, csv_dir),
                daemon=True
            )
            worker.start()
            workers.append(worker)
        
        try:
            # Wait for queue to be empty
            while not campaign_queue.empty():
                time.sleep(1)
                completed = len(self.results)
                print(f"\rProgress: {completed}/{len(campaigns)} campaigns completed", end='', flush=True)
            
            # Add sentinel values to stop workers
            for _ in range(self.num_workers):
                campaign_queue.put(None)
            
            # Wait for all workers to finish
            for worker in workers:
                worker.join(timeout=10)
            
            print("\n")
        
        except KeyboardInterrupt:
            print("\n\n⚠ Interrupted by user - stopping workers...")
            self.stop_requested = True
            
            # Wait a bit for workers to stop
            time.sleep(2)
        
        total_time = time.time() - start_time
        
        # Print summary
        self._print_summary(total_time, len(campaigns))
    
    def _print_summary(self, total_time, total_campaigns):
        """Print summary of results."""
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        
        success = [r for r in self.results if r['status'] == 'success']
        failed = [r for r in self.results if r['status'] != 'success']
        
        if success:
            print(f"\n✓ Successfully created {len(success)} campaign groups:")
            for r in success:
                print(f"  • [Worker {r['worker']}] {r['campaign']}: {r['variants']} ({r['duration']:.1f}s)")
        
        if failed:
            print(f"\n✗ Failed {len(failed)} campaign groups")
        
        avg_time = total_time / max(len(self.results), 1)
        print(f"\n⏱ Total time: {total_time:.1f}s")
        print(f"⏱ Average per campaign: {avg_time:.1f}s")
        print(f"\n✓ Done! {len(success)} successful, {len(failed)} failed")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple Parallel Campaign Creation")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--csv-dir", type=Path, default=Path("data/input"))
    parser.add_argument("--session", type=Path, default=Path("session.json"))
    parser.add_argument("--workers", type=int, default=2, choices=range(1, 6))
    parser.add_argument("--slow-mo", type=int, default=100)
    parser.add_argument("--no-headless", action="store_true")
    
    args = parser.parse_args()
    
    if not args.input.exists():
        print(f"✗ Input file not found: {args.input}")
        return 1
    
    print(f"Parsing {args.input}...")
    batch = parse_csv(args.input)
    enabled = len([c for c in batch.campaigns if c.is_enabled])
    print(f"✓ Found {enabled} enabled campaigns\n")
    
    creator = SimpleParallelCreator(
        num_workers=args.workers,
        headless=not args.no_headless,
        slow_mo=args.slow_mo
    )
    
    try:
        creator.create_campaigns(batch, args.session, args.csv_dir)
        return 0
    except KeyboardInterrupt:
        print("\n⚠ Stopped by user")
        return 130
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())



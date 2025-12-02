#!/usr/bin/env python3
"""
Campaign Creation Tool V2 - PARALLEL VERSION

Creates multiple campaigns simultaneously using async Playwright.
Expected speedup: 3-5x for batches of campaigns.
"""

import sys
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.async_api import async_playwright, Page, BrowserContext
from config import Config
from campaign_automation_v2.csv_parser import parse_csv
from campaign_automation_v2.models import CampaignDefinition

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CampaignTask:
    """Represents a single campaign creation task."""
    campaign: CampaignDefinition
    variant: str  # desktop, ios, or android
    geo: str
    csv_path: Optional[Path]
    ios_campaign_id: Optional[str] = None  # For Android cloning


class ParallelCampaignCreator:
    """
    Creates campaigns in parallel using multiple browser contexts.
    
    Architecture:
    - 1 Browser instance (shared)
    - N Context instances (isolated, parallel)
    - Each context = independent session with own cookies/storage
    """
    
    def __init__(
        self, 
        max_workers: int = 3,
        headless: bool = True,
        slow_mo: int = 100
    ):
        """
        Initialize parallel creator.
        
        Args:
            max_workers: Maximum number of parallel browser contexts (default: 3)
                        - Too high = rate limiting, resource exhaustion
                        - Too low = not much speedup
                        - Recommended: 2-4
            headless: Run browsers in headless mode
            slow_mo: Milliseconds to slow down operations (lower = faster)
        """
        self.max_workers = max_workers
        self.headless = headless
        self.slow_mo = slow_mo
        self.results = []
        
    async def create_campaigns(
        self, 
        batch, 
        session_file: Path,
        csv_dir: Path
    ) -> Dict:
        """
        Create all campaigns in parallel.
        
        Strategy:
        1. Load session once
        2. Create browser with N contexts
        3. Distribute campaigns across contexts
        4. Run in parallel with asyncio.gather()
        
        Args:
            batch: CampaignBatch from CSV parser
            session_file: Authenticated session file
            csv_dir: Directory containing CSV files
            
        Returns:
            Dictionary with results
        """
        logger.info("="*70)
        logger.info(f"PARALLEL CAMPAIGN CREATION - {self.max_workers} workers")
        logger.info("="*70)
        
        # Build task list
        tasks = self._build_task_list(batch, csv_dir)
        logger.info(f"Total tasks to process: {len(tasks)}")
        
        # Start parallel processing
        async with async_playwright() as p:
            # Launch single browser
            browser = await p.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo
            )
            
            try:
                # Load session storage from file
                import json
                with open(session_file) as f:
                    session_data = json.load(f)
                
                # Create worker contexts (each with session)
                contexts = []
                for i in range(self.max_workers):
                    context = await browser.new_context(
                        viewport={'width': 1920, 'height': 1080},
                        storage_state=session_data
                    )
                    contexts.append(context)
                    logger.info(f"✓ Created worker context {i+1}")
                
                # Distribute tasks across workers
                worker_tasks = [[] for _ in range(self.max_workers)]
                for i, task in enumerate(tasks):
                    worker_tasks[i % self.max_workers].append(task)
                
                # Create worker coroutines
                workers = []
                for i, task_list in enumerate(worker_tasks):
                    if task_list:  # Only create worker if it has tasks
                        worker = self._worker(
                            worker_id=i+1,
                            context=contexts[i],
                            tasks=task_list
                        )
                        workers.append(worker)
                
                # Run all workers in parallel
                logger.info(f"Starting {len(workers)} workers...")
                results = await asyncio.gather(*workers, return_exceptions=True)
                
                # Process results
                all_results = []
                for worker_results in results:
                    if isinstance(worker_results, Exception):
                        logger.error(f"Worker failed: {worker_results}")
                    else:
                        all_results.extend(worker_results)
                
                # Cleanup
                for context in contexts:
                    await context.close()
                
                await browser.close()
                
                return self._summarize_results(all_results)
                
            except Exception as e:
                logger.error(f"Parallel processing failed: {e}")
                await browser.close()
                raise
    
    async def _worker(
        self, 
        worker_id: int, 
        context: BrowserContext, 
        tasks: List[CampaignTask]
    ) -> List[Dict]:
        """
        Worker coroutine that processes a list of tasks sequentially.
        
        Each worker:
        1. Gets its own Page from its Context
        2. Processes tasks one by one
        3. Returns results
        
        Args:
            worker_id: Worker identifier for logging
            context: Browser context for this worker
            tasks: List of campaign tasks to process
            
        Returns:
            List of results
        """
        logger.info(f"[Worker {worker_id}] Starting with {len(tasks)} tasks")
        
        page = await context.new_page()
        await page.set_default_timeout(30000)
        
        results = []
        
        for i, task in enumerate(tasks, 1):
            logger.info(f"[Worker {worker_id}] Task {i}/{len(tasks)}: {task.campaign.group} - {task.variant}")
            
            try:
                result = await self._process_task(page, task)
                results.append(result)
                
                status = "✓" if result['status'] == 'success' else "✗"
                logger.info(f"[Worker {worker_id}] {status} Completed: {task.campaign.group} - {task.variant}")
                
            except Exception as e:
                logger.error(f"[Worker {worker_id}] ✗ Task failed: {e}")
                results.append({
                    'campaign': task.campaign.group,
                    'variant': task.variant,
                    'status': 'failed',
                    'error': str(e)
                })
        
        await page.close()
        logger.info(f"[Worker {worker_id}] Finished all tasks")
        
        return results
    
    async def _process_task(self, page: Page, task: CampaignTask) -> Dict:
        """
        Process a single campaign creation task.
        
        This needs to be converted to async versions of your creator methods.
        For now, showing the structure.
        
        Args:
            page: Playwright page
            task: Campaign task to process
            
        Returns:
            Result dictionary
        """
        # TODO: Convert CampaignCreator to async
        # For now, this shows the structure
        
        result = {
            'campaign': task.campaign.group,
            'variant': task.variant,
            'geo': task.geo,
            'status': 'pending',
            'campaign_id': None,
            'ads_created': 0,
            'error': None
        }
        
        try:
            # This is where you'd call async versions of:
            # - creator.create_desktop_campaign()
            # - creator.create_ios_campaign()
            # - creator.create_android_campaign()
            # - uploader.upload_to_campaign()
            
            # Placeholder - you need to convert creator_sync.py to async
            logger.warning(f"Task processing not yet implemented (async conversion needed)")
            result['status'] = 'not_implemented'
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
        
        return result
    
    def _build_task_list(self, batch, csv_dir: Path) -> List[CampaignTask]:
        """
        Build list of independent tasks from campaign batch.
        
        Challenge: Android campaigns depend on iOS (need iOS campaign ID).
        Solution: Create iOS tasks first, then Android tasks will be handled
                 in a second pass or within the same worker.
        
        Args:
            batch: CampaignBatch
            csv_dir: CSV directory
            
        Returns:
            List of CampaignTask objects
        """
        tasks = []
        
        for campaign in batch.campaigns:
            if not campaign.is_enabled:
                continue
            
            geo = campaign.geo[0] if campaign.geo else "US"
            csv_path = csv_dir / campaign.csv_file if campaign.csv_file else None
            
            # Add desktop and iOS tasks (independent)
            for variant in campaign.variants:
                # Skip Android for now (handle in second pass)
                if variant == "android":
                    continue
                
                # Skip Android if mobile_combined
                if campaign.mobile_combined and variant == "android":
                    continue
                
                task = CampaignTask(
                    campaign=campaign,
                    variant=variant,
                    geo=geo,
                    csv_path=csv_path
                )
                tasks.append(task)
        
        # TODO: Handle Android campaigns (need iOS IDs first)
        # This requires a two-phase approach or shared state
        
        return tasks
    
    def _summarize_results(self, results: List[Dict]) -> Dict:
        """Summarize all results."""
        summary = {
            'total': len(results),
            'success': sum(1 for r in results if r['status'] == 'success'),
            'failed': sum(1 for r in results if r['status'] == 'failed'),
            'results': results
        }
        
        logger.info("="*70)
        logger.info("PARALLEL CREATION SUMMARY")
        logger.info("="*70)
        logger.info(f"Total tasks: {summary['total']}")
        logger.info(f"✓ Successful: {summary['success']}")
        logger.info(f"✗ Failed: {summary['failed']}")
        
        return summary


# ============================================================================
# CLI Interface
# ============================================================================

async def main():
    """Main entry point for parallel campaign creation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Parallel Campaign Creation (EXPERIMENTAL)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create campaigns with 3 parallel workers
  python create_campaigns_v2_PARALLEL.py --input campaigns.csv --workers 3
  
  # Fast mode (more workers, less slowdown)
  python create_campaigns_v2_PARALLEL.py --input campaigns.csv --workers 4 --slow-mo 50
  
  # Conservative mode (fewer workers, more reliable)
  python create_campaigns_v2_PARALLEL.py --input campaigns.csv --workers 2 --slow-mo 200

Performance Tips:
  - Start with 2-3 workers to avoid rate limiting
  - Monitor CPU/memory usage
  - Use headless mode for faster performance
  - Reduce slow-mo once you're confident it's stable
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
        "--workers",
        type=int,
        default=3,
        choices=range(1, 11),
        help="Number of parallel workers (1-10, default: 3)"
    )
    
    parser.add_argument(
        "--slow-mo",
        type=int,
        default=100,
        help="Slow down operations by N milliseconds (default: 100)"
    )
    
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browsers in visible mode (useful for debugging)"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return 1
    
    if not args.session.exists():
        logger.error(f"Session file not found: {args.session}")
        return 1
    
    # Parse campaigns
    logger.info(f"Parsing {args.input}...")
    batch = parse_csv(args.input)
    logger.info(f"✓ Found {len(batch.campaigns)} campaigns")
    
    # Create parallel processor
    creator = ParallelCampaignCreator(
        max_workers=args.workers,
        headless=not args.no_headless,
        slow_mo=args.slow_mo
    )
    
    # Run parallel creation
    try:
        results = await creator.create_campaigns(
            batch=batch,
            session_file=args.session,
            csv_dir=args.csv_dir
        )
        
        return 0 if results['success'] > 0 else 1
        
    except KeyboardInterrupt:
        logger.warning("\n⚠ Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"✗ Parallel creation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))



"""
Campaign orchestrator - coordinates campaign creation workflow.

Manages the end-to-end process of creating campaigns, uploading ads,
and tracking progress.
"""

import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime

from .models import CampaignBatch, CampaignDefinition, CampaignStatus
from .creator import CampaignCreator, CampaignCreationError
from .progress import ProgressTracker
from .checkpoint import CheckpointManager

# Import native uploader
import sys
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from native_uploader import NativeAdUploader


class CampaignOrchestrator:
    """Orchestrates campaign creation workflow."""
    
    def __init__(
        self,
        batch: CampaignBatch,
        csv_dir: Path,
        session_file: Path,
        checkpoint_dir: Path,
        headless: bool = True,
        slow_mo: int = 500,
        verbose: bool = False
    ):
        """
        Initialize orchestrator.
        
        Args:
            batch: CampaignBatch to process
            csv_dir: Directory containing CSV ad files
            session_file: Path to browser session file
            checkpoint_dir: Directory for checkpoints
            headless: Run browser in headless mode
            slow_mo: Slow down operations (ms)
            verbose: Verbose output
        """
        self.batch = batch
        self.csv_dir = csv_dir
        self.session_file = session_file
        self.checkpoint_dir = checkpoint_dir
        self.headless = headless
        self.slow_mo = slow_mo
        self.verbose = verbose
        
        self.tracker = ProgressTracker(batch, verbose)
        self.checkpoint_mgr = CheckpointManager(checkpoint_dir)
    
    async def run(self):
        """Run the campaign creation workflow."""
        print(f"\n{'='*65}")
        print(f"CAMPAIGN CREATION STARTED")
        print(f"Session ID: {self.batch.session_id}")
        print(f"{'='*65}\n")
        
        async with CampaignCreator(
            self.session_file,
            headless=self.headless,
            slow_mo=self.slow_mo
        ) as creator:
            
            # Process each campaign
            for campaign in self.batch.campaigns:
                if not campaign.is_enabled:
                    print(f"\n⊗ Skipping campaign: {campaign.group} (disabled)")
                    continue
                
                await self._process_campaign(creator, campaign)
                
                # Save checkpoint after each campaign
                self.checkpoint_mgr.save(self.batch)
        
        # Print final summary
        self.tracker.print_summary()
        
        # Clean up checkpoint if all successful
        if self.tracker.failed_variants == 0:
            self.checkpoint_mgr.delete(self.batch.session_id)
    
    async def _process_campaign(
        self,
        creator: CampaignCreator,
        campaign: CampaignDefinition
    ):
        """Process a single campaign set."""
        self.tracker.start_campaign(campaign)
        
        # Determine geo (first geo code)
        geo = campaign.geo[0] if campaign.geo else "US"
        
        # Track iOS campaign ID for Android cloning
        ios_campaign_id: Optional[str] = None
        
        # Process each variant
        for variant in campaign.variants:
            # Skip if already completed (from checkpoint)
            variant_status = campaign.get_variant_status(variant)
            if variant_status.status == CampaignStatus.COMPLETED:
                self.tracker.skip_variant(
                    campaign,
                    variant,
                    f"Already completed (ID: {variant_status.campaign_id})"
                )
                self.tracker.completed_variants += 1
                continue
            
            try:
                self.tracker.start_variant(campaign, variant)
                
                # Create campaign based on variant type
                if variant == "desktop":
                    campaign_id, campaign_name = await self._create_desktop(
                        creator, campaign, geo
                    )
                elif variant == "ios":
                    campaign_id, campaign_name = await self._create_ios(
                        creator, campaign, geo
                    )
                    ios_campaign_id = campaign_id  # Save for Android
                elif variant == "android":
                    if not ios_campaign_id:
                        # Check if iOS was already created in previous run
                        ios_status = campaign.get_variant_status("ios")
                        if ios_status.campaign_id:
                            ios_campaign_id = ios_status.campaign_id
                        else:
                            raise CampaignCreationError(
                                "iOS campaign must be created before Android"
                            )
                    
                    campaign_id, campaign_name = await self._create_android(
                        creator, campaign, geo, ios_campaign_id
                    )
                else:
                    raise CampaignCreationError(f"Unknown variant: {variant}")
                
                # Upload ads
                self.tracker.update_step(campaign, variant, "Uploading ads...")
                ads_uploaded = await self._upload_ads(
                    creator.page,
                    campaign_id,
                    campaign_name,
                    campaign.csv_file
                )
                
                # Mark as completed
                self.tracker.complete_variant(
                    campaign,
                    variant,
                    campaign_id,
                    campaign_name,
                    ads_uploaded
                )
                
            except Exception as e:
                error_msg = str(e)
                step = campaign.get_variant_status(variant).step
                
                self.tracker.fail_variant(
                    campaign,
                    variant,
                    error_msg,
                    step
                )
                
                # Continue to next variant on failure
                continue
        
        self.tracker.complete_campaign(campaign)
    
    async def _create_desktop(
        self,
        creator: CampaignCreator,
        campaign: CampaignDefinition,
        geo: str
    ) -> tuple:
        """Create Desktop campaign."""
        self.tracker.update_step(campaign, "desktop", "Cloning Desktop template")
        campaign_id, campaign_name = await creator.create_desktop_campaign(campaign, geo)
        return campaign_id, campaign_name
    
    async def _create_ios(
        self,
        creator: CampaignCreator,
        campaign: CampaignDefinition,
        geo: str
    ) -> tuple:
        """Create iOS campaign."""
        self.tracker.update_step(campaign, "ios", "Cloning iOS template")
        campaign_id, campaign_name = await creator.create_ios_campaign(campaign, geo)
        return campaign_id, campaign_name
    
    async def _create_android(
        self,
        creator: CampaignCreator,
        campaign: CampaignDefinition,
        geo: str,
        ios_campaign_id: str
    ) -> tuple:
        """Create Android campaign."""
        self.tracker.update_step(campaign, "android", "Cloning iOS campaign")
        campaign_id, campaign_name = await creator.create_android_campaign(
            campaign, geo, ios_campaign_id
        )
        return campaign_id, campaign_name
    
    async def _upload_ads(
        self,
        page,
        campaign_id: str,
        campaign_name: str,
        csv_file: str
    ) -> int:
        """
        Upload ads using native uploader.
        
        Args:
            page: Playwright page (on ad creation page)
            campaign_id: Campaign ID
            campaign_name: Campaign name
            csv_file: CSV filename
            
        Returns:
            Number of ads uploaded
        """
        csv_path = self.csv_dir / csv_file
        
        # Use NativeAdUploader to upload ads
        uploader = NativeAdUploader(page, campaign_id)
        
        # Upload CSV
        ads_data = await uploader.load_and_process_csv(str(csv_path), campaign_name)
        ads_uploaded = await uploader.upload_ads(ads_data)
        
        # Save campaign after upload
        await page.click('button:text("Save Campaign")')
        await asyncio.sleep(2)
        
        return ads_uploaded


async def create_campaigns(
    batch: CampaignBatch,
    csv_dir: Path,
    session_file: Path,
    checkpoint_dir: Path,
    headless: bool = True,
    slow_mo: int = 500,
    verbose: bool = False
):
    """
    Create campaigns from batch.
    
    Args:
        batch: CampaignBatch to process
        csv_dir: Directory containing CSV ad files
        session_file: Path to browser session file
        checkpoint_dir: Directory for checkpoints
        headless: Run browser in headless mode
        slow_mo: Slow down operations (ms)
        verbose: Verbose output
    """
    orchestrator = CampaignOrchestrator(
        batch=batch,
        csv_dir=csv_dir,
        session_file=session_file,
        checkpoint_dir=checkpoint_dir,
        headless=headless,
        slow_mo=slow_mo,
        verbose=verbose
    )
    
    await orchestrator.run()


"""
Progress tracker with progress bars.

Provides visual feedback during campaign creation similar to the rename tool.
"""

import time
from typing import Optional, List
from datetime import datetime, timedelta

from .models import CampaignBatch, CampaignDefinition, CampaignStatus


class ProgressTracker:
    """Tracks and displays campaign creation progress."""
    
    def __init__(self, batch: CampaignBatch, verbose: bool = False):
        """
        Initialize progress tracker.
        
        Args:
            batch: CampaignBatch to track
            verbose: Enable verbose output
        """
        self.batch = batch
        self.verbose = verbose
        self.start_time = datetime.now()
        
        # Statistics
        self.total_variants = batch.total_variants
        self.completed_variants = 0
        self.failed_variants = 0
        self.skipped_variants = 0
        
        # Current operation
        self.current_campaign: Optional[CampaignDefinition] = None
        self.current_variant: Optional[str] = None
        self.current_step: Optional[str] = None
    
    def start_campaign(self, campaign: CampaignDefinition):
        """Mark campaign as started."""
        self.current_campaign = campaign
        campaign.status = CampaignStatus.IN_PROGRESS
        
        if self.verbose:
            print(f"\n{'='*65}")
            print(f"Starting Campaign Set: {campaign.group}")
            print(f"{'='*65}")
    
    def start_variant(self, campaign: CampaignDefinition, variant: str):
        """Mark variant as started."""
        self.current_variant = variant
        campaign.update_variant_status(variant, CampaignStatus.IN_PROGRESS)
        
        print(f"\n[{self._get_timestamp()}] Creating {variant.upper()} campaign...")
    
    def update_step(self, campaign: CampaignDefinition, variant: str, step: str):
        """Update current step."""
        self.current_step = step
        campaign.update_variant_status(variant, CampaignStatus.IN_PROGRESS, step=step)
        
        if self.verbose:
            print(f"  └─ {step}")
    
    def complete_variant(
        self,
        campaign: CampaignDefinition,
        variant: str,
        campaign_id: str,
        campaign_name: str,
        ads_uploaded: int
    ):
        """Mark variant as completed."""
        self.completed_variants += 1
        
        campaign.update_variant_status(
            variant,
            CampaignStatus.COMPLETED,
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            ads_uploaded=ads_uploaded,
            completed_at=datetime.now().isoformat()
        )
        
        elapsed = self._get_elapsed()
        print(f"  ✓ Created: {campaign_name} (ID: {campaign_id})")
        print(f"    Uploaded {ads_uploaded} ads | Elapsed: {elapsed}")
        
        self._print_progress()
    
    def fail_variant(
        self,
        campaign: CampaignDefinition,
        variant: str,
        error: str,
        step: Optional[str] = None
    ):
        """Mark variant as failed."""
        self.failed_variants += 1
        
        campaign.update_variant_status(
            variant,
            CampaignStatus.FAILED,
            error=error,
            step=step
        )
        
        print(f"  ✗ Failed: {error}")
        if step:
            print(f"    At step: {step}")
        
        self._print_progress()
    
    def skip_variant(self, campaign: CampaignDefinition, variant: str, reason: str):
        """Mark variant as skipped."""
        self.skipped_variants += 1
        
        campaign.update_variant_status(
            variant,
            CampaignStatus.SKIPPED,
            error=reason
        )
        
        print(f"  ⊗ Skipped: {reason}")
    
    def complete_campaign(self, campaign: CampaignDefinition):
        """Mark campaign set as completed."""
        campaign.status = CampaignStatus.COMPLETED
        
        if self.verbose:
            print(f"\n✓ Completed Campaign Set: {campaign.group}")
    
    def print_summary(self):
        """Print final summary."""
        elapsed = self._get_elapsed()
        
        print("\n" + "=" * 65)
        print("CAMPAIGN CREATION SUMMARY")
        print("=" * 65)
        
        print(f"\nTotal time: {elapsed}")
        print(f"Total campaign variants processed: {self.total_variants}")
        print(f"  ✓ Successfully created: {self.completed_variants}")
        
        if self.failed_variants > 0:
            print(f"  ✗ Failed: {self.failed_variants}")
        
        if self.skipped_variants > 0:
            print(f"  ⊗ Skipped: {self.skipped_variants}")
        
        # Success rate
        if self.total_variants > 0:
            success_rate = (self.completed_variants / self.total_variants) * 100
            print(f"\nSuccess rate: {success_rate:.1f}%")
        
        # Show failures
        if self.failed_variants > 0:
            print("\n" + "-" * 65)
            print("FAILED CAMPAIGNS")
            print("-" * 65)
            
            for campaign in self.batch.campaigns:
                for variant, status in campaign.variant_statuses.items():
                    if status.status == CampaignStatus.FAILED:
                        print(f"\n{campaign.group} ({variant})")
                        print(f"  Error: {status.error}")
                        if status.step:
                            print(f"  Failed at: {status.step}")
        
        # Show completed
        if self.completed_variants > 0:
            print("\n" + "-" * 65)
            print("SUCCESSFULLY CREATED CAMPAIGNS")
            print("-" * 65)
            
            for campaign in self.batch.campaigns:
                for variant, status in campaign.variant_statuses.items():
                    if status.status == CampaignStatus.COMPLETED:
                        print(f"  ✓ {status.campaign_name} (ID: {status.campaign_id})")
        
        print("\n" + "=" * 65 + "\n")
    
    def _print_progress(self):
        """Print progress bar."""
        processed = self.completed_variants + self.failed_variants + self.skipped_variants
        percent = (processed / self.total_variants * 100) if self.total_variants > 0 else 0
        
        bar_width = 40
        filled = int(bar_width * processed / self.total_variants) if self.total_variants > 0 else 0
        bar = "█" * filled + "░" * (bar_width - filled)
        
        elapsed = self._get_elapsed()
        
        # Estimate remaining time
        if processed > 0 and processed < self.total_variants:
            elapsed_seconds = (datetime.now() - self.start_time).total_seconds()
            avg_seconds = elapsed_seconds / processed
            remaining_seconds = avg_seconds * (self.total_variants - processed)
            remaining = self._format_duration(remaining_seconds)
            eta_str = f" | ETA: {remaining}"
        else:
            eta_str = ""
        
        print(f"\n[{bar}] {processed}/{self.total_variants} ({percent:.1f}%) | {elapsed}{eta_str}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp string."""
        return datetime.now().strftime("%H:%M:%S")
    
    def _get_elapsed(self) -> str:
        """Get elapsed time string."""
        elapsed_seconds = (datetime.now() - self.start_time).total_seconds()
        return self._format_duration(elapsed_seconds)
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human-readable string."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"


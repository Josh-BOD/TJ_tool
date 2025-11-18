"""Campaign mapping and batch processing manager."""

import logging
import pandas as pd
import time
from collections import deque
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from src.checkpoint import CheckpointManager

logger = logging.getLogger(__name__)


class Campaign:
    """Represents a single campaign upload task."""
    
    def __init__(self, campaign_id: str, csv_filename: str, campaign_name: str = "", enabled: bool = True):
        """
        Initialize campaign.
        
        Args:
            campaign_id: TrafficJunky campaign ID
            csv_filename: Name of CSV file to upload
            campaign_name: Friendly name for logging
            enabled: Whether this campaign should be processed
        """
        self.campaign_id = campaign_id
        self.csv_filename = csv_filename
        self.campaign_name = campaign_name or campaign_id
        self.enabled = enabled
        self.status = 'pending'
        self.ads_created = 0
        self.error = None
        self.invalid_creatives = []


class CampaignManager:
    """Manages campaign-CSV mappings and batch processing."""
    
    def __init__(self, mapping_file: Path, csv_input_dir: Path, checkpoint_file: Optional[Path] = None):
        """
        Initialize campaign manager.
        
        Args:
            mapping_file: Path to campaign mapping CSV
            csv_input_dir: Directory containing CSV files
            checkpoint_file: Optional path to checkpoint file for resume functionality
        """
        self.mapping_file = mapping_file
        self.csv_input_dir = csv_input_dir
        self.campaigns: List[Campaign] = []
        self.results: List[Dict] = []
        
        # Progress tracking
        self.start_time = None
        self.campaign_times = deque(maxlen=10)  # Track last 10 upload times for moving average
        self.completed_count = 0
        
        # Checkpoint management
        self.checkpoint = CheckpointManager(checkpoint_file) if checkpoint_file else None
        self.retry_failed = False
    
    def load_campaigns(self) -> bool:
        """
        Load campaigns from mapping file with validation.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            logger.info(f"Loading campaign mapping from {self.mapping_file}")
            
            if not self.mapping_file.exists():
                logger.error(f"❌ Mapping file not found: {self.mapping_file}")
                logger.error(f"   Create it at: data/input/campaign_mapping.csv")
                return False
            
            # Read mapping file with error handling
            try:
                df = pd.read_csv(self.mapping_file)
            except pd.errors.ParserError as e:
                logger.error(f"❌ CSV parsing error in {self.mapping_file}")
                logger.error(f"   {str(e)}")
                logger.error(f"   Common issues:")
                logger.error(f"   - Unmatched quotes in campaign_name")
                logger.error(f"   - Extra newlines in cells")
                logger.error(f"   - Missing commas between columns")
                return False
            except Exception as e:
                logger.error(f"❌ Failed to read mapping file: {e}")
                return False
            
            # Validate required columns
            required_cols = ['campaign_id', 'csv_filename']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.error(f"❌ Mapping file missing required columns: {missing_cols}")
                logger.error(f"   Found columns: {list(df.columns)}")
                logger.error(f"   Required format: campaign_id,csv_filename,campaign_name,enabled")
                return False
            
            # Validate and load campaigns
            errors_found = []
            campaign_ids_seen = set()
            
            for idx, row in df.iterrows():
                row_num = idx + 2  # +2 because: +1 for header, +1 for 0-index
                
                # Validate campaign_id
                try:
                    campaign_id = str(row['campaign_id']).strip()
                    if not campaign_id or campaign_id == 'nan':
                        errors_found.append(f"Row {row_num}: Empty campaign_id")
                        continue
                except:
                    errors_found.append(f"Row {row_num}: Invalid campaign_id")
                    continue
                
                # Check for duplicate campaign IDs
                if campaign_id in campaign_ids_seen:
                    errors_found.append(f"Row {row_num}: Duplicate campaign_id '{campaign_id}'")
                    continue
                campaign_ids_seen.add(campaign_id)
                
                # Validate csv_filename
                try:
                    csv_filename = str(row['csv_filename']).strip()
                    if not csv_filename or csv_filename == 'nan':
                        errors_found.append(f"Row {row_num}: Empty csv_filename for campaign {campaign_id}")
                        continue
                    # Check for invalid characters (quotes, newlines)
                    if '"' in csv_filename or '\n' in csv_filename:
                        errors_found.append(f"Row {row_num}: Invalid characters in csv_filename for campaign {campaign_id}")
                        continue
                except:
                    errors_found.append(f"Row {row_num}: Invalid csv_filename for campaign {campaign_id}")
                    continue
                
                # Parse enabled column (be flexible with TRUE/True/true/1)
                enabled_value = str(row.get('enabled', 'true')).strip().lower()
                if enabled_value in ['true', '1', 'yes', 't']:
                    enabled = True
                elif enabled_value in ['false', '0', 'no', 'f', 'nan', '']:
                    enabled = False
                else:
                    errors_found.append(f"Row {row_num}: Invalid 'enabled' value '{enabled_value}' for campaign {campaign_id} (use 'true' or 'false')")
                    enabled = False
                
                # Get campaign name (optional)
                campaign_name = str(row.get('campaign_name', '')).strip()
                if campaign_name == 'nan':
                    campaign_name = ''
                
                # Create campaign
                campaign = Campaign(
                    campaign_id=campaign_id,
                    csv_filename=csv_filename,
                    campaign_name=campaign_name,
                    enabled=enabled
                )
                
                # Verify CSV file exists
                csv_path = self.csv_input_dir / campaign.csv_filename
                if not csv_path.exists():
                    logger.warning(f"⚠️  Row {row_num}: CSV not found for campaign {campaign.campaign_id}: {csv_filename}")
                    campaign.enabled = False
                    campaign.error = f"CSV file not found: {campaign.csv_filename}"
                
                self.campaigns.append(campaign)
            
            # Report validation errors
            if errors_found:
                logger.error(f"❌ Found {len(errors_found)} validation error(s) in mapping file:")
                for error in errors_found[:10]:  # Show first 10 errors
                    logger.error(f"   {error}")
                if len(errors_found) > 10:
                    logger.error(f"   ... and {len(errors_found) - 10} more errors")
                logger.error(f"")
                logger.error(f"💡 Fix the errors in: {self.mapping_file}")
                logger.error(f"   Then run the tool again.")
                return False
            
            if len(self.campaigns) == 0:
                logger.error(f"❌ No valid campaigns found in mapping file")
                return False
            
            enabled_count = sum(1 for c in self.campaigns if c.enabled)
            logger.info(f"✓ Loaded {len(self.campaigns)} campaigns ({enabled_count} enabled)")
            
            # Show warning for disabled campaigns
            disabled = [c for c in self.campaigns if not c.enabled]
            if disabled:
                logger.info(f"⊘ Skipping {len(disabled)} disabled/invalid campaigns")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load campaigns: {e}")
            logger.exception("Detailed error:")
            return False
    
    def get_next_campaign(self) -> Optional[Campaign]:
        """
        Get next enabled campaign to process.
        
        Returns:
            Campaign object or None if no more campaigns
        """
        for campaign in self.campaigns:
            if campaign.enabled and campaign.status == 'pending':
                # If checkpoint exists, check if we should process this campaign
                if self.checkpoint:
                    if not self.checkpoint.should_process_campaign(campaign.campaign_id, self.retry_failed):
                        # Skip this campaign (already successful)
                        checkpoint_data = self.checkpoint.get_campaign_data(campaign.campaign_id)
                        if checkpoint_data and checkpoint_data.get('status') == 'success':
                            campaign.status = 'skipped'
                            campaign.ads_created = checkpoint_data.get('ads_created', 0)
                            logger.info(f"⊘ Skipping campaign {campaign.campaign_id} - already successful "
                                      f"({campaign.ads_created} ads)")
                        continue
                return campaign
        return None
    
    def get_csv_path(self, campaign: Campaign) -> Path:
        """Get full path to campaign's CSV file."""
        return self.csv_input_dir / campaign.csv_filename
    
    def mark_success(self, campaign: Campaign, ads_created: int):
        """Mark campaign as successfully processed."""
        campaign.status = 'success'
        campaign.ads_created = ads_created
        logger.info(f"✓ Campaign {campaign.campaign_id} ({campaign.campaign_name}): {ads_created} ads created")
        
        # Save to checkpoint
        if self.checkpoint:
            self.checkpoint.update_campaign(
                campaign.campaign_id,
                'success',
                ads_created=ads_created,
                campaign_name=campaign.campaign_name,
                csv_file=campaign.csv_filename
            )
    
    def mark_failed(self, campaign: Campaign, error: str, invalid_creatives: List[str] = None):
        """Mark campaign as failed."""
        campaign.status = 'failed'
        campaign.error = error
        if invalid_creatives:
            campaign.invalid_creatives = invalid_creatives
        logger.error(f"✗ Campaign {campaign.campaign_id} ({campaign.campaign_name}): {error}")
        
        # Save to checkpoint
        if self.checkpoint:
            self.checkpoint.update_campaign(
                campaign.campaign_id,
                'failed',
                error=error,
                campaign_name=campaign.campaign_name,
                csv_file=campaign.csv_filename,
                invalid_creatives_count=len(invalid_creatives) if invalid_creatives else 0
            )
    
    def mark_skipped(self, campaign: Campaign, reason: str):
        """Mark campaign as skipped."""
        campaign.status = 'skipped'
        campaign.error = reason
        logger.warning(f"⊘ Campaign {campaign.campaign_id} ({campaign.campaign_name}): {reason}")
    
    def start_tracking(self):
        """Start progress tracking."""
        self.start_time = time.time()
        self.completed_count = 0
        self.campaign_times.clear()
    
    def get_progress_stats(self) -> Dict:
        """
        Get current progress statistics.
        
        Returns:
            Dict with: total, completed, remaining, avg_time_per_campaign, eta_seconds, speed_cpm, elapsed
        """
        enabled_campaigns = [c for c in self.campaigns if c.enabled]
        total = len(enabled_campaigns)
        completed = sum(1 for c in enabled_campaigns if c.status in ['success', 'failed'])
        remaining = total - completed
        
        # Calculate average time per campaign (moving average of last 10)
        avg_time = sum(self.campaign_times) / len(self.campaign_times) if self.campaign_times else 0
        
        # Estimate remaining time
        eta_seconds = avg_time * remaining if avg_time > 0 else 0
        
        # Calculate current upload speed (campaigns per minute)
        elapsed = time.time() - self.start_time if self.start_time else 0
        speed_cpm = (completed / elapsed * 60) if elapsed > 0 and completed > 0 else 0
        
        return {
            'total': total,
            'completed': completed,
            'remaining': remaining,
            'avg_time_per_campaign': avg_time,
            'eta_seconds': eta_seconds,
            'speed_cpm': speed_cpm,
            'elapsed': elapsed
        }
    
    def record_campaign_time(self, duration: float):
        """Record time taken for a campaign."""
        self.campaign_times.append(duration)
        self.completed_count += 1
    
    def initialize_checkpoint(self, session_id: str, use_existing: bool = True):
        """
        Initialize checkpoint for tracking progress.
        
        Args:
            session_id: Unique session identifier
            use_existing: If True, load existing checkpoint; if False, start fresh
        """
        if not self.checkpoint:
            return
        
        # Try to load existing checkpoint
        if use_existing:
            loaded = self.checkpoint.load()
            if loaded:
                stats = self.checkpoint.get_stats()
                logger.info(f"📋 Resuming from checkpoint:")
                logger.info(f"   • {stats['success']} successful")
                logger.info(f"   • {stats['failed']} failed")
                logger.info(f"   • {stats['pending']} remaining")
                return
        
        # Initialize new checkpoint
        campaign_ids = [c.campaign_id for c in self.campaigns if c.enabled]
        self.checkpoint.initialize_session(session_id, campaign_ids)
        logger.info(f"📋 Checkpoint initialized - tracking {len(campaign_ids)} campaigns")
    
    def set_retry_failed(self, retry: bool):
        """
        Set whether to retry failed campaigns.
        
        Args:
            retry: If True, retry previously failed campaigns
        """
        self.retry_failed = retry
        if retry:
            logger.info("⟳ Will retry previously failed campaigns")
    
    def clear_checkpoint(self):
        """Clear checkpoint file."""
        if self.checkpoint:
            self.checkpoint.clear()
    
    def generate_summary_report(self, output_dir: Path) -> Path:
        """
        Generate summary report of all campaign uploads.
        
        Args:
            output_dir: Directory to save report
            
        Returns:
            Path to generated report
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = output_dir / f"upload_summary_{timestamp}.csv"
            
            # Prepare report data
            report_data = []
            for campaign in self.campaigns:
                report_data.append({
                    'campaign_id': campaign.campaign_id,
                    'campaign_name': campaign.campaign_name,
                    'csv_file': campaign.csv_filename,
                    'status': campaign.status,
                    'ads_created': campaign.ads_created,
                    'error': campaign.error or '',
                    'invalid_creatives_count': len(campaign.invalid_creatives),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            
            # Save report
            df = pd.DataFrame(report_data)
            df.to_csv(report_path, index=False)
            
            logger.info(f"✓ Summary report saved: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"Failed to generate summary report: {e}")
            return None
    
    def generate_invalid_creatives_report(self, output_dir: Path) -> Optional[Path]:
        """
        Generate report of invalid creatives that were removed.
        
        Args:
            output_dir: Directory to save report
            
        Returns:
            Path to generated report or None if no invalid creatives
        """
        try:
            # Check if any campaigns have invalid creatives
            has_invalid = any(len(c.invalid_creatives) > 0 for c in self.campaigns)
            if not has_invalid:
                logger.info("No invalid creatives to report")
                return None
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = output_dir / f"invalid_creatives_{timestamp}.csv"
            
            # Prepare report data
            report_data = []
            for campaign in self.campaigns:
                for creative_id in campaign.invalid_creatives:
                    report_data.append({
                        'campaign_id': campaign.campaign_id,
                        'campaign_name': campaign.campaign_name,
                        'creative_id': creative_id,
                        'error': 'Content category mismatch',
                        'action_required': 'Mark creative as "All" in TrafficJunky',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
            
            # Save report
            df = pd.DataFrame(report_data)
            df.to_csv(report_path, index=False)
            
            logger.info(f"✓ Invalid creatives report saved: {report_path}")
            logger.info(f"  Total invalid creatives: {len(report_data)}")
            
            return report_path
            
        except Exception as e:
            logger.error(f"Failed to generate invalid creatives report: {e}")
            return None
    
    def print_summary(self):
        """Print summary of all campaigns to console."""
        total = len(self.campaigns)
        success = sum(1 for c in self.campaigns if c.status == 'success')
        failed = sum(1 for c in self.campaigns if c.status == 'failed')
        skipped = sum(1 for c in self.campaigns if c.status == 'skipped')
        total_ads = sum(c.ads_created for c in self.campaigns)
        
        print("\n" + "="*60)
        print("UPLOAD SUMMARY")
        print("="*60)
        print(f"Total campaigns: {total}")
        print(f"✓ Successful:   {success}")
        print(f"✗ Failed:       {failed}")
        print(f"⊘ Skipped:      {skipped}")
        print(f"📊 Total ads created: {total_ads}")
        print("="*60)
        
        if failed > 0:
            print("\nFailed campaigns:")
            for campaign in self.campaigns:
                if campaign.status == 'failed':
                    print(f"  ✗ {campaign.campaign_id} ({campaign.campaign_name}): {campaign.error}")
        
        if any(c.invalid_creatives for c in self.campaigns):
            total_invalid = sum(len(c.invalid_creatives) for c in self.campaigns)
            print(f"\n⚠️  {total_invalid} invalid creative(s) found - check invalid_creatives report")
        
        print()


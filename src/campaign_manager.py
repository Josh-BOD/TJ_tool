"""Campaign mapping and batch processing manager."""

import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

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
    
    def __init__(self, mapping_file: Path, csv_input_dir: Path):
        """
        Initialize campaign manager.
        
        Args:
            mapping_file: Path to campaign mapping CSV
            csv_input_dir: Directory containing CSV files
        """
        self.mapping_file = mapping_file
        self.csv_input_dir = csv_input_dir
        self.campaigns: List[Campaign] = []
        self.results: List[Dict] = []
    
    def load_campaigns(self) -> bool:
        """
        Load campaigns from mapping file.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            logger.info(f"Loading campaign mapping from {self.mapping_file}")
            
            if not self.mapping_file.exists():
                logger.error(f"Mapping file not found: {self.mapping_file}")
                return False
            
            # Read mapping file
            df = pd.read_csv(self.mapping_file)
            
            # Validate required columns
            required_cols = ['campaign_id', 'csv_filename']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"Mapping file missing required columns: {required_cols}")
                return False
            
            # Load campaigns
            for _, row in df.iterrows():
                campaign = Campaign(
                    campaign_id=str(row['campaign_id']),
                    csv_filename=row['csv_filename'],
                    campaign_name=row.get('campaign_name', ''),
                    enabled=str(row.get('enabled', 'true')).lower() == 'true'
                )
                
                # Verify CSV file exists
                csv_path = self.csv_input_dir / campaign.csv_filename
                if not csv_path.exists():
                    logger.warning(f"CSV not found for campaign {campaign.campaign_id}: {csv_path}")
                    campaign.enabled = False
                    campaign.error = f"CSV file not found: {campaign.csv_filename}"
                
                self.campaigns.append(campaign)
            
            enabled_count = sum(1 for c in self.campaigns if c.enabled)
            logger.info(f"✓ Loaded {len(self.campaigns)} campaigns ({enabled_count} enabled)")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load campaigns: {e}")
            return False
    
    def get_next_campaign(self) -> Optional[Campaign]:
        """
        Get next enabled campaign to process.
        
        Returns:
            Campaign object or None if no more campaigns
        """
        for campaign in self.campaigns:
            if campaign.enabled and campaign.status == 'pending':
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
    
    def mark_failed(self, campaign: Campaign, error: str, invalid_creatives: List[str] = None):
        """Mark campaign as failed."""
        campaign.status = 'failed'
        campaign.error = error
        if invalid_creatives:
            campaign.invalid_creatives = invalid_creatives
        logger.error(f"✗ Campaign {campaign.campaign_id} ({campaign.campaign_name}): {error}")
    
    def mark_skipped(self, campaign: Campaign, reason: str):
        """Mark campaign as skipped."""
        campaign.status = 'skipped'
        campaign.error = reason
        logger.warning(f"⊘ Campaign {campaign.campaign_id} ({campaign.campaign_name}): {reason}")
    
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


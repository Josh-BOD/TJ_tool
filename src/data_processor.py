"""Data processing and campaign categorization logic."""

from typing import Dict, List
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CampaignMetrics:
    """Calculated metrics for a campaign."""
    campaign_id: int
    campaign_name: str
    campaign_type: str
    status: str
    
    # Raw metrics from API
    spend: float
    conversions: int
    clicks: int
    impressions: int
    ctr: float
    cpm: float
    daily_budget: float
    daily_budget_left: float
    
    # Calculated metrics
    ecpa: float
    cvr: float
    budget_velocity: float
    daily_spend: float
    
    # URLs
    overview_url: str
    
    def __str__(self) -> str:
        return f"Campaign({self.campaign_name}, eCPA: ${self.ecpa:.2f}, Conv: {self.conversions}, Spend: ${self.spend:.2f})"


class CampaignCategorizer:
    """Categorizes campaigns based on performance thresholds."""
    
    # Category thresholds (from user requirements)
    CATEGORY_RULES = {
        'what_to_do_more_of': {
            'ecpa_max': 50.0,
            'conversions_min': 5,
            'spend_min': 250.0
        },
        'to_watch': {
            'ecpa_min': 100.0,
            'ecpa_max': 200.0,
            'conversions_min': 3,
            'spend_min': 250.0,
            'budget_velocity_min': 70.0,
            'budget_velocity_max': 90.0
        },
        'scaled': {
            'ecpa_max': 60.0,
            'budget_velocity_min': 95.0  # Hitting budget limits
        },
        'killed': {
            'ecpa_min': 120.0,
            'spend_min': 250.0,
            'budget_velocity_max': 60.0,
            'zero_conversions_spend_threshold': 250.0
        }
    }
    
    @staticmethod
    def calculate_metrics(campaign_data: Dict) -> CampaignMetrics:
        """
        Calculate all derived metrics for a campaign.
        
        Args:
            campaign_data: Raw campaign data from API
            
        Returns:
            CampaignMetrics object with all calculated fields
        """
        # Extract raw metrics (handle various API formats)
        campaign_id = campaign_data.get('campaignId', 0)
        campaign_name = campaign_data.get('campaignName', 'Unknown')
        campaign_type = campaign_data.get('campaignType', 'unknown')
        status = campaign_data.get('status', 'unknown')
        
        spend = float(campaign_data.get('cost', 0))
        conversions = int(campaign_data.get('conversions', 0))
        clicks = int(campaign_data.get('clicks', 0))
        
        # Impressions might be string or int
        impressions_raw = campaign_data.get('impressions', 0)
        impressions = int(impressions_raw) if impressions_raw else 0
        
        ctr = float(campaign_data.get('CTR', 0))
        cpm = float(campaign_data.get('CPM', 0))
        daily_budget = float(campaign_data.get('dailyBudget', 0))
        daily_budget_left = float(campaign_data.get('dailyBudgetLeft', 0))
        
        # Calculate derived metrics
        ecpa = spend / conversions if conversions > 0 else 0
        cvr = (conversions / clicks * 100) if clicks > 0 else 0
        
        # Daily spend calculation
        daily_spend = daily_budget - daily_budget_left if daily_budget > 0 else spend
        
        # Budget velocity (as percentage)
        budget_velocity = (daily_spend / daily_budget * 100) if daily_budget > 0 else 0
        
        # Campaign overview URL
        overview_url = f"https://advertiser.trafficjunky.com/campaign/overview/{campaign_id}"
        
        return CampaignMetrics(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            campaign_type=campaign_type,
            status=status,
            spend=spend,
            conversions=conversions,
            clicks=clicks,
            impressions=impressions,
            ctr=ctr,
            cpm=cpm,
            daily_budget=daily_budget,
            daily_budget_left=daily_budget_left,
            ecpa=ecpa,
            cvr=cvr,
            budget_velocity=budget_velocity,
            daily_spend=daily_spend,
            overview_url=overview_url
        )
    
    @classmethod
    def categorize_campaign(cls, metrics: CampaignMetrics) -> List[str]:
        """
        Categorize a campaign based on performance metrics.
        
        A campaign can belong to multiple categories.
        
        Args:
            metrics: CampaignMetrics object
            
        Returns:
            List of category names the campaign belongs to
        """
        categories = []
        
        # What to do more of: Great performance
        rules = cls.CATEGORY_RULES['what_to_do_more_of']
        if (metrics.ecpa > 0 and metrics.ecpa < rules['ecpa_max'] and
            metrics.conversions >= rules['conversions_min'] and
            metrics.spend >= rules['spend_min']):
            categories.append('what_to_do_more_of')
        
        # To Watch: Borderline performance, needs tweaking
        rules = cls.CATEGORY_RULES['to_watch']
        if (metrics.ecpa >= rules['ecpa_min'] and metrics.ecpa <= rules['ecpa_max'] and
            metrics.conversions >= rules['conversions_min'] and
            metrics.spend >= rules['spend_min'] and
            rules['budget_velocity_min'] <= metrics.budget_velocity <= rules['budget_velocity_max']):
            categories.append('to_watch')
        
        # Scaled: Hitting budget limits with good eCPA
        rules = cls.CATEGORY_RULES['scaled']
        if (metrics.ecpa > 0 and metrics.ecpa < rules['ecpa_max'] and
            metrics.budget_velocity >= rules['budget_velocity_min']):
            categories.append('scaled')
        
        # Killed: Poor performance
        rules = cls.CATEGORY_RULES['killed']
        killed_conditions = [
            # High eCPA with significant spend
            (metrics.ecpa >= rules['ecpa_min'] and metrics.spend >= rules['spend_min'] and
             metrics.budget_velocity <= rules['budget_velocity_max']),
            # Zero conversions after significant spend
            (metrics.conversions == 0 and metrics.spend >= rules['zero_conversions_spend_threshold'])
        ]
        if any(killed_conditions):
            categories.append('killed')
        
        return categories
    
    @staticmethod
    def filter_active_campaigns(campaigns: List[CampaignMetrics], min_spend: float = 100.0, min_impressions: int = 100) -> List[CampaignMetrics]:
        """
        Filter campaigns by minimum activity thresholds.
        
        Args:
            campaigns: List of CampaignMetrics
            min_spend: Minimum spend to include (default: $100)
            min_impressions: Minimum impressions to include (default: 100)
            
        Returns:
            Filtered list of campaigns
        """
        filtered = []
        for campaign in campaigns:
            # Only include active campaigns
            if campaign.status.lower() != 'active':
                logger.debug(f"Skipping {campaign.campaign_name} - status: {campaign.status}")
                continue
            
            # Check minimum spend
            if campaign.spend < min_spend:
                logger.debug(f"Skipping {campaign.campaign_name} - spend ${campaign.spend:.2f} < ${min_spend}")
                continue
            
            # Check minimum impressions
            if campaign.impressions < min_impressions:
                logger.debug(f"Skipping {campaign.campaign_name} - impressions {campaign.impressions} < {min_impressions}")
                continue
            
            # Exclude campaigns with zero spend
            if campaign.spend == 0:
                logger.debug(f"Skipping {campaign.campaign_name} - zero spend")
                continue
            
            filtered.append(campaign)
        
        logger.info(f"Filtered {len(campaigns)} campaigns to {len(filtered)} active campaigns")
        return filtered


class DataProcessor:
    """Main data processing orchestrator."""
    
    def __init__(self):
        self.categorizer = CampaignCategorizer()
    
    def process_campaigns(self, raw_campaigns: List[Dict]) -> Dict[str, List[CampaignMetrics]]:
        """
        Process raw campaign data and categorize.
        
        Args:
            raw_campaigns: List of raw campaign data from API
            
        Returns:
            Dictionary with category names as keys and lists of campaigns as values
            {
                'what_to_do_more_of': [...],
                'to_watch': [...],
                'scaled': [...],
                'killed': [...],
                'uncategorized': [...]
            }
        """
        logger.info(f"Processing {len(raw_campaigns)} campaigns")
        
        # Calculate metrics for all campaigns
        all_metrics = []
        for campaign_data in raw_campaigns:
            try:
                metrics = self.categorizer.calculate_metrics(campaign_data)
                all_metrics.append(metrics)
            except Exception as e:
                campaign_name = campaign_data.get('campaignName', 'Unknown')
                logger.error(f"Error processing campaign {campaign_name}: {e}")
                continue
        
        # Filter to active campaigns only
        active_campaigns = self.categorizer.filter_active_campaigns(all_metrics)
        
        # Categorize campaigns
        categorized = {
            'what_to_do_more_of': [],
            'to_watch': [],
            'scaled': [],
            'killed': [],
            'uncategorized': []
        }
        
        for metrics in active_campaigns:
            categories = self.categorizer.categorize_campaign(metrics)
            
            if not categories:
                categorized['uncategorized'].append(metrics)
            else:
                for category in categories:
                    categorized[category].append(metrics)
        
        # Sort each category by spend (highest first)
        for category in categorized:
            categorized[category].sort(key=lambda x: x.spend, reverse=True)
        
        # Log summary
        logger.info(f"Categorization complete:")
        for category, campaigns in categorized.items():
            logger.info(f"  {category}: {len(campaigns)} campaigns")
        
        return categorized


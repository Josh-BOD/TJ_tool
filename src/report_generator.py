"""Generate markdown performance reports for Slack Canvas."""

from datetime import datetime
from typing import Dict, List
import logging
from pathlib import Path
from src.data_processor import CampaignMetrics
from config.config import Config

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate formatted markdown reports from campaign data."""
    
    # Category display names and emojis
    CATEGORY_DISPLAY = {
        'what_to_do_more_of': ('What to do more of', '🟢'),
        'to_watch': ('To Watch', '🟡'),
        'scaled': ('Scaled', '📈'),
        'killed': ('Killed', '❌'),
        'uncategorized': ('Other', '⚪')
    }
    
    # Category criteria descriptions
    CATEGORY_CRITERIA = {
        'what_to_do_more_of': '*eCPA < $50 | Conversions > 5 | Spend > $250*',
        'to_watch': '*eCPA $100-$200 | Conversions > 3 | Spend > $250 | Budget Velocity 70-90%*',
        'scaled': '*eCPA < $60 | Budget Velocity > 95% (hitting limits)*',
        'killed': '*eCPA > $120 + Spend > $250 + Velocity < 60% | OR Zero conversions after $250 spend*',
        'uncategorized': '*Does not meet any category criteria*'
    }
    
    def __init__(self, output_dir: Path = None):
        """
        Initialize report generator.
        
        Args:
            output_dir: Directory to save reports. Defaults to Config.REPORT_OUTPUT_DIR
        """
        self.output_dir = output_dir or Config.REPORT_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def format_campaign_line(self, campaign: CampaignMetrics) -> str:
        """
        Format a single campaign as a markdown line.
        
        Format: [Campaign_Name](URL) - eCPA: $X.XX | Conv: X | Spend: $X.XX
        
        Args:
            campaign: CampaignMetrics object
            
        Returns:
            Formatted markdown string
        """
        return (
            f"[{campaign.campaign_name}]({campaign.overview_url}) - "
            f"eCPA: ${campaign.ecpa:.2f} | "
            f"Conv: {campaign.conversions} | "
            f"Spend: ${campaign.spend:.2f}"
        )
    
    def generate_category_section(self, category_name: str, campaigns: List[CampaignMetrics], show_empty: bool = True) -> str:
        """
        Generate markdown section for a category.
        
        Args:
            category_name: Internal category name (e.g., 'what_to_do_more_of')
            campaigns: List of campaigns in this category
            show_empty: Whether to show section if empty
            
        Returns:
            Markdown formatted section
        """
        if not campaigns and not show_empty:
            return ""
        
        display_name, emoji = self.CATEGORY_DISPLAY.get(category_name, (category_name.title(), ''))
        criteria = self.CATEGORY_CRITERIA.get(category_name, '')
        
        lines = [f"## {display_name} {emoji}"]
        
        # Add criteria description
        if criteria:
            lines.append(criteria)
        
        lines.append("")  # Empty line before campaigns
        
        if not campaigns:
            lines.append("None")
        else:
            for campaign in campaigns:
                lines.append(f"- {self.format_campaign_line(campaign)}")
        
        lines.append("")  # Empty line after section
        return "\n".join(lines)
    
    def calculate_summary_stats(self, categorized_campaigns: Dict[str, List[CampaignMetrics]]) -> Dict:
        """
        Calculate summary statistics across all campaigns.
        
        Args:
            categorized_campaigns: Dictionary of categorized campaigns
            
        Returns:
            Dictionary with summary stats
        """
        all_campaigns = []
        for campaigns in categorized_campaigns.values():
            all_campaigns.extend(campaigns)
        
        if not all_campaigns:
            return {
                'total_campaigns': 0,
                'total_spend': 0,
                'total_conversions': 0,
                'average_ecpa': 0,
                'total_clicks': 0,
                'total_impressions': 0
            }
        
        total_spend = sum(c.spend for c in all_campaigns)
        total_conversions = sum(c.conversions for c in all_campaigns)
        total_clicks = sum(c.clicks for c in all_campaigns)
        total_impressions = sum(c.impressions for c in all_campaigns)
        
        average_ecpa = total_spend / total_conversions if total_conversions > 0 else 0
        
        return {
            'total_campaigns': len(all_campaigns),
            'total_spend': total_spend,
            'total_conversions': total_conversions,
            'average_ecpa': average_ecpa,
            'total_clicks': total_clicks,
            'total_impressions': total_impressions
        }
    
    def calculate_budget_utilization(self, categorized_campaigns: Dict[str, List[CampaignMetrics]]) -> Dict:
        """
        Calculate budget utilization stats.
        
        Args:
            categorized_campaigns: Dictionary of categorized campaigns
            
        Returns:
            Dictionary with budget stats
        """
        all_campaigns = []
        for campaigns in categorized_campaigns.values():
            all_campaigns.extend(campaigns)
        
        if not all_campaigns:
            return {
                'total_budget': 0,
                'total_spent': 0,
                'avg_velocity': 0
            }
        
        total_budget = sum(c.daily_budget for c in all_campaigns if c.daily_budget > 0)
        total_spent = sum(c.daily_spend for c in all_campaigns)
        
        avg_velocity = (total_spent / total_budget * 100) if total_budget > 0 else 0
        
        return {
            'total_budget': total_budget,
            'total_spent': total_spent,
            'avg_velocity': avg_velocity
        }
    
    def generate_summary_section(self, categorized_campaigns: Dict[str, List[CampaignMetrics]]) -> str:
        """
        Generate summary statistics section.
        
        Args:
            categorized_campaigns: Dictionary of categorized campaigns
            
        Returns:
            Markdown formatted summary
        """
        stats = self.calculate_summary_stats(categorized_campaigns)
        budget = self.calculate_budget_utilization(categorized_campaigns)
        
        lines = [
            "## Summary 📊\n",
            f"**Total Campaigns:** {stats['total_campaigns']}",
            f"**Total Spend:** ${stats['total_spend']:.2f}",
            f"**Total Conversions:** {stats['total_conversions']}",
            f"**Average eCPA:** ${stats['average_ecpa']:.2f}",
            f"**Budget Utilization:** {budget['avg_velocity']:.1f}% (${budget['total_spent']:.2f} / ${budget['total_budget']:.2f})",
            ""
        ]
        
        return "\n".join(lines)
    
    def generate_report(
        self, 
        categorized_campaigns: Dict[str, List[CampaignMetrics]],
        period: str,
        start_date: datetime,
        end_date: datetime,
        include_summary: bool = True,
        show_empty_categories: bool = True
    ) -> str:
        """
        Generate complete markdown report.
        
        Args:
            categorized_campaigns: Dictionary of categorized campaigns
            period: Time period description (e.g., 'today', 'yesterday')
            start_date: Start date of reporting period
            end_date: End date of reporting period
            include_summary: Whether to include summary stats
            show_empty_categories: Whether to show empty categories
            
        Returns:
            Complete markdown report as string
        """
        # Header
        date_str = start_date.strftime("%d-%m-%Y")
        if start_date != end_date:
            date_str += f" to {end_date.strftime('%d-%m-%Y')}"
        
        lines = [
            f"# Campaign Performance Report - {date_str}\n",
            f"**Period:** {period.title()}",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')}",
            ""
        ]
        
        # Summary section
        if include_summary:
            lines.append(self.generate_summary_section(categorized_campaigns))
        
        # Category sections (in order)
        category_order = ['what_to_do_more_of', 'to_watch', 'scaled', 'killed']
        
        for category in category_order:
            campaigns = categorized_campaigns.get(category, [])
            section = self.generate_category_section(category, campaigns, show_empty=show_empty_categories)
            if section:
                lines.append(section)
        
        # Uncategorized (if any and if showing empty)
        if show_empty_categories or categorized_campaigns.get('uncategorized'):
            section = self.generate_category_section('uncategorized', categorized_campaigns.get('uncategorized', []), show_empty=show_empty_categories)
            if section:
                lines.append(section)
        
        # Footer
        lines.extend([
            "---",
            "",
            "*Generated by TrafficJunky Performance Analysis Tool*"
        ])
        
        return "\n".join(lines)
    
    def save_report(
        self, 
        report_content: str,
        filename: str = None,
        start_date: datetime = None
    ) -> Path:
        """
        Save report to file.
        
        Args:
            report_content: Markdown content to save
            filename: Optional custom filename. If not provided, uses date-based naming
            start_date: Start date for auto-generated filename (DD-MM-YYYY format)
            
        Returns:
            Path to saved file
        """
        if not filename:
            if start_date:
                date_str = start_date.strftime("%d-%m-%Y")
            else:
                date_str = datetime.now().strftime("%d-%m-%Y")
            filename = f"tj_analysis_{date_str}.md"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"Report saved to: {filepath}")
        return filepath
    
    def generate_and_save(
        self,
        categorized_campaigns: Dict[str, List[CampaignMetrics]],
        period: str,
        start_date: datetime,
        end_date: datetime,
        filename: str = None,
        include_summary: bool = True
    ) -> Path:
        """
        Generate report and save to file in one step.
        
        Args:
            categorized_campaigns: Dictionary of categorized campaigns
            period: Time period description
            start_date: Start date of reporting period
            end_date: End date of reporting period
            filename: Optional custom filename
            include_summary: Whether to include summary stats
            
        Returns:
            Path to saved file
        """
        report = self.generate_report(
            categorized_campaigns,
            period,
            start_date,
            end_date,
            include_summary=include_summary
        )
        
        return self.save_report(report, filename=filename, start_date=start_date)


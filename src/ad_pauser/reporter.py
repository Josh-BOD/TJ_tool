"""Report generation for ad pausing operations."""

import logging
from pathlib import Path
from datetime import datetime
from typing import Dict

from .models import PauseBatch

logger = logging.getLogger(__name__)


def generate_pause_report(batch: PauseBatch, output_dir: Path) -> Path:
    """
    Generate a markdown report of the pause operation.
    
    Args:
        batch: PauseBatch with results
        output_dir: Directory to save report (default: ./data/reports)
        
    Returns:
        Path to generated report file
    """
    try:
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"pause_report_{timestamp}.md"
        report_path = output_dir / report_filename
        
        logger.info(f"Generating pause report: {report_filename}")
        
        # Mark end time if not already set
        if not batch.end_time:
            batch.end_time = datetime.now()
        
        # Build report content
        report_lines = []
        
        # Header
        report_lines.append(f"# Ad Pause Report")
        report_lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if batch.dry_run:
            report_lines.append(f"\n**⚠️ DRY RUN MODE** - No ads were actually paused")
        
        report_lines.append("\n---\n")
        
        # Summary Section
        report_lines.append("## Summary\n")
        report_lines.append(f"- **Total Campaigns Processed:** {batch.total_campaigns_processed}")
        report_lines.append(f"- **Total Ads Paused:** {batch.total_ads_paused}")
        report_lines.append(f"- **Total Creative IDs Requested:** {len(batch.creative_ids)}")
        report_lines.append(f"- **Duration:** {_format_duration(batch.duration_seconds)}")
        report_lines.append(f"- **Successful Campaigns:** {batch.successful_campaigns}")
        report_lines.append(f"- **Partial Success:** {batch.partial_campaigns}")
        report_lines.append(f"- **Failed Campaigns:** {batch.failed_campaigns}")
        
        report_lines.append("\n---\n")
        
        # Campaign Results Section
        report_lines.append("## Campaign Results\n")
        
        for i, result in enumerate(batch.results, 1):
            # Status icon
            if result.status == 'success':
                status_icon = "✓"
            elif result.status == 'partial':
                status_icon = "⚠"
            else:
                status_icon = "✗"
            
            report_lines.append(f"### {i}. Campaign {result.campaign_id}")
            if result.campaign_name != result.campaign_id:
                report_lines.append(f"**Name:** {result.campaign_name}")
            
            report_lines.append(f"\n- **Status:** {status_icon} {result.status.upper()}")
            report_lines.append(f"- **Time Taken:** {result.time_taken:.1f}s")
            report_lines.append(f"- **Pages Processed:** {result.pages_processed}")
            report_lines.append(f"- **Ads Found:** {len(result.ads_found)}/{len(batch.creative_ids)}")
            report_lines.append(f"- **Ads Paused:** {len(result.ads_paused)}")
            
            # Paused Creative IDs
            if result.ads_paused:
                report_lines.append(f"\n**Paused Creative IDs:** ({len(result.ads_paused)})")
                for creative_id in sorted(result.ads_paused):
                    report_lines.append(f"- {creative_id}")
            
            # Not Found Creative IDs
            if result.ads_not_found:
                report_lines.append(f"\n**Not Found in Campaign:** ({len(result.ads_not_found)})")
                for creative_id in sorted(result.ads_not_found):
                    report_lines.append(f"- {creative_id}")
            
            # Errors
            if result.errors:
                report_lines.append(f"\n**Errors:** ({len(result.errors)})")
                for error in result.errors:
                    report_lines.append(f"- {error}")
            
            report_lines.append("\n---\n")
        
        # Creative IDs Not Found Across All Campaigns
        not_found_all = batch.get_all_not_found()
        if not_found_all:
            report_lines.append("## Creative IDs Not Found Across All Campaigns\n")
            report_lines.append(f"The following Creative IDs were not found in any of the {batch.total_campaigns_processed} campaigns:\n")
            
            for creative_id in sorted(not_found_all.keys()):
                count = not_found_all[creative_id]
                report_lines.append(f"- **{creative_id}** (searched in {count} campaign{'s' if count > 1 else ''})")
            
            report_lines.append("\n---\n")
        
        # Detailed Statistics
        report_lines.append("## Detailed Statistics\n")
        
        total_found = sum(len(r.ads_found) for r in batch.results)
        total_paused = batch.total_ads_paused
        total_requested = len(batch.creative_ids) * batch.total_campaigns_processed
        
        report_lines.append(f"- **Total Creative IDs Requested:** {len(batch.creative_ids)}")
        report_lines.append(f"- **Total Search Operations:** {total_requested} ({len(batch.creative_ids)} IDs × {batch.total_campaigns_processed} campaigns)")
        report_lines.append(f"- **Total Matches Found:** {total_found}")
        report_lines.append(f"- **Total Ads Paused:** {total_paused}")
        report_lines.append(f"- **Success Rate:** {(total_paused / total_found * 100) if total_found > 0 else 0:.1f}%")
        
        if batch.total_ads_paused > 0:
            avg_time_per_ad = batch.duration_seconds / batch.total_ads_paused
            report_lines.append(f"- **Average Time per Ad Paused:** {avg_time_per_ad:.2f}s")
        
        if batch.total_campaigns_processed > 0:
            avg_time_per_campaign = batch.duration_seconds / batch.total_campaigns_processed
            report_lines.append(f"- **Average Time per Campaign:** {avg_time_per_campaign:.1f}s")
        
        report_lines.append("\n---\n")
        
        # Footer
        report_lines.append(f"\n*Report generated by Pause_ads_V1.py*")
        report_lines.append(f"\n*Start Time: {batch.start_time.strftime('%Y-%m-%d %H:%M:%S')}*")
        report_lines.append(f"\n*End Time: {batch.end_time.strftime('%Y-%m-%d %H:%M:%S')}*")
        
        # Write report to file
        report_content = "\n".join(report_lines)
        report_path.write_text(report_content)
        
        logger.info(f"✓ Report saved to: {report_path}")
        
        return report_path
        
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise


def _format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "2m 34s" or "45s")
    """
    if seconds < 60:
        return f"{seconds:.0f}s"
    
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    
    if minutes < 60:
        return f"{minutes}m {secs}s"
    
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}h {mins}m {secs}s"


def print_summary_to_console(batch: PauseBatch):
    """
    Print a summary of results to console.
    
    Args:
        batch: PauseBatch with results
    """
    print("\n" + "="*70)
    print("PAUSE OPERATION SUMMARY")
    print("="*70)
    
    if batch.dry_run:
        print("\n⚠️  DRY RUN MODE - No ads were actually paused")
    
    print(f"\nCampaigns Processed: {batch.total_campaigns_processed}")
    print(f"Ads Paused: {batch.total_ads_paused}")
    print(f"Duration: {_format_duration(batch.duration_seconds)}")
    
    # Successful campaigns
    if batch.successful_campaigns > 0:
        print(f"\n✓ {batch.successful_campaigns} campaign(s) - FULL SUCCESS")
        for result in batch.results:
            if result.status == 'success':
                print(f"  • {result.campaign_name} - {len(result.ads_paused)} ads paused")
    
    # Partial campaigns
    if batch.partial_campaigns > 0:
        print(f"\n⚠ {batch.partial_campaigns} campaign(s) - PARTIAL SUCCESS")
        for result in batch.results:
            if result.status == 'partial':
                print(f"  • {result.campaign_name} - {len(result.ads_paused)}/{len(result.ads_found)} ads paused")
    
    # Failed campaigns
    if batch.failed_campaigns > 0:
        print(f"\n✗ {batch.failed_campaigns} campaign(s) - FAILED")
        for result in batch.results:
            if result.status == 'failed':
                error_msg = result.errors[0] if result.errors else "Unknown error"
                print(f"  • {result.campaign_name} - {error_msg}")
    
    # Not found summary
    not_found_all = batch.get_all_not_found()
    if not_found_all:
        print(f"\n⚠ {len(not_found_all)} Creative ID(s) not found in any campaign:")
        for creative_id in sorted(not_found_all.keys())[:10]:  # Show first 10
            print(f"  • {creative_id}")
        if len(not_found_all) > 10:
            print(f"  ... and {len(not_found_all) - 10} more")
    
    print("\n" + "="*70)


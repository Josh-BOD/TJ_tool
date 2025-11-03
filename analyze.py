#!/usr/bin/env python3
"""
TrafficJunky Campaign Performance Analysis Tool

Fetches campaign data from TrafficJunky API, analyzes performance,
and generates categorized markdown reports for Slack Canvas.
"""

import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.config import Config
from src.api_client import TrafficJunkyAPIClient
from src.data_processor import DataProcessor
from src.report_generator import ReportGenerator
from colorama import Fore, Style, init

# Initialize colorama for colored output
init(autoreset=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Config.LOG_DIR / 'analyze.log')
    ]
)
logger = logging.getLogger(__name__)


def print_header():
    """Print tool header."""
    print("\n" + "=" * 70)
    print(f"{Fore.CYAN}TrafficJunky Campaign Performance Analysis Tool{Style.RESET_ALL}")
    print("=" * 70 + "\n")


def print_success(message: str):
    """Print success message."""
    print(f"{Fore.GREEN}✓{Style.RESET_ALL} {message}")


def print_error(message: str):
    """Print error message."""
    print(f"{Fore.RED}✗{Style.RESET_ALL} {message}")


def print_info(message: str):
    """Print info message."""
    print(f"{Fore.BLUE}ℹ{Style.RESET_ALL} {message}")


def print_warning(message: str):
    """Print warning message."""
    print(f"{Fore.YELLOW}⚠{Style.RESET_ALL} {message}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Analyze TrafficJunky campaign performance and generate reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze.py                    # Use default period (today)
  python analyze.py --period yesterday # Yesterday's performance
  python analyze.py --period last7days # Last 7 days
  python analyze.py --test-api         # Test API connection
  python analyze.py --period today --output my_report.md
        """
    )
    
    parser.add_argument(
        '--period',
        choices=['yesterday', 'last7days', 'last30days'],
        default=Config.DEFAULT_TIME_PERIOD,
        help='Time period to analyze (default: yesterday)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Custom output filename (default: tj_analysis_DD-MM-YYYY.md)'
    )
    
    parser.add_argument(
        '--no-summary',
        action='store_true',
        help='Exclude summary statistics from report'
    )
    
    parser.add_argument(
        '--hide-empty',
        action='store_true',
        help='Hide empty categories in report'
    )
    
    parser.add_argument(
        '--test-api',
        action='store_true',
        help='Test API connection and exit'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print_header()
    
    # Validate configuration
    print_info("Validating configuration...")
    errors = Config.validate()
    
    if not Config.TJ_API_KEY:
        print_error("TJ_API_KEY not set in .env file")
        print_info("Please add your TrafficJunky API key to .env:")
        print_info("  1. Log into TrafficJunky dashboard")
        print_info("  2. Go to Profile > API Token")
        print_info("  3. Generate/copy token and add to .env: TJ_API_KEY=your_key")
        return 1
    
    if errors:
        for error in errors:
            print_error(error)
        return 1
    
    print_success("Configuration valid")
    
    # Initialize API client
    try:
        print_info("Initializing TrafficJunky API client...")
        api_client = TrafficJunkyAPIClient()
        print_success("API client initialized")
    except Exception as e:
        print_error(f"Failed to initialize API client: {e}")
        return 1
    
    # Test API connection if requested
    if args.test_api:
        print_info("Testing API connection...")
        if api_client.test_connection():
            print_success("API connection successful!")
            return 0
        else:
            print_error("API connection failed")
            return 1
    
    # Get date range
    try:
        start_date, end_date = api_client.get_date_range(args.period)
        print_info(f"Analyzing period: {args.period}")
        print_info(f"  Start: {start_date.strftime('%d/%m/%Y')}")
        print_info(f"  End: {end_date.strftime('%d/%m/%Y')}")
    except ValueError as e:
        print_error(str(e))
        return 1
    
    # Fetch campaign data
    try:
        print_info("Fetching campaign data from TrafficJunky API...")
        raw_campaigns = api_client.get_campaigns_stats(start_date, end_date, limit=500)
        print_success(f"Fetched {len(raw_campaigns)} campaigns")
    except Exception as e:
        print_error(f"Failed to fetch campaign data: {e}")
        logger.exception("Error fetching campaigns")
        return 1
    
    if not raw_campaigns:
        print_warning("No campaign data found for this period")
        print_info("Possible reasons:")
        print_info("  - No campaigns were active during this period")
        print_info("  - API returned empty results")
        print_info("  - Date range is outside available data")
        return 0
    
    # Process and categorize campaigns
    try:
        print_info("Processing and categorizing campaigns...")
        processor = DataProcessor()
        categorized = processor.process_campaigns(raw_campaigns)
        
        # Print category summary
        print_success("Categorization complete:")
        for category, campaigns in categorized.items():
            if campaigns:
                display_name = ReportGenerator.CATEGORY_DISPLAY.get(category, (category, ''))[0]
                print(f"  {display_name}: {len(campaigns)} campaigns")
    except Exception as e:
        print_error(f"Failed to process campaigns: {e}")
        logger.exception("Error processing campaigns")
        return 1
    
    # Generate report
    try:
        print_info("Generating markdown report...")
        generator = ReportGenerator()
        
        report_path = generator.generate_and_save(
            categorized,
            period=args.period,
            start_date=start_date,
            end_date=end_date,
            filename=args.output,
            include_summary=not args.no_summary
        )
        
        print_success(f"Report saved to: {report_path}")
        print_info(f"Full path: {report_path.absolute()}")
    except Exception as e:
        print_error(f"Failed to generate report: {e}")
        logger.exception("Error generating report")
        return 1
    
    # Final summary
    print("\n" + "=" * 70)
    print(f"{Fore.GREEN}Analysis complete!{Style.RESET_ALL}")
    print("=" * 70)
    print(f"\nReport ready for Slack Canvas: {Fore.CYAN}{report_path.name}{Style.RESET_ALL}\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())


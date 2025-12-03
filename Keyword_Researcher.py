#!/usr/bin/env python3
"""
Keyword_Researcher.py - Keyword Discovery Tool

Discovers related keywords by searching TrafficJunky's keyword selector.
Takes seed keywords from a CSV and outputs discovered keywords in the same format.

Usage:
    # Basic usage
    python Keyword_Researcher.py --input data/input/Keyword_Researcher/seeds.csv \\
                                  --output data/output/Keyword_Researcher/discovered.csv

    # With screenshots for debugging
    python Keyword_Researcher.py --input data/input/Keyword_Researcher/seeds.csv \\
                                  --output data/output/Keyword_Researcher/discovered.csv \\
                                  --screenshots

    # Include original seeds in output
    python Keyword_Researcher.py --input data/input/Keyword_Researcher/seeds.csv \\
                                  --output data/output/Keyword_Researcher/discovered.csv \\
                                  --include-originals
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.sync_api import sync_playwright
from config import Config
from auth import TJAuthenticator
from keyword_researcher import (
    parse_input_csv,
    get_unique_seed_keywords,
    get_existing_keywords,
    get_groups_from_rows,
    generate_output_filename,
    write_output_csv,
    write_output_csvs_by_group,
    write_simple_keyword_list,
    KeywordResearcher,
    ResearchBatch,
)

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/keyword_research_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Keyword Discovery Tool - Find related keywords via TrafficJunky',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  %(prog)s --input data/input/Keyword_Researcher/seeds.csv --output data/output/Keyword_Researcher/discovered.csv

  # With screenshots
  %(prog)s --input seeds.csv --output discovered.csv --screenshots

  # Include original seeds in output
  %(prog)s --input seeds.csv --output discovered.csv --include-originals

Input CSV format (same as Niche-Findom_v2.csv):
  group,keywords,keyword_matches,gender,geo,multi_geo,csv_file,...
  Milfs,stepmom,,all,US;CA,,stepmom.csv,...

Output will be in the same format with discovered keywords.
        """
    )
    
    parser.add_argument(
        '--input',
        required=True,
        type=Path,
        help='Path to input CSV with seed keywords (Niche-Findom_v2.csv format)'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Path to output CSV (default: auto-named based on group, e.g., niche-Milfs_v2.csv)'
    )
    
    parser.add_argument(
        '--screenshots',
        action='store_true',
        help='Take screenshots during research (saved to data/screenshots/)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (no visible window)'
    )
    
    parser.add_argument(
        '--include-originals',
        action='store_true',
        help='Include original seed keywords in output CSV'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Seconds to wait between keyword searches (default: 2.0)'
    )
    
    parser.add_argument(
        '--simple-output',
        type=Path,
        help='Also output a simple keyword list CSV (keyword, source_seed)'
    )
    
    parser.add_argument(
        '--campaign-id',
        type=str,
        default='1013085241',
        help='Campaign ID to use for accessing keyword selector (any existing campaign)'
    )
    
    return parser.parse_args()


def print_summary(batch: ResearchBatch, discovered_keywords: dict, output_dir: Path):
    """Print summary of research results."""
    print("\n" + "="*70)
    print("RESEARCH SUMMARY")
    print("="*70)
    
    print(f"\nSeed Keywords: {batch.total_seeds}")
    print(f"Successful: {batch.completed_count}")
    print(f"Failed: {batch.failed_count}")
    print(f"Total Discovered: {batch.total_discovered}")
    
    # Unique keywords
    unique_keywords = set()
    for keywords in discovered_keywords.values():
        unique_keywords.update(k.lower() for k in keywords)
    print(f"Unique Keywords: {len(unique_keywords)}")
    
    if batch.duration_seconds > 0:
        print(f"\nTime Taken: {batch.duration_seconds:.1f}s")
        avg_time = batch.duration_seconds / max(batch.total_seeds, 1)
        print(f"Avg per Keyword: {avg_time:.1f}s")
    
    print(f"\n✓ Output saved to: {output_dir}/")
    
    # Show top discoveries
    if discovered_keywords:
        print("\nTop discoveries by seed:")
        for seed, keywords in list(discovered_keywords.items())[:5]:
            print(f"  • {seed}: {len(keywords)} keywords")
            if keywords[:3]:
                print(f"    e.g., {', '.join(keywords[:3])}")


def main():
    """Main entry point."""
    args = parse_arguments()
    
    print("="*70)
    print("KEYWORD RESEARCHER - KEYWORD DISCOVERY TOOL")
    print("="*70)
    
    print(f"\nInput CSV: {args.input}")
    
    # Validate input file exists
    if not args.input.exists():
        print(f"\n✗ Error: Input CSV not found: {args.input}")
        return 1
    
    try:
        # Parse input CSV
        print(f"\nParsing input CSV...")
        seed_rows, fieldnames = parse_input_csv(args.input)
        seed_keywords = get_unique_seed_keywords(seed_rows)
        existing_keywords = get_existing_keywords(seed_rows)
        
        # Get groups for output
        groups = get_groups_from_rows(seed_rows)
        output_dir = Path("data/output/Keyword_Researcher")
        
        print(f"Output directory: {output_dir}")
        print(f"Groups found: {', '.join(groups)}")
        output_files = [f"niche-{g.replace(' ', '-')}_v2.csv" for g in groups]
        print(f"Will create: {', '.join(output_files)}")
        
        print(f"✓ Found {len(seed_keywords)} unique seed keywords")
        print(f"✓ Found {len(existing_keywords)} existing keywords to exclude")
        
        if len(seed_keywords) == 0:
            print("\n✗ Error: No seed keywords found in CSV")
            return 1
        
        # Show preview
        print(f"\nSeed keywords to research:")
        for kw in seed_keywords[:10]:
            print(f"  • {kw}")
        if len(seed_keywords) > 10:
            print(f"  ... and {len(seed_keywords) - 10} more")
        
        # Initialize batch
        batch = ResearchBatch(
            seed_keywords=seed_keywords,
            start_time=datetime.now()
        )
        
        # Start browser & authenticate
        print("\n" + "="*70)
        print("BROWSER AUTHENTICATION")
        print("="*70)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=args.headless,
                slow_mo=100
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = context.new_page()
            page.set_default_timeout(30000)
            
            # Login (same as campaign creation)
            authenticator = TJAuthenticator(Config.TJ_USERNAME, Config.TJ_PASSWORD)
            
            print("\nLogging in (solve reCAPTCHA manually if prompted)...")
            if not authenticator.manual_login(page, timeout=180):
                print("\n✗ Login failed!")
                browser.close()
                return 1
            
            authenticator.save_session(context)
            print("✓ Logged in successfully")
            
            # Initialize researcher
            screenshot_dir = Config.SCREENSHOT_DIR if args.screenshots else None
            researcher = KeywordResearcher(
                page=page,
                campaign_id=args.campaign_id,
                delay_between_searches=args.delay,
                take_screenshots=args.screenshots,
                screenshot_dir=screenshot_dir
            )
            
            # Navigate to keyword selector
            print("\n" + "="*70)
            print("NAVIGATING TO KEYWORD SELECTOR")
            print("="*70)
            
            if not researcher.navigate_to_keyword_selector():
                print("\n✗ Failed to navigate to keyword selector!")
                print("Tip: The campaign creation flow may have changed.")
                browser.close()
                return 1
            
            # Research keywords
            print("\n" + "="*70)
            print("RESEARCHING KEYWORDS")
            print("="*70)
            
            results = researcher.research_keywords_batch(
                seed_keywords=seed_keywords,
                existing_keywords=existing_keywords
            )
            
            batch.results = results
            batch.end_time = datetime.now()
            
            browser.close()
        
        # Compile discovered keywords
        discovered_keywords = {}
        for result in batch.results:
            if result.status == 'success' and result.discovered_keywords:
                discovered_keywords[result.seed_keyword] = result.discovered_keywords
        
        # Write output CSVs (one per group)
        print("\n" + "="*70)
        print("WRITING OUTPUT")
        print("="*70)
        
        results = write_output_csvs_by_group(
            output_dir=output_dir,
            original_rows=seed_rows,
            discovered_keywords=discovered_keywords,
            fieldnames=fieldnames,
            include_originals=args.include_originals
        )
        
        total_rows = 0
        for group, count in results.items():
            print(f"✓ {group}: {count} keywords → niche-{group.replace(' ', '-')}_v2.csv")
            total_rows += count
        
        # Optional simple output
        if args.simple_output:
            simple_rows = write_simple_keyword_list(args.simple_output, discovered_keywords)
            print(f"✓ Wrote {simple_rows} keywords to {args.simple_output}")
        
        # Print summary
        print_summary(batch, discovered_keywords, output_dir)
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        return 130
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.exception("Exception details:")
        print(f"\n✗ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)


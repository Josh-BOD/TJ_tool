#!/usr/bin/env python3
"""
Multilingual Campaign Generator

Generates per-language ad CSVs (English + native-language) and a campaign
creation CSV consumable by create_campaigns_v2_sync.py.

Usage:
    # Dry run (preview + placeholder translations)
    python create_multilingual.py \
        --languages data/input/Multilingual_Campaign_Creation/example_languages.csv \
        --ads data/input/Multilingual_Campaign_Creation/example_base_ads_native.csv \
        --format NATIVE --group Milfs

    # Live (call OpenRouter for real translations)
    python create_multilingual.py \
        --languages data/input/Multilingual_Campaign_Creation/example_languages.csv \
        --ads data/input/Multilingual_Campaign_Creation/example_base_ads_native.csv \
        --format NATIVE --group Milfs --live

    # Live + launch campaign creation
    python create_multilingual.py \
        --languages ... --ads ... --format NATIVE --group Milfs \
        --live --create-campaigns --no-headless --slow-mo 1000
"""

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import Config
from multilingual.translator import Translator
from multilingual.csv_generator import MultilingualCSVGenerator, parse_languages_csv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)
logger = logging.getLogger(__name__)


def build_preview_table(languages, group_name, ad_format):
    """Print a preview table of campaigns that will be generated."""
    print("\n" + "=" * 80)
    print("MULTILINGUAL CAMPAIGN PREVIEW")
    print("=" * 80)

    total_campaigns = 0
    total_std_variants = 0
    total_rmkt_variants = 0

    for lang in languages:
        if not lang.get("enabled", True):
            continue

        lang_codes = [c.strip().lower() for c in lang["lang_code"].split(",") if c.strip()]
        lang_name = lang.get("lang_name", "")
        geo = lang["geo"].upper()
        bid_type = lang.get("bid_type", "CPA").upper()

        categories = [c.strip().lower() for c in lang.get("categories", "straight").split(",") if c.strip()]
        types = [t.strip().lower() for t in lang.get("types", "standard").split(",") if t.strip()]

        keywords = lang.get("keywords", "").strip()
        keyword_title = keywords.split(";")[0].strip().title().replace(" ", "") if keywords else "Broad"

        std_variant_count = len([v.strip() for v in lang.get("variants", "desktop,ios,android").split(",")])

        codes_display = ",".join(c.upper() for c in lang_codes)
        print(f"\n  {geo} [{codes_display}]  categories: {','.join(categories)} | types: {','.join(types)}")

        for campaign_type in types:
            is_rmkt = campaign_type == "remarketing"
            type_label = " RMKT" if is_rmkt else ""
            device_count = 2 if is_rmkt else std_variant_count

            for category in categories:
                cat_label = f" [{category.upper()}]" if category != "straight" else ""

                for code in lang_codes:
                    code_up = code.upper()
                    print(f"    {code_up}{type_label}{cat_label}:  {geo}_{code_up}_{ad_format}_{bid_type}_ALL_KEY-{keyword_title}_DESK_M_JB", end="")
                    if is_rmkt:
                        print(" (Remarketing)")
                        print(f"              + All Mobile variant")
                    else:
                        print()
                        print(f"              + iOS + Android variants")

                    total_campaigns += 1
                    if is_rmkt:
                        total_rmkt_variants += device_count
                    else:
                        total_std_variants += device_count

    total_variants = total_std_variants + total_rmkt_variants

    print(f"\n{'=' * 80}")
    print(f"TOTAL: {total_campaigns} campaign rows -> {total_variants} campaign variants")
    print(f"{'=' * 80}")

    return total_campaigns


def main():
    parser = argparse.ArgumentParser(
        description="Generate multilingual campaign CSVs with translated ad copy"
    )
    parser.add_argument(
        "--languages", required=True,
        help="Path to languages CSV (defines lang/geo/settings per row)",
    )
    parser.add_argument(
        "--ads", required=False, default=None,
        help="Fallback base ads CSV (used if ad_csv_* columns not in languages CSV)",
    )
    parser.add_argument(
        "--format", required=True, choices=["NATIVE", "INSTREAM"],
        help="Ad format (NATIVE or INSTREAM)",
    )
    parser.add_argument(
        "--group", required=True,
        help="Group/niche name (e.g., Milfs)",
    )

    # Dry run / live
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run", action="store_true", default=True,
        help="Preview mode with placeholder translations (default)",
    )
    mode_group.add_argument(
        "--live", action="store_true",
        help="Call OpenRouter API for real translations",
    )

    # Translation options
    parser.add_argument(
        "--model", default=None,
        help=f"OpenRouter model (default: {Config.OPENROUTER_MODEL})",
    )
    parser.add_argument(
        "--clear-cache", action="store_true",
        help="Clear translation cache before running",
    )

    # Campaign creation
    parser.add_argument(
        "--create-campaigns", action="store_true",
        help="Launch create_campaigns_v2_sync.py after generating CSVs",
    )
    parser.add_argument(
        "--no-headless", action="store_true",
        help="Run browser in visible mode (passed to campaign creator)",
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Run browser in headless mode (passed to campaign creator)",
    )
    parser.add_argument(
        "--slow-mo", type=int, default=None,
        help="Slow motion delay in ms (passed to campaign creator)",
    )

    # Output
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory (default: data/output/multilingual/{group}_{timestamp})",
    )

    args = parser.parse_args()

    # Resolve dry_run
    dry_run = not args.live

    # Validate inputs
    languages_path = Path(args.languages)
    ads_path = Path(args.ads) if args.ads else None

    if not languages_path.exists():
        print(f"Error: Languages CSV not found: {languages_path}")
        sys.exit(1)
    if ads_path and not ads_path.exists():
        print(f"Error: Ads CSV not found: {ads_path}")
        sys.exit(1)

    # Parse languages
    languages = parse_languages_csv(languages_path)
    enabled_count = sum(1 for l in languages if l.get("enabled", True))

    if enabled_count == 0:
        print("No enabled languages found in CSV")
        sys.exit(1)

    print(f"\nLoaded {enabled_count} enabled geos from {languages_path}")
    print(f"Base ads: {ads_path}")
    print(f"Format: {args.format}")
    print(f"Group: {args.group}")
    print(f"Mode: {'DRY RUN (placeholder translations)' if dry_run else 'LIVE (OpenRouter API)'}")

    # Preview
    total = build_preview_table(languages, args.group, args.format)

    if dry_run:
        print("\n[DRY RUN] Generating with placeholder translations...")
        print("[DRY RUN] Use --live to call OpenRouter for real translations\n")

    # Setup output dir
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("data/output/multilingual") / f"{args.group}_{timestamp}"

    # Setup translator
    translator = None
    if not dry_run:
        api_key = Config.OPENROUTER_API_KEY
        if not api_key:
            print("Error: OPENROUTER_API_KEY not set in .env")
            print("Add: OPENROUTER_API_KEY=sk-or-v1-...")
            sys.exit(1)

        model = args.model or Config.OPENROUTER_MODEL
        translator = Translator(api_key=api_key, model=model)

        if args.clear_cache:
            translator.clear_cache()

        print(f"Model: {model}")

    # Generate
    generator = MultilingualCSVGenerator(
        translator=translator,
        ad_format=args.format,
        group_name=args.group,
        output_dir=output_dir,
        dry_run=dry_run,
    )

    campaigns_csv = generator.generate(languages, ads_path)

    print(f"\n{'=' * 80}")
    print("OUTPUT FILES")
    print(f"{'=' * 80}")
    print(f"  Campaign CSV: {campaigns_csv}")
    print(f"  Ad CSVs:      {generator.ads_dir}/")

    # List generated ad files
    ad_files = sorted(generator.ads_dir.glob("*.csv"))
    for f in ad_files:
        print(f"                {f.name}")

    print(f"\nTo create campaigns:")
    print(f"  python create_campaigns_v2_sync.py --input {campaigns_csv} --dry-run")

    # Optionally launch campaign creation
    if args.create_campaigns:
        print(f"\n{'=' * 80}")
        print("LAUNCHING CAMPAIGN CREATION")
        print(f"{'=' * 80}")

        cmd = [
            sys.executable, "create_campaigns_v2_sync.py",
            "--input", str(campaigns_csv),
        ]
        if args.headless:
            cmd.append("--headless")
        elif args.no_headless:
            cmd.append("--no-headless")
        if args.slow_mo is not None:
            cmd.extend(["--slow-mo", str(args.slow_mo)])

        print(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd)


if __name__ == "__main__":
    main()

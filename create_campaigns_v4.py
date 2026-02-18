#!/usr/bin/env python3
"""
Campaign Creation Tool V4 — Full-Field Campaign Automation

Creates campaigns from scratch with support for ALL ~63 CSV columns,
including toggle-gated targeting sections, smart bidder, schedule,
and budget configuration.

Input:  Any CSV following TEMPLATE_ALL_FIELDS.csv column spec
Output: data/output/V4_Campaign_Creation/{timestamp}/

Usage:
    python create_campaigns_v4.py <csv_file>
    python create_campaigns_v4.py data/input/Blank_Campaign_Creation/my_campaigns.csv
    python create_campaigns_v4.py <csv_file> --dry-run
    python create_campaigns_v4.py <csv_file> --headless
"""

import sys
import csv
import logging
import argparse
import traceback
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.sync_api import sync_playwright

from config import Config
from auth import TJAuthenticator
from v4.csv_parser import parse_v4_csv, V4CSVParseError
from v4.creator import V4CampaignCreator, V4CreationError

# Paths
OUTPUT_DIR = Path(__file__).parent / "data" / "output" / "V4_Campaign_Creation"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [V4] %(message)s',
)
logger = logging.getLogger(__name__)


# ─── Dry Run ─────────────────────────────────────────────────────

def validate_csv_only(csv_path: Path):
    """Validate CSV file without creating campaigns."""
    logger.info(f"Validating CSV: {csv_path}")
    logger.info("=" * 60)

    try:
        configs = parse_v4_csv(csv_path)
        enabled = [c for c in configs if c.enabled]

        logger.info(f"CSV parsed successfully")
        logger.info(f"  Total rows: {len(configs)}")
        logger.info(f"  Enabled: {len(enabled)}")
        total_variants = sum(len(c.variants) for c in enabled)
        logger.info(f"  Total variants to create: {total_variants}")
        logger.info("")

        for i, cfg in enumerate(enabled, 1):
            logger.info(f"Campaign {i}: {cfg.group}")
            logger.info(f"  Keywords: {', '.join(cfg.keywords) or '(none)'}")
            logger.info(f"  Geo: {', '.join(cfg.geo)}")
            logger.info(f"  Variants: {', '.join(cfg.variants)}")
            logger.info(f"  CSV File: {cfg.csv_file}")
            logger.info(f"  Settings:")
            logger.info(f"    Device: {cfg.device or '(auto)'}")
            logger.info(f"    Ad Format: {cfg.ad_format_type} / {cfg.format_type}")
            logger.info(f"    Ad Type: {cfg.ad_type}  Dims: {cfg.ad_dimensions}")
            logger.info(f"    Content Category: {cfg.content_category}")
            logger.info(f"    Gender: {cfg.gender}  Labels: {cfg.labels or '(none)'}")
            logger.info(f"    Bid Type: {cfg.bid_type}  Campaign Type: {cfg.campaign_type}")
            # Toggle-gated sections
            toggles = []
            if cfg.has_os_targeting:       toggles.append("OS")
            if cfg.has_browser_targeting:  toggles.append("Browser")
            if cfg.has_browser_language:   toggles.append("BrowserLang")
            if cfg.has_postal_codes:       toggles.append("PostalCode")
            if cfg.has_isp_targeting:      toggles.append("ISP")
            if cfg.has_ip_targeting:       toggles.append("IP")
            if cfg.has_income_targeting:   toggles.append("Income")
            if cfg.has_retargeting:        toggles.append("Retarget")
            if cfg.has_vr_targeting:       toggles.append("VR")
            if cfg.has_segment_targeting:  toggles.append("Segment")
            logger.info(f"    Toggle sections: {', '.join(toggles) or '(none)'}")
            logger.info(f"    Budget: ${cfg.daily_budget}  Freq cap: {cfg.frequency_cap}")
            logger.info("")

        logger.info("=" * 60)
        logger.info("Dry run complete — CSV is valid")
        return True

    except V4CSVParseError as e:
        logger.error(f"CSV parse error: {e}")
        return False
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        traceback.print_exc()
        return False


# ─── Report ──────────────────────────────────────────────────────

def save_report(results: list, csv_path: Path, session_dir: Path):
    """Save a CSV report of created campaigns."""
    session_dir.mkdir(parents=True, exist_ok=True)
    report_path = session_dir / f"{csv_path.stem}_report.csv"

    try:
        with open(report_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Campaign ID', 'Campaign Name', 'Variant', 'Status'])
            for cid, cname, var, status in results:
                writer.writerow([cid, cname, var, status])

        logger.info(f"Report saved: {report_path}")
        return report_path
    except Exception as e:
        logger.error(f"Failed to save report: {e}")
        return None


# ─── Upload Only ────────────────────────────────────────────────

def upload_ads_only(csv_path: Path, campaign_id: str, headless: bool = False, slow_mo: int = 500):
    """Upload ads to an existing campaign (skip steps 1-4)."""
    logger.info("=" * 60)
    logger.info(f"Upload Ads Only — Campaign {campaign_id}")
    logger.info("=" * 60)

    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return

    try:
        configs = parse_v4_csv(csv_path)
        enabled = [c for c in configs if c.enabled]
    except V4CSVParseError as e:
        logger.error(f"CSV parse error: {e}")
        return

    if not enabled:
        logger.warning("No enabled campaigns found in CSV")
        return

    config = enabled[0]
    csv_dir = str(csv_path.parent)
    ad_csv_path = Path(csv_dir) / config.csv_file

    if not ad_csv_path.exists():
        logger.error(f"Ad CSV not found: {ad_csv_path}")
        return

    logger.info(f"Ad CSV: {ad_csv_path}")
    logger.info(f"Format: {config.ad_format_type} / {config.format_type}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=slow_mo)

        # Auth
        authenticator = TJAuthenticator(Config.TJ_USERNAME, Config.TJ_PASSWORD)
        context = authenticator.load_session(browser)
        logged_in = False
        if context:
            context.set_default_timeout(30000)
            page = context.new_page()
            page.set_default_timeout(30000)
            try:
                url = f"https://advertiser.trafficjunky.com/campaign/{campaign_id}/ad-settings#section_adSpecs"
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                import time as _t; _t.sleep(2)
                curr_url = page.url
                if "sign-in" not in curr_url:
                    logged_in = True
                    logger.info("Logged in via saved session")
                else:
                    page.close(); context.close()
            except Exception:
                page.close(); context.close()

        if not logged_in:
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = context.new_page()
            page.set_default_timeout(30000)
            logger.info("Logging in (solve reCAPTCHA if prompted)...")
            if not authenticator.manual_login(page, timeout=180):
                logger.error("Login failed!")
                browser.close()
                return
            url = f"https://advertiser.trafficjunky.com/campaign/{campaign_id}/ad-settings#section_adSpecs"
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            import time as _t; _t.sleep(2)

        authenticator.save_session(context)

        # Import step5 and run it directly
        from v4.steps.step5_ad_settings import configure_step5
        configure_step5(page, config, csv_dir, f"campaign_{campaign_id}")

        browser.close()

    logger.info("Upload complete!")


# ─── Main Run ────────────────────────────────────────────────────

def _launch_browser_and_auth(p, authenticator, headless, slow_mo):
    """Launch browser and authenticate. Returns (browser, page)."""
    browser = p.chromium.launch(headless=headless, slow_mo=slow_mo)

    context = authenticator.load_session(browser)
    logged_in = False
    if context:
        context.set_default_timeout(30000)
        page = context.new_page()
        page.set_default_timeout(30000)
        try:
            page.goto("https://advertiser.trafficjunky.com/campaign/drafts/bid/create",
                      wait_until="domcontentloaded", timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            import time as _t; _t.sleep(2)
            url = page.url
            title = page.title()
            has_form = page.evaluate('document.querySelectorAll("input, select").length > 0')
            if "sign-in" not in url and "404" not in title and has_form:
                logged_in = True
                logger.info("Logged in via saved session")
            else:
                logger.info("Saved session invalid")
                page.close()
                context.close()
        except Exception as e:
            logger.info(f"Saved session check failed: {e}")
            try:
                page.close()
                context.close()
            except Exception:
                pass

    if not logged_in:
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        page.set_default_timeout(30000)
        logger.info("Logging in (solve reCAPTCHA if prompted)...")
        if not authenticator.manual_login(page, timeout=180):
            logger.error("Login failed!")
            browser.close()
            return None, None

    authenticator.save_session(context)
    logger.info("Logged in successfully")
    return browser, page


def run_v4(csv_path: Path, dry_run: bool = False, headless: bool = False, slow_mo: int = 500, name_prefix: str = ""):
    """Main runner for V4 campaign creation."""
    logger.info("=" * 60)
    logger.info("Campaign Creation V4 — Full-Field Automation")
    logger.info("=" * 60)
    logger.info(f"CSV: {csv_path}")

    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return

    if dry_run:
        validate_csv_only(csv_path)
        return

    # Parse CSV
    try:
        configs = parse_v4_csv(csv_path)
        enabled = [c for c in configs if c.enabled]
    except V4CSVParseError as e:
        logger.error(f"CSV parse error: {e}")
        return

    if not enabled:
        logger.warning("No enabled campaigns found in CSV")
        return

    total_variants = sum(len(c.variants) for c in enabled)
    logger.info(f"Enabled campaigns: {len(enabled)}")
    logger.info(f"Total variants to create: {total_variants}")

    csv_dir = str(csv_path.parent)

    # Session output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = OUTPUT_DIR / timestamp
    session_dir.mkdir(parents=True, exist_ok=True)

    # Launch browser
    with sync_playwright() as p:
        authenticator = TJAuthenticator(Config.TJ_USERNAME, Config.TJ_PASSWORD)
        browser, page = _launch_browser_and_auth(p, authenticator, headless, slow_mo)
        if not browser:
            return

        # Create campaigns
        creator = V4CampaignCreator(page, name_prefix=name_prefix)
        results = []
        total_created = 0
        total_failed = 0

        for i, config in enumerate(enabled, 1):
            logger.info(f"\n{'#' * 60}")
            logger.info(f"Campaign {i}/{len(enabled)}: {config.group}")
            logger.info(f"  Keywords: {', '.join(config.keywords) or '(none)'}")
            logger.info(f"  Variants: {', '.join(config.variants)}")
            logger.info(f"{'#' * 60}")

            for variant in config.variants:
                try:
                    cid, cname = creator.create_campaign(config, variant, csv_dir)
                    results.append((cid, cname, variant, "Created"))
                    total_created += 1
                except (V4CreationError, Exception) as e:
                    error_msg = str(e)
                    is_crash = "browser has been closed" in error_msg or "Target page" in error_msg

                    if is_crash:
                        logger.warning(f"  [{variant}] Browser crashed, relaunching...")
                        try:
                            browser.close()
                        except Exception:
                            pass

                        browser, page = _launch_browser_and_auth(p, authenticator, headless, slow_mo)
                        if not browser:
                            logger.error("  Could not relaunch browser — aborting")
                            results.append(("", "", variant, f"FAILED: {e}"))
                            total_failed += 1
                            break
                        creator = V4CampaignCreator(page, name_prefix=name_prefix)

                        # Retry this variant with fresh browser
                        try:
                            cid, cname = creator.create_campaign(config, variant, csv_dir)
                            results.append((cid, cname, variant, "Created"))
                            total_created += 1
                            continue
                        except Exception as retry_e:
                            logger.error(f"  FAILED [{variant}] (retry): {retry_e}")
                            results.append(("", "", variant, f"FAILED: {retry_e}"))
                            total_failed += 1
                            continue

                    # Non-crash failure
                    logger.error(f"  FAILED [{variant}]: {e}")
                    if isinstance(e, V4CreationError) and e.orphan_id:
                        logger.error(f"  ORPHAN CAMPAIGN: {e.orphan_id}")
                    results.append(("", "", variant, f"FAILED: {e}"))
                    total_failed += 1

        try:
            browser.close()
        except Exception:
            pass

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Created: {total_created}")
    logger.info(f"Failed:  {total_failed}")

    if results:
        logger.info("\nResults:")
        for cid, cname, var, status in results:
            if cid:
                logger.info(f"  [{var}] {cname} (ID: {cid})")
            else:
                logger.info(f"  [{var}] {status}")

        save_report(results, csv_path, session_dir)

    logger.info("\nV4 Campaign creation complete!")


# ─── CLI ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Create TrafficJunky campaigns — V4 full-field automation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_campaigns_v4.py my_campaigns.csv
  python create_campaigns_v4.py my_campaigns.csv --dry-run
  python create_campaigns_v4.py my_campaigns.csv --prefix "TEST_"
  python create_campaigns_v4.py my_campaigns.csv --upload-only 2611371   # retry ads only
        """,
    )

    parser.add_argument('csv_file', type=str, help='Path to CSV with campaign definitions')
    parser.add_argument('--dry-run', action='store_true', help='Validate CSV only')
    parser.add_argument('--headless', action='store_true', help='Run browser headless')
    parser.add_argument('--slow-mo', type=int, default=500, help='Slow motion delay in ms')
    parser.add_argument('--prefix', type=str, default='', help='Prefix to prepend to campaign names (e.g. TEST_)')
    parser.add_argument('--upload-only', type=str, metavar='CAMPAIGN_ID',
                        help='Skip creation, just upload ads to an existing campaign')

    args = parser.parse_args()
    if args.upload_only:
        upload_ads_only(Path(args.csv_file), args.upload_only, headless=args.headless, slow_mo=args.slow_mo)
    else:
        run_v4(Path(args.csv_file), dry_run=args.dry_run, headless=args.headless, slow_mo=args.slow_mo, name_prefix=args.prefix)


if __name__ == "__main__":
    main()

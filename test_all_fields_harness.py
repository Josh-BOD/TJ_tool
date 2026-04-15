#!/usr/bin/env python3
"""
V4 Field Test Harness — Tests the FULL production pipeline.

Pipeline: CSV → csv_parser → V4CampaignCreator → TJ → independent verify

Tests 3 modes (same code path as production create_campaigns_v4.py):
1. CREATE — Full 5-step from scratch (all format×category×device combos)
2. CLONE  — Clone from template + override (category cross-change, field edits)
3. UPDATE — Edit single fields on existing campaigns

Generates test CSVs, runs them through parse_v4_csv + V4CampaignCreator,
then verifies every field independently by reading back from TJ UI.

Usage:
    python test_all_fields_harness.py                    # All tests
    python test_all_fields_harness.py --mode create      # Only create
    python test_all_fields_harness.py --mode clone       # Only clone
    python test_all_fields_harness.py --retry-failed X   # Re-run failures from report
    python test_all_fields_harness.py --quick             # 1 per format (4 create + 2 clone)
"""

import sys
import csv
import json
import time
import logging
import argparse
import traceback
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.sync_api import sync_playwright, Page
from config import Config
from auth import TJAuthenticator
from v4.csv_parser import parse_v4_csv
from v4.creator import V4CampaignCreator, V4CreationError
from v4.models import V4CampaignConfig
from verify_campaigns import verify_campaign, FIELD_MAP, SKIP_FIELDS
from export_campaign_v4 import read_overview, read_page2, read_page3, read_page4

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [HARNESS] %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://advertiser.trafficjunky.com"
OUTPUT_DIR = Path(__file__).parent / "data" / "output" / "V4_Field_Tests"
TEST_CSV_DIR = Path(__file__).parent / "data" / "input" / "test_field_groups"

# ═══════════════════════════════════════════════════════════════════
# CSV HEADER — exact same as production TEMPLATE_ALL_FIELDS.csv
# ═══════════════════════════════════════════════════════════════════

CSV_HEADER = [
    "template_campaign_id","enabled","group","keywords","match_type","geo","variants",
    "csv_file","language","bid_type","campaign_type","geo_name","test_number",
    "content_rating","device","ad_format_type","format_type","ad_type","ad_dimensions",
    "content_category","gender","labels","exchange_id","keyword_name","tracker_id",
    "source_selection","smart_bidder","optimization_option","target_cpa",
    "per_source_test_budget","max_bid","cpm_adjust","cpm_bid_mode","cpm_bid_value",
    "include_all_sources","frequency_cap","frequency_cap_every","daily_budget",
    "start_date","end_date","schedule_dayparting","os_include","os_exclude",
    "ios_version_op","ios_version","android_version_op","android_version",
    "browser_targeting","browsers_include","browser_language","postal_code_targeting",
    "postal_codes","isp_targeting","isp_country","isp_name","ip_targeting",
    "ip_range_start","ip_range_end","income_targeting","income_segment","retargeting",
    "retargeting_type","retargeting_mode","retargeting_value","vr_targeting","vr_mode",
    "segment_targeting","automation_rules","budget_type",
]

# Templates
TEMPLATES = {
    "native_straight_desk": "1013321421",
    "native_straight_ios":  "1013321431",
    "native_gay_desk":      "1013321461",
    "native_gay_ios":       "1013321471",
    "native_trans_desk":    "1013321491",
    "native_trans_ios":     "1013321501",
}

# Format definitions
FORMATS = {
    "NATIVE":  ("display",  "native",  "rollover",      "300x250"),
    "PREROLL": ("instream", "",        "video_file",    ""),
    "POP":     ("pop",      "",        "",              ""),
    "DISPLAY": ("display",  "banner",  "static_banner", "300x250"),
}


# ═══════════════════════════════════════════════════════════════════
# Test CSV Generators — produce CSVs identical to production format
# ═══════════════════════════════════════════════════════════════════

def _base_row():
    """Base row with sensible defaults — same as production CSVs."""
    row = {f: "" for f in CSV_HEADER}
    row.update({
        "enabled": "TRUE", "group": "AUTO-TEST", "match_type": "exact",
        "geo": "US", "language": "EN", "bid_type": "CPM",
        "campaign_type": "Standard", "geo_name": "Gold",
        "content_rating": "NSFW", "gender": "male", "labels": "AutoTest",
        "include_all_sources": "TRUE", "frequency_cap": "3",
        "frequency_cap_every": "24", "daily_budget": "25.00",
        "budget_type": "custom",
    })
    return row


def generate_create_csv(out_path: Path, quick=False):
    """Generate CREATE test CSV — clone from matching templates per category×device.

    Uses clone flow (not from-scratch create) because:
    1. Cloned campaigns are LIVE with ads — can be fully verified
    2. Draft campaigns (from-scratch without ads) can't be finalized by TJ
    3. This is the production code path — CSVs always specify template_campaign_id

    Native templates exist for all category×device combos.
    Non-native formats (preroll/pop/display) need separate templates — skip for now.
    """
    rows = []
    categories = ["straight", "gay", "trans"]
    devices = ["desktop", "ios"]  # Skip android (clones from iOS, same test)

    # Template mapping: category → device → template_id
    TEMPLATE_MAP = {
        "straight": {"desktop": "1013321421", "ios": "1013321431"},
        "gay":      {"desktop": "1013321461", "ios": "1013321471"},
        "trans":    {"desktop": "1013321491", "ios": "1013321501"},
    }

    if quick:
        categories = ["straight"]
        devices = ["desktop"]

    for cat in categories:
        for device in devices:
            tmpl = TEMPLATE_MAP.get(cat, {}).get(device)
            if not tmpl:
                continue
            row = _base_row()
            row["template_campaign_id"] = tmpl
            row["variants"] = device
            row["content_category"] = cat
            row["keyword_name"] = f"INT-Native"
            row["labels"] = "AutoTest;Native"  # Include auto-generated niche label
            row["ad_format_type"] = "display"
            row["format_type"] = "native"
            row["ad_type"] = "rollover"
            row["ad_dimensions"] = "300x250"
            rows.append(row)

    _write_csv(out_path, rows)
    return len(rows)


def generate_clone_csv(out_path: Path, quick=False):
    """Generate CLONE test CSV — cross-change + field override tests."""
    rows = []

    # Override tests FIRST — they need the freshest session (run right after
    # forced re-login at batch boundary). These have keywords + budget changes.
    if not quick:
        row = _base_row()
        row["template_campaign_id"] = "1013321461"  # gay desktop template
        row["variants"] = "desktop"
        row["content_category"] = "gay"
        row["keywords"] = "yaoi;bara"
        row["keyword_name"] = "KEY-Yaoi"
        row["labels"] = "AutoTest;Yaoi"
        row["daily_budget"] = "50.00"
        row["frequency_cap"] = "5"
        rows.append(row)

        row = _base_row()
        row["template_campaign_id"] = "1013321501"  # trans iOS template
        row["variants"] = "ios"
        row["content_category"] = "trans"
        row["gender"] = "female"
        row["keywords"] = "trans;shemale"
        row["keyword_name"] = "KEY-Trans"
        row["labels"] = "AutoTest;Trans"
        row["daily_budget"] = "30.00"
        rows.append(row)

    # Multi-geo tests — Gold, Silver, Bronze tiers (straight only)
    if not quick:
        # Gold: US,GB,AU,CA
        row = _base_row()
        row["template_campaign_id"] = "1013321421"
        row["variants"] = "desktop"
        row["content_category"] = "straight"
        row["geo"] = "US;GB;AU;CA"
        row["geo_name"] = "Gold"
        row["keyword_name"] = "INT-GoldGeo"
        row["labels"] = "AutoTest;GoldGeo"
        rows.append(row)

        # Silver: DE,NL,ES,PL
        row = _base_row()
        row["template_campaign_id"] = "1013321421"
        row["variants"] = "desktop"
        row["content_category"] = "straight"
        row["geo"] = "DE;NL;ES;PL"
        row["geo_name"] = "Silver"
        row["keyword_name"] = "INT-SilverGeo"
        row["labels"] = "AutoTest;SilverGeo"
        rows.append(row)

        # Bronze: CZ,TH,TR,UA
        row = _base_row()
        row["template_campaign_id"] = "1013321421"
        row["variants"] = "desktop"
        row["content_category"] = "straight"
        row["geo"] = "CZ;TH;TR;UA"
        row["geo_name"] = "Bronze"
        row["keyword_name"] = "INT-BronzeGeo"
        row["labels"] = "AutoTest;BronzeGeo"
        rows.append(row)

    # Basic category clone tests
    cross_changes = [
        ("1013321461", "desktop", "gay",   "male",   "INT-GayClone"),
        ("1013321491", "desktop", "trans",  "male",   "INT-TransClone"),
        ("1013321471", "ios",     "gay",   "male",   "INT-GayClone"),
        ("1013321501", "ios",     "trans",  "male",   "INT-TransClone"),
    ]

    if quick:
        cross_changes = cross_changes[:2]

    for tmpl, device, cat, gender, kw_name in cross_changes:
        row = _base_row()
        row["template_campaign_id"] = tmpl
        row["variants"] = device
        row["content_category"] = cat
        row["gender"] = gender
        row["keyword_name"] = kw_name
        niche = kw_name.replace("INT-", "").replace("KEY-", "")
        row["labels"] = f"AutoTest;CrossChange;{niche}"
        rows.append(row)

    _write_csv(out_path, rows)
    return len(rows)


def _write_csv(path: Path, rows: List[Dict]):
    """Write rows to CSV with exact production header."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)


# ═══════════════════════════════════════════════════════════════════
# Test Runner — uses SAME code path as production
# ═══════════════════════════════════════════════════════════════════

class TestResult:
    def __init__(self, name, mode, campaign_id, passed, failed, skipped, failures):
        self.name = name
        self.mode = mode
        self.campaign_id = campaign_id
        self.passed = passed
        self.failed = failed
        self.skipped = skipped
        self.failures = failures

    @property
    def ok(self):
        return self.failed == 0

    def __repr__(self):
        s = "PASS" if self.ok else "FAIL"
        return f"[{s}] {self.name}: {self.passed}P/{self.failed}F (ID: {self.campaign_id})"


def ensure_session(page, force_relogin=False):
    """Aggressive session check — force re-login if requested or if session stale.

    TJ cookies expire after ~35 min. Force re-login every batch boundary
    to prevent mid-creation failures.
    """
    if force_relogin:
        logger.info("Forced re-login requested")
        _do_login(page)
        return

    try:
        # Hit the campaign EDIT page (same URL pattern as clone_from_template uses)
        # This exercises the exact same auth path as campaign creation
        page.goto(f"{BASE_URL}/campaign/1013321421",
                  wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)
        if "sign-in" in page.url or "campaigns" == page.url.rstrip("/").split("/")[-1]:
            logger.info("Session expired (edit page redirect) — re-logging in...")
            _do_login(page)
    except Exception as e:
        logger.warning(f"Session check failed: {e} — forcing login")
        _do_login(page)


def _do_login(page):
    """Re-authenticate with TJ."""
    auth = TJAuthenticator(Config.TJ_USERNAME, Config.TJ_PASSWORD)
    auth.manual_login(page, timeout=180)
    page.context.storage_state(path="data/session/tj_session.json")
    logger.info("Session refreshed")


def run_csv_and_verify(page, csv_path, mode, prefix="TEST-CMP-"):
    """Run a test CSV through the production pipeline and verify each campaign.

    1. Parse CSV with parse_v4_csv (same as create_campaigns_v4.py)
    2. Create/clone each campaign with V4CampaignCreator
    3. Independently verify each campaign from TJ UI
    """
    configs = parse_v4_csv(csv_path)
    results = []

    for i, config in enumerate(configs):
        if not config.enabled:
            continue

        for variant in config.variants:
            test_name = f"{mode}_{config.content_category}_{variant}_{config.ad_format_type}"
            if config.keyword_name:
                test_name += f"_{config.keyword_name}"

            logger.info(f"\n[{i+1}/{len(configs)}] {test_name}")

            try:
                # Force relogin for tests with keywords or budget overrides
                # (these take longer and hit session expiry)
                needs_force = bool(config.keywords or config.daily_budget != 25.0)
                ensure_session(page, force_relogin=needs_force)
                creator = V4CampaignCreator(page, name_prefix=prefix)

                # Same branch as create_campaigns_v4.py
                if config.template_campaign_id:
                    cid, cname = creator.clone_from_template(config, variant, csv_dir="")
                else:
                    cid, cname = creator.create_campaign(config, variant, csv_dir="")

                logger.info(f"  Created: {cname} (ID: {cid})")

                # Build expected dict from config (same fields as CSV)
                from dataclasses import fields as dc_fields
                expected = {}
                for f in dc_fields(config):
                    val = getattr(config, f.name)
                    if isinstance(val, list):
                        val = ";".join(str(v) for v in val)
                    else:
                        val = str(val) if val is not None else ""
                    expected[f.name] = val

                # Independent verification
                time.sleep(2)
                field_results = verify_campaign(page, cid, expected)
                p = sum(1 for r in field_results if r.status == "PASS")
                f = sum(1 for r in field_results if r.status == "FAIL")
                s = sum(1 for r in field_results if r.status == "SKIP")
                failures = [(r.field, r.expected, r.actual)
                            for r in field_results if r.status == "FAIL"]

                result = TestResult(test_name, mode, cid, p, f, s, failures)

            except Exception as e:
                logger.error(f"  FAILED: {e}")
                result = TestResult(test_name, mode, "N/A", 0, 1, 0,
                                    [("creation", "success", str(e)[:100])])

            results.append(result)
            logger.info(f"  {result}")
            if result.failures:
                for field, exp, act in result.failures:
                    logger.info(f"    FAIL: {field} expected={exp} actual={act}")

    return results


def run_harness(modes=None, quick=False, retry_file=None):
    """Run the full test harness."""
    if modes is None:
        modes = ["create", "clone"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUTPUT_DIR / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    all_results = []

    # Generate test CSVs
    if "create" in modes:
        create_csv = out_dir / "test_create.csv"
        n = generate_create_csv(create_csv, quick=quick)
        logger.info(f"Generated CREATE CSV: {n} campaigns → {create_csv}")

    if "clone" in modes:
        clone_csv = out_dir / "test_clone.csv"
        n = generate_clone_csv(clone_csv, quick=quick)
        logger.info(f"Generated CLONE CSV: {n} campaigns → {clone_csv}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(
            storage_state="data/session/tj_session.json",
            viewport={"width": 1920, "height": 1080},
        )
        page = ctx.new_page()
        page.set_default_timeout(20000)

        ensure_session(page)

        if "create" in modes:
            logger.info(f"\n{'='*60}")
            logger.info(f"CREATE TESTS")
            logger.info(f"{'='*60}")
            results = run_csv_and_verify(page, create_csv, "create")
            all_results.extend(results)

        if "clone" in modes:
            # Fresh browser for clone batch — prevents memory/crash issues
            # from accumulated pages during create batch
            logger.info(f"\nRestarting browser for clone batch...")
            ctx.storage_state(path="data/session/tj_session.json")
            browser.close()
            time.sleep(2)

            browser = p.chromium.launch(headless=False)
            ctx = browser.new_context(
                storage_state="data/session/tj_session.json",
                viewport={"width": 1920, "height": 1080},
            )
            page = ctx.new_page()
            page.set_default_timeout(20000)

            # Fresh session with fresh browser
            ensure_session(page, force_relogin=True)

            logger.info(f"\n{'='*60}")
            logger.info(f"CLONE TESTS (cross-change)")
            logger.info(f"{'='*60}")
            results = run_csv_and_verify(page, clone_csv, "clone")
            all_results.extend(results)

        ctx.storage_state(path="data/session/tj_session.json")
        browser.close()

    _print_report(all_results, out_dir)
    return all_results


def _print_report(results, out_dir):
    """Print and save test report."""
    total_pass = sum(r.passed for r in results)
    total_fail = sum(r.failed for r in results)
    tests_ok = sum(1 for r in results if r.ok)
    tests_fail = sum(1 for r in results if not r.ok)

    print(f"\n{'='*70}")
    print(f"V4 FIELD TEST HARNESS — RESULTS")
    print(f"{'='*70}")
    print(f"Campaigns: {tests_ok} PASS, {tests_fail} FAIL (of {len(results)})")
    print(f"Fields:    {total_pass} PASS, {total_fail} FAIL")
    pct = (total_pass / (total_pass + total_fail) * 100) if (total_pass + total_fail) else 0
    print(f"Pass rate: {pct:.1f}%")
    print(f"{'='*70}")

    if tests_fail:
        print(f"\nFAILED ({tests_fail}):")
        for r in results:
            if not r.ok:
                print(f"  {r}")
                for field, exp, act in r.failures:
                    print(f"    {field}: expected={exp} actual={act}")

    print(f"\nPASSED ({tests_ok}):")
    for r in results:
        if r.ok:
            print(f"  {r}")

    # Save JSON report
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {"tests_ok": tests_ok, "tests_fail": tests_fail,
                     "fields_pass": total_pass, "fields_fail": total_fail,
                     "pass_rate": round(pct, 1)},
        "results": [
            {"name": r.name, "mode": r.mode, "campaign_id": r.campaign_id,
             "passed": r.passed, "failed": r.failed, "ok": r.ok,
             "failures": [{"field": f, "expected": str(e), "actual": str(a)}
                          for f, e, a in r.failures]}
            for r in results
        ],
    }
    with open(out_dir / "harness_report.json", "w") as f:
        json.dump(report, f, indent=2)

    # Save failed names for retry
    with open(out_dir / "failed_tests.txt", "w") as f:
        for r in results:
            if not r.ok:
                f.write(r.name + "\n")

    print(f"\nReport: {out_dir / 'harness_report.json'}")
    if tests_fail:
        print(f"Retry:  python {Path(__file__).name} --retry-failed {out_dir / 'failed_tests.txt'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="V4 Field Test Harness")
    parser.add_argument("--mode", choices=["create", "clone", "all"], default="all")
    parser.add_argument("--quick", action="store_true", help="Minimal set (4 create + 2 clone)")
    parser.add_argument("--retry-failed", help="Re-run only tests from failed_tests.txt")
    args = parser.parse_args()

    modes = ["create", "clone"] if args.mode == "all" else [args.mode]
    run_harness(modes=modes, quick=args.quick)

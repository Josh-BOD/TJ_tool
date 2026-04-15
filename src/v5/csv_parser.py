"""V5 CSV parser — extends V4 parser with 5 new columns."""

import csv
import logging
from pathlib import Path
from typing import List

from v4.csv_parser import _bool, _float, _int, _list, _optional_float, V4CSVParseError
from .models import V5CampaignConfig

logger = logging.getLogger(__name__)


def _row_to_v5_config(row: dict, row_num: int) -> V5CampaignConfig:
    """Convert one CSV row into a V5CampaignConfig (backwards-compatible with V4 CSVs)."""
    def g(key: str, default: str = "") -> str:
        return row.get(key, default).strip() if row.get(key) else default

    # Required fields
    group = g("group")
    csv_file = g("csv_file")
    if not group:
        raise V4CSVParseError(f"Row {row_num}: 'group' is required")
    if not csv_file:
        logger.info(f"Row {row_num}: no csv_file — template ads will be preserved")

    return V5CampaignConfig(
        # ── V4 fields (identical to v4/csv_parser.py) ────────────
        template_campaign_id=g("template_campaign_id"),
        enabled=_bool(g("enabled", "TRUE")),
        group=group,
        keywords=_list(g("keywords")),
        match_type=g("match_type", "exact").lower(),
        geo=_list(g("geo", "US")),
        variants=_list(g("variants", "desktop")),
        csv_file=csv_file,
        language=g("language", "EN").upper(),
        bid_type=g("bid_type", "CPA").upper(),
        campaign_type=g("campaign_type", "Standard").title(),
        content_rating=g("content_rating", "NSFW").upper(),
        device=g("device", ""),
        ad_format_type=g("ad_format_type", "display").lower(),
        format_type=g("format_type", "native").lower(),
        ad_type=g("ad_type", "rollover").lower(),
        ad_dimensions=g("ad_dimensions", "300x250"),
        content_category=g("content_category", "straight").lower(),
        gender=g("gender", "all").lower(),
        labels=_list(g("labels")),
        exchange_id=g("exchange_id"),
        geo_name=g("geo_name"),
        test_number=g("test_number"),
        keyword_name=g("keyword_name"),
        os_include=g("os_include"),
        os_exclude=g("os_exclude"),
        ios_version_op=g("ios_version_op"),
        ios_version=g("ios_version"),
        android_version_op=g("android_version_op"),
        android_version=g("android_version"),
        browsers_include=_list(g("browsers_include")),
        browser_language=g("browser_language"),
        postal_codes=_list(g("postal_codes")),
        isp_country=g("isp_country"),
        isp_name=g("isp_name"),
        ip_range_start=g("ip_range_start"),
        ip_range_end=g("ip_range_end"),
        income_segment=g("income_segment"),
        retargeting_type=g("retargeting_type"),
        retargeting_mode=g("retargeting_mode"),
        retargeting_value=g("retargeting_value"),
        vr_mode=g("vr_mode"),
        segment_targeting=g("segment_targeting"),
        tracker_id=g("tracker_id"),
        source_selection=g("source_selection"),
        smart_bidder=g("smart_bidder"),
        optimization_option=g("optimization_option"),
        target_cpa=_float(g("target_cpa"), 5.00),
        per_source_test_budget=_float(g("per_source_test_budget"), 5.00),
        max_bid=_float(g("max_bid"), 0.30),
        cpm_adjust=_optional_float(g("cpm_adjust")),
        cpm_bid_mode=g("cpm_bid_mode", "").lower(),
        cpm_bid_value=_optional_float(g("cpm_bid_value")),
        include_all_sources=_bool(g("include_all_sources", "TRUE")),
        automation_rules=g("automation_rules"),
        start_date=g("start_date"),
        end_date=g("end_date"),
        schedule_dayparting=g("schedule_dayparting"),
        frequency_cap=_int(g("frequency_cap"), 3),
        frequency_cap_every=_int(g("frequency_cap_every"), 24),
        budget_type=g("budget_type", "custom").lower(),
        daily_budget=_float(g("daily_budget"), 25.00),

        # ── V5 new fields (with backwards-compatible defaults) ───
        keywords_exclude=_list(g("keywords_exclude")),
        segment_targeting_exclude=g("segment_targeting_exclude"),
        ad_rotation=g("ad_rotation", "autopilot").lower(),
        autopilot_method=g("autopilot_method", "ctr").lower(),
        launch_paused=_bool(g("launch_paused", "TRUE")),
    )


def parse_v5_csv(csv_path: str | Path) -> List[V5CampaignConfig]:
    """Parse a V5 campaign CSV. Backwards-compatible with V4 CSVs."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise V4CSVParseError(f"CSV file not found: {csv_path}")

    configs: List[V5CampaignConfig] = []

    with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            try:
                config = _row_to_v5_config(row, row_num)
                configs.append(config)
            except V4CSVParseError:
                raise
            except Exception as e:
                raise V4CSVParseError(f"Row {row_num}: failed to parse — {e}") from e

    if not configs:
        raise V4CSVParseError("CSV file contains no data rows")

    logger.info(f"Parsed {len(configs)} V5 campaign configs from {csv_path.name}")
    return configs

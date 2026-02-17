"""V4 data models for full-field campaign configuration."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class V4CampaignConfig:
    """Complete campaign configuration covering all ~63 CSV columns."""

    # ── Core ──────────────────────────────────────────────────────
    enabled: bool = True
    group: str = ""
    keywords: List[str] = field(default_factory=list)
    match_type: str = "exact"          # "exact" or "broad"
    geo: List[str] = field(default_factory=lambda: ["US"])
    variants: List[str] = field(default_factory=lambda: ["desktop"])
    csv_file: str = ""

    # ── Step 1: Basic Settings ────────────────────────────────────
    language: str = "EN"
    bid_type: str = "CPA"              # CPA or CPM
    campaign_type: str = "Standard"    # Standard or Remarketing
    content_rating: str = "NSFW"       # NSFW or SFW
    device: str = ""                   # "" = auto from variant; "all", "desktop", "mobile"
    ad_format_type: str = "display"    # display, instream, pop
    format_type: str = "native"        # banner, native
    ad_type: str = "rollover"          # static_banner, video_banner, video_file, rollover
    ad_dimensions: str = "300x250"
    content_category: str = "straight" # straight, gay, trans
    gender: str = "all"                # all, male, female
    labels: List[str] = field(default_factory=list)
    exchange_id: str = ""
    geo_name: str = ""
    test_number: str = ""

    # ── Step 2: Toggle-Gated Targeting ────────────────────────────
    # OS targeting
    os_include: str = ""               # e.g. "iOS" or "iOS;Android"
    os_exclude: str = ""
    ios_version_op: str = ""           # newer_than, older_than, equal, between
    ios_version: str = ""              # e.g. "16.0"
    android_version_op: str = ""
    android_version: str = ""

    # Browser targeting
    browsers_include: List[str] = field(default_factory=list)  # e.g. ["Chrome","Firefox"]

    # Browser language
    browser_language: str = ""         # language code e.g. "DE"

    # Postal code targeting
    postal_codes: List[str] = field(default_factory=list)

    # ISP targeting
    isp_country: str = ""
    isp_name: str = ""

    # IP targeting
    ip_range_start: str = ""
    ip_range_end: str = ""

    # Income / public segment targeting
    income_segment: str = ""           # e.g. "$45,000 - $74,999"

    # Retargeting
    retargeting_type: str = ""         # click or impression
    retargeting_mode: str = ""         # include or exclude
    retargeting_value: str = ""        # audience/pixel name

    # VR targeting
    vr_mode: str = ""                  # "vr" or "non_vr"

    # Segment targeting
    segment_targeting: str = ""        # segment name/ID

    # ── Step 3: Tracking & Sources ────────────────────────────────
    tracker_id: str = ""               # conversion tracker name
    source_selection: str = ""         # "", "ALL", or semicolon-separated source names
    smart_bidder: str = ""             # "smart_cpm", "smart_cpa", or ""
    optimization_option: str = ""      # balanced, aggressive, conservative
    target_cpa: float = 5.00
    per_source_test_budget: float = 5.00
    max_bid: float = 0.30
    cpm_adjust: Optional[float] = None # percentage adjustment to suggested CPM
    include_all_sources: bool = True
    automation_rules: str = ""         # JSON or named rule preset

    # ── Step 4: Schedule & Budget ─────────────────────────────────
    start_date: str = ""               # YYYY-MM-DD
    end_date: str = ""                 # YYYY-MM-DD
    schedule_dayparting: str = ""      # JSON dayparting config
    frequency_cap: int = 3
    frequency_cap_every: int = 24      # hours
    daily_budget: float = 25.00

    # ── Derived helpers ───────────────────────────────────────────
    @property
    def primary_keyword(self) -> str:
        return self.keywords[0] if self.keywords else "Broad"

    @property
    def is_cpm(self) -> bool:
        return self.bid_type.upper() == "CPM"

    @property
    def is_remarketing(self) -> bool:
        return self.campaign_type.lower() == "remarketing"

    @property
    def has_os_targeting(self) -> bool:
        return bool(self.os_include or self.os_exclude)

    @property
    def has_browser_targeting(self) -> bool:
        return bool(self.browsers_include)

    @property
    def has_browser_language(self) -> bool:
        return bool(self.browser_language)

    @property
    def has_postal_codes(self) -> bool:
        return bool(self.postal_codes)

    @property
    def has_isp_targeting(self) -> bool:
        return bool(self.isp_country and self.isp_name)

    @property
    def has_ip_targeting(self) -> bool:
        return bool(self.ip_range_start and self.ip_range_end)

    @property
    def has_income_targeting(self) -> bool:
        return bool(self.income_segment)

    @property
    def has_retargeting(self) -> bool:
        return bool(self.retargeting_value)

    @property
    def has_vr_targeting(self) -> bool:
        return bool(self.vr_mode)

    @property
    def has_segment_targeting(self) -> bool:
        return bool(self.segment_targeting)

    def device_for_variant(self, variant: str) -> str:
        """Return the device radio value for a given variant."""
        if self.device:
            return self.device
        v = variant.lower().strip()
        if v == "all":
            return "all"
        if v == "desktop":
            return "desktop"
        if v in ("ios", "android", "all_mobile", "mobile"):
            return "mobile"
        return "desktop"

"""V5 data models — extends V4 with keyword exclude, segment exclude, ad rotation, launch control."""

from dataclasses import dataclass, field
from typing import List, Optional

from v4.models import V4CampaignConfig


@dataclass
class V5CampaignConfig(V4CampaignConfig):
    """V5 campaign config — 74 columns (V4's 69 + 5 new).

    New fields:
    - keywords_exclude: Keywords to exclude from targeting
    - segment_targeting_exclude: Segments to exclude
    - ad_rotation: Manual or Autopilot ad rotation
    - autopilot_method: CTR or CPA (when ad_rotation=autopilot)
    - launch_paused: Whether to launch campaign paused
    """

    # ── New V5 fields ─────────────────────────────────────────────
    keywords_exclude: List[str] = field(default_factory=list)
    segment_targeting_exclude: str = ""
    ad_rotation: str = "autopilot"       # "manual" or "autopilot"
    autopilot_method: str = "ctr"        # "ctr" or "cpa"
    launch_paused: bool = True           # Launch paused by default

    # ── V5 defaults (production values) ───────────────────────────
    # Override V4 defaults with production values
    # daily_budget default stays 25.0 in V4, but V5 harness sets 250.0

    @property
    def has_keyword_exclude(self) -> bool:
        return bool(self.keywords_exclude)

    @property
    def has_segment_exclude(self) -> bool:
        return bool(self.segment_targeting_exclude)

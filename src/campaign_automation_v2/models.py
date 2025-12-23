"""
Campaign data models.

Defines the data structures for campaign definitions and settings.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class CampaignStatus(Enum):
    """Campaign creation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class MatchType(Enum):
    """Keyword match type."""
    BROAD = "broad"
    EXACT = "exact"


class VersionOperator(Enum):
    """OS version operator."""
    ALL = "all"  # All versions
    NEWER_THAN = "newer_than"  # Newer than (>)
    OLDER_THAN = "older_than"  # Older than (<)
    EQUAL = "equal"  # Equal to (=)


@dataclass
class OSVersion:
    """OS version constraint."""
    operator: VersionOperator = VersionOperator.ALL
    version: Optional[str] = None  # e.g., "18.4", "11.0"
    
    def __str__(self) -> str:
        if self.operator == VersionOperator.ALL:
            return "All Versions"
        elif self.operator == VersionOperator.NEWER_THAN:
            return f">{self.version}"
        elif self.operator == VersionOperator.OLDER_THAN:
            return f"<{self.version}"
        elif self.operator == VersionOperator.EQUAL:
            return f"={self.version}"
        return "All Versions"
    
    @staticmethod
    def parse(value: str) -> 'OSVersion':
        """Parse OS version string like '>18.4' or '11.0'."""
        if not value or value.lower() in ('all', ''):
            return OSVersion(VersionOperator.ALL)
        
        value = value.strip()
        if value.startswith('>'):
            return OSVersion(VersionOperator.NEWER_THAN, value[1:].strip())
        elif value.startswith('<'):
            return OSVersion(VersionOperator.OLDER_THAN, value[1:].strip())
        elif value.startswith('='):
            return OSVersion(VersionOperator.EQUAL, value[1:].strip())
        else:
            # If just a version number, treat as "newer than"
            return OSVersion(VersionOperator.NEWER_THAN, value)


@dataclass
class Keyword:
    """Keyword with match type."""
    name: str
    match_type: MatchType
    
    def __str__(self) -> str:
        return f"{self.name} ({self.match_type.value})"


@dataclass
class CampaignSettings:
    """Campaign-specific settings."""
    target_cpa: float = 50.0
    per_source_test_budget: float = 200.0
    max_bid: float = 10.0
    frequency_cap: int = 2
    max_daily_budget: float = 250.0
    gender: str = "male"
    ios_version: Optional[OSVersion] = None  # iOS version constraint
    android_version: Optional[OSVersion] = None  # Android version constraint
    ad_format: str = "NATIVE"  # Options: "NATIVE", "INSTREAM" (used for campaign naming)
    
    # Campaign type and bidding settings
    campaign_type: str = "Standard"  # Options: "Standard" (keyword), "Remarketing" (audience)
    bid_type: str = "CPA"  # Options: "CPA", "CPM"
    
    # V3 From-Scratch settings (first page configuration)
    labels: List[str] = field(default_factory=list)  # Campaign labels (e.g., ["Native", "Test"])
    device: str = "desktop"  # all, desktop, mobile
    ad_format_type: str = "display"  # display, instream, pop
    format_type: str = "native"  # banner, native (for display ads)
    ad_type: str = "rollover"  # static_banner, video_banner, rollover
    ad_dimensions: str = "640x360"  # 300x250, 950x250, 468x60, 305x99, 300x100, 970x90, 320x480, 640x360
    content_category: str = "straight"  # straight, gay, trans
    
    def __post_init__(self):
        """Initialize version constraints if not set."""
        if self.ios_version is None:
            self.ios_version = OSVersion(VersionOperator.ALL)
        if self.android_version is None:
            self.android_version = OSVersion(VersionOperator.ALL)
        # Normalize ad_format to uppercase
        self.ad_format = self.ad_format.upper()
        # Normalize campaign_type to title case
        self.campaign_type = self.campaign_type.title()
        # Normalize bid_type to uppercase
        self.bid_type = self.bid_type.upper()
        # Normalize new fields to lowercase
        self.device = self.device.lower()
        self.ad_format_type = self.ad_format_type.lower()
        self.format_type = self.format_type.lower()
        self.ad_type = self.ad_type.lower()
        self.content_category = self.content_category.lower()
    
    @property
    def is_remarketing(self) -> bool:
        """Check if this is a remarketing campaign."""
        return self.campaign_type.lower() == "remarketing"
    
    @property
    def is_cpm(self) -> bool:
        """Check if this campaign uses CPM bidding."""
        return self.bid_type.upper() == "CPM"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "target_cpa": self.target_cpa,
            "per_source_test_budget": self.per_source_test_budget,
            "max_bid": self.max_bid,
            "frequency_cap": self.frequency_cap,
            "max_daily_budget": self.max_daily_budget,
            "gender": self.gender,
            "ios_version": str(self.ios_version) if self.ios_version else "All Versions",
            "android_version": str(self.android_version) if self.android_version else "All Versions",
            "ad_format": self.ad_format,
            "campaign_type": self.campaign_type,
            "bid_type": self.bid_type,
            # V3 From-Scratch settings
            "labels": self.labels,
            "device": self.device,
            "ad_format_type": self.ad_format_type,
            "format_type": self.format_type,
            "ad_type": self.ad_type,
            "ad_dimensions": self.ad_dimensions,
            "content_category": self.content_category
        }


@dataclass
class VariantStatus:
    """Status of a campaign variant (desktop/ios/android)."""
    status: CampaignStatus = CampaignStatus.PENDING
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    ads_uploaded: int = 0
    error: Optional[str] = None
    step: Optional[str] = None  # Current step if in progress
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "ads_uploaded": self.ads_uploaded,
            "error": self.error,
            "step": self.step,
            "completed_at": self.completed_at
        }


@dataclass
class CampaignDefinition:
    """Definition of a campaign set (can create multiple variants)."""
    group: str
    keywords: List[Keyword]
    geo: List[str]
    csv_file: str
    variants: List[str]  # ["desktop", "ios", "android"] or ["desktop", "all mobile"]
    settings: CampaignSettings
    enabled: bool = True
    mobile_combined: bool = False  # True when using "all mobile" variant (iOS + Android in same campaign)
    test_number: Optional[str] = None  # Test number for naming (e.g., "12" becomes "_T-12")
    
    # Status tracking
    status: CampaignStatus = CampaignStatus.PENDING
    variant_statuses: Dict[str, VariantStatus] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize variant statuses."""
        if not self.variant_statuses:
            for variant in self.variants:
                self.variant_statuses[variant] = VariantStatus()
    
    @property
    def primary_keyword(self) -> str:
        """Get the primary (first) keyword for naming."""
        return self.keywords[0].name if self.keywords else "Unknown"
    
    @property
    def is_enabled(self) -> bool:
        """Check if campaign should be created."""
        return self.enabled
    
    @property
    def is_completed(self) -> bool:
        """Check if all variants are completed."""
        return all(
            vs.status == CampaignStatus.COMPLETED 
            for vs in self.variant_statuses.values()
        )
    
    @property
    def has_failures(self) -> bool:
        """Check if any variants failed."""
        return any(
            vs.status == CampaignStatus.FAILED 
            for vs in self.variant_statuses.values()
        )
    
    def get_variant_status(self, variant: str) -> VariantStatus:
        """Get status for a specific variant."""
        return self.variant_statuses.get(variant, VariantStatus())
    
    def update_variant_status(
        self,
        variant: str,
        status: CampaignStatus,
        **kwargs
    ):
        """Update variant status."""
        if variant not in self.variant_statuses:
            self.variant_statuses[variant] = VariantStatus()
        
        variant_status = self.variant_statuses[variant]
        variant_status.status = status
        
        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(variant_status, key):
                setattr(variant_status, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "group": self.group,
            "keywords": [
                {"name": kw.name, "match_type": kw.match_type.value}
                for kw in self.keywords
            ],
            "geo": self.geo,
            "csv_file": self.csv_file,
            "variants": self.variants,
            "settings": self.settings.to_dict(),
            "enabled": self.enabled,
            "mobile_combined": self.mobile_combined,
            "test_number": self.test_number,
            "status": self.status.value,
            "variant_statuses": {
                variant: vs.to_dict()
                for variant, vs in self.variant_statuses.items()
            }
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'CampaignDefinition':
        """Create CampaignDefinition from dictionary."""
        # Parse keywords
        keywords = [
            Keyword(
                name=kw["name"],
                match_type=MatchType(kw["match_type"])
            )
            for kw in data.get("keywords", [])
        ]
        
        # Parse settings
        settings_data = data.get("settings", {})
        settings = CampaignSettings(
            target_cpa=settings_data.get("target_cpa", 50.0),
            per_source_test_budget=settings_data.get("per_source_test_budget", 200.0),
            max_bid=settings_data.get("max_bid", 10.0),
            frequency_cap=settings_data.get("frequency_cap", 2),
            max_daily_budget=settings_data.get("max_daily_budget", 250.0),
            gender=settings_data.get("gender", "male"),
            ios_version=OSVersion.parse(settings_data.get("ios_version", "All Versions")),
            android_version=OSVersion.parse(settings_data.get("android_version", "All Versions")),
            ad_format=settings_data.get("ad_format", "NATIVE"),
            campaign_type=settings_data.get("campaign_type", "Standard"),
            bid_type=settings_data.get("bid_type", "CPA"),
            # V3 From-Scratch settings
            labels=settings_data.get("labels", []),
            device=settings_data.get("device", "desktop"),
            ad_format_type=settings_data.get("ad_format_type", "display"),
            format_type=settings_data.get("format_type", "native"),
            ad_type=settings_data.get("ad_type", "rollover"),
            ad_dimensions=settings_data.get("ad_dimensions", "640x360"),
            content_category=settings_data.get("content_category", "straight")
        )
        
        # Parse variant statuses
        variant_statuses = {}
        for variant, vs_data in data.get("variant_statuses", {}).items():
            variant_statuses[variant] = VariantStatus(
                status=CampaignStatus(vs_data.get("status", "pending")),
                campaign_id=vs_data.get("campaign_id"),
                campaign_name=vs_data.get("campaign_name"),
                ads_uploaded=vs_data.get("ads_uploaded", 0),
                error=vs_data.get("error"),
                step=vs_data.get("step"),
                completed_at=vs_data.get("completed_at")
            )
        
        return CampaignDefinition(
            group=data["group"],
            keywords=keywords,
            geo=data.get("geo", []),
            csv_file=data.get("csv_file", ""),
            variants=data.get("variants", []),
            settings=settings,
            enabled=data.get("enabled", True),
            mobile_combined=data.get("mobile_combined", False),
            test_number=data.get("test_number"),
            status=CampaignStatus(data.get("status", "pending")),
            variant_statuses=variant_statuses
        )


@dataclass
class CampaignBatch:
    """Batch of campaign definitions to create."""
    campaigns: List[CampaignDefinition]
    input_file: str
    session_id: str
    
    @property
    def total_campaigns(self) -> int:
        """Total number of campaign sets."""
        return len(self.campaigns)
    
    @property
    def enabled_campaigns(self) -> List[CampaignDefinition]:
        """Get only enabled campaigns."""
        return [c for c in self.campaigns if c.is_enabled]
    
    @property
    def total_variants(self) -> int:
        """Total number of variants to create across all campaigns."""
        return sum(len(c.variants) for c in self.enabled_campaigns)
    
    @property
    def completed_count(self) -> int:
        """Count of completed campaign sets."""
        return sum(1 for c in self.campaigns if c.is_completed)
    
    @property
    def failed_count(self) -> int:
        """Count of failed campaign sets."""
        return sum(1 for c in self.campaigns if c.has_failures)
    
    def get_campaign_by_group(self, group: str) -> Optional[CampaignDefinition]:
        """Find campaign by group name."""
        for campaign in self.campaigns:
            if campaign.group == group:
                return campaign
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "campaigns": [c.to_dict() for c in self.campaigns],
            "input_file": self.input_file,
            "session_id": self.session_id,
            "total_campaigns": self.total_campaigns,
            "total_variants": self.total_variants,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count
        }


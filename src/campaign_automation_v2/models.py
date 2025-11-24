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
    ad_format: str = "NATIVE"  # Options: "NATIVE", "INSTREAM"
    
    def __post_init__(self):
        """Initialize version constraints if not set."""
        if self.ios_version is None:
            self.ios_version = OSVersion(VersionOperator.ALL)
        if self.android_version is None:
            self.android_version = OSVersion(VersionOperator.ALL)
        # Normalize ad_format to uppercase
        self.ad_format = self.ad_format.upper()
    
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
            "ad_format": self.ad_format
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
    variants: List[str]  # ["desktop", "ios", "android"]
    settings: CampaignSettings
    enabled: bool = True
    
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
            "status": self.status.value,
            "variant_statuses": {
                variant: vs.to_dict()
                for variant, vs in self.variant_statuses.items()
            }
        }


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


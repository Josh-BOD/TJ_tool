"""Data models for ad pausing operations."""

from dataclasses import dataclass, field
from typing import List, Set, Dict, Any
from datetime import datetime


@dataclass
class PauseResult:
    """Result of pausing ads in a single campaign."""
    campaign_id: str
    campaign_name: str
    ads_found: List[str] = field(default_factory=list)  # Creative IDs found on page
    ads_paused: List[str] = field(default_factory=list)  # Creative IDs successfully paused
    ads_not_found: List[str] = field(default_factory=list)  # Creative IDs not found in campaign
    pages_processed: int = 0
    time_taken: float = 0.0
    errors: List[str] = field(default_factory=list)
    status: str = 'pending'  # 'success', 'partial', 'failed'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'campaign_id': self.campaign_id,
            'campaign_name': self.campaign_name,
            'ads_found': self.ads_found,
            'ads_paused': self.ads_paused,
            'ads_not_found': self.ads_not_found,
            'pages_processed': self.pages_processed,
            'time_taken': self.time_taken,
            'errors': self.errors,
            'status': self.status
        }


@dataclass
class PauseBatch:
    """Batch of pause operations across multiple campaigns."""
    creative_ids: Set[str]
    campaign_ids: List[str]
    results: List[PauseResult] = field(default_factory=list)
    dry_run: bool = False
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default=None)
    
    @property
    def total_ads_paused(self) -> int:
        """Total number of ads paused across all campaigns."""
        return sum(len(r.ads_paused) for r in self.results)
    
    @property
    def total_campaigns_processed(self) -> int:
        """Total number of campaigns processed."""
        return len(self.results)
    
    @property
    def successful_campaigns(self) -> int:
        """Number of campaigns with status 'success'."""
        return sum(1 for r in self.results if r.status == 'success')
    
    @property
    def failed_campaigns(self) -> int:
        """Number of campaigns with status 'failed'."""
        return sum(1 for r in self.results if r.status == 'failed')
    
    @property
    def partial_campaigns(self) -> int:
        """Number of campaigns with status 'partial'."""
        return sum(1 for r in self.results if r.status == 'partial')
    
    @property
    def duration_seconds(self) -> float:
        """Total duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()
    
    def get_all_not_found(self) -> Dict[str, int]:
        """Get all creative IDs not found with count of campaigns searched."""
        not_found = {}
        for result in self.results:
            for creative_id in result.ads_not_found:
                not_found[creative_id] = not_found.get(creative_id, 0) + 1
        return not_found
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'creative_ids': list(self.creative_ids),
            'campaign_ids': self.campaign_ids,
            'results': [r.to_dict() for r in self.results],
            'dry_run': self.dry_run,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_ads_paused': self.total_ads_paused,
            'total_campaigns_processed': self.total_campaigns_processed,
            'successful_campaigns': self.successful_campaigns,
            'failed_campaigns': self.failed_campaigns,
            'partial_campaigns': self.partial_campaigns,
            'duration_seconds': self.duration_seconds
        }


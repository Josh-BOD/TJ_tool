"""
Data models for Keyword Research tool.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class DiscoveredKeyword:
    """A keyword discovered from TJ's keyword search."""
    keyword: str
    source_seed: str  # The seed keyword that led to this discovery
    
    def __hash__(self):
        return hash(self.keyword.lower())
    
    def __eq__(self, other):
        if isinstance(other, DiscoveredKeyword):
            return self.keyword.lower() == other.keyword.lower()
        return False


@dataclass
class SeedKeywordRow:
    """A row from the input CSV containing a seed keyword and its settings."""
    group: str
    keyword: str
    keyword_matches: str
    gender: str
    geo: str
    multi_geo: str
    csv_file: str
    target_cpa: float
    per_source_budget: float
    max_bid: float
    frequency_cap: int
    max_daily_budget: float
    variants: str
    ios_version: str
    android_version: str
    ad_format: str
    enabled: bool
    extra_columns: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV output."""
        result = {
            'group': self.group,
            'keywords': self.keyword,
            'keyword_matches': self.keyword_matches,
            'gender': self.gender,
            'geo': self.geo,
            'multi_geo': self.multi_geo,
            'csv_file': self.csv_file,
            'target_cpa': self.target_cpa,
            'per_source_budget': self.per_source_budget,
            'max_bid': self.max_bid,
            'frequency_cap': self.frequency_cap,
            'max_daily_budget': self.max_daily_budget,
            'variants': self.variants,
            'ios_version': self.ios_version,
            'android_version': self.android_version,
            'ad_format': self.ad_format,
            'enabled': self.enabled,
        }
        result.update(self.extra_columns)
        return result
    
    def create_discovered_row(self, discovered_keyword: str) -> 'SeedKeywordRow':
        """Create a new row with a discovered keyword, inheriting all settings."""
        return SeedKeywordRow(
            group=self.group,
            keyword=discovered_keyword,
            keyword_matches=self.keyword_matches,
            gender=self.gender,
            geo=self.geo,
            multi_geo=self.multi_geo,
            csv_file=self.csv_file,
            target_cpa=self.target_cpa,
            per_source_budget=self.per_source_budget,
            max_bid=self.max_bid,
            frequency_cap=self.frequency_cap,
            max_daily_budget=self.max_daily_budget,
            variants=self.variants,
            ios_version=self.ios_version,
            android_version=self.android_version,
            ad_format=self.ad_format,
            enabled=False,  # Default to disabled so user can review
            extra_columns=self.extra_columns.copy()
        )


@dataclass
class ResearchResult:
    """Result of researching a single seed keyword."""
    seed_keyword: str
    discovered_keywords: List[str] = field(default_factory=list)
    status: str = 'pending'  # pending, success, failed
    error: Optional[str] = None
    time_taken: float = 0.0


@dataclass
class ResearchBatch:
    """Batch of keyword research operations."""
    seed_keywords: List[str]
    results: List[ResearchResult] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def total_seeds(self) -> int:
        return len(self.seed_keywords)
    
    @property
    def completed_count(self) -> int:
        return sum(1 for r in self.results if r.status == 'success')
    
    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if r.status == 'failed')
    
    @property
    def total_discovered(self) -> int:
        return sum(len(r.discovered_keywords) for r in self.results)
    
    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

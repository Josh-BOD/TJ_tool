"""
Campaign definition validator.

Validates campaign definitions for correctness before creation.
"""

from pathlib import Path
from typing import List, Tuple, Optional
import re

from .models import CampaignDefinition, CampaignBatch, Keyword

# Import from parent src directory
import sys
from pathlib import Path
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from campaign_templates import VALID_GEO_CODES, VALID_DEVICES, VALID_GENDERS


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class CampaignValidator:
    """Validates campaign definitions."""
    
    def __init__(self, csv_dir: Path):
        """
        Initialize validator.
        
        Args:
            csv_dir: Directory containing CSV ad files
        """
        self.csv_dir = csv_dir
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_batch(self, batch: CampaignBatch) -> Tuple[bool, List[str], List[str]]:
        """
        Validate entire campaign batch.
        
        Args:
            batch: CampaignBatch to validate
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        # Validate each campaign
        for i, campaign in enumerate(batch.campaigns, start=1):
            self._validate_campaign(campaign, i)
        
        # Check for duplicate campaign names
        self._check_duplicates(batch)
        
        is_valid = len(self.errors) == 0
        return is_valid, self.errors.copy(), self.warnings.copy()
    
    def _validate_campaign(self, campaign: CampaignDefinition, index: int):
        """Validate a single campaign definition."""
        prefix = f"Campaign {index} ('{campaign.group}')"
        
        # Validate group name
        if not campaign.group or len(campaign.group) > 64:
            self.errors.append(
                f"{prefix}: Group name must be 1-64 characters"
            )
        
        # Validate keywords
        if not campaign.keywords:
            self.errors.append(f"{prefix}: No keywords specified")
        else:
            for kw in campaign.keywords:
                self._validate_keyword(kw, prefix)
        
        # Validate geo codes
        for geo in campaign.geo:
            if geo.upper() not in VALID_GEO_CODES:
                self.warnings.append(
                    f"{prefix}: Geo code '{geo}' may not be valid. "
                    f"Common codes: US, CA, UK, AU, NZ"
                )
        
        # Validate CSV file
        csv_path = self.csv_dir / campaign.csv_file
        if not csv_path.exists():
            self.errors.append(
                f"{prefix}: CSV file not found: {campaign.csv_file}"
            )
        elif csv_path.stat().st_size == 0:
            self.errors.append(
                f"{prefix}: CSV file is empty: {campaign.csv_file}"
            )
        
        # Validate variants
        if not campaign.variants:
            self.errors.append(f"{prefix}: No variants specified")
        else:
            for variant in campaign.variants:
                if variant.lower() not in VALID_DEVICES:
                    self.errors.append(
                        f"{prefix}: Invalid variant '{variant}'. "
                        f"Must be: desktop, ios, or android"
                    )
        
        # Validate settings
        self._validate_settings(campaign, prefix)
    
    def _validate_keyword(self, keyword: Keyword, prefix: str):
        """Validate a keyword."""
        if not keyword.name or not keyword.name.strip():
            self.errors.append(f"{prefix}: Empty keyword found")
            return
        
        # Check for suspicious characters
        if re.search(r'[<>{}[\]\\]', keyword.name):
            self.warnings.append(
                f"{prefix}: Keyword '{keyword.name}' contains unusual characters"
            )
        
        # Warn about very long keywords
        if len(keyword.name) > 50:
            self.warnings.append(
                f"{prefix}: Keyword '{keyword.name}' is very long (>50 chars)"
            )
    
    def _validate_settings(self, campaign: CampaignDefinition, prefix: str):
        """Validate campaign settings."""
        settings = campaign.settings
        
        # Validate numeric values
        if settings.target_cpa <= 0:
            self.errors.append(
                f"{prefix}: Target CPA must be positive (got {settings.target_cpa})"
            )
        elif settings.target_cpa < 1:
            self.warnings.append(
                f"{prefix}: Target CPA is very low (${settings.target_cpa})"
            )
        
        if settings.per_source_test_budget <= 0:
            self.errors.append(
                f"{prefix}: Per Source Budget must be positive"
            )
        
        if settings.max_bid <= 0:
            self.errors.append(
                f"{prefix}: Max Bid must be positive"
            )
        elif settings.max_bid > settings.target_cpa:
            self.warnings.append(
                f"{prefix}: Max Bid (${settings.max_bid}) is higher than "
                f"Target CPA (${settings.target_cpa})"
            )
        
        if settings.frequency_cap < 1 or settings.frequency_cap > 99:
            self.errors.append(
                f"{prefix}: Frequency Cap must be between 1 and 99"
            )
        
        if settings.max_daily_budget <= 0:
            self.errors.append(
                f"{prefix}: Max Daily Budget must be positive"
            )
        elif settings.max_daily_budget < settings.per_source_test_budget:
            self.warnings.append(
                f"{prefix}: Max Daily Budget (${settings.max_daily_budget}) is "
                f"less than Per Source Budget (${settings.per_source_test_budget})"
            )
        
        # Validate gender
        if settings.gender.lower() not in VALID_GENDERS:
            self.errors.append(
                f"{prefix}: Invalid gender '{settings.gender}'. "
                f"Must be: male, female, or all"
            )
    
    def _check_duplicates(self, batch: CampaignBatch):
        """Check for duplicate campaign names."""
        from campaign_templates import generate_campaign_name, DEFAULT_SETTINGS
        
        seen_names = {}
        
        for i, campaign in enumerate(batch.campaigns, start=1):
            if not campaign.is_enabled:
                continue
            
            for variant in campaign.variants:
                # Generate what the campaign name would be
                geo = campaign.geo[0] if campaign.geo else "US"
                keyword = campaign.primary_keyword
                
                name = generate_campaign_name(
                    geo=geo,
                    language=DEFAULT_SETTINGS["language"],
                    ad_format=DEFAULT_SETTINGS["ad_format"],
                    bid_type=DEFAULT_SETTINGS["bid_type"],
                    source=DEFAULT_SETTINGS["source"],
                    keyword=keyword,
                    device=variant,
                    gender=campaign.settings.gender
                )
                
                if name in seen_names:
                    self.errors.append(
                        f"Duplicate campaign name would be created: {name}\n"
                        f"  First: Campaign {seen_names[name]} ('{campaign.group}')\n"
                        f"  Duplicate: Campaign {i} ('{campaign.group}')"
                    )
                else:
                    seen_names[name] = i


def validate_batch(batch: CampaignBatch, csv_dir: Path) -> Tuple[bool, List[str], List[str]]:
    """
    Validate campaign batch.
    
    Args:
        batch: CampaignBatch to validate
        csv_dir: Directory containing CSV ad files
        
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    validator = CampaignValidator(csv_dir)
    return validator.validate_batch(batch)


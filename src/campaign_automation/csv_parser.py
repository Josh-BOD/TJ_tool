"""
CSV input parser for campaign definitions.

Parses CSV files containing campaign definitions and converts them to
CampaignDefinition objects.
"""

import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import (
    CampaignDefinition,
    CampaignSettings,
    Keyword,
    MatchType,
    CampaignBatch
)

# Import from parent src directory
import sys
from pathlib import Path
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from campaign_templates import DEFAULT_SETTINGS


class CSVParseError(Exception):
    """Raised when CSV parsing fails."""
    pass


class CSVParser:
    """Parser for campaign definition CSV files."""
    
    # Required columns
    REQUIRED_COLUMNS = {
        "group",
        "keywords",
        "keyword_matches",
        "csv_file",
        "variants",
        "enabled"
    }
    
    # Optional columns with defaults
    OPTIONAL_COLUMNS = {
        "geo": "US",
        "target_cpa": 50.0,
        "per_source_budget": 200.0,
        "max_bid": 10.0,
        "frequency_cap": 2,
        "max_daily_budget": 250.0,
        "gender": "male"
    }
    
    def __init__(self, csv_path: Path):
        """
        Initialize CSV parser.
        
        Args:
            csv_path: Path to CSV file
        """
        self.csv_path = csv_path
        self.row_number = 0
    
    def parse(self) -> CampaignBatch:
        """
        Parse CSV file and return CampaignBatch.
        
        Returns:
            CampaignBatch object
            
        Raises:
            CSVParseError: If parsing fails
        """
        if not self.csv_path.exists():
            raise CSVParseError(f"CSV file not found: {self.csv_path}")
        
        campaigns = []
        
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Validate headers
                self._validate_headers(reader.fieldnames)
                
                # Parse each row
                for self.row_number, row in enumerate(reader, start=2):  # Start at 2 (after header)
                    try:
                        campaign = self._parse_row(row)
                        if campaign:
                            campaigns.append(campaign)
                    except Exception as e:
                        raise CSVParseError(
                            f"Error parsing row {self.row_number}: {str(e)}"
                        )
        
        except csv.Error as e:
            raise CSVParseError(f"CSV format error: {str(e)}")
        except Exception as e:
            if isinstance(e, CSVParseError):
                raise
            raise CSVParseError(f"Failed to parse CSV: {str(e)}")
        
        if not campaigns:
            raise CSVParseError("No campaigns found in CSV file")
        
        # Create batch
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch = CampaignBatch(
            campaigns=campaigns,
            input_file=str(self.csv_path),
            session_id=session_id
        )
        
        return batch
    
    def _validate_headers(self, headers: Optional[List[str]]):
        """Validate CSV headers."""
        if not headers:
            raise CSVParseError("CSV file is empty or has no headers")
        
        headers_set = set(h.strip().lower() for h in headers)
        missing = self.REQUIRED_COLUMNS - headers_set
        
        if missing:
            raise CSVParseError(
                f"Missing required columns: {', '.join(sorted(missing))}"
            )
    
    def _parse_row(self, row: Dict[str, str]) -> Optional[CampaignDefinition]:
        """Parse a single CSV row into CampaignDefinition."""
        # Normalize keys (strip whitespace, lowercase)
        row = {k.strip().lower(): v.strip() for k, v in row.items()}
        
        # Skip empty rows
        if not any(row.values()):
            return None
        
        # Parse enabled flag
        enabled = self._parse_bool(row.get("enabled", "true"))
        
        # Parse required fields
        group = self._get_required(row, "group")
        keywords = self._parse_keywords(row)
        geo = self._parse_geo(row)
        csv_file = self._get_required(row, "csv_file")
        variants = self._parse_variants(row)
        
        # Parse settings
        settings = CampaignSettings(
            target_cpa=self._parse_float(
                row.get("target_cpa"),
                DEFAULT_SETTINGS["target_cpa"]
            ),
            per_source_test_budget=self._parse_float(
                row.get("per_source_budget"),
                DEFAULT_SETTINGS["per_source_test_budget"]
            ),
            max_bid=self._parse_float(
                row.get("max_bid"),
                DEFAULT_SETTINGS["max_bid"]
            ),
            frequency_cap=self._parse_int(
                row.get("frequency_cap"),
                DEFAULT_SETTINGS["frequency_cap"]
            ),
            max_daily_budget=self._parse_float(
                row.get("max_daily_budget"),
                DEFAULT_SETTINGS["max_daily_budget"]
            ),
            gender=row.get("gender", DEFAULT_SETTINGS["gender"]).lower()
        )
        
        return CampaignDefinition(
            group=group,
            keywords=keywords,
            geo=geo,
            csv_file=csv_file,
            variants=variants,
            settings=settings,
            enabled=enabled
        )
    
    def _get_required(self, row: Dict[str, str], key: str) -> str:
        """Get required field value."""
        value = row.get(key, "").strip()
        if not value:
            raise CSVParseError(f"Missing required field: {key}")
        return value
    
    def _parse_keywords(self, row: Dict[str, str]) -> List[Keyword]:
        """Parse keywords and match types."""
        keywords_str = self._get_required(row, "keywords")
        matches_str = self._get_required(row, "keyword_matches")
        
        # Split by semicolon
        keyword_names = [k.strip() for k in keywords_str.split(";") if k.strip()]
        match_types = [m.strip().lower() for m in matches_str.split(";") if m.strip()]
        
        if not keyword_names:
            raise CSVParseError("No keywords specified")
        
        if len(keyword_names) != len(match_types):
            raise CSVParseError(
                f"Keywords count ({len(keyword_names)}) doesn't match "
                f"match types count ({len(match_types)})"
            )
        
        keywords = []
        for name, match in zip(keyword_names, match_types):
            try:
                match_type = MatchType(match)
            except ValueError:
                raise CSVParseError(
                    f"Invalid match type '{match}' for keyword '{name}'. "
                    f"Must be 'broad' or 'exact'"
                )
            keywords.append(Keyword(name=name, match_type=match_type))
        
        return keywords
    
    def _parse_geo(self, row: Dict[str, str]) -> List[str]:
        """Parse geo country codes."""
        geo_str = row.get("geo", "US").strip()
        if not geo_str:
            geo_str = "US"
        
        # Split by semicolon and uppercase
        geo_codes = [g.strip().upper() for g in geo_str.split(";") if g.strip()]
        
        if not geo_codes:
            geo_codes = ["US"]
        
        return geo_codes
    
    def _parse_variants(self, row: Dict[str, str]) -> List[str]:
        """Parse device variants."""
        variants_str = self._get_required(row, "variants")
        
        # Split by comma and lowercase
        variants = [v.strip().lower() for v in variants_str.split(",") if v.strip()]
        
        if not variants:
            raise CSVParseError("No variants specified")
        
        # Validate variant names
        valid_variants = {"desktop", "ios", "android"}
        for variant in variants:
            if variant not in valid_variants:
                raise CSVParseError(
                    f"Invalid variant '{variant}'. "
                    f"Must be one of: desktop, ios, android"
                )
        
        return variants
    
    def _parse_bool(self, value: str) -> bool:
        """Parse boolean value."""
        if not value:
            return True
        
        value = value.strip().lower()
        if value in ("true", "yes", "1", "y"):
            return True
        elif value in ("false", "no", "0", "n"):
            return False
        else:
            raise CSVParseError(f"Invalid boolean value: {value}")
    
    def _parse_float(self, value: Optional[str], default: float) -> float:
        """Parse float value with default."""
        if not value or not value.strip():
            return default
        
        try:
            return float(value.strip())
        except ValueError:
            raise CSVParseError(f"Invalid number: {value}")
    
    def _parse_int(self, value: Optional[str], default: int) -> int:
        """Parse integer value with default."""
        if not value or not value.strip():
            return default
        
        try:
            return int(value.strip())
        except ValueError:
            raise CSVParseError(f"Invalid integer: {value}")


def parse_csv(csv_path: Path) -> CampaignBatch:
    """
    Parse campaign definitions from CSV file.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        CampaignBatch object
        
    Raises:
        CSVParseError: If parsing fails
    """
    parser = CSVParser(csv_path)
    return parser.parse()


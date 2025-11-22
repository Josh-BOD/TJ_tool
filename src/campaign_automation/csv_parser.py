"""
CSV input parser for campaign definitions.

Parses CSV files containing campaign definitions and converts them to
CampaignDefinition objects.

CSV Format:
-----------

Required Columns:
- group: Campaign group name (e.g., "Milfs", "Cougars")
- keywords: Semicolon-separated list (e.g., "milf;milfs;milf porn")
- csv_file: Path to ad CSV file
- variants: Comma-separated device types (e.g., "desktop,ios,android")
- enabled: TRUE/FALSE to enable/disable this row

Optional Columns:
- keyword_matches: Only specify "broad" for keywords that need it
  Examples:
    - "broad" = first keyword is broad, rest are exact
    - "broad;broad" = first 2 keywords are broad, rest are exact
    - "" or omit = all keywords are exact
- gender: "male", "female", or "all" (default: "male")
- geo: Semicolon-separated geos for ONE campaign (e.g., "US;CA;UK")
- multi_geo: Semicolon-separated geos to create SEPARATE campaigns (e.g., "CA;AUS")
  Note: Use either 'geo' OR 'multi_geo', not both
- target_cpa: Target CPA (default: 50.0)
- per_source_budget: Per-source test budget (default: 200.0)
- max_bid: Maximum bid (default: 10.0)
- frequency_cap: Frequency cap (default: 2)
- max_daily_budget: Maximum daily budget (default: 250.0)

Examples:
---------

1. Create separate campaigns for CA and AUS:
   group,keywords,keyword_matches,gender,geo,multi_geo,csv_file,...,enabled
   Milfs,"milf;milfs;mature",broad,,,"CA;AUS",ads.csv,...,TRUE
   
   Result: 2 campaigns (Milfs-CA, Milfs-AUS), each with 3 variants

2. Create one campaign targeting multiple geos:
   group,keywords,keyword_matches,gender,geo,multi_geo,csv_file,...,enabled
   Milfs,"milf;milfs;mature",broad,female,"US;CA;UK",,ads.csv,...,TRUE
   
   Result: 1 campaign (Milfs) targeting US+CA+UK, with 3 variants

3. Mix of broad and exact keywords:
   keywords: "milf;milfs;milf porn;cougar;older woman"
   keyword_matches: "broad;broad"
   Result: First 2 are broad, last 3 are exact
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
        "csv_file",
        "variants",
        "enabled"
    }
    
    # Optional columns with defaults
    OPTIONAL_COLUMNS = {
        "geo": "US",  # Single campaign with multiple geos (semicolon-separated, e.g., "US;CA;UK")
        "multi_geo": "",  # Create separate campaigns per geo (semicolon-separated, e.g., "US;CA;UK")
        "keyword_matches": "",  # Only specify "broad" for keywords that need it (e.g., "broad;broad" = first 2 broad, rest exact)
        "target_cpa": 50.0,
        "per_source_budget": 200.0,
        "max_bid": 10.0,
        "frequency_cap": 2,
        "max_daily_budget": 250.0,
        "gender": "male"  # Options: "male", "female", "all"
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
                        campaign_list = self._parse_row(row)
                        if campaign_list:
                            campaigns.extend(campaign_list)  # Add all campaigns from this row
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
    
    def _parse_row(self, row: Dict[str, str]) -> List[CampaignDefinition]:
        """
        Parse a single CSV row into one or more CampaignDefinition objects.
        
        Two modes:
        1. If 'multi_geo' is specified: Creates separate campaigns for each geo
        2. If only 'geo' is specified: Creates a single campaign with those geos
        
        Returns:
            List of CampaignDefinition objects
        """
        # Normalize keys (strip whitespace, lowercase)
        row = {k.strip().lower(): v.strip() for k, v in row.items()}
        
        # Skip empty rows
        if not any(row.values()):
            return []
        
        # Parse enabled flag
        enabled = self._parse_bool(row.get("enabled", "true"))
        
        # Parse required fields
        group = self._get_required(row, "group")
        keywords = self._parse_keywords(row)
        csv_file = self._get_required(row, "csv_file")
        variants = self._parse_variants(row)
        
        # Check if multi_geo is specified
        multi_geo_str = row.get("multi_geo", "").strip()
        
        # Parse settings (same for all campaigns)
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
        
        campaigns = []
        
        if multi_geo_str:
            # Mode 1: Create separate campaigns for each geo
            geo_codes = [g.strip().upper() for g in multi_geo_str.split(";") if g.strip()]
            if not geo_codes:
                raise CSVParseError("multi_geo specified but no geo codes provided")
            
            for geo_code in geo_codes:
                campaign = CampaignDefinition(
                    group=group,
                    keywords=keywords,
                    geo=[geo_code],  # Single geo per campaign
                    csv_file=csv_file,
                    variants=variants,
                    settings=settings,
                    enabled=enabled
                )
                campaigns.append(campaign)
        else:
            # Mode 2: Single campaign with geos from 'geo' column
            geo_list = self._parse_geo(row)
            campaign = CampaignDefinition(
                group=group,
                keywords=keywords,
                geo=geo_list,  # Can be multiple geos in one campaign
                csv_file=csv_file,
                variants=variants,
                settings=settings,
                enabled=enabled
            )
            campaigns.append(campaign)
        
        return campaigns
    
    def _get_required(self, row: Dict[str, str], key: str) -> str:
        """Get required field value."""
        value = row.get(key, "").strip()
        if not value:
            raise CSVParseError(f"Missing required field: {key}")
        return value
    
    def _parse_keywords(self, row: Dict[str, str]) -> List[Keyword]:
        """
        Parse keywords and match types.
        
        Match types are simplified:
        - Only specify "broad" for keywords that need it
        - All remaining keywords default to "exact"
        
        Examples:
        - keywords: "milf;milfs;milf porn;cougar;older woman"
        - keyword_matches: "broad;broad" -> first 2 are broad, rest are exact
        - keyword_matches: "broad" -> first 1 is broad, rest are exact
        - keyword_matches: "" or not provided -> all are exact
        """
        keywords_str = self._get_required(row, "keywords")
        matches_str = row.get("keyword_matches", "").strip()
        
        # Split keywords by semicolon
        keyword_names = [k.strip() for k in keywords_str.split(";") if k.strip()]
        
        if not keyword_names:
            raise CSVParseError("No keywords specified")
        
        # Split match types by semicolon (only the ones specified as broad)
        if matches_str:
            match_types_input = [m.strip().lower() for m in matches_str.split(";") if m.strip()]
        else:
            match_types_input = []
        
        # Build full match types list: specified matches + default to exact for rest
        match_types = []
        for i in range(len(keyword_names)):
            if i < len(match_types_input):
                # Use specified match type
                match_type_str = match_types_input[i]
                if match_type_str not in ("broad", "exact"):
                    raise CSVParseError(
                        f"Invalid match type '{match_type_str}' for keyword '{keyword_names[i]}'. "
                        f"Must be 'broad' or 'exact'"
                    )
                match_types.append(match_type_str)
            else:
                # Default to exact for remaining keywords
                match_types.append("exact")
        
        # Create keyword objects
        keywords = []
        for name, match in zip(keyword_names, match_types):
            match_type = MatchType(match)
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


"""
CSV input parser for campaign definitions.

Parses CSV files containing campaign definitions and converts them to
CampaignDefinition objects.

CSV Format:
-----------

Required Columns:
- group: Campaign group name (e.g., "Milfs", "Cougars")
- keywords: Semicolon-separated list (e.g., "milf;milfs;milf porn") - optional for remarketing
- csv_file: Path to ad CSV file
- variants: Comma-separated device types (e.g., "desktop,ios,android,all mobile")
- enabled: TRUE/FALSE to enable/disable this row

Optional Columns:
- campaign_type: "Standard" or "Remarketing" (default: "Standard")
  - Standard: Uses keyword targeting templates
  - Remarketing: Uses remarketing/retargeting templates
- bid_type: "CPA" or "CPM" (default: "CPA")
  - CPA: Cost Per Action bidding (uses Target CPA, Per Source Budget, Max Bid)
  - CPM: Cost Per Mille bidding (uses suggested CPM bids from sources)
- keyword_matches: Only specify "broad" for keywords that need it
  Examples:
    - "broad" = first keyword is broad, rest are exact
    - "broad;broad" = first 2 keywords are broad, rest are exact
    - "" or omit = all keywords are exact
- gender: "male", "female", or "all" (default: "male")
- geo: Semicolon-separated geos for ONE campaign (e.g., "US;CA;UK")
- multi_geo: Semicolon-separated geos to create SEPARATE campaigns (e.g., "CA;AUS")
  Note: Use either 'geo' OR 'multi_geo', not both
- target_cpa: Target CPA (default: 50.0) - only used for CPA bid_type
- per_source_budget: Per-source test budget (default: 200.0) - only used for CPA bid_type
- max_bid: Maximum bid (default: 10.0)
- frequency_cap: Frequency cap (default: 2)
- max_daily_budget: Maximum daily budget (default: 250.0)

V3 From-Scratch Columns (for creating campaigns without templates):
- labels: Comma-separated labels (e.g., "Native,Test") (default: empty)
- device: "all", "desktop", or "mobile" (default: "desktop")
- ad_format_type: "display", "instream", or "pop" (default: "display")
- format_type: "banner" or "native" (default: "native")
- ad_type: "static_banner", "video_banner", or "rollover" (default: "rollover")
- ad_dimensions: Ad size (e.g., "640x360", "300x250") (default: "640x360")
- content_category: "straight", "gay", or "trans" (default: "straight")

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

4. Remarketing campaign with CPM bidding:
   group,keywords,ad_format,campaign_type,bid_type,variants,csv_file,enabled
   Milfs,,NATIVE,Remarketing,CPM,"desktop,all mobile",ads.csv,TRUE
   
   Result: Remarketing campaigns using CPM bidding (no keywords needed)

5. Remarketing campaign with keywords (hybrid):
   group,keywords,ad_format,campaign_type,bid_type,variants,csv_file,enabled
   Milfs,"milf;milfs",NATIVE,Remarketing,CPA,"desktop,all mobile",ads.csv,TRUE
   
   Result: Remarketing campaigns with additional keyword targeting
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
    CampaignBatch,
    OSVersion
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
    
    # Required columns (keywords is now optional for campaigns without keyword targeting)
    REQUIRED_COLUMNS = {
        "group",
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
        "gender": "male",  # Options: "male", "female", "all"
        "ios_version": "",  # iOS version constraint (e.g., ">18.4" or "18.4")
        "android_version": "",  # Android version constraint (e.g., ">11.0" or "11.0")
        "ad_format": "NATIVE",  # Options: "NATIVE", "INSTREAM" (default: NATIVE for V1 compatibility)
        "campaign_type": "Standard",  # Options: "Standard", "Remarketing"
        "bid_type": "CPA",  # Options: "CPA", "CPM"
        "geo_name": "",  # Custom geo short name for naming (e.g., "OTH2" for multiple geos)
        "cpm_adjust": "",  # CPM adjustment percentage (e.g., "10" = +10%, "-5" = -5%)
        "t": "",  # Test number (e.g., "12" becomes "_T-12" in campaign name)
        # V3 From-Scratch columns
        "labels": "",  # Comma-separated labels (e.g., "Native,Test")
        "device": "desktop",  # Options: "all", "desktop", "mobile"
        "ad_format_type": "display",  # Options: "display", "instream", "pop"
        "format_type": "native",  # Options: "banner", "native"
        "ad_type": "rollover",  # Options: "static_banner", "video_banner", "rollover"
        "ad_dimensions": "640x360",  # Options: "300x250", "950x250", "468x60", "305x99", "300x100", "970x90", "320x480", "640x360"
        "content_category": "straight",  # Options: "straight", "gay", "trans"
        "language": "EN",  # Language code (e.g., "EN", "ES", "DE")
    }
    
    # Valid values for campaign type and bidding
    VALID_CAMPAIGN_TYPES = {"standard", "remarketing"}
    VALID_BID_TYPES = {"cpa", "cpm"}
    
    # Valid values for V3 columns
    VALID_DEVICES = {"all", "desktop", "mobile"}
    VALID_AD_FORMAT_TYPES = {"display", "instream", "pop"}
    # Format types: for Display (banner/native), for PreRoll (video file, n/a)
    VALID_FORMAT_TYPES = {"banner", "native", "video file", "n/a", ""}
    # Ad types: for Display (static_banner/video_banner/rollover), for PreRoll (video_file)
    VALID_AD_TYPES = {"static_banner", "video_banner", "rollover", "video_file", "in-stream video", "preroll", "pre-roll", "video file", ""}
    # Ad dimensions: Display sizes + PreRoll sizes
    VALID_AD_DIMENSIONS = {
        # Display/Native dimensions
        "300x250", "950x250", "468x60", "305x99", "300x100", "970x90", "320x480", "640x360",
        # PreRoll dimensions
        "pre-roll (16:9)", "preroll (16:9)", "16:9"
    }
    VALID_CONTENT_CATEGORIES = {"straight", "gay", "trans"}
    
    # Mappings from user-friendly names to internal values
    AD_FORMAT_TYPE_MAP = {
        "in-stream video": "instream",
        "in-stream": "instream",
        "preroll": "instream",
        "pre-roll": "instream",
    }
    FORMAT_TYPE_MAP = {
        "video file": "video file",  # Keep as-is for PreRoll
        "n/a": "",
    }
    AD_TYPE_MAP = {
        "in-stream video": "video_file",  # PreRoll uses video_file
        "video file": "video_file",
        "preroll": "video_file",
        "pre-roll": "video_file",
    }
    AD_DIMENSIONS_MAP = {
        "pre-roll (16:9)": "640x360",  # PreRoll uses 640x360
        "preroll (16:9)": "640x360",
        "16:9": "640x360",
        "640x360": "640x360",
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
        
        # Parse V3 columns with validation
        labels = self._parse_labels(row.get("labels", ""))
        device = self._parse_validated_field(
            row.get("device", "desktop").lower(),
            self.VALID_DEVICES,
            "device",
            "desktop"
        )
        ad_format_type = self._parse_validated_field(
            row.get("ad_format_type", "display").lower(),
            self.VALID_AD_FORMAT_TYPES,
            "ad_format_type",
            "display",
            self.AD_FORMAT_TYPE_MAP
        )
        format_type = self._parse_validated_field(
            row.get("format_type", "native").lower(),
            self.VALID_FORMAT_TYPES,
            "format_type",
            "native",
            self.FORMAT_TYPE_MAP
        )
        ad_type = self._parse_validated_field(
            row.get("ad_type", "rollover").lower(),
            self.VALID_AD_TYPES,
            "ad_type",
            "rollover",
            self.AD_TYPE_MAP
        )
        ad_dimensions = self._parse_validated_field(
            row.get("ad_dimensions", "640x360").lower(),
            self.VALID_AD_DIMENSIONS,
            "ad_dimensions",
            "640x360",
            self.AD_DIMENSIONS_MAP
        )
        content_category = self._parse_validated_field(
            row.get("content_category", "straight").lower(),
            self.VALID_CONTENT_CATEGORIES,
            "content_category",
            "straight"
        )
        
        # Parse campaign_type and bid_type with validation
        campaign_type = self._parse_validated_field(
            row.get("campaign_type", "Standard"),
            self.VALID_CAMPAIGN_TYPES,
            "campaign_type",
            "standard"
        ).title()  # Convert to title case (Standard, Remarketing)
        
        bid_type = self._parse_validated_field(
            row.get("bid_type", "CPA"),
            self.VALID_BID_TYPES,
            "bid_type",
            "cpa"
        ).upper()  # Convert to uppercase (CPA, CPM)
        
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
            gender=row.get("gender", DEFAULT_SETTINGS["gender"]).lower(),
            ios_version=OSVersion.parse(row.get("ios_version", "")),
            android_version=OSVersion.parse(row.get("android_version", "")),
            ad_format=row.get("ad_format", DEFAULT_SETTINGS["ad_format"]).upper(),  # Parse ad_format from CSV
            campaign_type=campaign_type,
            bid_type=bid_type,
            geo_name=row.get("geo_name", "").strip(),  # Custom geo short name
            cpm_adjust=self._parse_int_or_none(row.get("cpm_adjust", "")),  # CPM adjustment percentage
            # V3 From-Scratch settings
            labels=labels,
            device=device,
            ad_format_type=ad_format_type,
            format_type=format_type,
            ad_type=ad_type,
            ad_dimensions=ad_dimensions,
            content_category=content_category,
            language=row.get("language", "EN").strip().upper()
        )
        
        # Parse test number (can be numeric or alphanumeric like "12", "12A", "V2", etc.)
        # Support both "t" and "test_number" column names
        test_number = row.get("test_number", "").strip() or row.get("t", "").strip()
        if not test_number:
            test_number = None
        
        campaigns = []
        
        # Check if "all mobile" variant is used
        mobile_combined = "all mobile" in variants
        is_remarketing = campaign_type.lower() == "remarketing"
        
        # Expand "all mobile" to actual variants for processing
        expanded_variants = []
        for variant in variants:
            if variant == "all mobile":
                if is_remarketing:
                    # For remarketing, keep "all_mobile" as a single variant
                    # We have dedicated all_mobile templates for remarketing
                    if "all_mobile" not in expanded_variants:
                        expanded_variants.append("all_mobile")
                else:
                    # For standard campaigns, expand to ios+android (original behavior)
                    # This creates combined iOS+Android targeting in a single campaign
                    if "ios" not in expanded_variants:
                        expanded_variants.append("ios")
                    if "android" not in expanded_variants:
                        expanded_variants.append("android")
            else:
                if variant not in expanded_variants:
                    expanded_variants.append(variant)
        
        if multi_geo_str:
            # Mode 1: Create separate campaigns for each geo
            # Support both semicolon and comma separators
            if "," in multi_geo_str:
                geo_codes = [g.strip().upper() for g in multi_geo_str.split(",") if g.strip()]
            else:
                geo_codes = [g.strip().upper() for g in multi_geo_str.split(";") if g.strip()]
            
            if not geo_codes:
                raise CSVParseError("multi_geo specified but no geo codes provided")
            
            for geo_code in geo_codes:
                campaign = CampaignDefinition(
                    group=group,
                    keywords=keywords,
                    geo=[geo_code],  # Single geo per campaign
                    csv_file=csv_file,
                    variants=expanded_variants,
                    settings=settings,
                    enabled=enabled,
                    mobile_combined=mobile_combined,
                    test_number=test_number
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
                variants=expanded_variants,
                settings=settings,
                enabled=enabled,
                mobile_combined=mobile_combined,
                test_number=test_number
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
        - keywords: "" or not provided -> no keyword targeting (empty list)
        """
        keywords_str = row.get("keywords", "").strip()
        matches_str = row.get("keyword_matches", "").strip()

        # Split keywords by semicolon
        keyword_names = [k.strip() for k in keywords_str.split(";") if k.strip()]

        # Keywords are now optional - return empty list if none specified
        if not keyword_names:
            return []
        
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
        """Parse geo country codes. Supports both comma and semicolon separators."""
        geo_str = row.get("geo", "US").strip()
        if not geo_str:
            geo_str = "US"
        
        # Split by comma or semicolon and uppercase
        # Check which separator is used
        if "," in geo_str:
            geo_codes = [g.strip().upper() for g in geo_str.split(",") if g.strip()]
        else:
            geo_codes = [g.strip().upper() for g in geo_str.split(";") if g.strip()]
        
        if not geo_codes:
            geo_codes = ["US"]
        
        return geo_codes
    
    def _parse_variants(self, row: Dict[str, str]) -> List[str]:
        """
        Parse device variants.
        
        Supports:
        - "desktop", "ios", "android"
        - "all mobile" or "all_mobile" - creates a single campaign targeting both iOS and Android
        
        The "all mobile" variant is used to create campaigns with both iOS and Android
        targeting in a single campaign (naming will use MOB_ALL instead of iOS/AND).
        For remarketing campaigns, this uses the "all_mobile" template directly.
        """
        variants_str = self._get_required(row, "variants")
        
        # Split by comma and lowercase
        variants = [v.strip().lower() for v in variants_str.split(",") if v.strip()]
        
        if not variants:
            raise CSVParseError("No variants specified")
        
        # Validate variant names and normalize "all_mobile"/"all mobile"
        valid_variants = {"desktop", "ios", "android", "all mobile", "all_mobile"}
        expanded_variants = []
        
        for variant in variants:
            if variant not in valid_variants:
                raise CSVParseError(
                    f"Invalid variant '{variant}'. "
                    f"Must be one of: desktop, ios, android, all mobile"
                )
            
            # Normalize "all_mobile" to "all mobile" for consistency
            if variant == "all_mobile":
                variant = "all mobile"
            
            # "all mobile" is handled differently - mark for special processing
            # It will be expanded later when we know this campaign needs mobile_combined
            expanded_variants.append(variant)
        
        return expanded_variants
    
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
    
    def _parse_int_or_none(self, value: Optional[str]) -> Optional[int]:
        """Parse integer value, return None if empty."""
        if not value or not value.strip():
            return None
        
        try:
            return int(value.strip())
        except ValueError:
            raise CSVParseError(f"Invalid integer: {value}")
    
    def _parse_labels(self, value: str) -> List[str]:
        """Parse comma-separated labels."""
        if not value or not value.strip():
            return []
        
        # Split by comma and strip whitespace
        labels = [l.strip() for l in value.split(",") if l.strip()]
        return labels
    
    def _parse_validated_field(
        self, 
        value: str, 
        valid_values: set, 
        field_name: str,
        default: str,
        value_map: dict = None
    ) -> str:
        """Parse a field and validate against allowed values, with optional mapping."""
        if not value or not value.strip():
            return default
        
        value = value.strip().lower()
        
        # Apply mapping if provided
        if value_map and value in value_map:
            value = value_map[value]
        
        if value not in valid_values:
            raise CSVParseError(
                f"Invalid {field_name} '{value}'. "
                f"Must be one of: {', '.join(sorted(valid_values))}"
            )
        return value


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


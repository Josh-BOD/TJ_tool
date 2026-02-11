"""
Campaign template configuration and constants.

Contains template campaign IDs, default settings, and naming conventions.
Supports both NATIVE and INSTREAM ad formats.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# Template campaign IDs by ad format (CONSTANTS - never change)
# Used for STANDARD campaigns (keyword targeting)
TEMPLATE_CAMPAIGNS = {
    "NATIVE": {
        "desktop": {
            "id": "1013076141",
            "name": "TEMPLATE_EN_NATIVE_CPA_ALL_KEY-ENTER-Keywords_DESK_M_JB",
            "device": "desktop"
        },
        "ios": {
            "id": "1013076221", 
            "name": "TEMPLATE_EN_NATIVE_CPA_ALL_KEY-ENTERKEYWORDS_iOS_M_JB",
            "device": "mobile",
            "os": "iOS"
        },
        # Android clones from iOS campaign, not from template
        "android": {
            "clone_from": "ios",
            "device": "mobile",
            "os": "Android"
        }
    },
    "INSTREAM": {
        "desktop": {
            "id": "1013076111",
            "name": "TEMPLATE_EN_INSTREAM_CPA_ALL_KEY-ENTER-Keywords_DESK_M_JB",
            "device": "desktop"
        },
        "ios": {
            "id": "1013076101",
            "name": "TEMPLATE_EN_INSTREAM_CPA_ALL_KEY-ENTERKEYWORDS_iOS_M_JB",
            "device": "mobile",
            "os": "iOS"
        },
        # Android clones from iOS campaign, not from template
        "android": {
            "clone_from": "ios",
            "device": "mobile",
            "os": "Android"
        }
    }
}

# Remarketing template campaign IDs by ad format (CONSTANTS - never change)
# Used for REMARKETING campaigns (audience retargeting)
REMARKETING_TEMPLATES = {
    "NATIVE": {
        "desktop": {
            "id": "1013186231",
            "name": "TEMPLATE_EN_NATIVE_RMK_DESK",
            "device": "desktop"
        },
        "all_mobile": {
            "id": "1013186221",
            "name": "TEMPLATE_EN_NATIVE_RMK_MOB_ALL",
            "device": "mobile",
            "os": ["iOS", "Android"]  # Both OS combined
        },
        # For separate iOS/Android, clone from all_mobile and modify OS targeting
        "ios": {
            "clone_from": "all_mobile",
            "device": "mobile",
            "os": "iOS"
        },
        "android": {
            "clone_from": "all_mobile",
            "device": "mobile",
            "os": "Android"
        }
    },
    "INSTREAM": {  # Preroll
        "desktop": {
            "id": "1013186211",
            "name": "TEMPLATE_EN_PREROLL_RMK_DESK",
            "device": "desktop"
        },
        "all_mobile": {
            "id": "1013186201",
            "name": "TEMPLATE_EN_PREROLL_RMK_MOB_ALL",
            "device": "mobile",
            "os": ["iOS", "Android"]  # Both OS combined
        },
        # For separate iOS/Android, clone from all_mobile and modify OS targeting
        "ios": {
            "clone_from": "all_mobile",
            "device": "mobile",
            "os": "iOS"
        },
        "android": {
            "clone_from": "all_mobile",
            "device": "mobile",
            "os": "Android"
        }
    }
}

# Legacy template campaigns (for backward compatibility with V1)
# V1 scripts will use this directly
TEMPLATE_CAMPAIGNS_V1 = TEMPLATE_CAMPAIGNS["NATIVE"]


# Default values (can be overridden per campaign)
DEFAULT_SETTINGS = {
    "geo": ["US"],
    "language": "EN",
    "ad_format": "NATIVE",  # V1 default
    "bid_type": "CPA",
    "source": "ALL",
    "target_cpa": 50.0,
    "per_source_test_budget": 200.0,
    "max_bid": 10.0,
    "frequency_cap": 2,
    "max_daily_budget": 250.0,
    "gender": "male",
    "conversion_tracker": "Redtrack - Purchase",
    "include_all_sources": True,
    "ad_rotation": "autopilot_ctr",
}


# Campaign naming convention pattern
# Example (standard): US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB
# Example (remarketing): US_EN_NATIVE_CPM_ALL_RMK-Milfs_DESK_M_JB
# Example (all mobile): US_EN_NATIVE_CPA_ALL_KEY-Milfs_MOB_ALL_M_JB
# Example (multi-geo): US-CA_EN_NATIVE_CPA_ALL_KEY-Milfs_MOB_ALL_M_JB
# Example (custom geo name): OTH2_EN_NATIVE_CPM_ALL_RMK-Milfs_DESK_M_JB
# Example (with test number): US_EN_NATIVE_CPA_ALL_KEY-Milfs_MOB_ALL_M_JB_T-12
def generate_campaign_name(
    geo: str,
    language: str,
    ad_format: str,
    bid_type: str,
    source: str,
    keyword: str,
    device: str,
    gender: str,
    user_initials: str = "JB",
    mobile_combined: bool = False,
    test_number: str = None,
    campaign_type: str = "Standard",
    geo_name: str = None,
    content_category: str = "straight"
) -> str:
    """
    Generate campaign name following TrafficJunky naming convention.

    Naming: {GEO}_{LANG}_{FORMAT}_{BID}_{SOURCE}_{TARGETING}_{DEVICE}_{GENDER}_{INITIALS}

    Targeting part depends on campaign_type and content_category:
      - Standard straight:      KEY-{keyword}     (e.g., KEY-Broad, KEY-Milfs)
      - Standard gay:           Gay
      - Standard trans:         Trans
      - Remarketing straight:   Remarketing
      - Remarketing gay:        Gay-Remarketing
      - Remarketing trans:      Trans-Remarketing
    """
    # Use custom geo_name if provided, otherwise build from geo codes
    if geo_name and geo_name.strip():
        geo_str = geo_name.strip()
    elif isinstance(geo, list):
        geo_str = "-".join(geo)
    else:
        geo_str = geo

    # Capitalize keyword for name (use "Broad" if empty/no keyword targeting)
    if keyword and keyword.strip() and keyword.lower() != "unknown":
        keyword_title = keyword.title().replace(" ", "")
    else:
        keyword_title = "Broad"

    # Convert gender to abbreviation (ALL = MF for Male+Female)
    gender_map = {"male": "M", "female": "F", "all": "MF"}
    gender_abbr = gender_map.get(gender.lower(), "M")

    # Convert device to abbreviation
    if mobile_combined and device.lower() in ("ios", "android", "all_mobile"):
        device_abbr = "MOB_ALL"
    else:
        device_map = {"desktop": "DESK", "ios": "iOS", "android": "AND", "all_mobile": "MOB_ALL"}
        device_abbr = device_map.get(device.lower(), device.upper())

    # Convert ad_format for campaign name (INSTREAM -> PREROLL)
    ad_format_name = "PREROLL" if ad_format.upper() == "INSTREAM" else ad_format.upper()

    # Build targeting part based on campaign_type + content_category
    cat = (content_category or "straight").lower()
    is_remarketing = campaign_type.lower() == "remarketing"

    if cat == "gay":
        targeting_part = "Gay-Remarketing" if is_remarketing else "Gay"
    elif cat == "trans":
        targeting_part = "Trans-Remarketing" if is_remarketing else "Trans"
    else:
        # straight
        if is_remarketing:
            targeting_part = "Remarketing"
        else:
            targeting_part = f"KEY-{keyword_title}"

    # Build base name
    base_name = (
        f"{geo_str}_{language}_{ad_format_name}_{bid_type}_{source}_"
        f"{targeting_part}_{device_abbr}_{gender_abbr}_{user_initials}"
    )

    # Add test number suffix if provided
    if test_number:
        return f"{base_name}_T-{test_number}"
    else:
        return base_name


# Valid values for validation
VALID_DEVICES = ["desktop", "ios", "android", "all_mobile"]
VALID_GENDERS = ["male", "female", "all"]
VALID_MATCH_TYPES = ["broad", "exact"]
VALID_AD_FORMATS = ["NATIVE", "INSTREAM"]
VALID_CAMPAIGN_TYPES = ["Standard", "Remarketing"]
VALID_BID_TYPES = ["CPA", "CPM"]

# ISO 2-letter country codes (common ones)
VALID_GEO_CODES = [
    "US", "CA", "UK", "AU", "NZ", "DE", "FR", "IT", "ES", "NL",
    "BE", "SE", "NO", "DK", "FI", "IE", "AT", "CH", "PT", "PL",
    "CZ", "HU", "RO", "GR", "BG", "HR", "SI", "SK", "EE", "LV",
    "LT", "CY", "MT", "LU", "IS", "JP", "KR", "SG", "HK", "TW",
    "MY", "TH", "ID", "PH", "VN", "IN", "BR", "MX", "AR", "CL",
    "CO", "PE", "VE", "EC", "UY", "PY", "BO", "CR", "PA", "GT",
    "HN", "SV", "NI", "CU", "DO", "PR", "JM", "TT", "BB", "BS",
    "BZ", "GY", "SR", "GF", "FK", "GL", "PM", "BM", "KY", "TC",
    "VG", "VI", "AI", "MS", "GP", "MQ", "BL", "MF", "SX", "CW"
]


def get_default_settings() -> Dict[str, Any]:
    """Get a copy of default settings."""
    return DEFAULT_SETTINGS.copy()


def get_templates_for_format(ad_format: str) -> Dict[str, Any]:
    """
    Get standard template campaigns for a specific ad format.
    
    Args:
        ad_format: "NATIVE" or "INSTREAM"
        
    Returns:
        Dictionary of template campaigns for the format
        
    Raises:
        ValueError: If ad_format is invalid
    """
    ad_format = ad_format.upper()
    if ad_format not in VALID_AD_FORMATS:
        raise ValueError(f"Invalid ad format: {ad_format}. Must be one of {VALID_AD_FORMATS}")
    return TEMPLATE_CAMPAIGNS[ad_format]


def get_remarketing_templates(ad_format: str) -> Dict[str, Any]:
    """
    Get remarketing template campaigns for a specific ad format.
    
    Args:
        ad_format: "NATIVE" or "INSTREAM"
        
    Returns:
        Dictionary of remarketing template campaigns for the format
        
    Raises:
        ValueError: If ad_format is invalid
    """
    ad_format = ad_format.upper()
    if ad_format not in VALID_AD_FORMATS:
        raise ValueError(f"Invalid ad format: {ad_format}. Must be one of {VALID_AD_FORMATS}")
    return REMARKETING_TEMPLATES[ad_format]


def load_templates(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Load templates from config/templates.json.

    Args:
        path: Path to templates.json (default: config/templates.json relative to project root)

    Returns:
        Dictionary of templates, or None if file doesn't exist
    """
    if path is None:
        # Default path relative to this file's parent (src/) -> project root
        path = Path(__file__).parent.parent / "config" / "templates.json"
    else:
        path = Path(path)

    if not path.exists():
        return None

    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Could not load templates from {path}: {e}")
        return None


# Cache for loaded templates (loaded once per process)
_loaded_templates: Optional[Dict[str, Any]] = None
_templates_loaded: bool = False


def _get_loaded_templates() -> Optional[Dict[str, Any]]:
    """Get cached loaded templates, loading from file on first call."""
    global _loaded_templates, _templates_loaded
    if not _templates_loaded:
        _loaded_templates = load_templates()
        _templates_loaded = True
    return _loaded_templates


def get_templates(ad_format: str, campaign_type: str = "Standard", content_category: str = "straight") -> Dict[str, Any]:
    """
    Get template campaigns for a specific ad format, campaign type, and content category.

    Looks up orientation-specific templates from config/templates.json first.
    Falls back to hardcoded TEMPLATE_CAMPAIGNS/REMARKETING_TEMPLATES if JSON is missing
    or doesn't have the requested combination.

    Args:
        ad_format: "NATIVE" or "INSTREAM"
        campaign_type: "Standard" or "Remarketing"
        content_category: "straight", "gay", or "trans" (default: "straight")

    Returns:
        Dictionary of template campaigns for the format, type, and orientation

    Raises:
        ValueError: If ad_format or campaign_type is invalid
    """
    ad_format = ad_format.upper()
    campaign_type_title = campaign_type.title()
    content_category = content_category.lower()

    if ad_format not in VALID_AD_FORMATS:
        raise ValueError(f"Invalid ad format: {ad_format}. Must be one of {VALID_AD_FORMATS}")
    if campaign_type_title not in VALID_CAMPAIGN_TYPES:
        raise ValueError(f"Invalid campaign type: {campaign_type}. Must be one of {VALID_CAMPAIGN_TYPES}")

    # Map ad_format to template label (INSTREAM -> PREROLL in templates.json)
    label_map = {"NATIVE": "NATIVE", "INSTREAM": "PREROLL"}
    template_label = label_map.get(ad_format, ad_format)

    # Try loading from templates.json
    loaded = _get_loaded_templates()
    if loaded:
        label_data = loaded.get(template_label)
        if label_data:
            type_data = label_data.get(campaign_type_title)
            if type_data:
                category_data = type_data.get(content_category)
                if category_data:
                    logger.debug(
                        f"Using templates.json: {template_label}/{campaign_type_title}/{content_category}"
                    )
                    return category_data

    # Fallback to hardcoded templates (orientation-agnostic, straight-only)
    if content_category != "straight":
        logger.warning(
            f"No templates.json entry for {template_label}/{campaign_type_title}/{content_category}. "
            f"Falling back to hardcoded templates (straight only). "
            f"Run create_templates.py to generate orientation-specific templates."
        )

    if campaign_type_title == "Remarketing":
        return REMARKETING_TEMPLATES[ad_format]
    else:
        return TEMPLATE_CAMPAIGNS[ad_format]


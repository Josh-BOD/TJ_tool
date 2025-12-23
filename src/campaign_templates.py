"""
Campaign template configuration and constants.

Contains template campaign IDs, default settings, and naming conventions.
Supports both NATIVE and INSTREAM ad formats.
"""

from typing import Dict, Any


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
    campaign_type: str = "Standard"
) -> str:
    """
    Generate campaign name following TrafficJunky naming convention.
    
    Args:
        geo: Country code or codes (e.g., "US", "CA", or list like ["US", "CA"])
        language: Language code (e.g., "EN")
        ad_format: Ad format (e.g., "NATIVE")
        bid_type: Bidding type (e.g., "CPA", "CPM")
        source: Source type (e.g., "ALL", "PH")
        keyword: Primary keyword (e.g., "Milfs") - used as group name for remarketing
        device: Device type (e.g., "DESK", "iOS", "AND")
        gender: Target gender ("M", "F", "ALL")
        user_initials: User initials (default: "JB")
        mobile_combined: If True, use "MOB_ALL" for mobile campaigns (default: False)
        test_number: Test number/label (e.g., "12", "12A", "V2") - adds "_T-{number}" suffix
        campaign_type: Campaign type - "Standard" (keyword) or "Remarketing" (audience)
    
    Returns:
        Campaign name string
    """
    # Handle geo as list or string
    if isinstance(geo, list):
        geo_str = "-".join(geo)  # Join multiple geos with dash
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
    # If mobile_combined is True and device is mobile, use MOB_ALL
    if mobile_combined and device.lower() in ("ios", "android", "all_mobile"):
        device_abbr = "MOB_ALL"
    else:
        device_map = {"desktop": "DESK", "ios": "iOS", "android": "AND", "all_mobile": "MOB_ALL"}
        device_abbr = device_map.get(device.lower(), device.upper())
    
    # Convert ad_format for campaign name (INSTREAM -> PREROLL)
    ad_format_name = "PREROLL" if ad_format.upper() == "INSTREAM" else ad_format.upper()
    
    # Determine targeting type prefix (KEY for keywords, RMK for remarketing)
    targeting_prefix = "RMK" if campaign_type.lower() == "remarketing" else "KEY"
    
    # Build base name
    base_name = (
        f"{geo_str}_{language}_{ad_format_name}_{bid_type}_{source}_"
        f"{targeting_prefix}-{keyword_title}_{device_abbr}_{gender_abbr}_{user_initials}"
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


def get_templates(ad_format: str, campaign_type: str = "Standard") -> Dict[str, Any]:
    """
    Get template campaigns for a specific ad format and campaign type.
    
    Args:
        ad_format: "NATIVE" or "INSTREAM"
        campaign_type: "Standard" or "Remarketing"
        
    Returns:
        Dictionary of template campaigns for the format and type
        
    Raises:
        ValueError: If ad_format or campaign_type is invalid
    """
    ad_format = ad_format.upper()
    campaign_type_title = campaign_type.title()
    
    if ad_format not in VALID_AD_FORMATS:
        raise ValueError(f"Invalid ad format: {ad_format}. Must be one of {VALID_AD_FORMATS}")
    if campaign_type_title not in VALID_CAMPAIGN_TYPES:
        raise ValueError(f"Invalid campaign type: {campaign_type}. Must be one of {VALID_CAMPAIGN_TYPES}")
    
    if campaign_type_title == "Remarketing":
        return REMARKETING_TEMPLATES[ad_format]
    else:
        return TEMPLATE_CAMPAIGNS[ad_format]


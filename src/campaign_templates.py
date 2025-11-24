"""
Campaign template configuration and constants.

Contains template campaign IDs, default settings, and naming conventions.
Supports both NATIVE and INSTREAM ad formats.
"""

from typing import Dict, Any


# Template campaign IDs by ad format (CONSTANTS - never change)
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
# Example: US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB
def generate_campaign_name(
    geo: str,
    language: str,
    ad_format: str,
    bid_type: str,
    source: str,
    keyword: str,
    device: str,
    gender: str,
    user_initials: str = "JB"
) -> str:
    """
    Generate campaign name following TrafficJunky naming convention.
    
    Args:
        geo: Country code (e.g., "US", "CA")
        language: Language code (e.g., "EN")
        ad_format: Ad format (e.g., "NATIVE")
        bid_type: Bidding type (e.g., "CPA", "CPM")
        source: Source type (e.g., "ALL", "PH")
        keyword: Primary keyword (e.g., "Milfs")
        device: Device type (e.g., "DESK", "iOS", "AND")
        gender: Target gender ("M", "F", "ALL")
        user_initials: User initials (default: "JB")
    
    Returns:
        Campaign name string
    """
    # Capitalize keyword for name
    keyword_title = keyword.title().replace(" ", "")
    
    # Convert gender to abbreviation
    gender_map = {"male": "M", "female": "F", "all": "ALL"}
    gender_abbr = gender_map.get(gender.lower(), "M")
    
    # Convert device to abbreviation
    device_map = {"desktop": "DESK", "ios": "iOS", "android": "AND"}
    device_abbr = device_map.get(device.lower(), device.upper())
    
    # Convert ad_format for campaign name (INSTREAM -> PREROLL)
    ad_format_name = "PREROLL" if ad_format.upper() == "INSTREAM" else ad_format.upper()
    
    return (
        f"{geo}_{language}_{ad_format_name}_{bid_type}_{source}_"
        f"KEY-{keyword_title}_{device_abbr}_{gender_abbr}_{user_initials}"
    )


# Valid values for validation
VALID_DEVICES = ["desktop", "ios", "android"]
VALID_GENDERS = ["male", "female", "all"]
VALID_MATCH_TYPES = ["broad", "exact"]
VALID_AD_FORMATS = ["NATIVE", "INSTREAM"]

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
    Get template campaigns for a specific ad format.
    
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


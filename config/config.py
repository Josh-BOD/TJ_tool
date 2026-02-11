"""Configuration management for TrafficJunky Automation Tool."""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""
    
    # ====================================
    # TrafficJunky Credentials
    # ====================================
    TJ_USERNAME: str = os.getenv('TJ_USERNAME', '')
    TJ_PASSWORD: str = os.getenv('TJ_PASSWORD', '')
    TJ_API_KEY: str = os.getenv('TJ_API_KEY', '')
    
    # ====================================
    # Campaign Configuration
    # ====================================
    # Campaigns are loaded from campaign_mapping.csv
    # No need to configure campaign IDs in .env
    
    # ====================================
    # OpenRouter (Translation API)
    # ====================================
    OPENROUTER_API_KEY: str = os.getenv('OPENROUTER_API_KEY', '')
    OPENROUTER_MODEL: str = os.getenv('OPENROUTER_MODEL', 'deepseek/deepseek-chat')

    # ====================================
    # File Paths
    # ====================================
    BASE_DIR: Path = Path(__file__).parent.parent
    CSV_INPUT_DIR: Path = BASE_DIR / os.getenv('CSV_INPUT_DIR', './data/input')
    CSV_OUTPUT_DIR: Path = BASE_DIR / os.getenv('CSV_OUTPUT_DIR', './data/output')
    REPORT_OUTPUT_DIR: Path = BASE_DIR / os.getenv('REPORT_OUTPUT_DIR', './data/reports')
    WIP_DIR: Path = BASE_DIR / os.getenv('WIP_DIR', './data/wip')  # Work In Progress - temporary modified CSVs
    LOG_DIR: Path = BASE_DIR / os.getenv('LOG_DIR', './logs')
    CREATIVE_DIR: Path = BASE_DIR / os.getenv('CREATIVE_DIR', './data/creatives')
    SCREENSHOT_DIR: Path = BASE_DIR / 'screenshots'
    
    # ====================================
    # Browser Settings
    # ====================================
    HEADLESS_MODE: bool = os.getenv('HEADLESS_MODE', 'False').lower() == 'true'
    BROWSER_TYPE: str = os.getenv('BROWSER_TYPE', 'chromium')
    TIMEOUT: int = int(os.getenv('TIMEOUT', '30000'))
    SLOW_MO: int = int(os.getenv('SLOW_MO', '500'))
    
    # ====================================
    # Automation Behavior
    # ====================================
    DRY_RUN: bool = os.getenv('DRY_RUN', 'True').lower() == 'true'
    TAKE_SCREENSHOTS: bool = os.getenv('TAKE_SCREENSHOTS', 'True').lower() == 'true'
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY: int = int(os.getenv('RETRY_DELAY', '5'))
    
    # ====================================
    # Logging
    # ====================================
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_TO_FILE: bool = os.getenv('LOG_TO_FILE', 'True').lower() == 'true'
    LOG_TO_CONSOLE: bool = os.getenv('LOG_TO_CONSOLE', 'True').lower() == 'true'
    
    # ====================================
    # URLs
    # ====================================
    TJ_BASE_URL: str = 'https://advertiser.trafficjunky.com'
    TJ_LOGIN_URL: str = 'https://www.trafficjunky.com/sign-in'
    TJ_CAMPAIGNS_URL: str = f'{TJ_BASE_URL}/campaigns'
    TJ_API_BASE_URL: str = 'https://api.trafficjunky.com/api'
    
    # ====================================
    # Reporting Settings
    # ====================================
    DEFAULT_TIME_PERIOD: str = os.getenv('DEFAULT_TIME_PERIOD', 'yesterday')  # yesterday, last7days, last30days
    TIMEZONE: str = 'America/New_York'  # EST - TJ reports in EST
    
    @classmethod
    def validate(cls) -> List[str]:
        """
        Validate configuration and return list of errors.
        
        Returns:
            List of validation error messages. Empty list if valid.
        """
        errors = []
        
        if not cls.TJ_USERNAME:
            errors.append("TJ_USERNAME is not set in .env file")
        
        if not cls.TJ_PASSWORD:
            errors.append("TJ_PASSWORD is not set in .env file")
        
        # Ensure directories exist
        for dir_path in [cls.CSV_INPUT_DIR, cls.CSV_OUTPUT_DIR, cls.REPORT_OUTPUT_DIR,
                        cls.WIP_DIR, cls.LOG_DIR, cls.CREATIVE_DIR, cls.SCREENSHOT_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        return errors
    
    @classmethod
    def get_campaign_url(cls, campaign_id: str) -> str:
        """Get the ad settings URL for a specific campaign."""
        return f"{cls.TJ_BASE_URL}/campaign/{campaign_id}/ad-settings#section_adSpecs"
    
    @classmethod
    def get_campaign_overview_url(cls, campaign_id: str) -> str:
        """Get the overview URL for a specific campaign."""
        return f"{cls.TJ_BASE_URL}/campaign/overview/{campaign_id}"
    
    @classmethod
    def display_config(cls):
        """Display current configuration (hiding sensitive data)."""
        print("\n" + "="*50)
        print("TrafficJunky Automation Tool - Configuration")
        print("="*50)
        print(f"Username: {cls.TJ_USERNAME[:3]}***" if cls.TJ_USERNAME else "Username: NOT SET")
        print(f"Password: {'*' * 8}" if cls.TJ_PASSWORD else "Password: NOT SET")
        print(f"Campaign Mapping: data/input/campaign_mapping.csv")
        print(f"Dry Run Mode: {cls.DRY_RUN}")
        print(f"Headless Mode: {cls.HEADLESS_MODE}")
        print(f"Browser: {cls.BROWSER_TYPE}")
        print(f"Take Screenshots: {cls.TAKE_SCREENSHOTS}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print("="*50 + "\n")


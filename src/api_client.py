"""TrafficJunky API Client for fetching campaign performance data."""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from config.config import Config

logger = logging.getLogger(__name__)


class TrafficJunkyAPIClient:
    """Client for interacting with the TrafficJunky API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the API client.
        
        Args:
            api_key: TrafficJunky API key. If not provided, will use Config.TJ_API_KEY
        """
        self.api_key = api_key or Config.TJ_API_KEY
        self.base_url = Config.TJ_API_BASE_URL
        
        if not self.api_key:
            raise ValueError("TJ_API_KEY not set. Please add it to your .env file.")
    
    def _format_date(self, date: datetime) -> str:
        """
        Format date for TJ API (DD/MM/YYYY).
        
        Args:
            date: Python datetime object
            
        Returns:
            Formatted date string
        """
        return date.strftime("%d/%m/%Y")
    
    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """
        Make HTTP request to TJ API.
        
        Args:
            endpoint: API endpoint (e.g., '/campaigns/bids/stats.json')
            params: Query parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            requests.exceptions.RequestException: On API error
        """
        url = f"{self.base_url}{endpoint}"
        params['api_key'] = self.api_key
        
        logger.info(f"Making API request to: {url}")
        logger.debug(f"Parameters: {params}")
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"API request successful. Response size: {len(str(data))} bytes")
            return data
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            logger.error(f"Response: {e.response.text if hasattr(e, 'response') else 'No response'}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
        except ValueError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise
    
    def get_campaigns_stats(
        self, 
        start_date: datetime, 
        end_date: datetime,
        limit: int = 500,
        offset: int = 0
    ) -> List[Dict]:
        """
        Fetch campaign statistics for a date range.
        
        Uses the /api/campaigns/bids/stats.json endpoint.
        
        Args:
            start_date: Start date for reporting period
            end_date: End date for reporting period
            limit: Maximum number of campaigns to fetch (default: 500)
            offset: Offset for pagination (default: 0)
            
        Returns:
            List of campaign statistics dictionaries
            
        Example response format:
        [
            {
                "campaignId": 1013022481,
                "campaignName": "US_EN_PREROLL_CPA_PH_KEY-Blowjob_DESK_M_JB",
                "campaignType": "preroll",
                "dailyBudget": 1000,
                "dailyBudgetLeft": 250,
                "status": "active",
                "clicks": 450,
                "impressions": "45000",
                "CTR": 1.0,
                "CPM": 16.67,
                "cost": 750.50,
                "conversions": 15,
                "adsPaused": 0,
                "numberOfCreative": 10,
                ...
            },
            ...
        ]
        """
        params = {
            'startDate': self._format_date(start_date),
            'endDate': self._format_date(end_date),
            'limit': limit,
            'offset': offset
        }
        
        logger.info(f"Fetching campaign stats from {params['startDate']} to {params['endDate']}")
        
        data = self._make_request('/campaigns/bids/stats.json', params)
        
        # The API returns data in various formats, let's handle it
        if isinstance(data, list):
            campaigns = data
        elif isinstance(data, dict):
            # Sometimes the API returns a dict with campaign IDs as keys
            campaigns = list(data.values()) if data else []
        else:
            logger.warning(f"Unexpected API response format: {type(data)}")
            campaigns = []
        
        logger.info(f"Fetched {len(campaigns)} campaigns")
        return campaigns
    
    def get_campaign_stats(
        self,
        campaign_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[Dict]:
        """
        Fetch statistics for a single campaign.
        
        Uses the /api/campaigns/stats.json endpoint.
        
        Args:
            campaign_id: Campaign ID
            start_date: Start date for reporting period
            end_date: End date for reporting period
            
        Returns:
            Campaign statistics dictionary or None if not found
        """
        params = {
            'startDate': self._format_date(start_date),
            'endDate': self._format_date(end_date),
            'limit': 1,
            'offset': 0
        }
        
        logger.info(f"Fetching stats for campaign {campaign_id}")
        
        data = self._make_request('/campaigns/stats.json', params)
        
        # The response has campaign_id as key
        if isinstance(data, dict) and campaign_id in data:
            campaign_data = data[campaign_id]
            return campaign_data[0] if isinstance(campaign_data, list) and campaign_data else campaign_data
        
        logger.warning(f"No stats found for campaign {campaign_id}")
        return None
    
    @staticmethod
    def get_date_range(period: str) -> tuple[datetime, datetime]:
        """
        Get date range for common time periods.
        
        Args:
            period: One of 'today', 'yesterday', 'last7days', 'last30days'
            
        Returns:
            Tuple of (start_date, end_date)
            
        Raises:
            ValueError: If period is invalid
        """
        today = datetime.now()
        
        if period == 'today':
            return (today, today)
        elif period == 'yesterday':
            yesterday = today - timedelta(days=1)
            return (yesterday, yesterday)
        elif period == 'last7days':
            start = today - timedelta(days=7)
            return (start, today)
        elif period == 'last30days':
            start = today - timedelta(days=30)
            return (start, today)
        else:
            raise ValueError(f"Invalid period: {period}. Must be one of: today, yesterday, last7days, last30days")
    
    def test_connection(self) -> bool:
        """
        Test API connection and authentication.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to fetch today's stats (minimal request)
            start, end = self.get_date_range('today')
            self.get_campaigns_stats(start, end, limit=1)
            logger.info("API connection test successful")
            return True
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False


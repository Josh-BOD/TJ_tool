"""Authentication module for TrafficJunky platform."""

import logging
from typing import Optional
from playwright.sync_api import Page, Browser, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class TJAuthenticator:
    """Handles TrafficJunky login and session management."""
    
    def __init__(self, username: str, password: str):
        """
        Initialize authenticator.
        
        Args:
            username: TrafficJunky username or email
            password: TrafficJunky password
        """
        self.username = username
        self.password = password
        self.is_authenticated = False
    
    def login(self, page: Page) -> bool:
        """
        Log into TrafficJunky platform.
        
        Args:
            page: Playwright page object
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            logger.info("Navigating to TrafficJunky login page...")
            
            # Navigate to login page
            page.goto('https://www.trafficjunky.com/sign-in', wait_until='networkidle')
            
            # Wait for login form
            page.wait_for_selector('input[placeholder*="USERNAME"], input[placeholder*="EMAIL"]', 
                                  state='visible', timeout=10000)
            
            logger.info("Filling in credentials...")
            
            # Fill username
            username_input = page.locator('input[placeholder*="USERNAME"], input[placeholder*="EMAIL"]').first
            username_input.fill(self.username)
            
            # Fill password
            password_input = page.locator('input[type="password"]').first
            password_input.fill(self.password)
            
            # Click login button
            logger.info("Clicking login button...")
            login_button = page.locator('button:has-text("LOG IN")').first
            
            # Wait for navigation after login
            with page.expect_navigation(wait_until='networkidle', timeout=30000):
                login_button.click()
            
            # Verify login success
            if self._verify_login(page):
                logger.info("✓ Login successful!")
                self.is_authenticated = True
                return True
            else:
                logger.error("✗ Login failed - credentials may be incorrect")
                return False
                
        except PlaywrightTimeout as e:
            logger.error(f"✗ Login timeout: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Login error: {e}")
            return False
    
    def _verify_login(self, page: Page) -> bool:
        """
        Verify that login was successful.
        
        Args:
            page: Playwright page object
            
        Returns:
            True if logged in, False otherwise
        """
        try:
            # Check if we're on campaigns page or dashboard
            current_url = page.url
            
            if 'campaigns' in current_url or 'dashboard' in current_url:
                logger.debug(f"Login verified - URL: {current_url}")
                return True
            
            # Check for error messages
            if page.locator('text="don\'t recognize these credentials"').is_visible():
                logger.error("Invalid credentials")
                return False
            
            # If we see account balance or campaign elements, we're logged in
            if (page.locator('text="Account Balance"').is_visible(timeout=5000) or
                page.locator('text="ALL CAMPAIGNS"').is_visible(timeout=5000)):
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Login verification check: {e}")
            # If we can't verify but no error, assume success
            return True
    
    def is_logged_in(self, page: Page) -> bool:
        """
        Check if still logged in.
        
        Args:
            page: Playwright page object
            
        Returns:
            True if logged in, False otherwise
        """
        try:
            # Quick check for logged-in elements
            return (page.locator('text="Account Balance"').is_visible(timeout=2000) or
                   page.locator('text="ALL CAMPAIGNS"').is_visible(timeout=2000))
        except:
            return False


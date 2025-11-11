"""Authentication module for TrafficJunky platform."""

import logging
import json
from pathlib import Path
from typing import Optional
from playwright.sync_api import Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class TJAuthenticator:
    """Handles TrafficJunky login and session management."""
    
    def __init__(self, username: str, password: str, session_dir: Optional[Path] = None):
        """
        Initialize authenticator.
        
        Args:
            username: TrafficJunky username or email
            password: TrafficJunky password
            session_dir: Directory to store session data (default: ./data/session)
        """
        self.username = username
        self.password = password
        self.is_authenticated = False
        self.session_dir = session_dir or Path('./data/session')
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.session_dir / 'tj_session.json'
    
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
            
            # Handle cookie consent popup
            try:
                logger.info("Checking for cookie consent...")
                accept_button = page.locator('button:has-text("Accept All")')
                if accept_button.is_visible(timeout=3000):
                    logger.info("Accepting cookies...")
                    accept_button.click()
                    page.wait_for_timeout(1000)
            except:
                logger.debug("No cookie popup or already dismissed")
            
            # Wait for login form
            logger.info("Waiting for login form...")
            page.wait_for_selector('input[placeholder*="USERNAME"]', state='visible', timeout=10000)
            
            logger.info("Filling in credentials...")
            
            # Fill username
            username_input = page.locator('input[placeholder*="USERNAME"]').first
            username_input.click()
            username_input.fill(self.username)
            
            # Fill password
            password_input = page.locator('input[type="password"]').first
            password_input.click()
            password_input.fill(self.password)
            
            # Wait a moment for the form to enable the button
            page.wait_for_timeout(1000)
            
            # Wait for LOGIN button to be enabled
            logger.info("Waiting for login button to be enabled...")
            login_button = page.locator('button:has-text("LOG IN")')
            
            # Check if button is still disabled (might need reCAPTCHA)
            try:
                login_button.wait_for(state='enabled', timeout=5000)
            except:
                logger.warning("Login button still disabled - may need reCAPTCHA")
                logger.info("Attempting to click anyway...")
            
            # Click login button
            logger.info("Clicking login button...")
            
            # Wait for navigation after login
            with page.expect_navigation(wait_until='networkidle', timeout=30000):
                login_button.click(force=True, timeout=5000)
            
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
            logger.exception("Login exception details:")
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
            current_url = page.url
            
            # If we're on advertiser subdomain and not on sign-in page, we're likely logged in
            if 'advertiser.trafficjunky.com' in current_url and 'sign-in' not in current_url:
                logger.debug(f"Logged in - on advertiser page: {current_url}")
                return True
            
            # If URL contains campaigns or dashboard, we're logged in
            if any(keyword in current_url for keyword in ['campaigns', 'dashboard', 'campaign/overview']):
                logger.debug(f"Logged in - URL check: {current_url}")
                return True
            
            # Check for common logged-in elements
            try:
                if (page.locator('[href*="/campaigns"]').is_visible(timeout=2000) or
                    page.locator('a:has-text("Campaigns")').is_visible(timeout=2000)):
                    logger.debug("Logged in - found campaigns link")
                    return True
            except:
                pass
            
            return False
        except Exception as e:
            logger.debug(f"Login check error: {e}")
            return False
    
    def save_session(self, context: BrowserContext) -> bool:
        """
        Save browser session to file.
        
        Args:
            context: Playwright browser context
            
        Returns:
            True if saved successfully
        """
        try:
            logger.info(f"Saving session to {self.session_file}...")
            context.storage_state(path=str(self.session_file))
            logger.info("✓ Session saved successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False
    
    def load_session(self, browser: Browser) -> Optional[BrowserContext]:
        """
        Load saved session and create browser context.
        
        Args:
            browser: Playwright browser instance
            
        Returns:
            BrowserContext with loaded session or None if failed
        """
        try:
            if not self.session_file.exists():
                logger.debug("No saved session found")
                return None
            
            logger.info("Loading saved session...")
            context = browser.new_context(storage_state=str(self.session_file))
            logger.info("✓ Session loaded successfully")
            return context
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None
    
    def manual_login(self, page: Page, timeout: int = 120) -> bool:
        """
        Wait for user to manually log in.
        
        Args:
            page: Playwright page object
            timeout: How long to wait for manual login (seconds)
            
        Returns:
            True if login detected, False if timeout
        """
        try:
            logger.info("="*60)
            logger.info("MANUAL LOGIN REQUIRED")
            logger.info("="*60)
            
            # Navigate to login page and wait for it to fully load
            logger.info("Navigating to login page...")
            page.goto('https://www.trafficjunky.com/sign-in', wait_until='networkidle')
            page.wait_for_timeout(2000)  # Extra wait for any JS to initialize
            
            # Handle cookie consent popup
            try:
                logger.info("Checking for cookie consent...")
                accept_button = page.locator('button:has-text("Accept All")')
                if accept_button.is_visible(timeout=3000):
                    logger.info("Accepting cookies...")
                    accept_button.click()
                    page.wait_for_timeout(1000)
            except:
                logger.info("No cookie popup (already dismissed)")
            
            # Pre-fill credentials
            try:
                logger.info("Pre-filling credentials...")
                page.wait_for_selector('input[placeholder*="USERNAME"]', state='visible', timeout=10000)
                
                username_input = page.locator('input[placeholder*="USERNAME"]').first
                username_input.click()
                page.wait_for_timeout(300)
                # Type character-by-character to trigger JavaScript validation
                username_input.type(self.username, delay=50)
                page.wait_for_timeout(300)
                
                password_input = page.locator('input[type="password"]').first
                password_input.click()
                page.wait_for_timeout(300)
                # Type character-by-character to trigger JavaScript validation
                password_input.type(self.password, delay=50)
                page.wait_for_timeout(300)
                
                # Click somewhere else to trigger form validation and enable the button
                logger.info("Triggering form validation...")
                try:
                    # Click on the page heading
                    page.locator('h1').first.click()
                except:
                    # If that fails, just press Tab
                    page.keyboard.press('Tab')
                
                page.wait_for_timeout(1500)
                logger.info("✓ Credentials filled")
            except Exception as e:
                logger.error(f"Error pre-filling credentials: {e}")
                logger.exception("Credential fill error:")
            
            logger.info("")
            logger.info("⏳ Please solve the reCAPTCHA...")
            logger.info("   (I'll automatically click LOGIN once you solve it)")
            logger.info("="*60)
            logger.info(f"Waiting up to {timeout} seconds...")
            logger.info("")
            
            # Wait for LOGIN button to be visible (it's actually an input element!)
            logger.info("Looking for LOGIN button...")
            try:
                # The LOGIN button is an input element with ID submitBtn
                login_button_selector = 'input#submitBtn, input[type="submit"], input[value*="LOG IN"]'
                page.wait_for_selector(login_button_selector, state='visible', timeout=10000)
                logger.info("✓ LOGIN button found (input#submitBtn)")
                login_button = page.locator('input#submitBtn').first
                    
            except Exception as e:
                logger.error(f"✗ LOGIN button not found: {e}")
                # Take a screenshot for debugging
                try:
                    screenshot_path = './screenshots/login_error.png'
                    page.screenshot(path=screenshot_path)
                    logger.error(f"Screenshot saved to: {screenshot_path}")
                except:
                    pass
                return False
            
            # Check button state once before loop for debugging
            try:
                initial_disabled = login_button.get_attribute('disabled')
                logger.info(f"Initial button state - disabled attribute: '{initial_disabled}'")
            except Exception as e:
                logger.warning(f"Could not get initial button state: {e}")
            
            for i in range(timeout // 2):
                try:
                    # First check if user already logged in manually
                    if self.is_logged_in(page):
                        logger.info("✓ Login detected (manually completed)!")
                        self.is_authenticated = True
                        return True
                    
                    # Check if button is enabled (no disabled attribute)
                    try:
                        disabled_attr = login_button.get_attribute('disabled')
                    except Exception as e:
                        logger.warning(f"Error getting button attribute: {e}")
                        disabled_attr = 'error'
                    
                    # Log every 5 iterations for debugging
                    if i % 5 == 0:
                        logger.info(f"[Check #{i}] Button disabled attribute: '{disabled_attr}'")
                    
                    # Button is enabled when disabled attribute is None or empty string
                    # (TrafficJunky removes the disabled attribute when reCAPTCHA is solved)
                    if disabled_attr is None or disabled_attr == '':
                        logger.info("✓ reCAPTCHA solved! Button enabled. Auto-clicking LOGIN...")
                        
                        # Wait a moment for any JS to settle
                        page.wait_for_timeout(800)
                        
                        # Click the login button
                        try:
                            login_button.click(timeout=5000)
                            logger.info("✓ LOGIN button clicked! Waiting for redirect...")
                            
                            # Wait for navigation/login to complete
                            page.wait_for_timeout(4000)
                            
                            # Check if logged in
                            if self.is_logged_in(page):
                                logger.info("✓ Login successful!")
                                self.is_authenticated = True
                                return True
                            else:
                                logger.warning("Button clicked but not logged in yet, waiting longer...")
                                page.wait_for_timeout(2000)
                                if self.is_logged_in(page):
                                    logger.info("✓ Login successful (after delay)!")
                                    self.is_authenticated = True
                                    return True
                        except Exception as e:
                            logger.warning(f"Error clicking login button: {e}")
                            # Still check if we're logged in anyway
                            if self.is_logged_in(page):
                                logger.info("✓ Login successful (despite click error)!")
                                self.is_authenticated = True
                                return True
                    
                except Exception as e:
                    # Log the error for debugging
                    logger.error(f"⚠️  Loop iteration {i} error: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                
                if i % 10 == 0 and i > 0:  # Print status every 20 seconds
                    logger.info(f"Still waiting for reCAPTCHA... ({i*2}/{timeout} seconds)")
                
                page.wait_for_timeout(2000)
            
            logger.error("✗ Login timeout - reCAPTCHA not solved in time")
            return False
            
        except Exception as e:
            logger.error(f"✗ Manual login error: {e}")
            logger.exception("Manual login exception:")
            return False


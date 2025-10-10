#!/usr/bin/env python3
"""
Twitter Agent using Selenium for reliable browser automation
"""

import asyncio
import os
import time
import re
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Set
from dotenv import load_dotenv
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import random
import undetected_chromedriver as uc

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SeleniumTwitterAgent:
    def __init__(self):
        self.base_prompt = "Rules: keep your response less than 500 characters. avoid all the followings in your response: avoid double dashes --, avoid double hyphens like --,avoid **,avoid references,avoid citations,avoid math formulas. Do NOT ask me anything further and only output the response and start the response with a full sentence that doesn't start with numbers. Write a short fact-based impactful, entertaining, fun and amusing response teaching a fresh, complementary insight about the following text in a human-like entertaining language: '{tweet_content}'"

        # Configuration from environment
        self.delay_between_tweets = int(os.getenv('DELAY_BETWEEN_TWEETS', 5))
        self.max_tweets_per_session = int(os.getenv('MAX_TWEETS_PER_SESSION', 5))
        self.perplexity_wait_time = int(os.getenv('PERPLEXITY_WAIT_TIME', 60))
        self.perplexity_responses_per_chat = max(1, int(os.getenv('PERPLEXITY_RESPONSES_PER_CHAT', 2)))
        self.headless = os.getenv('HEADLESS', 'false').lower() == 'true'
        self.debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        self.feed_type = os.getenv('TWITTER_FEED_TYPE', 'following').lower()

        # Configure debug logging
        if self.debug_mode:
            logger.setLevel(logging.DEBUG)
            logger.info("🐛 Debug mode enabled - verbose logging activated")
        else:
            logger.setLevel(logging.INFO)

        # Log configuration summary
        logger.info(f"⚙️ Twitter Agent Configuration:")
        logger.info(f"   📱 Tweet delay: {self.delay_between_tweets}s")
        logger.info(f"   🎯 Max tweets per session: {self.max_tweets_per_session}")
        logger.info(f"   ⏱️ Perplexity wait time: {self.perplexity_wait_time}s")
        logger.info(f"   💬 Responses per chat: {self.perplexity_responses_per_chat}")
        logger.info(f"   👻 Headless mode: {self.headless}")
        logger.info(f"   📺 Twitter feed: {self.feed_type.title()}")

        self.driver = None

        # Persistent tweet tracking
        self.processed_tweets_file = Path("processed_tweets.json")
        self.processed_tweets = self._load_processed_tweets()
        self.current_username = None  # Will be detected after login

        # Track last response to avoid reusing stale content
        self.last_response_text = None
        self.last_response_time = 0

        # Track Perplexity chat session usage
        self.current_chat_response_count = 0

    def _load_processed_tweets(self) -> Set[str]:
        """Load processed tweet hashes from file"""
        try:
            if self.processed_tweets_file.exists():
                with open(self.processed_tweets_file, 'r') as f:
                    data = json.load(f)
                    processed_set = set(data.get('processed_tweets', []))
                    logger.info(f"Loaded {len(processed_set)} previously processed tweets")
                    return processed_set
        except Exception as e:
            logger.warning(f"Could not load processed tweets file: {e}")
        return set()

    def _save_processed_tweets(self):
        """Save processed tweet hashes to file"""
        try:
            data = {
                'processed_tweets': list(self.processed_tweets),
                'last_updated': time.time()
            }
            with open(self.processed_tweets_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(self.processed_tweets)} processed tweets to file")
        except Exception as e:
            logger.warning(f"Could not save processed tweets file: {e}")

    def _get_tweet_hash(self, tweet_content: str) -> str:
        """Generate a hash for tweet content to use as unique identifier"""
        return hashlib.md5(tweet_content.encode('utf-8')).hexdigest()

    def setup_driver(self):
        """Set up Chrome driver with undetected_chromedriver for better reliability"""
        logger.info("Setting up Undetected Chrome driver...")

        # Configure undetected_chromedriver options
        chrome_options = uc.ChromeOptions()

        if self.headless:
            chrome_options.add_argument("--headless=new")

        # ALWAYS use a separate Chrome profile for automation (avoids conflicts)
        automation_profile_dir = Path.home() / ".chrome_automation_profile"
        automation_profile_dir.mkdir(exist_ok=True)
        user_data_dir = str(automation_profile_dir)
        logger.info(f"📁 Using automation-specific Chrome profile: {user_data_dir}")
        logger.info("ℹ️  First time: You'll need to log into X.com manually")
        logger.info("ℹ️  After that: Logins are remembered!")
        
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        
        # Use a specific profile directory for this session
        profile_directory = os.getenv('CHROME_PROFILE_DIRECTORY', 'TwitterAgent')
        chrome_options.add_argument(f"--profile-directory={profile_directory}")

        # Additional options for stability
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--disable-popup-blocking")
        
        # Disable automation indicators (undetected_chromedriver handles most of this)
        chrome_options.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2  # Disable notifications
        })

        try:
            logger.info("🚀 Initializing undetected Chrome driver...")
            logger.info("⏳ This may take 10-30 seconds on first run...")
            logger.info("💻 System: macOS ARM64 (Apple Silicon)")
            
            # Use undetected_chromedriver with specific settings for ARM Macs
            # Get Chrome major version
            import platform
            import subprocess
            
            try:
                chrome_version_output = subprocess.check_output([
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", 
                    "--version"
                ]).decode('utf-8').strip()
                chrome_version = chrome_version_output.split()[-1]
                chrome_major_version = int(chrome_version.split('.')[0])
                logger.info(f"🌐 Detected Chrome version: {chrome_version} (major: {chrome_major_version})")
            except:
                chrome_major_version = None
                logger.warning("⚠️  Could not detect Chrome version, will auto-detect")
            
            # Find ARM64 ChromeDriver - try multiple locations
            chromedriver_path = None
            home_dir = str(Path.home())
            possible_paths = [
                f"{home_dir}/bin/chromedriver",    # User local bin (recommended)
                "/opt/homebrew/bin/chromedriver",  # Homebrew ARM Mac
                "/usr/local/bin/chromedriver",     # Homebrew Intel Mac
                "/usr/bin/chromedriver"            # System
            ]
            
            for path in possible_paths:
                if Path(path).exists():
                    chromedriver_path = path
                    logger.info(f"✅ Found ChromeDriver at: {chromedriver_path}")
                    break
            
            if not chromedriver_path:
                logger.warning("⚠️  ChromeDriver not found in standard locations, will auto-download")
            
            # Create driver with ARM64 ChromeDriver
            self.driver = uc.Chrome(
                options=chrome_options,
                version_main=chrome_major_version,  # Use detected version
                driver_executable_path=chromedriver_path,  # Use system ChromeDriver if available
                use_subprocess=False,  # Better for ARM Macs
                headless=self.headless,
                suppress_welcome=True
            )
            
            # Set a reasonable page load timeout
            self.driver.set_page_load_timeout(60)
            
            logger.info("✅ Undetected Chrome driver initialized successfully!")
            logger.info("🎯 This driver is designed to bypass X.com bot detection")
            return True
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Failed to initialize Chrome driver: {e}")
            
            if "Bad CPU type" in error_msg or "Errno 86" in error_msg:
                logger.error("=" * 80)
                logger.error("🚨 ERROR: Architecture mismatch (ARM64 vs x86_64)")
                logger.error("")
                logger.error("Fix for Apple Silicon Macs:")
                logger.error("  1. Clear cache: rm -rf ~/Library/Application\\ Support/undetected_chromedriver/")
                logger.error("  2. Install ARM ChromeDriver manually:")
                logger.error("     brew install --cask chromedriver")
                logger.error("  3. Or install using arch:")
                logger.error("     arch -arm64 python3 -m pip install --force-reinstall undetected-chromedriver")
                logger.error("  4. Try again: python3 twitter_agent_selenium.py")
                logger.error("=" * 80)
            elif "DevToolsActivePort" in error_msg or "timed out" in error_msg.lower():
                logger.error("=" * 80)
                logger.error("🚨 ERROR: Chrome initialization timeout or conflict!")
                logger.error("")
                logger.error("Quick fix:")
                logger.error("  1. Run: ./kill_chrome.sh")
                logger.error("  2. Wait 5 seconds")
                logger.error("  3. Try again")
                logger.error("=" * 80)
            elif "session not created" in error_msg:
                logger.error("=" * 80)
                logger.error("🚨 ERROR: Could not create Chrome session")
                logger.error("")
                logger.error("Possible solutions:")
                logger.error("  1. Close all Chrome: ./kill_chrome.sh")
                logger.error("  2. Update Chrome to latest version")
                logger.error("  3. Clear automation profile:")
                logger.error("     rm -rf ~/.chrome_automation_profile")
                logger.error("=" * 80)
            
            return False

    def wait_for_element(self, by, selector, timeout=10):
        """Wait for an element to be present"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except TimeoutException:
            return None

    def wait_for_clickable(self, by, selector, timeout=10):
        """Wait for an element to be clickable"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            return element
        except TimeoutException:
            return None

    def navigate_to_twitter(self) -> bool:
        """Navigate to Twitter and check login status"""
        try:
            logger.info("Navigating to X.com...")
            self.driver.get("https://x.com")
            time.sleep(5)

            # Check if we're logged in by looking for specific elements
            try:
                # Look for the home timeline or user menu
                home_element = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="AppTabBar_Home_Link"]')
                logger.info("Successfully logged in to X.com")

                # Select the appropriate feed after successful login
                if not self.select_feed():
                    logger.warning("Failed to select feed, continuing with default")

                return True
            except NoSuchElementException:
                try:
                    # Look for sign in button
                    signin_element = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Sign in')]")
                    logger.warning("Not logged in to X.com. Please log in manually.")
                    input("Please log in to X.com in the browser window and press Enter to continue...")
                    time.sleep(3)
                    return self.navigate_to_twitter()  # Check again
                except NoSuchElementException:
                    logger.info("Login status unclear, proceeding...")
                    return True

        except Exception as e:
            logger.error(f"Error navigating to X.com: {e}")
            return False

    def select_feed(self) -> bool:
        """Select the appropriate Twitter feed (For you or Following)"""
        try:
            logger.info(f"Selecting Twitter feed: {self.feed_type.title()}")

            # If 'for you' is selected, no action needed (it's usually the default)
            if self.feed_type == 'for you':
                logger.info("Using 'For you' feed (default)")
                return True

            # For 'following' feed, we need to click on the Following tab
            if self.feed_type == 'following':
                # Common selectors for the Following tab
                following_selectors = [
                    '[role="tab"] span:contains("Following")',
                    '[data-testid="ScrollSnap-List"] div[role="tab"]:nth-child(2)',
                    'div[role="tablist"] div[role="tab"]:contains("Following")',
                    'a[href="/home"]:contains("Following")',
                    '[aria-label="Following timeline"]',
                    'span:contains("Following")'
                ]

                # Try to find and click the Following tab
                for selector in following_selectors:
                    try:
                        # Handle :contains() pseudo-selector
                        if ':contains(' in selector:
                            # Extract the text to search for
                            text_to_find = selector.split(':contains("')[1].split('")')[0]
                            base_selector = selector.split(':contains(')[0]

                            # Find elements using the base selector
                            elements = self.driver.find_elements(By.CSS_SELECTOR, base_selector) if base_selector else []

                            # If no base selector, search all elements
                            if not base_selector:
                                elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{text_to_find}')]")

                            for element in elements:
                                if text_to_find.lower() in element.text.lower() and element.is_displayed():
                                    element.click()
                                    logger.info(f"✅ Successfully clicked Following tab using: {selector}")
                                    time.sleep(2)
                                    return True
                        else:
                            # Regular CSS selector
                            element = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if element.is_displayed():
                                element.click()
                                logger.info(f"✅ Successfully clicked Following tab using: {selector}")
                                time.sleep(2)
                                return True
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue

                # Fallback: try to find any element with "Following" text
                try:
                    following_element = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Following')]")
                    if following_element.is_displayed():
                        following_element.click()
                        logger.info("✅ Successfully clicked Following tab using fallback method")
                        time.sleep(2)
                        return True
                except Exception as e:
                    logger.debug(f"Fallback method failed: {e}")

                logger.warning("Could not find Following tab, continuing with default feed")
                return False

            logger.warning(f"Unknown feed type: {self.feed_type}")
            return False

        except Exception as e:
            logger.error(f"Error selecting feed: {e}")
            return False

    def extract_tweets_from_timeline(self) -> List[Dict[str, str]]:
        """Extract tweets from the timeline"""
        try:
            logger.info("Extracting tweets from timeline...")

            # Make sure we're on the home timeline
            try:
                home_link = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="AppTabBar_Home_Link"]')
                home_link.click()
                time.sleep(3)
            except:
                pass

            tweets = []
            attempts = 0
            max_attempts = 5

            while len(tweets) < self.max_tweets_per_session and attempts < max_attempts:
                attempts += 1
                logger.info(f"Extraction attempt {attempts}/{max_attempts}")

                # Find tweet articles
                try:
                    tweet_articles = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')
                    logger.info(f"Found {len(tweet_articles)} tweet articles")

                    for article in tweet_articles:
                        try:
                            # Extract tweet text with multiple selectors
                            tweet_text_element = None
                            tweet_text_selectors = [
                                '[data-testid="tweetText"]',
                                '[data-testid="tweet-text"]', 
                                '.tweet-text',
                                '[role="group"] div[lang]',
                                'div[data-testid="tweet"] div[lang]',
                                'article div[lang]'
                            ]
                            
                            for selector in tweet_text_selectors:
                                try:
                                    tweet_text_element = article.find_element(By.CSS_SELECTOR, selector)
                                    if tweet_text_element and tweet_text_element.text.strip():
                                        break
                                except:
                                    continue
                            
                            if not tweet_text_element:
                                logger.debug("Could not find tweet text element, skipping...")
                                continue
                                
                            tweet_text = tweet_text_element.text.strip()

                            # Skip if too short (minimum 30 characters) or already processed
                            tweet_hash = self._get_tweet_hash(tweet_text)
                            if len(tweet_text) < 30 or tweet_hash in self.processed_tweets:
                                logger.debug(f"Skipping tweet: length={len(tweet_text)} (min 30 chars), already_processed={tweet_hash in self.processed_tweets}")
                                continue

                            # Try to extract tweet ID from links
                            tweet_id = f"tweet_{len(tweets)}_{int(time.time())}"
                            try:
                                links = article.find_elements(By.TAG_NAME, "a")
                                for link in links:
                                    href = link.get_attribute("href") or ""
                                    if "/status/" in href:
                                        tweet_id = href.split("/status/")[-1].split("?")[0]
                                        break
                            except:
                                pass

                            # Extract username
                            username = "unknown"
                            try:
                                user_links = article.find_elements(By.CSS_SELECTOR, 'a[href^="/"]')
                                for link in user_links:
                                    href = link.get_attribute("href") or ""
                                    if href.count("/") == 3 and "/status/" not in href:  # Profile link
                                        username = href.split("/")[-1]
                                        break
                            except:
                                pass

                            tweet_data = {
                                'id': tweet_id,
                                'content': tweet_text,
                                'username': username,
                                'element': article
                            }

                            tweets.append(tweet_data)
                            self.processed_tweets.add(tweet_hash)

                            logger.info(f"Extracted tweet {len(tweets)}: {tweet_text[:100]}...")

                            if len(tweets) >= self.max_tweets_per_session:
                                break

                        except Exception as e:
                            logger.warning(f"Error extracting individual tweet: {e}")
                            continue

                except Exception as e:
                    logger.warning(f"Error finding tweet articles: {e}")

                # If we haven't collected enough tweets, scroll down
                if len(tweets) < self.max_tweets_per_session:
                    logger.info("Scrolling down to load more tweets...")
                    self.driver.execute_script("window.scrollBy(0, 1000);")
                    time.sleep(3)

            logger.info(f"Successfully extracted {len(tweets)} tweets")
            return tweets

        except Exception as e:
            logger.error(f"Error extracting tweets: {e}")
            return []

    def extract_single_tweet(self) -> dict:
        """Extract a single unprocessed tweet from the timeline"""
        try:
            logger.info("Looking for a single unprocessed tweet...")

            # Make sure we're on the home timeline
            try:
                home_link = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="AppTabBar_Home_Link"]')
                home_link.click()
                time.sleep(2)
            except:
                pass

            # Scroll a bit to refresh content
            self.driver.execute_script("window.scrollBy(0, 300);")
            time.sleep(2)

            # Find tweet articles
            tweet_articles = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')
            logger.info(f"Found {len(tweet_articles)} tweet articles")

            for article in tweet_articles:
                try:
                    # Extract tweet text with multiple selectors
                    tweet_text_element = None
                    tweet_text_selectors = [
                        '[data-testid="tweetText"]',
                        '[data-testid="tweet-text"]', 
                        '.tweet-text',
                        '[role="group"] div[lang]',
                        'div[data-testid="tweet"] div[lang]',
                        'article div[lang]'
                    ]
                    
                    for selector in tweet_text_selectors:
                        try:
                            tweet_text_element = article.find_element(By.CSS_SELECTOR, selector)
                            if tweet_text_element and tweet_text_element.text.strip():
                                break
                        except:
                            continue
                    
                    if not tweet_text_element:
                        logger.debug("Could not find tweet text element, skipping...")
                        continue
                        
                    tweet_text = tweet_text_element.text.strip()

                    # Skip if too short (minimum 30 characters) or already processed
                    tweet_hash = self._get_tweet_hash(tweet_text)
                    if len(tweet_text) < 30 or tweet_hash in self.processed_tweets:
                        logger.debug(f"Skipping tweet: length={len(tweet_text)} (min 30 chars), already_processed={tweet_hash in self.processed_tweets}")
                        continue

                    # Check if this is our own tweet/reply - skip it
                    try:
                        # Look for username in the tweet
                        username_element = article.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"] a')
                        username = username_element.get_attribute('href')
                        if username:
                            # Extract username from URL like https://x.com/username
                            username = username.split('/')[-1].lower()
                            
                            # Skip if this is our own tweet (we don't want to reply to ourselves)
                            if self.current_username and username == self.current_username:
                                logger.info(f"🚫 Skipping our own tweet from @{username}")
                                continue
                                
                    except Exception as e:
                        logger.debug(f"Could not extract username: {e}")
                        # If we can't determine the username, continue processing
                        pass

                    # Try to extract tweet ID from links
                    tweet_id = f"tweet_{int(time.time())}"
                    try:
                        links = article.find_elements(By.TAG_NAME, "a")
                        for link in links:
                            href = link.get_attribute("href") or ""
                            if "/status/" in href:
                                tweet_id = href.split("/status/")[-1].split("?")[0]
                                break
                    except:
                        pass

                    # Extract username
                    username = "unknown"
                    try:
                        user_links = article.find_elements(By.CSS_SELECTOR, 'a[href^="/"]')
                        for link in user_links:
                            href = link.get_attribute("href") or ""
                            if href.count("/") == 3 and "/status/" not in href:  # Profile link
                                username = href.split("/")[-1]
                                break
                    except:
                        pass

                    tweet_data = {
                        'id': tweet_id,
                        'content': tweet_text,
                        'username': username,
                        'element': article
                    }

                    # Mark as processed
                    self.processed_tweets.add(tweet_hash)
                    logger.info(f"Found unprocessed tweet: {tweet_text[:100]}...")
                    return tweet_data

                except Exception as e:
                    logger.warning(f"Error extracting individual tweet: {e}")
                    continue

            logger.info("No unprocessed tweets found")
            return None

        except Exception as e:
            logger.error(f"Error extracting single tweet: {e}")
            return None

    def check_perplexity_login_status(self) -> bool:
        """Check if we're logged into Perplexity.ai"""
        try:
            logger.info("Checking Perplexity.ai login status...")

            # Look for login indicators
            login_indicators = [
                "Log in",
                "Sign in",
                "Sign up",
                "Get started"
            ]

            # Look for logged-in indicators
            logged_in_indicators = [
                "Pro",
                "Profile",
                "Settings",
                "Upgrade"
            ]

            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()

            # Check for login required text
            for indicator in login_indicators:
                if indicator.lower() in page_text:
                    logger.warning(f"Found login indicator: '{indicator}' - may not be logged in")

            # Check for logged-in indicators
            logged_in_found = False
            for indicator in logged_in_indicators:
                if indicator.lower() in page_text:
                    logger.info(f"Found logged-in indicator: '{indicator}'")
                    logged_in_found = True
                    break

            return logged_in_found

        except Exception as e:
            logger.warning(f"Could not determine login status: {e}")
            return True  # Assume logged in if we can't determine

    def find_perplexity_input_field(self):
        """Find the Perplexity input field using multiple strategies for SPA"""
        logger.info("Looking for Perplexity input field...")

        # Wait for SPA elements to be ready
        max_wait = 15
        wait_time = 0
        
        while wait_time < max_wait:
            # Multiple selectors to try for the input field (prioritize contenteditable)
            input_selectors = [
                ("div[contenteditable='true']", "Content editable div"),  # PRIORITY: Move to top
                ("div[role='textbox']", "Textbox role div"),
                ("textarea", "Generic textarea"),
                ("textarea[placeholder*='Ask']", "Textarea with 'Ask' placeholder"),
                ("textarea[placeholder*='question']", "Textarea with 'question' placeholder"),
                ("textarea[placeholder*='anything']", "Textarea with 'anything' placeholder"),
                ("input[type='text']", "Text input field"),
                ("[placeholder*='Ask']", "Any element with 'Ask' placeholder"),
                ("[placeholder*='question']", "Any element with 'question' placeholder"),
                ("[placeholder*='anything']", "Any element with 'anything' placeholder"),
                ("[aria-label*='search']", "Search aria-label"),
                ("[aria-label*='input']", "Input aria-label"),
                ("[aria-label*='query']", "Query aria-label"),
                (".search-input", "Search input by class"),
                ("#search", "Search input by ID"),
                ("[data-testid*='search']", "Search input by test-id"),  # MOVED DOWN: Less priority
                ("[data-testid*='input']", "Input by test-id"),
                ("[data-testid*='query']", "Query input by test-id"),
            ]

            for selector, description in input_selectors:
                try:
                    logger.debug(f"Trying selector: {selector} ({description})")
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        if element and element.is_displayed() and element.is_enabled():
                            # Additional check to ensure element is interactable
                            try:
                                # Test if we can interact with the element
                                self.driver.execute_script("arguments[0].focus();", element)
                                # Additional check - try to get the element's rect to ensure it's truly interactable
                                rect = element.rect
                                if rect['width'] > 0 and rect['height'] > 0:
                                    logger.info(f"✅ Found input field using: {description}")
                                    return element
                            except Exception as interact_error:
                                logger.debug(f"Element found but not interactable: {interact_error}")
                                continue
                except NoSuchElementException:
                    continue
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            # If no element found, wait a bit and try again
            if wait_time < max_wait - 1:
                logger.debug(f"No input field found, waiting... ({wait_time + 1}/{max_wait})")
                time.sleep(1)
                wait_time += 1
            else:
                break

        # If none of the selectors work, try finding by tag name with more patience
        try:
            logger.info("Trying to find any textarea with extended wait...")
            textarea = self.wait_for_element(By.TAG_NAME, "textarea", timeout=10)
            if textarea:
                logger.info("✅ Found textarea with extended wait")
                return textarea
        except:
            pass

        return None

    def debug_perplexity_page(self):
        """Debug helper to understand what's on the Perplexity SPA page"""
        try:
            logger.info("=== DEBUGGING PERPLEXITY SPA PAGE ===")
            logger.info(f"Current URL: {self.driver.current_url}")
            logger.info(f"Page title: {self.driver.title}")

            # Check if SPA root is populated
            try:
                root_element = self.driver.find_element(By.ID, "root")
                root_text = root_element.text.strip()
                logger.info(f"Root element text length: {len(root_text)}")
                if len(root_text) > 0:
                    logger.info(f"Root element text snippet: {root_text[:200]}...")
                else:
                    logger.warning("Root element is empty - SPA may not have loaded")
            except:
                logger.warning("Could not find root element")

            # Look for form elements
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            divs_contenteditable = self.driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true']")
            divs_role_textbox = self.driver.find_elements(By.CSS_SELECTOR, "div[role='textbox']")

            logger.info(f"Found {len(textareas)} textarea elements")
            logger.info(f"Found {len(inputs)} input elements")
            logger.info(f"Found {len(buttons)} button elements")
            logger.info(f"Found {len(divs_contenteditable)} contenteditable divs")
            logger.info(f"Found {len(divs_role_textbox)} textbox role divs")

            # Check visible and interactable elements
            visible_textareas = [t for t in textareas if t.is_displayed()]
            visible_inputs = [i for i in inputs if i.is_displayed()]
            visible_buttons = [b for b in buttons if b.is_displayed()]

            logger.info(f"Found {len(visible_textareas)} visible textarea elements")
            logger.info(f"Found {len(visible_inputs)} visible input elements")
            logger.info(f"Found {len(visible_buttons)} visible button elements")

            # Try to get attributes from visible elements
            for i, textarea in enumerate(visible_textareas):
                placeholder = textarea.get_attribute("placeholder")
                aria_label = textarea.get_attribute("aria-label")
                data_testid = textarea.get_attribute("data-testid")
                rect = textarea.rect
                logger.info(f"Textarea {i+1}: placeholder='{placeholder}', aria-label='{aria_label}', data-testid='{data_testid}', rect={rect}")

            for i, input_elem in enumerate(visible_inputs):
                placeholder = input_elem.get_attribute("placeholder")
                input_type = input_elem.get_attribute("type")
                aria_label = input_elem.get_attribute("aria-label")
                data_testid = input_elem.get_attribute("data-testid")
                rect = input_elem.rect
                logger.info(f"Input {i+1}: type='{input_type}', placeholder='{placeholder}', aria-label='{aria_label}', data-testid='{data_testid}', rect={rect}")

            # Check for contenteditable divs
            for i, div in enumerate(divs_contenteditable):
                if div.is_displayed():
                    aria_label = div.get_attribute("aria-label")
                    data_testid = div.get_attribute("data-testid")
                    rect = div.rect
                    logger.info(f"Contenteditable div {i+1}: aria-label='{aria_label}', data-testid='{data_testid}', rect={rect}")

            # Check for textbox role divs
            for i, div in enumerate(divs_role_textbox):
                if div.is_displayed():
                    aria_label = div.get_attribute("aria-label")
                    data_testid = div.get_attribute("data-testid")
                    rect = div.rect
                    logger.info(f"Textbox role div {i+1}: aria-label='{aria_label}', data-testid='{data_testid}', rect={rect}")

            logger.info("=== END DEBUG INFO ===")

        except Exception as e:
            logger.error(f"Error during debugging: {e}")

    def debug_perplexity_ui_elements(self):
        """Debug helper to see what UI elements are available"""
        try:
            logger.info("🔍 DEBUG: Scanning Perplexity UI elements...")
            
            # Find all buttons with their text
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            visible_buttons = [b for b in buttons if b.is_displayed()]
            logger.info(f"📊 Found {len(visible_buttons)} visible buttons:")
            for i, btn in enumerate(visible_buttons[:20]):  # Show first 20
                try:
                    text = btn.text.strip()
                    aria_label = btn.get_attribute('aria-label')
                    class_name = btn.get_attribute('class')
                    if text or aria_label:
                        logger.info(f"   Button {i+1}: text='{text[:50]}', aria-label='{aria_label}', class='{class_name[:50] if class_name else ''}'")
                except:
                    pass
            
            # Find all divs with role
            divs_with_role = self.driver.find_elements(By.CSS_SELECTOR, "div[role]")
            logger.info(f"📊 Found {len(divs_with_role)} divs with role attribute")
            
            # Find elements with data-testid
            testid_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid]")
            logger.info(f"📊 Found {len(testid_elements)} elements with data-testid:")
            for elem in testid_elements[:10]:  # Show first 10
                try:
                    testid = elem.get_attribute('data-testid')
                    text = elem.text.strip()[:30]
                    logger.info(f"   data-testid='{testid}', text='{text}'")
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Debug failed: {e}")

    def select_gpt5_and_sources(self) -> bool:
        """Select GPT-5 Thinking model and configure sources"""
        try:
            logger.info("🤖 Configuring Perplexity: GPT-5 Thinking + Sources (Web, Academic, Social, Finance)")
            
            # Wait longer for the dynamic UI to fully load
            logger.info("⏱️ Waiting for Perplexity UI to fully load...")
            time.sleep(5)
            
            # Debug: Show what's available
            if self.debug_mode:
                self.debug_perplexity_ui_elements()
            
            # STEP 1: Click the MODEL selector button using explicit wait
            logger.info("🔍 Step 1: Looking for model selector button...")
            model_button = None
            
            try:
                # The model button's aria-label shows the CURRENT model name, not "Choose a model"
                # Look for buttons with aria-labels containing model names
                logger.info("   Searching for model selector button (aria-label shows current model)...")
                
                # Known model keywords that appear in aria-labels
                model_keywords = ['gpt', 'claude', 'gemini', 'sonar', 'thinking', 'grok', 'auto', 'o3']
                
                # Get all buttons
                all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                
                for btn in all_buttons:
                    if not btn.is_displayed():
                        continue
                    
                    aria_label = (btn.get_attribute('aria-label') or '').lower()
                    
                    # Check if this button's aria-label contains a model keyword
                    # and is NOT one of the other control buttons
                    if aria_label and any(keyword in aria_label for keyword in model_keywords):
                        # Make sure it's not a submit button or other control
                        if 'submit' not in aria_label and 'attach' not in aria_label and 'dictation' not in aria_label:
                            model_button = btn
                            logger.info(f"✅ Found model selector button with aria-label='{btn.get_attribute('aria-label')}'")
                            break
                
            except Exception as search_error:
                logger.warning(f"⚠️ Model button search failed: {search_error}")
            
            if model_button and model_button.is_displayed():
                try:
                    logger.info("🖱️ Clicking model selector...")
                    model_button.click()
                    time.sleep(3)
                    
                    # STEP 2: Look for GPT-5 Thinking option in the dropdown
                    logger.info("🔍 Step 2: Looking for GPT-5 Thinking in dropdown...")
                    
                    # Wait for dropdown to appear
                    time.sleep(2)
                    
                    # Look for menuitem divs containing model names
                    menu_items = self.driver.find_elements(By.CSS_SELECTOR, "div[role='menuitem']")
                    logger.info(f"📊 Found {len(menu_items)} menu items")
                    
                    found_model = False
                    for item in menu_items:
                        try:
                            if not item.is_displayed():
                                continue
                            
                            # Look for the span element containing the model name
                            try:
                                # Find all spans in this menuitem
                                spans = item.find_elements(By.TAG_NAME, "span")
                                model_name = ""
                                
                                for span in spans:
                                    span_text = span.text.strip()
                                    # Look for the main model name (skip badges like "new" or "max")
                                    if span_text and span_text.lower() not in ['new', 'max']:
                                        model_name = span_text
                                        break
                                
                                # Check if this is GPT-5 Thinking
                                if model_name.lower() == 'gpt-5 thinking':
                                    logger.info(f"🎯 Found GPT-5 Thinking option: '{model_name}'")
                                    
                                    # Click the menuitem div (not the span)
                                    try:
                                        # First try clicking the parent div with cursor-pointer class
                                        clickable_div = item.find_element(By.CSS_SELECTOR, "div.cursor-pointer")
                                        clickable_div.click()
                                        logger.info(f"✅ Selected model: GPT-5 Thinking")
                                        time.sleep(2)
                                        found_model = True
                                        break
                                    except:
                                        # Fallback: click the menuitem itself
                                        try:
                                            item.click()
                                            logger.info(f"✅ Selected model: GPT-5 Thinking (via menuitem)")
                                            time.sleep(2)
                                            found_model = True
                                            break
                                        except Exception as click_error:
                                            logger.debug(f"Direct click failed: {click_error}")
                                            # Try JavaScript click as last resort
                                            try:
                                                self.driver.execute_script("arguments[0].click();", item)
                                                logger.info(f"✅ Selected model: GPT-5 Thinking (via JavaScript)")
                                                time.sleep(2)
                                                found_model = True
                                                break
                                            except:
                                                logger.warning("Failed to click GPT-5 Thinking option")
                                                continue
                                        
                            except Exception as span_error:
                                logger.debug(f"Error finding span in menuitem: {span_error}")
                                continue
                                
                        except Exception as e:
                            logger.debug(f"Error checking menu item: {e}")
                            continue
                    
                    if not found_model:
                        logger.warning("⚠️ Could not find or click GPT-5 Thinking option")
                        logger.info("💡 Please manually select GPT-5 Thinking")
                        # Press ESC to close dropdown
                        try:
                            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                            time.sleep(1)
                        except:
                            pass
                                
                except Exception as e:
                    logger.warning(f"Error during model selection: {e}")
            else:
                logger.warning("⚠️ Model selector button not found or not visible")
                logger.info("💡 You may need to manually select GPT-5 Thinking")
            
            # STEP 3: Configure sources using exact selector
            time.sleep(2)
            logger.info("🔍 Step 3: Looking for sources selector button...")
            source_button = None
            
            try:
                # Try the exact data-testid selector
                source_button = self.driver.find_element(By.CSS_SELECTOR, 'button[data-testid="sources-switcher-button"]')
                logger.info("✅ Found sources selector using data-testid='sources-switcher-button'")
            except:
                logger.warning("⚠️ Could not find sources button with exact selector")
            
            if source_button and source_button.is_displayed():
                try:
                    logger.info("🖱️ Clicking sources selector...")
                    source_button.click()
                    time.sleep(3)
                    
                    # STEP 4: Select the sources (skip Web as it's already enabled by default)
                    # Use exact data-testid selectors from the HTML
                    sources_to_enable = {
                        'academic': 'source-toggle-scholar',
                        'social': 'source-toggle-social',
                        'finance': 'source-toggle-edgar'
                    }
                    
                    logger.info(f"🔍 Step 4: Enabling sources: {', '.join(sources_to_enable.keys())}")
                    logger.info("ℹ️  Skipping Web (already enabled by default)")
                    
                    enabled_sources = []
                    
                    for source_name, testid in sources_to_enable.items():
                        try:
                            # Find the menuitem with the specific data-testid
                            source_elem = self.driver.find_element(By.CSS_SELECTOR, f'div[data-testid="{testid}"]')
                            
                            if source_elem and source_elem.is_displayed():
                                # Check if it's already enabled by looking at the switch state
                                try:
                                    switch = source_elem.find_element(By.CSS_SELECTOR, 'button[role="switch"]')
                                    aria_checked = switch.get_attribute('aria-checked')
                                    
                                    if aria_checked == 'true':
                                        logger.info(f"ℹ️  {source_name.title()}: Already enabled")
                                        enabled_sources.append(source_name)
                                    else:
                                        # Click to enable
                                        logger.info(f"🎯 Clicking to enable: {source_name.title()}")
                                        source_elem.click()
                                        time.sleep(0.5)
                                        logger.info(f"✅ Enabled source: {source_name.title()}")
                                        enabled_sources.append(source_name)
                                except Exception as switch_error:
                                    # If we can't check the state, just click it
                                    logger.debug(f"Could not check switch state for {source_name}, clicking anyway: {switch_error}")
                                    source_elem.click()
                                    time.sleep(0.5)
                                    logger.info(f"✅ Clicked source: {source_name.title()}")
                                    enabled_sources.append(source_name)
                            else:
                                logger.warning(f"⚠️ Source not found or not visible: {source_name}")
                                
                        except Exception as e:
                            logger.warning(f"⚠️ Could not enable {source_name}: {e}")
                            continue
                    
                    logger.info(f"📊 Configured sources: Web (default), {', '.join([s.title() for s in enabled_sources])}")
                    
                    # Close the source selector
                    try:
                        self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        time.sleep(1)
                        logger.info("✅ Closed sources selector")
                    except:
                        pass
                        
                except Exception as e:
                    logger.warning(f"Error during source configuration: {e}")
            else:
                logger.warning("⚠️ Sources selector button not found or not visible")
                logger.info("💡 You may need to manually select sources")
            
            logger.info("✅ Perplexity configuration completed")
            logger.info("💡 Please verify the model and sources are correct")
            return True
            
        except Exception as e:
            logger.error(f"Error configuring Perplexity: {e}")
            logger.warning("⚠️ Continuing anyway - you may need to configure manually")
            return False

    def navigate_to_perplexity(self) -> bool:
        """Navigate to Perplexity.ai in a new tab with improved SPA loading detection"""
        try:
            logger.info("Opening Perplexity.ai in new tab...")

            # Open new tab
            self.driver.execute_script("window.open('https://perplexity.ai', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # Wait for initial page load
            time.sleep(3)
            
            # Wait for SPA to load - check for the root element to be populated
            logger.info("Waiting for Perplexity SPA to load...")
            max_wait = 30
            wait_time = 0
            
            while wait_time < max_wait:
                try:
                    # Check if the SPA has loaded by looking for common elements
                    root_element = self.driver.find_element(By.ID, "root")
                    if root_element and len(root_element.text.strip()) > 0:
                        logger.info("✅ Perplexity SPA loaded successfully")
                        break
                    
                    # Also check for any input elements as a backup
                    inputs = self.driver.find_elements(By.TAG_NAME, "textarea")
                    if inputs:
                        logger.info("✅ Found input elements, SPA likely loaded")
                        break
                        
                except:
                    pass
                
                time.sleep(1)
                wait_time += 1
                
                if wait_time % 5 == 0:
                    logger.info(f"Still waiting for SPA to load... ({wait_time}/{max_wait}s)")
            
            if wait_time >= max_wait:
                logger.warning("⚠️ SPA loading timeout, proceeding anyway...")
            
            # Additional wait for elements to be interactive
            time.sleep(2)

            # Check login status
            if not self.check_perplexity_login_status():
                logger.warning("⚠️  May not be logged into Perplexity.ai")
                logger.warning("Please log into Perplexity.ai in this browser window")
                if not self.headless:
                    input("Press Enter after logging into Perplexity.ai...")
                    time.sleep(2)

            # Configure GPT-5 Thinking and sources
            self.select_gpt5_and_sources()

            # Try to find input field with multiple strategies
            input_field = self.find_perplexity_input_field()

            if input_field:
                logger.info("✅ Successfully found Perplexity input field")
                return True
            else:
                logger.error("❌ Could not find Perplexity input field")

                # Debug the page to understand what's wrong
                self.debug_perplexity_page()

                if not self.headless:
                    logger.info("Browser window is open for manual inspection")
                    choice = input("Continue anyway? (y/n): ").lower().strip()
                    if choice == 'y':
                        return True

                return False

        except Exception as e:
            logger.error(f"Error navigating to Perplexity.ai: {e}")
            return False

    def query_perplexity(self, tweet_content: str) -> Optional[str]:
        """Submit query to Perplexity and get response with improved field detection"""
        try:
            logger.info("Querying Perplexity...")

            # Check if we need to start a fresh chat session
            if self.current_chat_response_count >= self.perplexity_responses_per_chat:
                logger.info(f"🔄 Chat limit reached ({self.current_chat_response_count}/{self.perplexity_responses_per_chat})")
                logger.info("💫 Starting fresh Perplexity chat session to maintain response quality...")

                if self.refresh_perplexity_with_new_chat():
                    logger.info("✅ Successfully started fresh Perplexity chat")
                    # Switch to the new Perplexity tab
                    if not self.switch_to_perplexity_tab():
                        logger.error("❌ Failed to switch to fresh Perplexity tab")
                        return None
                else:
                    logger.error("❌ Failed to start fresh Perplexity chat")
                    return None

            # Format the prompt
            prompt = self.base_prompt.format(tweet_content=tweet_content[:500])
            logger.info(f"Formatted prompt length: {len(prompt)} characters")

            # Find input field using improved method
            input_field = self.find_perplexity_input_field()
            if not input_field:
                logger.error("❌ Could not find Perplexity input field for querying")
                self.debug_perplexity_page()
                return None

            logger.info("✅ Found input field, proceeding with query...")

            # Clear any existing content with improved interaction for contenteditable divs
            try:
                # First, ensure the element is focused and interactable
                self.driver.execute_script("arguments[0].focus();", input_field)
                time.sleep(0.5)
                
                # Check if this is a contenteditable div
                is_contenteditable = input_field.get_attribute("contenteditable") == "true"
                
                if is_contenteditable:
                    logger.info("Clearing contenteditable div...")
                    # For contenteditable divs, clear textContent and innerHTML
                    self.driver.execute_script("""
                        arguments[0].textContent = '';
                        arguments[0].innerHTML = '';
                    """, input_field)
                    time.sleep(0.5)
                else:
                    # Try to clear using standard method for regular inputs
                    input_field.clear()
                    time.sleep(1)
                    
            except Exception as e:
                logger.warning(f"Could not clear input field: {e}")
                # Try alternative clearing methods
                try:
                    # Click to focus, then select all and delete
                    input_field.click()
                    time.sleep(0.5)
                    input_field.send_keys(Keys.CONTROL + "a")  # Select all
                    input_field.send_keys(Keys.DELETE)         # Delete
                    time.sleep(1)
                except Exception as clear_error:
                    logger.warning(f"Alternative clearing also failed: {clear_error}")
                    # Try JavaScript clearing as last resort
                    try:
                        self.driver.execute_script("""
                            if (arguments[0].tagName.toLowerCase() === 'div' && arguments[0].contentEditable === 'true') {
                                arguments[0].textContent = '';
                                arguments[0].innerHTML = '';
                            } else {
                                arguments[0].value = '';
                            }
                        """, input_field)
                        time.sleep(0.5)
                    except:
                        logger.warning("JavaScript clearing also failed, proceeding anyway...")

            # Type the prompt with improved interaction for contenteditable divs
            logger.info("Typing prompt...")
            try:
                # Ensure element is interactable by clicking first
                input_field.click()
                time.sleep(1)
                
                # Check if this is a contenteditable div
                is_contenteditable = input_field.get_attribute("contenteditable") == "true"
                
                if is_contenteditable:
                    logger.info("Detected contenteditable div, using specialized method...")
                    # For contenteditable divs, use multiple approaches
                    self.driver.execute_script("arguments[0].focus();", input_field)
                    time.sleep(0.5)
                    
                    # Method 1: Try textContent
                    self.driver.execute_script("arguments[0].textContent = arguments[1];", input_field, prompt)
                    time.sleep(0.5)
                    
                    # Method 2: Try innerHTML if textContent didn't work
                    content_check = self.driver.execute_script("return arguments[0].textContent;", input_field)
                    if not content_check.strip():
                        logger.info("textContent failed, trying innerHTML...")
                        self.driver.execute_script("arguments[0].innerHTML = arguments[1];", input_field, prompt)
                        time.sleep(0.5)
                    
                    # Method 3: Try simulating typing if innerHTML didn't work
                    content_check = self.driver.execute_script("return arguments[0].textContent;", input_field)
                    if not content_check.strip():
                        logger.info("innerHTML failed, trying simulated typing...")
                        # Clear first
                        self.driver.execute_script("""
                            arguments[0].focus();
                            document.execCommand('selectAll', false, null);
                            document.execCommand('delete', false, null);
                        """, input_field)
                        time.sleep(0.5)
                        
                        # Type character by character
                        for char in prompt:
                            self.driver.execute_script("""
                                arguments[0].focus();
                                document.execCommand('insertText', false, arguments[1]);
                            """, input_field, char)
                            time.sleep(0.01)  # Small delay between characters
                    
                    # Trigger comprehensive events
                    self.driver.execute_script("""
                        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                        arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
                        arguments[0].dispatchEvent(new Event('focus', { bubbles: true }));
                    """, input_field)
                    time.sleep(1)
                    
                    # Verify content was set
                    final_content = self.driver.execute_script("return arguments[0].textContent;", input_field)
                    if final_content.strip():
                        logger.info(f"✅ Successfully typed prompt in contenteditable div: '{final_content[:50]}...'")
                    else:
                        logger.warning("⚠️ Content may not have been set properly in contenteditable div")
                        # Try one more fallback method
                        input_field.send_keys(prompt)
                        logger.info("Used fallback send_keys method")
                else:
                    # Try standard typing for regular inputs/textareas
                    input_field.send_keys(prompt)
                    time.sleep(2)
                    logger.info("✅ Successfully typed prompt")
                    
            except Exception as e:
                logger.error(f"Failed to type prompt: {e}")
                # Try alternative method using JavaScript
                try:
                    logger.info("Trying alternative JavaScript method...")
                    # Try both value and textContent depending on element type
                    self.driver.execute_script("""
                        if (arguments[0].tagName.toLowerCase() === 'div' && arguments[0].contentEditable === 'true') {
                            arguments[0].textContent = arguments[1];
                            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                        } else {
                            arguments[0].value = arguments[1];
                            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    """, input_field, prompt)
                    time.sleep(1)
                    logger.info("✅ Successfully typed prompt using JavaScript")
                except Exception as js_error:
                    logger.error(f"JavaScript method also failed: {js_error}")
                    # Try one more time with fresh element reference
                    try:
                        logger.info("Trying with fresh element reference...")
                        fresh_input = self.find_perplexity_input_field()
                        if fresh_input:
                            self.driver.execute_script("arguments[0].textContent = arguments[1];", fresh_input, prompt)
                            self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", fresh_input)
                            input_field = fresh_input  # Update reference
                            logger.info("✅ Successfully typed with fresh element")
                        else:
                            logger.error("Could not find fresh element")
                            return None
                    except Exception as final_error:
                        logger.error(f"Final attempt failed: {final_error}")
                        return None

            # Submit the query with multiple methods
            logger.info("Submitting query...")

            # Record submission time to track response freshness
            query_submit_time = time.time()

            submitted = False
            
            # Method 1: Try RETURN key
            try:
                input_field.send_keys(Keys.RETURN)
                logger.info("✅ Query submitted with RETURN key")
                submitted = True
            except Exception as e:
                logger.warning(f"Failed to submit with RETURN key: {e}")
            
            # Method 2: Try ENTER key if RETURN failed
            if not submitted:
                try:
                    input_field.send_keys(Keys.ENTER)
                    logger.info("✅ Query submitted with ENTER key")
                    submitted = True
                except Exception as e:
                    logger.warning(f"Failed to submit with ENTER key: {e}")
            
            # Method 3: Look for submit button
            if not submitted:
                try:
                    submit_selectors = [
                        "button[type='submit']",
                        "button[aria-label*='submit']",
                        "button[aria-label*='Send']",
                        "button[aria-label*='Ask']",
                        "[data-testid*='submit']",
                        "[data-testid*='send']",
                        "button svg", # Often the submit button just has an SVG icon
                        "button[class*='submit']",
                        "button[class*='send']",
                    ]
                    
                    for selector in submit_selectors:
                        try:
                            submit_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for submit_btn in submit_buttons:
                                if submit_btn.is_displayed() and submit_btn.is_enabled():
                                    # Check if this button is near the input field
                                    try:
                                        input_rect = input_field.rect
                                        btn_rect = submit_btn.rect
                                        # If button is reasonably close to input field
                                        if abs(input_rect['y'] - btn_rect['y']) < 100:
                                            submit_btn.click()
                                            logger.info(f"✅ Query submitted using button: {selector}")
                                            submitted = True
                                            break
                                    except:
                                        # If we can't get rect, just try clicking
                                        submit_btn.click()
                                        logger.info(f"✅ Query submitted using button: {selector}")
                                        submitted = True
                                        break
                            if submitted:
                                break
                        except:
                            continue
                            
                except Exception as e:
                    logger.warning(f"Failed to find submit button: {e}")
            
            # Method 4: Enhanced JavaScript submission for contenteditable divs
            if not submitted:
                try:
                    logger.info("Trying enhanced JavaScript submission...")
                    # Enhanced script that works better with modern SPAs and contenteditable divs
                    js_script = """
                    // First, ensure the element is focused
                    arguments[0].focus();
                    
                    // Try to find and submit any form containing the input
                    var forms = document.querySelectorAll('form');
                    for (var i = 0; i < forms.length; i++) {
                        if (forms[i].contains(arguments[0])) {
                            forms[i].submit();
                            return 'form_submit';
                        }
                    }
                    
                    // Try to find a submit button near the input
                    var buttons = document.querySelectorAll('button');
                    var inputRect = arguments[0].getBoundingClientRect();
                    
                    for (var i = 0; i < buttons.length; i++) {
                        var btnRect = buttons[i].getBoundingClientRect();
                        // Check if button is reasonably close to input (within 200px)
                        if (Math.abs(inputRect.top - btnRect.top) < 200 && 
                            Math.abs(inputRect.left - btnRect.left) < 500) {
                            // Check if button looks like a submit button
                            var btnText = buttons[i].textContent.toLowerCase();
                            var hasSubmitIcon = buttons[i].querySelector('svg') !== null;
                            
                            if (btnText.includes('send') || btnText.includes('submit') || 
                                btnText.includes('ask') || hasSubmitIcon || btnText === '') {
                                buttons[i].click();
                                return 'button_click';
                            }
                        }
                    }
                    
                    // Try multiple keyboard events
                    var events = ['keydown', 'keypress', 'keyup'];
                    for (var j = 0; j < events.length; j++) {
                        var event = new KeyboardEvent(events[j], {
                            key: 'Enter',
                            code: 'Enter',
                            keyCode: 13,
                            which: 13,
                            bubbles: true,
                            cancelable: true
                        });
                        arguments[0].dispatchEvent(event);
                    }
                    
                    return 'keyboard_events';
                    """
                    result = self.driver.execute_script(js_script, input_field)
                    logger.info(f"✅ JavaScript submission attempted: {result}")
                    submitted = True
                except Exception as e:
                    logger.warning(f"Enhanced JavaScript submission failed: {e}")
            
            if not submitted:
                logger.error("Failed to submit query using any method")
                return None

            # Wait for response with validation
            logger.info(f"Waiting {self.perplexity_wait_time} seconds for Perplexity response...")

            # Track initial prose count to detect new responses
            initial_prose_count = 0
            try:
                initial_prose_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.prose")
                initial_prose_count = len(initial_prose_elements)
                logger.info(f"📊 Initial prose count before response: {initial_prose_count}")
            except:
                pass

            time.sleep(self.perplexity_wait_time)

            # Check if new response appeared
            try:
                final_prose_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.prose")
                final_prose_count = len(final_prose_elements)
                logger.info(f"📊 Final prose count after response: {final_prose_count}")

                if final_prose_count > initial_prose_count:
                    logger.info(f"✅ New response detected! {final_prose_count - initial_prose_count} new prose element(s)")
                else:
                    logger.warning(f"⚠️ No new prose elements detected (was {initial_prose_count}, now {final_prose_count})")
            except:
                pass

            # ULTRA-AGGRESSIVE: Scroll ALL THE WAY DOWN until no more scrolling possible
            logger.info("🔄 ULTRA-AGGRESSIVE: Scrolling ALL THE WAY DOWN until no more scrolling possible...")
            try:
                # Track scroll position to ensure we reach the absolute bottom
                prev_scroll_position = -1
                current_scroll_position = 0
                scroll_attempts = 0
                max_scroll_attempts = 15

                while prev_scroll_position != current_scroll_position and scroll_attempts < max_scroll_attempts:
                    prev_scroll_position = current_scroll_position
                    scroll_attempts += 1

                    # Multiple scrolling methods to ensure we reach the absolute bottom
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.3)

                    # Scroll all possible containers
                    self.driver.execute_script("""
                        // Scroll main window
                        window.scrollTo(0, document.body.scrollHeight);

                        // Find and scroll ALL possible containers
                        var allDivs = document.querySelectorAll('div');
                        for (var i = 0; i < allDivs.length; i++) {
                            var div = allDivs[i];
                            if (div.scrollHeight > div.clientHeight) {
                                div.scrollTop = div.scrollHeight;
                            }
                        }

                        // Try specific selectors
                        var containers = document.querySelectorAll('[class*="chat"], [class*="conversation"], [class*="messages"], [class*="thread"], [class*="responses"]');
                        for (var i = 0; i < containers.length; i++) {
                            containers[i].scrollTop = containers[i].scrollHeight;
                        }

                        // Scroll any element with overflow
                        var overflowElements = document.querySelectorAll('*');
                        for (var i = 0; i < overflowElements.length; i++) {
                            var el = overflowElements[i];
                            var style = window.getComputedStyle(el);
                            if (style.overflow === 'auto' || style.overflow === 'scroll' || style.overflowY === 'auto' || style.overflowY === 'scroll') {
                                el.scrollTop = el.scrollHeight;
                            }
                        }
                    """)
                    time.sleep(0.5)

                    # Check current scroll position
                    current_scroll_position = self.driver.execute_script("return window.pageYOffset + window.innerHeight;")
                    logger.info(f"Scroll attempt {scroll_attempts}: position {current_scroll_position}")

                logger.info(f"✅ Completed ultra-aggressive scrolling after {scroll_attempts} attempts")

                # Final aggressive scroll burst
                for i in range(3):
                    self.driver.execute_script("""
                        window.scrollTo(0, document.body.scrollHeight);
                        document.documentElement.scrollTop = document.documentElement.scrollHeight;
                    """)
                    time.sleep(0.2)

                logger.info("✅ Final scroll burst completed")

            except Exception as e:
                logger.warning(f"Error in ultra-aggressive scrolling: {e}")

            # Try to extract the response
            logger.info("Extracting LATEST response from Perplexity...")
            response_text = ""

            # RETRY LOGIC: Try multiple times to get the absolute latest response
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries and not response_text:
                retry_count += 1
                logger.info(f"🔄 ATTEMPT {retry_count}/{max_retries}: Finding the VERY LAST prose element")

                # Wait for content to load
                wait_time = 2 + retry_count  # Increasing wait time for each retry
                logger.info(f"⏱️ Waiting {wait_time} seconds for content to fully load...")
                time.sleep(wait_time)

                # Extra scroll before each attempt
                try:
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.5)
                except:
                    pass

                try:
                    # Get ALL prose elements - no filtering, just raw selection
                    prose_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.prose")
                    logger.info(f"📊 Attempt {retry_count}: Found {len(prose_elements)} total prose elements")

                    if prose_elements:
                        # On first attempt, show all elements for debugging
                        if retry_count == 1:
                            logger.info("🔍 ALL PROSE ELEMENTS FOUND (showing all for debugging):")
                            for i, element in enumerate(prose_elements):
                                if element.is_displayed():
                                    text = element.text.strip()
                                    logger.info(f"  Element {i+1}: '{text[:100]}...' (length: {len(text)})")

                        # TAKE THE ABSOLUTE LAST DISPLAYED ELEMENT - NO FILTERING
                        last_element = None
                        for element in reversed(prose_elements):  # Start from the end
                            if element.is_displayed():
                                text = element.text.strip()
                                if len(text) > 20:  # Minimal length check only
                                    last_element = element
                                    response_text = text
                                    break

                        if last_element is not None:
                            element_index = prose_elements.index(last_element)
                            logger.info(f"🎯 ATTEMPT {retry_count}: SELECTED THE VERY LAST PROSE ELEMENT:")
                            logger.info(f"   Element Index: {element_index + 1} out of {len(prose_elements)}")
                            logger.info(f"   Text Preview: '{response_text[:150]}...'")
                            logger.info(f"   Full Length: {len(response_text)} characters")
                            logger.info(f"🔍 First 30 chars: '{response_text[:30]}'")
                            logger.info(f"🔍 Last 30 chars: '{response_text[-30:]}'")

                            # Check if this is the same as last response
                            if (self.last_response_text and
                                response_text.strip() == self.last_response_text.strip()):
                                logger.warning(f"⚠️ ATTEMPT {retry_count}: Selected response matches previous response!")

                                if retry_count < max_retries:
                                    logger.info(f"🔄 Will retry {max_retries - retry_count} more time(s) to find new response...")
                                    response_text = ""  # Clear to trigger retry
                                    continue
                                else:
                                    logger.warning("⚠️ Max retries reached, using response anyway")

                            # If we got here and have response_text, we found a good response
                            if response_text:
                                logger.info(f"✅ Successfully found response on attempt {retry_count}")
                                break

                        else:
                            logger.warning(f"❌ Attempt {retry_count}: No displayable prose elements found")
                    else:
                        logger.warning(f"❌ Attempt {retry_count}: No prose elements found at all")

                except Exception as e:
                    logger.error(f"Attempt {retry_count} failed: {e}")

                # If no response found and more retries available, continue
                if not response_text and retry_count < max_retries:
                    logger.info(f"🔄 No response found on attempt {retry_count}, trying again...")

            # Final status
            if response_text:
                logger.info(f"✅ FINAL SUCCESS: Found response after {retry_count} attempt(s)")
            else:
                logger.error(f"❌ FINAL FAILURE: No response found after {max_retries} attempts")

            # Final validation and logging
            if response_text:
                logger.info(f"✅ FINAL SELECTED RESPONSE:")
                logger.info(f"✅ Response length: {len(response_text)} characters")
                logger.info(f"✅ First 20 chars: '{response_text[:20]}'")
                logger.info(f"✅ Last 20 chars: '{response_text[-20:]}'")
                logger.info(f"✅ Response preview: {response_text[:150]}...")
                logger.info("✅ This is the ABSOLUTE LAST RESPONSE that will be typed as reply")

                # Debug character analysis
                if response_text and len(response_text) > 0:
                    logger.info(f"🔍 First character: '{response_text[0]}' (ASCII: {ord(response_text[0])})")
                else:
                    logger.error("❌ Response text is empty!")
            else:
                logger.warning("❌ No valid response found - will try fallback")

            # If we still don't have a response, try a more comprehensive fallback
            if not response_text:
                logger.warning("🔄 No response found with primary methods, trying comprehensive fallback...")
                try:
                    # Get all text content and look for the longest reasonable response
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    lines = page_text.split('\n')

                    potential_responses = []
                    for line in lines:
                        line = line.strip()
                        if (30 < len(line) < 500 and
                            not any(skip_word in line.lower() for skip_word in ['ask anything', 'search', 'upgrade', 'sign in']) and
                            not any(prompt_word in line.lower() for prompt_word in ['rules:', 'do not use double', 'content:'])):
                            # Skip if matches last response
                            if not (self.last_response_text and line == self.last_response_text):
                                potential_responses.append(line)

                    if potential_responses:
                        # Take the longest response (usually most complete)
                        response_text = max(potential_responses, key=len)
                        logger.info(f"✅ Found fallback response: {response_text[:100]}...")
                    else:
                        logger.error("❌ No fallback response found")

                except Exception as fallback_e:
                    logger.error(f"Fallback response extraction failed: {fallback_e}")

            # Clean up the response
            if response_text:
                logger.info(f"Raw response length: {len(response_text)}")

                # Remove unwanted characters and patterns
                response_text = re.sub(r'[•\-\*]{2,}', '', response_text)  # Multiple bullets/dashes
                response_text = re.sub(r'\s+', ' ', response_text)         # Extra whitespace
                response_text = re.sub(r'^\d+\.?\s*', '', response_text)   # Leading numbers
                response_text = response_text.strip()

                # No character limit for premium account - keep full response
                logger.info(f"Full response length: {len(response_text)} characters")

                logger.info(f"✅ Cleaned response ({len(response_text)} chars): {response_text[:100]}...")

                # Save this response to detect staleness in future queries
                self.last_response_text = response_text
                self.last_response_time = time.time()

                # Increment chat response counter
                self.current_chat_response_count += 1
                logger.info(f"📊 Chat usage: {self.current_chat_response_count}/{self.perplexity_responses_per_chat} responses")

                return response_text
            else:
                logger.warning("❌ No valid response found from Perplexity")
                return None

        except Exception as e:
            logger.error(f"Error querying Perplexity: {e}")
            return None

    def switch_to_twitter_tab(self) -> bool:
        """Switch back to Twitter tab"""
        try:
            logger.info("Switching back to Twitter tab...")

            # Find the Twitter tab (should be the first one)
            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                current_url = self.driver.current_url
                if 'x.com' in current_url or 'twitter.com' in current_url:
                    logger.info("Successfully switched to Twitter tab")
                    return True

            logger.error("Could not find Twitter tab")
            return False

        except Exception as e:
            logger.error(f"Error switching to Twitter tab: {e}")
            return False

    def refresh_twitter_with_new_tab(self) -> bool:
        """Close and reopen Twitter tab for completely fresh view (no lingering modals/UI states)"""
        try:
            logger.info("🔄 Refreshing Twitter by closing and reopening tab...")

            # First, identify and preserve the Perplexity tab
            perplexity_handle = None
            twitter_handle = None

            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                current_url = self.driver.current_url
                if "perplexity.ai" in current_url:
                    perplexity_handle = handle
                    logger.info("✅ Found and preserved Perplexity tab")
                elif "x.com" in current_url or "twitter.com" in current_url:
                    twitter_handle = handle
                    logger.info("✅ Found Twitter tab to close")

            if not perplexity_handle:
                logger.error("❌ Could not find Perplexity tab - aborting refresh")
                return False

            # Close Twitter tab if found
            if twitter_handle:
                logger.info("🗑️ Closing old Twitter tab...")
                self.driver.switch_to.window(twitter_handle)
                self.driver.close()
                time.sleep(1)

                # Switch back to Perplexity tab temporarily
                self.driver.switch_to.window(perplexity_handle)
                logger.info("✅ Closed old Twitter tab")

            # Open new Twitter tab with fresh state
            logger.info("🆕 Opening fresh Twitter tab...")
            self.driver.execute_script("window.open('https://x.com/home', '_blank');")
            time.sleep(3)

            # Switch to the new Twitter tab
            new_handles = self.driver.window_handles
            for handle in new_handles:
                if handle != perplexity_handle:  # This should be our new Twitter tab
                    self.driver.switch_to.window(handle)
                    current_url = self.driver.current_url
                    if "x.com" in current_url:
                        logger.info("✅ Successfully opened fresh Twitter tab")

                        # Wait for page to fully load
                        logger.info("⏱️ Waiting for fresh Twitter page to load...")
                        time.sleep(5)

                        # Additional check: Close any lingering modals/dialogs just in case
                        try:
                            # Try pressing Escape key to close any modals
                            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                            time.sleep(1)
                            logger.info("✅ Sent Escape key to close any potential modals")
                        except:
                            pass

                        # Scroll to top to ensure we get the latest tweets
                        self.driver.execute_script("window.scrollTo(0, 0);")
                        time.sleep(2)

                        logger.info("✅ Fresh Twitter tab ready - completely clean state!")
                        return True

            logger.error("❌ Could not switch to new Twitter tab")
            return False

        except Exception as e:
            logger.error(f"❌ Error refreshing Twitter with new tab: {e}")
            return False

    def refresh_perplexity_with_new_chat(self) -> bool:
        """Close current Perplexity chat and open fresh homepage for new chat session"""
        try:
            logger.info("🔄 Starting fresh Perplexity chat session...")

            # First, identify and preserve the Twitter tab
            twitter_handle = None
            perplexity_handle = None

            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                current_url = self.driver.current_url
                if "x.com" in current_url or "twitter.com" in current_url:
                    twitter_handle = handle
                    logger.info("✅ Found and preserved Twitter tab")
                elif "perplexity.ai" in current_url:
                    perplexity_handle = handle
                    logger.info("✅ Found Perplexity tab to close")

            if not twitter_handle:
                logger.error("❌ Could not find Twitter tab - aborting Perplexity refresh")
                return False

            # Close Perplexity tab if found
            if perplexity_handle:
                logger.info("🗑️ Closing current Perplexity chat...")
                self.driver.switch_to.window(perplexity_handle)
                self.driver.close()
                time.sleep(1)

                # Switch back to Twitter tab temporarily
                self.driver.switch_to.window(twitter_handle)
                logger.info("✅ Closed current Perplexity chat")

            # Open new Perplexity tab with fresh homepage
            logger.info("🆕 Opening fresh Perplexity homepage...")
            self.driver.execute_script("window.open('https://www.perplexity.ai/', '_blank');")
            time.sleep(3)

            # Switch to the new Perplexity tab
            new_handles = self.driver.window_handles
            for handle in new_handles:
                if handle != twitter_handle:  # This should be our new Perplexity tab
                    self.driver.switch_to.window(handle)
                    current_url = self.driver.current_url
                    if "perplexity.ai" in current_url:
                        logger.info("✅ Successfully opened fresh Perplexity tab")

                        # Wait for page to fully load
                        logger.info("⏱️ Waiting for fresh Perplexity page to load...")
                        time.sleep(5)

                        # Configure GPT-5 Thinking and sources
                        self.select_gpt5_and_sources()

                        # Reset chat response counter
                        self.current_chat_response_count = 0
                        logger.info("🔄 Reset chat response counter to 0")

                        logger.info("✅ Fresh Perplexity chat ready - new session started!")
                        return True

            logger.error("❌ Could not switch to new Perplexity tab")
            return False

        except Exception as e:
            logger.error(f"❌ Error refreshing Perplexity with new chat: {e}")
            return False

    def switch_to_perplexity_tab(self) -> bool:
        """Switch to Perplexity tab for chat session"""
        try:
            logger.info("Switching to Perplexity tab...")

            # Find the Perplexity tab
            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                current_url = self.driver.current_url
                if 'perplexity.ai' in current_url:
                    logger.info("Successfully switched to Perplexity tab")
                    return True

            logger.error("Could not find Perplexity tab")
            return False

        except Exception as e:
            logger.error(f"Error switching to Perplexity tab: {e}")
            return False

    def detect_current_username(self) -> str:
        """Detect the current logged-in username"""
        try:
            logger.info("Detecting current username...")
            
            # Try multiple methods to get the username
            username_selectors = [
                '[data-testid="SideNav_AccountSwitcher_Button"] [data-testid="UserAvatar-Container-unknown"]',
                '[data-testid="SideNav_AccountSwitcher_Button"]',
                '[aria-label="Account menu"]',
                '[data-testid="UserName"]'
            ]
            
            for selector in username_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    # Try to get username from aria-label or other attributes
                    aria_label = element.get_attribute('aria-label')
                    if aria_label and '@' in aria_label:
                        username = aria_label.split('@')[-1].split()[0].lower()
                        logger.info(f"✅ Detected username: @{username}")
                        return username
                except:
                    continue
            
            # Fallback: try to get from URL when clicking profile
            try:
                # Look for profile link in sidebar
                profile_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/"]')
                for link in profile_links:
                    href = link.get_attribute('href')
                    if href and 'x.com/' in href and len(href.split('/')[-1]) > 0:
                        potential_username = href.split('/')[-1].lower()
                        # Basic validation - usernames are alphanumeric + underscore
                        if potential_username.replace('_', '').isalnum() and len(potential_username) > 2:
                            logger.info(f"✅ Detected username from profile link: @{potential_username}")
                            return potential_username
            except:
                pass
                
            logger.warning("Could not detect current username")
            return None
            
        except Exception as e:
            logger.error(f"Error detecting username: {e}")
            return None

    def post_tweet_response(self, original_tweet: Dict[str, str], response_text: str) -> bool:
        """Post response as a new tweet"""
        try:
            logger.info("Posting response as new tweet...")

            # Create contextual tweet
            context_text = f"Responding to @{original_tweet['username']}: {response_text}"

            # No character limit for premium account - keep full response
            logger.info(f"Full context text length: {len(context_text)} characters")

            # Click the compose tweet button
            compose_button = self.wait_for_clickable(By.CSS_SELECTOR, '[data-testid="SideNav_NewTweet_Button"]')
            if not compose_button:
                logger.error("Could not find compose tweet button")
                return False

            compose_button.click()
            time.sleep(2)

            # Find the tweet text area
            text_area = self.wait_for_element(By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]')
            if not text_area:
                logger.error("Could not find tweet text area")
                return False

            # Type the response
            text_area.send_keys(context_text)
            time.sleep(2)

            # Click the tweet button
            tweet_button = self.wait_for_clickable(By.CSS_SELECTOR, '[data-testid="tweetButtonInline"]')
            if not tweet_button:
                logger.error("Could not find tweet button")
                return False

            tweet_button.click()
            time.sleep(3)

            logger.info("Successfully posted tweet response!")
            return True

        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            return False

    def close_perplexity_tab(self):
        """Close the Perplexity tab"""
        try:
            # Close the current tab (should be Perplexity)
            self.driver.close()
            # Switch back to the remaining tab (Twitter)
            if self.driver.window_handles:
                self.driver.switch_to.window(self.driver.window_handles[0])
        except Exception as e:
            logger.warning(f"Error closing Perplexity tab: {e}")

    def prepare_tweet_reply(self, tweet: dict) -> bool:
        """Click on tweet and prepare reply interface before going to Perplexity"""
        try:
            logger.info(f"Preparing reply for tweet from @{tweet['username']}...")
            
            tweet_element = tweet.get('element')
            if not tweet_element:
                logger.error("Tweet element not found")
                return False
            
            # Step 1: Click on the tweet itself to open detailed view (more reliable)
            try:
                logger.info("Clicking on tweet to open detailed view...")
                # Try clicking on different parts of the tweet
                click_targets = [
                    'time',  # Tweet timestamp
                    '[data-testid="tweetText"]',  # Tweet text
                    'article',  # The whole article
                    '.css-175oi2r'  # Twitter's container class
                ]
                
                clicked = False
                for target in click_targets:
                    try:
                        if target == 'time':
                            time_element = tweet_element.find_element(By.TAG_NAME, 'time')
                            time_element.click()
                        else:
                            element = tweet_element.find_element(By.CSS_SELECTOR, target)
                            element.click()
                        clicked = True
                        logger.info(f"✅ Clicked tweet using: {target}")
                        break
                    except:
                        continue
                
                if not clicked:
                    # Fallback: click anywhere on the tweet element
                    self.driver.execute_script("arguments[0].click();", tweet_element)
                    logger.info("✅ Clicked tweet using JavaScript fallback")
                
                time.sleep(3)  # Wait for page to load
                
            except Exception as e:
                logger.warning(f"Could not click tweet: {e}, trying direct reply approach...")
            
            # Step 2: Find and click reply button (should be more accessible now)
            reply_selectors = [
                '[data-testid="reply"]',
                '[aria-label*="Reply"]',
                '[aria-label*="reply"]',
                'button[data-testid="reply"]',
                '[role="button"][aria-label*="Reply"]',
                '[role="button"][aria-label*="reply"]',
                'button[aria-label*="Reply"]',
                'button[aria-label*="reply"]'
            ]
            
            reply_button = None
            for selector in reply_selectors:
                try:
                    reply_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if reply_button.is_displayed() and reply_button.is_enabled():
                        logger.info(f"Found reply button using: {selector}")
                        break
                except:
                    continue
            
            if not reply_button:
                logger.error("Could not find reply button")
                return False
            
            # Step 3: Click reply button with multiple methods
            try:
                # Method 1: Standard click
                reply_button.click()
                logger.info("✅ Clicked reply button")
                time.sleep(2)
            except Exception as e:
                logger.warning(f"Standard click failed: {e}, trying JavaScript...")
                try:
                    # Method 2: JavaScript click
                    self.driver.execute_script("arguments[0].click();", reply_button)
                    logger.info("✅ Clicked reply button with JavaScript")
                    time.sleep(2)
                except Exception as js_e:
                    logger.error(f"Failed to click reply button: {js_e}")
                    return False
            
            # Step 4: Verify reply interface is open
            time.sleep(2)
            compose_selectors = [
                '[data-testid="tweetTextarea_0"]',
                '[data-testid="tweetTextarea"]',
                'div[contenteditable="true"]',
                'textarea[placeholder*="reply"]',
                'textarea[placeholder*="Reply"]'
            ]
            
            compose_found = False
            for selector in compose_selectors:
                try:
                    compose_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if compose_element.is_displayed():
                        logger.info(f"✅ Reply interface ready using: {selector}")
                        compose_found = True
                        break
                except:
                    continue
            
            if not compose_found:
                logger.error("Reply interface not found after clicking reply")
                return False
                
            logger.info("✅ Reply interface prepared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to prepare tweet reply: {e}")
            return False

    def paste_response_to_reply(self, response_text: str) -> bool:
        """Paste the Perplexity response to the prepared reply interface"""
        try:
            logger.info("Pasting response to reply interface...")
            
            # Find the compose area (should already be open)
            compose_selectors = [
                '[data-testid="tweetTextarea_0"]',
                '[data-testid="tweetTextarea"]',
                'div[contenteditable="true"]',
                'textarea[placeholder*="reply"]',
                'textarea[placeholder*="Reply"]'
            ]
            
            compose_element = None
            for selector in compose_selectors:
                try:
                    compose_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if compose_element.is_displayed():
                        logger.info(f"Found compose area using: {selector}")
                        break
                except:
                    continue
            
            if not compose_element:
                logger.error("Could not find compose area")
                return False
            
            # Use realistic typing that mimics human behavior to enable reply button
            try:
                logger.info("Typing response with realistic keyboard simulation...")
                
                # Step 1: Focus and clear the compose area
                compose_element.click()
                time.sleep(0.5)
                
                # Clear existing content
                self.driver.execute_script("""
                    var element = arguments[0];
                    element.focus();
                    
                    // Clear content based on element type
                    if (element.tagName.toLowerCase() === 'div' && element.contentEditable === 'true') {
                        element.textContent = '';
                        element.innerHTML = '';
                    } else {
                        element.value = '';
                    }
                """, compose_element)
                time.sleep(0.3)
                
                # Step 2: Type character by character with realistic timing
                logger.info(f"Typing {len(response_text)} characters...")
                
                for i, char in enumerate(response_text):
                    # Use send_keys for each character (most realistic)
                    compose_element.send_keys(char)
                    
                    # Add realistic typing delays
                    if char == ' ':
                        time.sleep(0.1)  # Longer pause for spaces
                    elif char in '.,!?':
                        time.sleep(0.15)  # Pause for punctuation
                    else:
                        time.sleep(0.05)  # Normal typing speed
                    
                    # Every 10 characters, trigger input events to help enable button
                    if (i + 1) % 10 == 0:
                        self.driver.execute_script("""
                            var element = arguments[0];
                            element.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                            element.dispatchEvent(new Event('keyup', { bubbles: true, cancelable: true }));
                        """, compose_element)
                
                logger.info("✅ Finished typing response")
                time.sleep(1)
                
                # Step 3: Final event triggering to ensure button is enabled
                self.driver.execute_script("""
                    var element = arguments[0];
                    
                    // Trigger comprehensive events like real typing
                    element.focus();
                    element.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                    element.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                    element.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, cancelable: true, key: 'a' }));
                    element.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, cancelable: true, key: 'a' }));
                    
                    // Simulate focus/blur cycle
                    element.blur();
                    setTimeout(function() { 
                        element.focus(); 
                    }, 100);
                """, compose_element)
                
                time.sleep(1)
                
                # Verify content was set
                content_check = self.driver.execute_script("return arguments[0].value || arguments[0].textContent || '';", compose_element)
                logger.info(f"✅ Content verification: {len(content_check)} characters typed")
                
            except Exception as e:
                logger.error(f"Failed to set content: {e}")
                return False
            
            # Find and click the post/reply button
            post_selectors = [
                '[data-testid="tweetButton"]',
                '[data-testid="tweetButtonInline"]',
                'button[data-testid="tweetButton"]',
                'button[data-testid="tweetButtonInline"]',
                '[role="button"][data-testid="tweetButton"]'
            ]
            
            post_button = None
            for selector in post_selectors:
                try:
                    post_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if post_button.is_displayed():
                        logger.info(f"Found post button using: {selector}")
                        break
                except:
                    continue
            
            if not post_button:
                logger.error("Could not find post button")
                return False
            
            # Wait for button to be enabled with better checking
            logger.info("Waiting for reply button to be enabled...")
            max_wait = 10
            button_enabled = False
            
            for i in range(max_wait):
                # Check if button is enabled
                is_enabled = post_button.is_enabled()
                is_disabled_attr = self.driver.execute_script("return arguments[0].disabled;", post_button)
                aria_disabled = self.driver.execute_script("return arguments[0].getAttribute('aria-disabled');", post_button)
                
                logger.info(f"Button check ({i+1}/{max_wait}): enabled={is_enabled}, disabled_attr={is_disabled_attr}, aria_disabled={aria_disabled}")
                
                if is_enabled and not is_disabled_attr and aria_disabled != 'true':
                    button_enabled = True
                    logger.info("✅ Reply button is enabled!")
                    break
                
                # If not enabled, try triggering more events
                if i < max_wait - 1:  # Don't trigger on last iteration
                    logger.info("Button not enabled, triggering more input events...")
                    self.driver.execute_script("""
                        var textArea = document.querySelector('[data-testid="tweetTextarea_0"]') || 
                                      document.querySelector('div[contenteditable="true"]');
                        if (textArea) {
                            textArea.focus();
                            
                            // Simulate more realistic typing events
                            textArea.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: 'a', keyCode: 65 }));
                            textArea.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                            textArea.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: 'a', keyCode: 65 }));
                            
                            // Force validation
                            textArea.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    """)
                
                time.sleep(1)
            
            if not button_enabled:
                logger.warning("⚠️ Reply button still not enabled after waiting, trying to click anyway...")
            
            try:
                # Click the button
                post_button.click()
                logger.info("✅ Clicked reply button")
                time.sleep(3)
                
                # Check for success indicators
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                    success_indicators = ["your reply was sent", "reply sent", "posted"]
                    
                    for indicator in success_indicators:
                        if indicator in page_text:
                            logger.info(f"✅ Success indicator found: '{indicator}'")
                            return True
                    
                    # Also check if we're back to timeline (indicates success)
                    current_url = self.driver.current_url
                    if 'status' not in current_url:  # Not on individual tweet page anymore
                        logger.info("✅ Returned to timeline - reply likely successful")
                        return True
                    
                    logger.info("✅ Reply appears successful (no error indicators)")
                    return True
                    
                except Exception as e:
                    logger.warning(f"Could not verify success: {e}")
                    return True  # Assume success if we can't verify
                    
            except Exception as e:
                logger.error(f"Failed to click reply button: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to paste response: {e}")
            return False

    def reply_to_tweet(self, tweet: dict, response_text: str) -> bool:
        """Reply to a specific tweet with the response using new workflow"""
        try:
            logger.info(f"Using new reply workflow for tweet from @{tweet['username']}...")
            return self.paste_response_to_reply(response_text)
        except Exception as e:
            logger.error(f"Error in reply workflow: {e}")
            return False

    def run(self):
        """Main execution loop"""
        logger.info("Starting Selenium Twitter Agent...")

        # Setup driver
        if not self.setup_driver():
            return

        try:
            # Navigate to Twitter and login
            if not self.navigate_to_twitter():
                return
            
            # Detect current username to avoid replying to our own tweets
            self.current_username = self.detect_current_username()
            
            logger.info("Starting one-by-one tweet processing...")
            
            # Open Perplexity ONCE at the beginning for chat session
            logger.info("Opening Perplexity.ai in new tab for chat session...")
            if not self.navigate_to_perplexity():
                logger.error("✗ Failed to navigate to Perplexity - cannot continue")
                return
            logger.info("✅ Perplexity chat session ready")
            
            processed_count = 0
            tweet_num = 0
            no_tweets_count = 0
            
            logger.info("🔄 Starting infinite tweet processing loop...")
            
            while True:  # Run forever
                tweet_num += 1
                logger.info(f"\n--- Looking for tweet {tweet_num} (processed: {processed_count}) ---")
                logger.info(f"📊 Current Perplexity chat: {self.current_chat_response_count}/{self.perplexity_responses_per_chat} responses used")

                # Extract a single tweet
                tweet = self.extract_single_tweet()
                if not tweet:
                    no_tweets_count += 1
                    logger.warning(f"No tweets found (attempt {no_tweets_count}/3)")
                    
                    if no_tweets_count >= 3:
                        logger.info("🔄 No tweets found after 3 attempts - refreshing with fresh Twitter tab...")

                        # Close and reopen Twitter tab for completely fresh state
                        if self.refresh_twitter_with_new_tab():
                            # Scroll down to load more tweets
                            logger.info("Scrolling to load more tweets...")
                            for i in range(3):
                                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                time.sleep(2)

                            no_tweets_count = 0  # Reset counter
                            logger.info("✅ Twitter refreshed with fresh tab - continuing search...")
                            continue
                        else:
                            logger.error("Could not refresh Twitter with fresh tab")
                            time.sleep(10)  # Wait before retrying
                            continue
                    else:
                        # Try scrolling before giving up
                        logger.info("Scrolling to load more tweets...")
                        try:
                            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(3)
                        except:
                            pass
                        continue
                
                # Reset no tweets counter when we find a tweet
                no_tweets_count = 0
                
                logger.info(f"Tweet content: {tweet['content'][:100]}...")
                
                # IMPROVED WORKFLOW: Use existing Perplexity chat session
                logger.info("Switching to Perplexity tab for chat...")
                if not self.switch_to_perplexity_tab():
                    logger.error(f"✗ Failed to switch to Perplexity for tweet {tweet_num}")
                    continue
                
                response = self.query_perplexity(tweet['content'])
                if not response:
                    logger.error(f"✗ Failed to get response for tweet {tweet_num}")
                    logger.info("🔄 Closing and reopening Perplexity with fresh chat session...")

                    # Close and reopen Perplexity tab for complete reset
                    try:
                        if self.refresh_perplexity_with_new_chat():
                            logger.info("✅ Successfully closed and reopened Perplexity with fresh chat")

                            # Switch to the fresh Perplexity tab
                            if self.switch_to_perplexity_tab():
                                logger.info("🔄 Retrying query with fresh Perplexity session...")

                                # Retry the query once with fresh Perplexity
                                response = self.query_perplexity(tweet['content'])
                                if response:
                                    logger.info("✅ Successfully got response after Perplexity refresh")
                                else:
                                    logger.error(f"✗ Failed to get response even after fresh Perplexity session for tweet {tweet_num}")
                                    continue
                            else:
                                logger.error("✗ Failed to switch to fresh Perplexity tab")
                                continue
                        else:
                            logger.error("✗ Failed to refresh Perplexity with new chat")
                            continue
                    except Exception as e:
                        logger.error(f"✗ Failed to refresh Perplexity: {e}")
                        continue

                # Only continue if we have a valid response
                if not response:
                    continue
                
                # Switch back to Twitter tab
                logger.info("Switching back to Twitter tab...")
                if not self.switch_to_twitter_tab():
                    logger.error(f"✗ Failed to switch back to Twitter for tweet {tweet_num}")
                    continue
                
                # Then prepare reply interface
                if not self.prepare_tweet_reply(tweet):
                    logger.error(f"✗ Failed to prepare reply for tweet {tweet_num}")
                    continue
                
                # Finally, type the RESPONSE (not prompt) to enable reply button
                if self.reply_to_tweet(tweet, response):
                    logger.info(f"✓ Successfully replied to tweet {tweet_num}")
                    processed_count += 1
                    
                    # Go back to Twitter home with completely fresh tab
                    logger.info("🏠 Going back to Twitter home with fresh tab...")
                    try:
                        # Close and reopen Twitter tab for completely fresh state
                        if self.refresh_twitter_with_new_tab():
                            logger.info("✅ Twitter home refreshed with completely fresh tab")
                        else:
                            logger.warning("Could not refresh Twitter with fresh tab, trying fallback...")
                            # Fallback to regular navigation if fresh tab fails
                            if self.switch_to_twitter_tab():
                                self.driver.get("https://x.com/home")
                                time.sleep(5)
                                self.driver.execute_script("window.scrollTo(0, 0);")
                                time.sleep(2)
                                logger.info("✅ Used fallback navigation to Twitter home")
                            else:
                                logger.warning("Could not switch to Twitter tab for home navigation")
                    except Exception as e:
                        logger.warning(f"Error navigating to Twitter home: {e}")
                        
                else:
                    logger.error(f"✗ Failed to reply to tweet {tweet_num}")
                
                # Keep Perplexity tab open for next tweet (chat session)
                
                # Save processed tweets periodically (every 5 tweets)
                if processed_count % 5 == 0:
                    logger.info("💾 Saving processed tweets...")
                    self._save_processed_tweets()
                
                # Wait between tweets
                wait_time = 0
                logger.info(f"Waiting {wait_time} seconds before next tweet...")
                time.sleep(wait_time)
            
        except KeyboardInterrupt:
            logger.info("\n🛑 Process interrupted by user")
            logger.info(f"📊 Final stats: {processed_count} tweets processed")
            # Save processed tweets before closing
            logger.info("💾 Saving processed tweets...")
            self._save_processed_tweets()
            # Close Perplexity tab on interruption
            self.close_perplexity_tab()
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            logger.info(f"📊 Final stats: {processed_count} tweets processed")
            # Save processed tweets before closing
            self._save_processed_tweets()
            # Close Perplexity tab on error
            self.close_perplexity_tab()
        finally:
            logger.info("Browser will remain open for inspection. Close manually when done.")
            try:
                input("Press Enter to close browser...")
                self.driver.quit()
            except:
                pass


def main():
    agent = SeleniumTwitterAgent()
    agent.run()


if __name__ == "__main__":
    main()

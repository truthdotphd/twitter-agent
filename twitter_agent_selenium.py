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

# Import AI service modules
from perplexity_service import PerplexityService
from chatgpt_service import ChatGPTService
from gemini_service import GeminiService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SeleniumTwitterAgent:
    def __init__(self):
        self.base_prompt = """
        You are a funny commentator.
        # Rules for your response
        0) don't start your response with "here is a twist", or "here is a fun twist", etc.
        1) keep your response LESS than 400 characters Less than 5 sentences. 
        2) avoid double dashes -- AND avoid double hyphens AND avoid colons : AND avoid semicolons ;
        3) avoid double stars **
        4) avoid references and citations
        5) avoid math formulas. 
        6) Do NOT ask me anything further, and only output the response
        7) start the response with a complete sentence
        8) don't start the response with numbers. 
        9) instead of using double or single dash/hyphen (-- or -) use semicolon comma colon (; , :)
        10) keep the language and style similar to humans not AI
        11) do not cite any reference in your response
        12) make the style, format, and wording of your response different from the previous responses in the chat.
        13) make sure the language is close to a typical human 
        14) sometimes use questions to make an engaging post
        15) keep it short strictly less than 400 characters and 5 sentences.
        16) write in full sentences.
        17) don't add ANY sources or references or citations
        18) keep the language engaging and fun
        19) YOUR RESPONSE MUST BE LESS THAN 400 CHARACTERS and LESS than 5 sentences!!
        20) I DON'T WANT TO SEE ANY REFERNCES or SOURCES or CITED LINKS IN YOUR RESPONSE!!

        Write a short fact-based impactful, entertaining, fun and amusing response teaching a fresh, complementary insight about the following text in a human-like entertaining language: 
        # Content to write the response about:

        '{tweet_content}'

        STRICT rules:
        1) DON'T WANT TO SEE ANY REFERNCES or SOURCES or CITED LINKS IN YOUR RESPONSE!! JUST WORDS WITH NO LINKS!
        2) YOUR RESPONSES ARE LENGHTY! Your response MUST be LESS than 5 sentences AND LESS than 400 english characters!! 
        3) you are still showing links to refeernces in your response, DON'T DO IT! I don't want to see the references in your response. just a plaintext without references.
        """
        # Configuration from environment
        self.ai_service = os.getenv('AI_SERVICE', 'perplexity').lower()
        self.delay_between_tweets = int(os.getenv('DELAY_BETWEEN_TWEETS', 5))
        self.max_tweets_per_session = int(os.getenv('MAX_TWEETS_PER_SESSION', 5))
        self.ai_wait_time = int(os.getenv('AI_WAIT_TIME', 60))
        self.ai_responses_per_chat = max(1, int(os.getenv('AI_RESPONSES_PER_CHAT', 2)))
        self.headless = os.getenv('HEADLESS', 'false').lower() == 'true'
        self.debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        self.feed_type = os.getenv('TWITTER_FEED_TYPE', 'following').lower()
        
        # Validation and retry configuration
        self.min_response_length = int(os.getenv('MIN_RESPONSE_LENGTH', 20))
        self.min_tweet_length = int(os.getenv('MIN_TWEET_LENGTH', 30))
        self.min_unique_word_ratio = float(os.getenv('MIN_UNIQUE_WORD_RATIO', 0.3))
        self.min_words_for_repetition_check = int(os.getenv('MIN_WORDS_FOR_REPETITION_CHECK', 3))
        self.max_ai_retries = int(os.getenv('MAX_AI_RETRIES', 3))
        self.max_extraction_attempts = int(os.getenv('MAX_EXTRACTION_ATTEMPTS', 5))
        self.no_tweets_threshold = int(os.getenv('NO_TWEETS_THRESHOLD', 3))
        self.scroll_attempts = int(os.getenv('SCROLL_ATTEMPTS', 3))
        self.save_frequency = int(os.getenv('SAVE_FREQUENCY', 5))
        self.button_wait_timeout = int(os.getenv('BUTTON_WAIT_TIMEOUT', 10))
        self.retry_wait_time = int(os.getenv('RETRY_WAIT_TIME', 2))
        
        # File and directory configuration
        self.processed_tweets_filename = os.getenv('PROCESSED_TWEETS_FILE', 'processed_tweets.json')
        self.chrome_profile_dir = os.getenv('CHROME_PROFILE_DIR', '.chrome_automation_profile_twitter')

        # Configure debug logging
        if self.debug_mode:
            logger.setLevel(logging.DEBUG)
            logger.info("🐛 Debug mode enabled - verbose logging activated")
        else:
            logger.setLevel(logging.INFO)

        # Log configuration summary
        logger.info(f"⚙️ Twitter Agent Configuration:")
        logger.info(f"   🤖 AI Service: {self.ai_service.upper()}")
        logger.info(f"   📱 Tweet delay: {self.delay_between_tweets}s")
        logger.info(f"   🎯 Max tweets per session: {self.max_tweets_per_session}")
        logger.info(f"   ⏱️ AI wait time: {self.ai_wait_time}s")
        logger.info(f"   💬 Responses per chat: {self.ai_responses_per_chat}")
        logger.info(f"   👻 Headless mode: {self.headless}")
        logger.info(f"   📺 Twitter feed: {self.feed_type.title()}")
        
        if self.debug_mode:
            logger.debug(f"⚙️ Advanced Configuration:")
            logger.debug(f"   📏 Min response length: {self.min_response_length} chars")
            logger.debug(f"   📏 Min tweet length: {self.min_tweet_length} chars")
            logger.debug(f"   🔄 Max AI retries: {self.max_ai_retries}")
            logger.debug(f"   🔄 Max extraction attempts: {self.max_extraction_attempts}")
            logger.debug(f"   💾 Save frequency: every {self.save_frequency} tweets")
            logger.debug(f"   📁 Processed tweets file: {self.processed_tweets_filename}")
            logger.debug(f"   📁 Chrome profile dir: {self.chrome_profile_dir}")

        self.driver = None
        self.ai_service_instance = None

        # Persistent tweet tracking
        self.processed_tweets_file = Path(self.processed_tweets_filename)
        self.processed_tweets = self._load_processed_tweets()
        self.current_username = None  # Will be detected after login

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
    
    def _is_error_response(self, response_text: str) -> bool:
        """Check if AI response contains error messages or invalid content"""
        if not response_text or len(response_text.strip()) < self.min_response_length:
            logger.warning(f"⚠️ Response too short or empty (min: {self.min_response_length} chars)")
            return True
        
        response_lower = response_text.lower().strip()
        
        # Common error patterns from AI assistants
        error_patterns = [
            "something went wrong",
            "an error occurred",
            "error occurred",
            "try again",
            "please try again",
            "sorry, i couldn't",
            "sorry, i can't",
            "i apologize",
            "i'm sorry",
            "unable to process",
            "unable to complete",
            "request failed",
            "connection error",
            "timeout error",
            "network error",
            "service unavailable",
            "temporarily unavailable",
            "please refresh",
            "please reload",
            "internal error",
            "system error",
            "technical difficulty",
            "experiencing issues",
            "something's not right",
            "oops",
            "whoops",
            "failed to load",
            "failed to generate",
            "could not generate",
            "unable to generate",
            "error generating",
            "error processing",
            "rate limit",
            "quota exceeded",
            "too many requests"
        ]
        
        # Check for error patterns
        for pattern in error_patterns:
            if pattern in response_lower:
                logger.warning(f"⚠️ Detected error pattern: '{pattern}' in response")
                return True
        
        # Check if response is just error codes or numbers
        if response_text.strip().isdigit():
            logger.warning("⚠️ Response appears to be just numbers")
            return True
        
        # Check if response is suspiciously repetitive (same word repeated)
        words = response_text.split()
        if len(words) > self.min_words_for_repetition_check and len(set(words)) < len(words) * self.min_unique_word_ratio:
            logger.warning(f"⚠️ Response appears to be repetitive (unique words ratio: {len(set(words))/len(words):.2f}, threshold: {self.min_unique_word_ratio})")
            return True
        
        logger.debug(f"✅ Response validation passed")
        return False

    def setup_driver(self):
        """Set up Chrome driver with undetected_chromedriver for better reliability"""
        logger.info("Setting up Undetected Chrome driver...")

        # Configure undetected_chromedriver options
        chrome_options = uc.ChromeOptions()

        if self.headless:
            chrome_options.add_argument("--headless=new")

        # ALWAYS use a separate Chrome profile for automation (avoids conflicts)
        # This ensures login persistence across sessions
        # Matching the working pattern from stock_analyzer.py
        automation_profile_dir = Path.home() / self.chrome_profile_dir
        automation_profile_dir.mkdir(exist_ok=True)
        user_data_dir = str(automation_profile_dir)
        
        logger.info(f"📁 Using persistent Chrome profile: {user_data_dir}")
        
        # Use a specific profile directory for this session
        profile_directory = os.getenv('CHROME_PROFILE_DIRECTORY', 'TwitterAgent')
        
        # Check if profile exists and has data (indicates previous login)
        profile_path = automation_profile_dir / profile_directory
        profile_exists = profile_path.exists() and (profile_path / "Preferences").exists()
        if profile_exists:
            logger.info("✅ Found existing profile - logins should be remembered")
        else:
            logger.info("ℹ️  First time: You'll need to log into X.com and AI service manually")
            logger.info("ℹ️  After that: Logins will be remembered!")
        
        # IMPORTANT: Pass both user-data-dir AND profile-directory as arguments
        # This matches the working pattern from stock_analyzer.py
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        chrome_options.add_argument(f"--profile-directory={profile_directory}")

        # Additional options for stability and profile persistence
        # Matching stock_analyzer.py pattern
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--no-sandbox")
        
        # Configure preferences for login persistence
        # Note: Keep credentials ENABLED (unlike stock_analyzer) for login persistence
        chrome_options.add_experimental_option("prefs", {
            "credentials_enable_service": True,  # KEEP TRUE for login persistence
            "profile.password_manager_enabled": True,  # KEEP TRUE for login persistence
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
            # IMPORTANT: user_data_dir is passed through chrome_options (matching stock_analyzer.py pattern)
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
            
            # Additional anti-detection measure (from stock_analyzer.py)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
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

    def setup_ai_service(self) -> bool:
        """Set up AI service instance"""
        try:
            logger.info(f"Setting up {self.ai_service.upper()} service...")
            
            if self.ai_service == 'chatgpt':
                self.ai_service_instance = ChatGPTService(
                    self.driver,
                    self.ai_wait_time,
                    self.debug_mode,
                    self.ai_responses_per_chat
                )
            elif self.ai_service == 'gemini':
                self.ai_service_instance = GeminiService(
                    self.driver,
                    self.ai_wait_time,
                    self.debug_mode,
                    self.ai_responses_per_chat
                )
            else:  # Default to perplexity
                self.ai_service_instance = PerplexityService(
                    self.driver,
                    self.ai_wait_time,
                    self.debug_mode,
                    self.ai_responses_per_chat
                )
            
            logger.info(f"✅ {self.ai_service.upper()} service initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize AI service: {e}")
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

            while len(tweets) < self.max_tweets_per_session and attempts < self.max_extraction_attempts:
                attempts += 1
                logger.info(f"Extraction attempt {attempts}/{self.max_extraction_attempts}")

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

                            # Skip if too short or already processed
                            tweet_hash = self._get_tweet_hash(tweet_text)
                            if len(tweet_text) < self.min_tweet_length or tweet_hash in self.processed_tweets:
                                logger.debug(f"Skipping tweet: length={len(tweet_text)} (min {self.min_tweet_length} chars), already_processed={tweet_hash in self.processed_tweets}")
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

                    # Skip if too short or already processed
                    tweet_hash = self._get_tweet_hash(tweet_text)
                    if len(tweet_text) < self.min_tweet_length or tweet_hash in self.processed_tweets:
                        logger.debug(f"Skipping tweet: length={len(tweet_text)} (min {self.min_tweet_length} chars), already_processed={tweet_hash in self.processed_tweets}")
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

            # First, identify and preserve the AI service tab
            ai_service_handle = None
            twitter_handle = None

            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                current_url = self.driver.current_url
                # Check for any AI service URL
                if any(service in current_url.lower() for service in ['perplexity.ai', 'chatgpt.com', 'chat.openai.com', 'gemini.google.com']):
                    ai_service_handle = handle
                    logger.info(f"✅ Found and preserved {self.ai_service.upper()} tab")
                elif "x.com" in current_url or "twitter.com" in current_url:
                    twitter_handle = handle
                    logger.info("✅ Found Twitter tab to close")

            if not ai_service_handle:
                logger.error(f"❌ Could not find {self.ai_service.upper()} tab - aborting refresh")
                return False

            # Close Twitter tab if found
            if twitter_handle:
                logger.info("🗑️ Closing old Twitter tab...")
                self.driver.switch_to.window(twitter_handle)
                self.driver.close()
                time.sleep(1)

                # Switch back to AI service tab temporarily
                self.driver.switch_to.window(ai_service_handle)
                logger.info("✅ Closed old Twitter tab")

            # Open new Twitter tab with fresh state
            logger.info("🆕 Opening fresh Twitter tab...")
            self.driver.execute_script("window.open('https://x.com/home', '_blank');")
            time.sleep(3)

            # Switch to the new Twitter tab
            new_handles = self.driver.window_handles
            for handle in new_handles:
                if handle != ai_service_handle:  # This should be our new Twitter tab
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

    def prepare_tweet_reply(self, tweet: dict) -> bool:
        """Click on tweet and prepare reply interface before querying AI service"""
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
        """Paste the AI service response to the prepared reply interface"""
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

                # Step 0: Dismiss any overlays/modals/dropdowns that might block clicks
                logger.info("Dismissing any overlays, modals, or dropdowns...")
                try:
                    # Method 1: Press ESC key to dismiss any modals/dropdowns
                    self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    time.sleep(0.5)
                    logger.info("✅ Pressed ESC to dismiss overlays")
                except:
                    pass

                try:
                    # Method 2: Click outside the compose area to dismiss dropdowns
                    self.driver.execute_script("document.body.click();")
                    time.sleep(0.3)
                    logger.info("✅ Clicked body to dismiss dropdowns")
                except:
                    pass

                try:
                    # Method 3: Remove autocomplete/typeahead dropdowns via JavaScript
                    self.driver.execute_script("""
                        var dropdowns = document.querySelectorAll('[id*="typeahead"], [id*="dropdown"], [role="listbox"]');
                        dropdowns.forEach(function(dropdown) {
                            if (dropdown && dropdown.style) {
                                dropdown.style.display = 'none';
                            }
                        });
                    """)
                    logger.info("✅ Hid autocomplete dropdowns")
                except:
                    pass

                # Step 1: Focus and clear the compose area
                logger.info("Focusing compose area...")

                # Scroll element into view first
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", compose_element)
                    time.sleep(0.5)
                    logger.info("✅ Scrolled element into view")
                except:
                    pass

                # Try multiple click methods to handle overlay issues
                clicked = False

                # Method 1: Standard click
                try:
                    compose_element.click()
                    clicked = True
                    logger.info("✅ Clicked compose area (standard)")
                except Exception as click_err:
                    logger.warning(f"Standard click failed: {click_err}")

                # Method 2: JavaScript click if standard failed
                if not clicked:
                    try:
                        self.driver.execute_script("arguments[0].click();", compose_element)
                        clicked = True
                        logger.info("✅ Clicked compose area (JavaScript)")
                    except Exception as js_click_err:
                        logger.warning(f"JavaScript click failed: {js_click_err}")

                # Method 3: Focus via JavaScript if clicks failed
                if not clicked:
                    try:
                        self.driver.execute_script("arguments[0].focus();", compose_element)
                        clicked = True
                        logger.info("✅ Focused compose area (JavaScript focus)")
                    except Exception as focus_err:
                        logger.warning(f"JavaScript focus failed: {focus_err}")

                if not clicked:
                    logger.error("❌ Could not click or focus compose area")
                    return False

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
            button_enabled = False
            
            for i in range(self.button_wait_timeout):
                # Check if button is enabled
                is_enabled = post_button.is_enabled()
                is_disabled_attr = self.driver.execute_script("return arguments[0].disabled;", post_button)
                aria_disabled = self.driver.execute_script("return arguments[0].getAttribute('aria-disabled');", post_button)
                
                logger.info(f"Button check ({i+1}/{self.button_wait_timeout}): enabled={is_enabled}, disabled_attr={is_disabled_attr}, aria_disabled={aria_disabled}")
                
                if is_enabled and not is_disabled_attr and aria_disabled != 'true':
                    button_enabled = True
                    logger.info("✅ Reply button is enabled!")
                    break
                
                # If not enabled, try triggering more events
                if i < self.button_wait_timeout - 1:  # Don't trigger on last iteration
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
            
            # Setup AI service
            if not self.setup_ai_service():
                logger.error("✗ Failed to setup AI service - cannot continue")
                return
            
            logger.info("Starting one-by-one tweet processing...")
            
            # Open AI service ONCE at the beginning for chat session
            logger.info(f"Opening {self.ai_service.upper()} in new tab for chat session...")
            if not self.ai_service_instance.navigate_new_tab():
                logger.error(f"✗ Failed to navigate to {self.ai_service.upper()} - cannot continue")
                return
            logger.info(f"✅ {self.ai_service.upper()} chat session ready")
            
            processed_count = 0
            tweet_num = 0
            no_tweets_count = 0
            
            logger.info("🔄 Starting infinite tweet processing loop...")
            
            while True:  # Run forever
                tweet_num += 1
                logger.info(f"\n--- Looking for tweet {tweet_num} (processed: {processed_count}) ---")
                logger.info(f"📊 Current {self.ai_service.upper()} chat: {self.ai_service_instance.current_chat_response_count}/{self.ai_responses_per_chat} responses used")

                # Extract a single tweet
                tweet = self.extract_single_tweet()
                if not tweet:
                    no_tweets_count += 1
                    logger.warning(f"No tweets found (attempt {no_tweets_count}/{self.no_tweets_threshold})")
                    
                    if no_tweets_count >= self.no_tweets_threshold:
                        logger.info(f"🔄 No tweets found after {self.no_tweets_threshold} attempts - refreshing with fresh Twitter tab...")

                        # Close and reopen Twitter tab for completely fresh state
                        if self.refresh_twitter_with_new_tab():
                            # Scroll down to load more tweets
                            logger.info("Scrolling to load more tweets...")
                            for i in range(self.scroll_attempts):
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
                
                # IMPROVED WORKFLOW: Use existing AI chat session
                logger.info(f"Switching to {self.ai_service.upper()} tab for chat...")
                if not self.ai_service_instance.switch_to_tab():
                    logger.error(f"✗ Failed to switch to {self.ai_service.upper()} for tweet {tweet_num}")
                    continue
                
                # Format prompt with base_prompt template
                prompt = self.base_prompt.format(tweet_content=tweet['content'])
                
                # Try to get a valid response with retry logic
                response = None
                retry_count = 0
                
                while retry_count < self.max_ai_retries:
                    if retry_count > 0:
                        logger.info(f"🔄 Retry attempt {retry_count}/{self.max_ai_retries-1} for tweet {tweet_num}")
                    
                    # Query AI service
                    raw_response = self.ai_service_instance.query(prompt)
                    
                    # Check if response is valid (not an error message)
                    if raw_response and not self._is_error_response(raw_response):
                        response = raw_response
                        logger.info(f"✅ Got valid response from {self.ai_service.upper()}")
                        break
                    elif raw_response:
                        logger.warning(f"❌ Response contains error message, retrying... (attempt {retry_count + 1}/{self.max_ai_retries})")
                        logger.debug(f"Error response preview: {raw_response[:100]}...")
                    else:
                        logger.warning(f"❌ No response received, retrying... (attempt {retry_count + 1}/{self.max_ai_retries})")
                    
                    retry_count += 1
                    
                    # If not the last retry, refresh AI service
                    if retry_count < self.max_ai_retries:
                        logger.info(f"🔄 Refreshing {self.ai_service.upper()} before retry...")
                        try:
                            if self.ai_service_instance.refresh():
                                logger.info(f"✅ Successfully refreshed {self.ai_service.upper()}")
                                # Switch to the fresh AI service tab
                                if not self.ai_service_instance.switch_to_tab():
                                    logger.error(f"✗ Failed to switch to fresh {self.ai_service.upper()} tab")
                                    break
                            else:
                                logger.error(f"✗ Failed to refresh {self.ai_service.upper()}")
                                break
                        except Exception as e:
                            logger.error(f"✗ Failed to refresh {self.ai_service.upper()}: {e}")
                            break
                        time.sleep(self.retry_wait_time)  # Brief pause before retry
                
                # Check if we got a valid response after all retries
                if not response:
                    logger.error(f"✗ Failed to get valid response after {self.max_ai_retries} attempts for tweet {tweet_num}")
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
                
                # Keep AI service tab open for next tweet (chat session)
                
                # Save processed tweets periodically
                if processed_count % self.save_frequency == 0:
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
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            logger.info(f"📊 Final stats: {processed_count} tweets processed")
            # Save processed tweets before closing
            self._save_processed_tweets()
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

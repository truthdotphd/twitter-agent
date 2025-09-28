#!/usr/bin/env python3
"""
Advanced Twitter Agent Browser - More robust tweet processing with Perplexity.ai
"""

import asyncio
import os
import time
import re
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any, Set
from dotenv import load_dotenv
from browser_use import Agent, Controller
from browser_use.browser.browser import Browser, BrowserConfig
import logging
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedTwitterAgent:
    def __init__(self):
        self.base_prompt = """Rules: Do NOT use double hyphens, do NOT use double dashes, do NOT use double stars at all! Do not include citations or references. Write a detailed, impactful response to the following that teaches something new and contrary to the status-quo views:

Content:
{tweet_content}

I repeat the most important rule: Do NOT use double hyphens, do NOT use double dashes, do NOT use double stars at all!"""

        # Configuration from environment
        self.delay_between_tweets = int(os.getenv('DELAY_BETWEEN_TWEETS', 30))
        self.max_tweets_per_session = int(os.getenv('MAX_TWEETS_PER_SESSION', 5))
        self.perplexity_wait_time = int(os.getenv('PERPLEXITY_WAIT_TIME', 60))
        self.headless = os.getenv('HEADLESS', 'false').lower() == 'true'

        self.browser_config = BrowserConfig(
            headless=self.headless,
            keep_open=True,
            disable_web_security=False,
            extra_chromium_args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-sandbox",
            ]
        )

        # Persistent tweet tracking
        self.processed_tweets_file = Path("processed_tweets.json")
        self.processed_tweets = self._load_processed_tweets()  # Track processed tweets to avoid duplicates

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

    async def initialize_browser(self) -> Browser:
        """Initialize browser with proper configuration"""
        logger.info("Initializing browser...")
        browser = Browser(config=self.browser_config)
        await browser.start()
        return browser

    async def wait_for_element(self, controller: Controller, selector: str, timeout: int = 10) -> bool:
        """Wait for an element to appear"""
        for _ in range(timeout):
            try:
                html = await controller.get_html()
                soup = BeautifulSoup(html, 'html.parser')
                if soup.select(selector):
                    return True
            except:
                pass
            await asyncio.sleep(1)
        return False

    async def navigate_to_twitter(self, controller: Controller) -> bool:
        """Navigate to Twitter and ensure we're logged in"""
        try:
            logger.info("Navigating to X.com...")
            await controller.navigate("https://x.com")
            await asyncio.sleep(5)

            # Wait for page to load
            html = await controller.get_html()

            # Check if we're logged in by looking for specific elements
            if 'data-testid="SideNav_AccountSwitcher_Button"' in html or 'data-testid="AppTabBar_Home_Link"' in html:
                logger.info("Successfully logged in to X.com")
                return True
            elif 'Sign in' in html or 'Log in' in html:
                logger.warning("Not logged in to X.com. Please log in manually and restart the script.")
                input("Press Enter after logging in...")
                return await self.navigate_to_twitter(controller)
            else:
                logger.info("Login status unclear, proceeding...")
                return True

        except Exception as e:
            logger.error(f"Error navigating to X.com: {e}")
            return False

    async def extract_tweets_from_timeline(self, controller: Controller) -> List[Dict[str, Any]]:
        """Extract tweets from the For You timeline using more sophisticated methods"""
        try:
            logger.info("Extracting tweets from timeline...")

            # Make sure we're on the home timeline
            try:
                await controller.click('[data-testid="AppTabBar_Home_Link"]')
                await asyncio.sleep(3)
            except:
                pass

            tweets = []
            attempts = 0
            max_attempts = 5

            while len(tweets) < self.max_tweets_per_session and attempts < max_attempts:
                attempts += 1
                logger.info(f"Extraction attempt {attempts}/{max_attempts}")

                # Get current page HTML
                html = await controller.get_html()
                soup = BeautifulSoup(html, 'html.parser')

                # Find tweet articles
                tweet_articles = soup.find_all('article', {'data-testid': 'tweet'})

                logger.info(f"Found {len(tweet_articles)} tweet articles")

                for article in tweet_articles:
                    try:
                        # Extract tweet text
                        tweet_text_elem = article.find('div', {'data-testid': 'tweetText'})
                        if not tweet_text_elem:
                            continue

                        tweet_text = tweet_text_elem.get_text(separator=' ', strip=True)

                        # Skip if too short (minimum 30 characters) or already processed
                        tweet_hash = self._get_tweet_hash(tweet_text)
                        if len(tweet_text) < 30 or tweet_hash in self.processed_tweets:
                            logger.debug(f"Skipping tweet: length={len(tweet_text)}, already_processed={tweet_hash in self.processed_tweets}")
                            continue

                        # Extract tweet ID from the article
                        tweet_id = None
                        links = article.find_all('a')
                        for link in links:
                            href = link.get('href', '')
                            if '/status/' in href:
                                tweet_id = href.split('/status/')[-1].split('?')[0]
                                break

                        if not tweet_id:
                            tweet_id = f"tweet_{len(tweets)}_{int(time.time())}"

                        # Extract username
                        username = "unknown"
                        user_link = article.find('a', href=lambda x: x and '/' in x and '/status/' not in x)
                        if user_link:
                            username = user_link.get('href', '/unknown').split('/')[-1]

                        tweet_data = {
                            'id': tweet_id,
                            'content': tweet_text,
                            'username': username,
                            'article_element': None  # We'll locate this when needed
                        }

                        tweets.append(tweet_data)
                        self.processed_tweets.add(tweet_hash)

                        logger.info(f"Extracted tweet {len(tweets)}: {tweet_text[:100]}...")

                        if len(tweets) >= self.max_tweets_per_session:
                            break

                    except Exception as e:
                        logger.warning(f"Error extracting individual tweet: {e}")
                        continue

                # If we haven't collected enough tweets, scroll down
                if len(tweets) < self.max_tweets_per_session:
                    logger.info("Scrolling down to load more tweets...")
                    await controller.scroll(direction="down", amount=3)
                    await asyncio.sleep(3)

            logger.info(f"Successfully extracted {len(tweets)} tweets")
            return tweets

        except Exception as e:
            logger.error(f"Error extracting tweets: {e}")
            return []

    async def navigate_to_perplexity(self, controller: Controller) -> bool:
        """Navigate to Perplexity.ai"""
        try:
            logger.info("Opening new tab for Perplexity.ai...")

            # Open new tab
            await controller.key("cmd+t")
            await asyncio.sleep(1)

            await controller.navigate("https://perplexity.ai")
            await asyncio.sleep(5)

            # Wait for the input field to be available
            if await self.wait_for_element(controller, 'textarea', timeout=10):
                logger.info("Successfully navigated to Perplexity.ai")
                return True
            else:
                logger.error("Perplexity.ai input field not found")
                return False

        except Exception as e:
            logger.error(f"Error navigating to Perplexity.ai: {e}")
            return False

    async def query_perplexity(self, controller: Controller, tweet_content: str) -> Optional[str]:
        """Submit query to Perplexity and get response"""
        try:
            logger.info("Querying Perplexity...")

            # Format the prompt with tweet content
            prompt = self.base_prompt.format(tweet_content=tweet_content[:500])  # Limit length

            # Clear any existing content in the textarea
            await controller.click("textarea")
            await asyncio.sleep(1)
            await controller.key("cmd+a")
            await asyncio.sleep(0.5)

            # Type our prompt
            await controller.type(prompt)
            await asyncio.sleep(2)

            # Submit the query
            await controller.key("Enter")

            # Wait for response to be generated
            logger.info(f"Waiting {self.perplexity_wait_time} seconds for Perplexity response...")

            # Wait and check for response indicators
            await asyncio.sleep(self.perplexity_wait_time)

            # Get the response
            html = await controller.get_html()
            soup = BeautifulSoup(html, 'html.parser')

            # Look for response content (Perplexity usually shows responses in specific divs)
            response_text = ""

            # Try multiple selectors to find the response
            response_selectors = [
                'div[data-testid="response"]',
                'div.prose',
                'div.answer',
                'div.response',
                '.bg-white p',
                'div p'
            ]

            for selector in response_selectors:
                response_elements = soup.select(selector)
                for elem in response_elements:
                    text = elem.get_text(separator=' ', strip=True)
                    if len(text) > 50 and len(text) < 500:  # Reasonable response length
                        response_text = text
                        break
                if response_text:
                    break

            # If no structured response found, try to extract from page text
            if not response_text:
                page_text = await controller.get_text()
                lines = page_text.split('\n')
                potential_responses = []

                for line in lines:
                    line = line.strip()
                    if (len(line) > 50 and len(line) < 400 and
                        not line.startswith('Ask') and
                        not line.startswith('Search') and
                        not line.startswith('Pro') and
                        not any(x in line.lower() for x in ['cookie', 'privacy', 'terms', 'sign up', 'log in'])):
                        potential_responses.append(line)

                if potential_responses:
                    response_text = potential_responses[0]

            # Clean up the response
            if response_text:
                # Remove unwanted characters and patterns
                response_text = re.sub(r'[•\-\*]{2,}', '', response_text)  # Remove multiple bullets/dashes
                response_text = re.sub(r'\s+', ' ', response_text)  # Clean whitespace
                response_text = response_text.strip()

                # Ensure it's under 280 characters
                if len(response_text) > 280:
                    response_text = response_text[:277] + "..."

                logger.info(f"Received response from Perplexity: {response_text[:100]}...")
                return response_text
            else:
                logger.warning("No valid response found from Perplexity")
                return None

        except Exception as e:
            logger.error(f"Error querying Perplexity: {e}")
            return None

    async def switch_to_twitter_tab(self, controller: Controller) -> bool:
        """Switch back to Twitter tab"""
        try:
            logger.info("Switching back to Twitter tab...")

            # Switch to previous tab (Twitter should be the first tab)
            await controller.key("cmd+shift+[")  # Previous tab on Mac
            await asyncio.sleep(2)

            # Verify we're on Twitter
            current_url = await controller.get_url()
            if 'x.com' in current_url or 'twitter.com' in current_url:
                logger.info("Successfully switched to Twitter tab")
                return True
            else:
                # Try switching tabs until we find Twitter
                for _ in range(5):
                    await controller.key("cmd+shift+[")
                    await asyncio.sleep(1)
                    current_url = await controller.get_url()
                    if 'x.com' in current_url or 'twitter.com' in current_url:
                        return True

                logger.error("Could not find Twitter tab")
                return False

        except Exception as e:
            logger.error(f"Error switching to Twitter tab: {e}")
            return False

    async def find_and_reply_to_tweet(self, controller: Controller, tweet_data: Dict[str, Any], response_text: str) -> bool:
        """Find specific tweet and reply to it"""
        try:
            logger.info(f"Looking for tweet to reply to: {tweet_data['content'][:50]}...")

            # Search for the tweet content on the page
            html = await controller.get_html()

            # If we can find the specific tweet, click its reply button
            soup = BeautifulSoup(html, 'html.parser')
            tweet_articles = soup.find_all('article', {'data-testid': 'tweet'})

            for article in tweet_articles:
                tweet_text_elem = article.find('div', {'data-testid': 'tweetText'})
                if tweet_text_elem:
                    tweet_text = tweet_text_elem.get_text(separator=' ', strip=True)

                    # Check if this matches our target tweet (partial match)
                    if self._is_similar_tweet(tweet_text, tweet_data['content']):
                        logger.info("Found matching tweet, attempting to reply...")

                        # Find reply button within this article
                        reply_button = article.find('button', {'data-testid': 'reply'})
                        if reply_button:
                            # We need to click using coordinates or a more specific selector
                            # For now, we'll use a general approach
                            try:
                                await controller.click('[data-testid="reply"]')
                                await asyncio.sleep(2)

                                # Type the response
                                await controller.type(response_text)
                                await asyncio.sleep(2)

                                # Send the reply
                                await controller.click('[data-testid="tweetButtonInline"]')
                                await asyncio.sleep(3)

                                logger.info("Successfully posted reply!")
                                return True

                            except Exception as e:
                                logger.warning(f"Failed to reply to specific tweet: {e}")
                                break

            # If we couldn't find the specific tweet or reply to it, post as new tweet
            logger.info("Could not find specific tweet, posting as new tweet instead...")
            return await self.post_as_new_tweet(controller, response_text, tweet_data)

        except Exception as e:
            logger.error(f"Error finding and replying to tweet: {e}")
            return False

    def _is_similar_tweet(self, text1: str, text2: str) -> bool:
        """Check if two tweet texts are similar (accounting for truncation, etc.)"""
        # Simple similarity check
        text1_clean = re.sub(r'\s+', ' ', text1.lower().strip())
        text2_clean = re.sub(r'\s+', ' ', text2.lower().strip())

        # Check if one is contained in the other or they share significant words
        if text1_clean in text2_clean or text2_clean in text1_clean:
            return True

        # Check word overlap
        words1 = set(text1_clean.split())
        words2 = set(text2_clean.split())

        if len(words1) > 0 and len(words2) > 0:
            overlap = len(words1.intersection(words2))
            overlap_ratio = overlap / min(len(words1), len(words2))
            return overlap_ratio > 0.7

        return False

    async def post_as_new_tweet(self, controller: Controller, response_text: str, original_tweet: Dict[str, Any]) -> bool:
        """Post response as a new tweet with context"""
        try:
            logger.info("Posting as new tweet...")

            # Create a contextual tweet
            context_text = f"Responding to @{original_tweet['username']}: {response_text}"

            # Ensure it's under 280 characters
            if len(context_text) > 280:
                available_chars = 280 - len(f"Responding to @{original_tweet['username']}: ")
                response_text = response_text[:available_chars-3] + "..."
                context_text = f"Responding to @{original_tweet['username']}: {response_text}"

            # Click compose button
            await controller.click('[data-testid="SideNav_NewTweet_Button"]')
            await asyncio.sleep(2)

            # Type the tweet
            await controller.type(context_text)
            await asyncio.sleep(2)

            # Post the tweet
            await controller.click('[data-testid="tweetButtonInline"]')
            await asyncio.sleep(3)

            logger.info("Successfully posted new tweet with context!")
            return True

        except Exception as e:
            logger.error(f"Error posting new tweet: {e}")
            return False

    async def run(self):
        """Main execution loop"""
        logger.info("Starting Advanced Twitter Agent...")

        browser = await self.initialize_browser()
        controller = Controller(browser=browser)

        try:
            # Navigate to Twitter
            if not await self.navigate_to_twitter(controller):
                logger.error("Failed to navigate to Twitter or not logged in")
                return

            # Extract tweets
            tweets = await self.extract_tweets_from_timeline(controller)
            if not tweets:
                logger.error("No tweets extracted")
                return

            logger.info(f"Processing {len(tweets)} tweets...")

            # Process each tweet
            for i, tweet in enumerate(tweets):
                logger.info(f"\n--- Processing tweet {i+1}/{len(tweets)} ---")
                logger.info(f"Tweet content: {tweet['content'][:100]}...")

                # Navigate to Perplexity in new tab
                if not await self.navigate_to_perplexity(controller):
                    logger.error("Failed to navigate to Perplexity")
                    continue

                # Query Perplexity
                response = await self.query_perplexity(controller, tweet['content'])
                if not response:
                    logger.error("Failed to get response from Perplexity")
                    # Close Perplexity tab and continue
                    await controller.key("cmd+w")
                    continue

                # Switch back to Twitter tab
                if not await self.switch_to_twitter_tab(controller):
                    logger.error("Failed to switch back to Twitter")
                    continue

                # Post reply or new tweet
                success = await self.find_and_reply_to_tweet(controller, tweet, response)
                if success:
                    logger.info(f"✓ Successfully processed tweet {i+1}")
                else:
                    logger.error(f"✗ Failed to post response for tweet {i+1}")

                # Close Perplexity tab
                await controller.key("cmd+shift+]")  # Switch to Perplexity tab
                await asyncio.sleep(1)
                await controller.key("cmd+w")  # Close tab
                await asyncio.sleep(1)

                # Wait between tweets to avoid rate limiting
                if i < len(tweets) - 1:
                    logger.info(f"Waiting {self.delay_between_tweets} seconds before next tweet...")
                    await asyncio.sleep(self.delay_between_tweets)

            logger.info("\n🎉 Completed processing all tweets!")
            
            # Save processed tweets to file
            self._save_processed_tweets()

        except Exception as e:
            logger.error(f"Error in main execution: {e}")

        finally:
            logger.info("Browser will remain open for inspection. Close manually when done.")
            input("Press Enter to close browser...")
            await browser.close()

async def main():
    """Entry point"""
    agent = AdvancedTwitterAgent()
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Twitter Agent Browser - Automated tweet processing with Perplexity.ai
"""

import asyncio
import os
import time
import re
from typing import List, Dict, Optional
from dotenv import load_dotenv
from browser_use import Agent, Controller
from browser_use.browser.browser import Browser, BrowserConfig
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TwitterAgent:
    def __init__(self):
        self.base_prompt = """Rules: Do NOT use double hyphens, do NOT use double dashes, do NOT use double stars at all! Do not include citations or references. Write a detailed, impactful response to the following that teaches something new and contrary to the status-quo views:
Content:
{tweet_content}.

I repeat the most important rule: Do NOT use double hyphens, do NOT use double dashes, do NOT use double stars at all!"""

        # Configuration from environment
        self.delay_between_tweets = int(os.getenv('DELAY_BETWEEN_TWEETS', 30))
        self.max_tweets_per_session = int(os.getenv('MAX_TWEETS_PER_SESSION', 10))
        self.perplexity_wait_time = int(os.getenv('PERPLEXITY_WAIT_TIME', 60))
        self.headless = os.getenv('HEADLESS', 'false').lower() == 'true'

        self.browser_config = BrowserConfig(
            headless=self.headless,
            keep_open=True,  # Keep browser open to maintain sessions
            disable_web_security=False,
        )

    async def initialize_browser(self) -> Browser:
        """Initialize browser with proper configuration"""
        logger.info("Initializing browser...")
        browser = Browser(config=self.browser_config)
        await browser.start()
        return browser

    async def navigate_to_twitter(self, controller: Controller) -> bool:
        """Navigate to Twitter and ensure we're logged in"""
        try:
            logger.info("Navigating to X.com...")
            await controller.navigate("https://x.com")
            await asyncio.sleep(3)

            # Check if we're logged in by looking for the compose button or timeline
            page_content = await controller.get_text()
            if "Sign in" in page_content or "Log in" in page_content:
                logger.warning("Not logged in to X.com. Please log in manually.")
                return False

            logger.info("Successfully navigated to X.com")
            return True

        except Exception as e:
            logger.error(f"Error navigating to X.com: {e}")
            return False

    async def extract_tweets(self, controller: Controller) -> List[Dict[str, str]]:
        """Extract tweets from the For You timeline"""
        try:
            logger.info("Extracting tweets from timeline...")

            # Wait for timeline to load
            await asyncio.sleep(5)

            # Get tweets from the timeline
            # We'll use a more specific approach to find tweet elements
            tweets = []

            # Scroll to ensure we have fresh tweets
            await controller.scroll(direction="down", amount=3)
            await asyncio.sleep(2)

            # Look for tweet articles (tweets are in article elements on X.com)
            page_source = await controller.get_html()

            # Simple approach: extract text content and try to identify tweets
            # This is a basic implementation - in a real scenario, you'd want more robust parsing
            text_content = await controller.get_text()

            # Split content and look for tweet-like patterns
            lines = text_content.split('\n')
            current_tweet = ""
            tweet_count = 0

            for i, line in enumerate(lines):
                # Skip empty lines and navigation elements
                if not line.strip() or line.strip() in ['Home', 'Explore', 'Notifications', 'Messages', 'Lists', 'Bookmarks', 'Profile']:
                    continue

                # Look for tweet content (this is a simplified approach) - minimum 30 characters
                if len(line.strip()) > 30 and not line.startswith('@') and not line.endswith('h') and not line.isdigit():
                    # This might be tweet content - minimum 30 characters
                    if current_tweet and len(current_tweet) > 30:
                        tweets.append({
                            'content': current_tweet.strip(),
                            'id': f"tweet_{tweet_count}"
                        })
                        tweet_count += 1
                        if tweet_count >= self.max_tweets_per_session:
                            break
                    current_tweet = line.strip()
                elif current_tweet:
                    # Continue building the current tweet
                    current_tweet += " " + line.strip()

            # Add the last tweet if it exists
            if current_tweet and len(current_tweet) > 50 and tweet_count < self.max_tweets_per_session:
                tweets.append({
                    'content': current_tweet.strip(),
                    'id': f"tweet_{tweet_count}"
                })

            logger.info(f"Extracted {len(tweets)} tweets")
            return tweets[:self.max_tweets_per_session]

        except Exception as e:
            logger.error(f"Error extracting tweets: {e}")
            return []

    async def navigate_to_perplexity(self, controller: Controller) -> bool:
        """Navigate to Perplexity.ai"""
        try:
            logger.info("Navigating to Perplexity.ai...")
            await controller.navigate("https://perplexity.ai")
            await asyncio.sleep(3)

            # Check if we're on the right page
            page_content = await controller.get_text()
            if "Perplexity" in page_content:
                logger.info("Successfully navigated to Perplexity.ai")
                return True
            else:
                logger.error("Failed to navigate to Perplexity.ai")
                return False

        except Exception as e:
            logger.error(f"Error navigating to Perplexity.ai: {e}")
            return False

    async def query_perplexity(self, controller: Controller, tweet_content: str) -> Optional[str]:
        """Submit query to Perplexity and get response"""
        try:
            logger.info("Querying Perplexity...")

            # Format the prompt with tweet content
            prompt = self.base_prompt.format(tweet_content=tweet_content)

            # Find the input field and submit the query
            # Look for textarea or input field
            await controller.click("textarea")  # Perplexity uses a textarea
            await asyncio.sleep(1)

            # Clear any existing content and type our prompt
            await controller.key("cmd+a")  # Select all
            await controller.type(prompt)
            await asyncio.sleep(2)

            # Submit the query (usually Enter key)
            await controller.key("Enter")

            # Wait for response
            logger.info(f"Waiting {self.perplexity_wait_time} seconds for Perplexity response...")
            await asyncio.sleep(self.perplexity_wait_time)

            # Get the response
            page_content = await controller.get_text()

            # Extract the response (this is simplified - you might need to parse the DOM better)
            # Look for the answer section
            lines = page_content.split('\n')
            response_lines = []
            found_answer = False

            for line in lines:
                if found_answer and line.strip() and len(line.strip()) > 10:
                    response_lines.append(line.strip())
                    if len(' '.join(response_lines)) > 200:  # Get enough content
                        break
                elif "answer" in line.lower() or (len(line.strip()) > 50 and not line.startswith("Ask") and not line.startswith("Search")):
                    found_answer = True
                    response_lines.append(line.strip())

            response = ' '.join(response_lines)

            # Clean up the response
            response = re.sub(r'\s+', ' ', response)  # Remove extra whitespace
            response = response.strip()

            # Ensure it's under 280 characters
            if len(response) > 280:
                response = response[:277] + "..."

            logger.info(f"Received response from Perplexity: {response[:100]}...")
            return response

        except Exception as e:
            logger.error(f"Error querying Perplexity: {e}")
            return None

    async def navigate_back_to_twitter(self, controller: Controller) -> bool:
        """Navigate back to Twitter"""
        try:
            logger.info("Navigating back to X.com...")
            await controller.navigate("https://x.com")
            await asyncio.sleep(3)
            return True
        except Exception as e:
            logger.error(f"Error navigating back to X.com: {e}")
            return False

    async def post_reply(self, controller: Controller, tweet_id: str, response_text: str) -> bool:
        """Post a reply to a specific tweet"""
        try:
            logger.info(f"Posting reply to tweet {tweet_id}...")

            # This is a simplified approach - in reality, you'd need to:
            # 1. Find the specific tweet
            # 2. Click the reply button
            # 3. Type the response
            # 4. Submit the reply

            # For now, we'll just compose a new tweet with the response
            # Look for the compose button
            await controller.click("[data-testid='SideNav_NewTweet_Button']")
            await asyncio.sleep(2)

            # Type the response
            await controller.type(response_text)
            await asyncio.sleep(2)

            # Post the tweet
            await controller.click("[data-testid='tweetButtonInline']")
            await asyncio.sleep(3)

            logger.info("Successfully posted reply")
            return True

        except Exception as e:
            logger.error(f"Error posting reply: {e}")
            return False

    async def run(self):
        """Main execution loop"""
        logger.info("Starting Twitter Agent...")

        browser = await self.initialize_browser()
        controller = Controller(browser=browser)

        try:
            # Navigate to Twitter
            if not await self.navigate_to_twitter(controller):
                logger.error("Failed to navigate to Twitter or not logged in")
                return

            # Extract tweets
            tweets = await self.extract_tweets(controller)
            if not tweets:
                logger.error("No tweets extracted")
                return

            # Process each tweet
            for i, tweet in enumerate(tweets):
                logger.info(f"Processing tweet {i+1}/{len(tweets)}")

                # Navigate to Perplexity
                if not await self.navigate_to_perplexity(controller):
                    logger.error("Failed to navigate to Perplexity")
                    continue

                # Query Perplexity
                response = await self.query_perplexity(controller, tweet['content'])
                if not response:
                    logger.error("Failed to get response from Perplexity")
                    continue

                # Navigate back to Twitter
                if not await self.navigate_back_to_twitter(controller):
                    logger.error("Failed to navigate back to Twitter")
                    continue

                # Post reply
                if not await self.post_reply(controller, tweet['id'], response):
                    logger.error("Failed to post reply")
                    continue

                # Wait between tweets to avoid rate limiting
                if i < len(tweets) - 1:
                    logger.info(f"Waiting {self.delay_between_tweets} seconds before next tweet...")
                    await asyncio.sleep(self.delay_between_tweets)

            logger.info("Completed processing all tweets")

        except Exception as e:
            logger.error(f"Error in main execution: {e}")

        finally:
            # Keep browser open for user to see results
            logger.info("Browser will remain open. Close manually when done.")
            input("Press Enter to close browser...")
            await browser.close()

async def main():
    """Entry point"""
    agent = TwitterAgent()
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
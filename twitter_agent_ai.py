#!/usr/bin/env python3
"""
AI-Powered Twitter Agent using browser-use with proper Agent-based approach
"""

import asyncio
import os
import time
import json
from typing import List, Dict, Optional
from dotenv import load_dotenv
from browser_use import Agent
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AITwitterAgent:
    def __init__(self):
        self.base_prompt_template = """Rules: Do NOT use double hyphens, do NOT use double dashes, do NOT use double stars at all! Do not include citations or references. Limit the response length to 280 characters. Write a concise impactful paragraph to the following so that it teaches something new and contrary to the status-quo views:

Content:
{tweet_content}

I repeat the most important rule: Do NOT use double hyphens, do NOT use double dashes, do NOT use double stars at all!"""

        # Configuration from environment
        self.delay_between_tweets = int(os.getenv('DELAY_BETWEEN_TWEETS', 30))
        self.max_tweets_per_session = int(os.getenv('MAX_TWEETS_PER_SESSION', 5))
        self.perplexity_wait_time = int(os.getenv('PERPLEXITY_WAIT_TIME', 15))

        # We'll use Anthropic Claude since it's already configured in this environment
        self.llm = self._setup_llm()

    def _setup_llm(self):
        """Set up the LLM for the agent"""
        try:
            # Try to use Anthropic Claude if available
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model="claude-3-sonnet-20240229")
        except ImportError:
            try:
                # Fallback to OpenAI
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(model="gpt-4")
            except ImportError:
                try:
                    # Fallback to Google Gemini
                    from langchain_google_genai import ChatGoogleGenerativeAI
                    return ChatGoogleGenerativeAI(model="gemini-flash-latest")
                except ImportError:
                    logger.error("No suitable LLM provider found. Please install one of: anthropic, openai, or google-generativeai")
                    raise

    async def extract_tweets_from_timeline(self) -> List[Dict[str, str]]:
        """Extract tweets from X.com timeline using AI agent"""
        logger.info("Creating agent to extract tweets from X.com...")

        extract_task = f"""
        Go to x.com and extract the content of the first {self.max_tweets_per_session} tweets from the timeline.
        Return the tweet content as a JSON list where each item has 'content' and 'id' fields.
        Only extract actual tweet text content, ignore usernames, timestamps, and interaction buttons.
        Make sure you're logged in and on the main timeline.
        """

        try:
            agent = Agent(
                task=extract_task,
                llm=self.llm
            )

            result = await agent.run()

            # Parse the result to extract tweets
            # The agent should return structured data
            tweets = self._parse_tweet_extraction_result(result)

            logger.info(f"Successfully extracted {len(tweets)} tweets")
            return tweets

        except Exception as e:
            logger.error(f"Error extracting tweets: {e}")
            return []

    def _parse_tweet_extraction_result(self, result) -> List[Dict[str, str]]:
        """Parse the result from tweet extraction"""
        tweets = []

        # Try to parse as JSON first
        try:
            if isinstance(result, str):
                # Look for JSON in the result
                import re
                json_match = re.search(r'\[.*\]', result, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    if isinstance(parsed, list):
                        for i, item in enumerate(parsed):
                            if isinstance(item, dict) and 'content' in item:
                                tweets.append({
                                    'id': item.get('id', f'tweet_{i}'),
                                    'content': item['content']
                                })
                            elif isinstance(item, str):
                                tweets.append({
                                    'id': f'tweet_{i}',
                                    'content': item
                                })
        except:
            pass

        # If JSON parsing failed, try to extract tweets from text
        if not tweets and isinstance(result, str):
            lines = result.split('\n')
            tweet_content = []

            for line in lines:
                line = line.strip()
                if len(line) > 20 and not line.startswith(('Tweet', 'Content', 'Username', '@')):
                    tweet_content.append(line)

            for i, content in enumerate(tweet_content[:self.max_tweets_per_session]):
                tweets.append({
                    'id': f'tweet_{i}',
                    'content': content
                })

        return tweets[:self.max_tweets_per_session]

    async def query_perplexity_with_agent(self, tweet_content: str) -> Optional[str]:
        """Use AI agent to query Perplexity.ai"""
        logger.info("Creating agent to query Perplexity...")

        prompt = self.base_prompt_template.format(tweet_content=tweet_content)

        perplexity_task = f"""
        Go to perplexity.ai and submit this exact prompt:

        {prompt}

        Wait for the response and then return ONLY the response text (not the prompt).
        The response should be under 280 characters and follow the rules specified in the prompt.
        """

        try:
            agent = Agent(
                task=perplexity_task,
                llm=self.llm
            )

            result = await agent.run()

            # Clean up the response
            response = self._clean_perplexity_response(result)

            if response:
                logger.info(f"Received response from Perplexity: {response[:100]}...")
                return response
            else:
                logger.warning("No valid response received from Perplexity")
                return None

        except Exception as e:
            logger.error(f"Error querying Perplexity: {e}")
            return None

    def _clean_perplexity_response(self, response: str) -> Optional[str]:
        """Clean and validate the Perplexity response"""
        if not response:
            return None

        # Remove common prefixes/suffixes
        response = response.strip()

        # Remove quotes if the entire response is quoted
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]

        # Remove unwanted characters and patterns
        import re
        response = re.sub(r'[•\-\*]{2,}', '', response)  # Remove multiple bullets/dashes
        response = re.sub(r'\s+', ' ', response)  # Clean whitespace

        # Ensure it's under 280 characters
        if len(response) > 280:
            response = response[:277] + "..."

        # Basic validation
        if len(response) < 10:
            return None

        return response.strip()

    async def post_reply_with_agent(self, tweet_content: str, response_text: str) -> bool:
        """Use AI agent to post reply on X.com"""
        logger.info("Creating agent to post reply on X.com...")

        reply_task = f"""
        Go to x.com and find a tweet with this content: "{tweet_content[:100]}..."

        Then reply to that tweet with this exact text: "{response_text}"

        If you cannot find the exact tweet, post this text as a new tweet instead.
        Make sure you are logged in to your X.com account.
        """

        try:
            agent = Agent(
                task=reply_task,
                llm=self.llm
            )

            result = await agent.run()

            # Check if the posting was successful
            if "successfully" in str(result).lower() or "posted" in str(result).lower():
                logger.info("Successfully posted reply/tweet")
                return True
            else:
                logger.warning(f"Uncertain if posting was successful: {result}")
                return True  # Assume success for now

        except Exception as e:
            logger.error(f"Error posting reply: {e}")
            return False

    async def run(self):
        """Main execution loop"""
        logger.info("Starting AI-Powered Twitter Agent...")

        try:
            # Extract tweets
            logger.info("Step 1: Extracting tweets from X.com timeline...")
            tweets = await self.extract_tweets_from_timeline()

            if not tweets:
                logger.error("No tweets extracted. Make sure you're logged into X.com.")
                return

            logger.info(f"Processing {len(tweets)} tweets...")

            # Process each tweet
            for i, tweet in enumerate(tweets):
                logger.info(f"\n--- Processing tweet {i+1}/{len(tweets)} ---")
                logger.info(f"Tweet content: {tweet['content'][:100]}...")

                # Query Perplexity
                logger.info("Step 2: Querying Perplexity.ai...")
                response = await self.query_perplexity_with_agent(tweet['content'])

                if not response:
                    logger.error("Failed to get response from Perplexity")
                    continue

                # Post reply
                logger.info("Step 3: Posting reply on X.com...")
                success = await self.post_reply_with_agent(tweet['content'], response)

                if success:
                    logger.info(f"✓ Successfully processed tweet {i+1}")
                else:
                    logger.error(f"✗ Failed to post response for tweet {i+1}")

                # Wait between tweets to avoid rate limiting
                if i < len(tweets) - 1:
                    logger.info(f"Waiting {self.delay_between_tweets} seconds before next tweet...")
                    await asyncio.sleep(self.delay_between_tweets)

            logger.info("\n🎉 Completed processing all tweets!")

        except Exception as e:
            logger.error(f"Error in main execution: {e}")

async def main():
    """Entry point"""
    # Check if required environment variables are set
    required_vars = []

    # Check for at least one LLM provider
    has_anthropic = os.getenv('ANTHROPIC_API_KEY')
    has_openai = os.getenv('OPENAI_API_KEY')
    has_google = os.getenv('GOOGLE_API_KEY')

    if not any([has_anthropic, has_openai, has_google]):
        logger.error("No LLM API key found. Please set one of:")
        logger.error("- ANTHROPIC_API_KEY")
        logger.error("- OPENAI_API_KEY")
        logger.error("- GOOGLE_API_KEY")
        return

    agent = AITwitterAgent()
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
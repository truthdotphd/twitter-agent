"""Main service orchestrator for the X.com Auto-Reply Service."""

import uuid
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..models import Config, ProcessingResult, ProcessedTweet, Tweet
from ..config import load_config, validate_config
from ..api.twitter_client import TwitterClient
from ..api.perplexity_client import PerplexityClient
from ..core.tweet_selector import TweetSelector
from ..core.reply_generator import ReplyGenerator
from ..utils.rate_limiter import RateLimiter
from ..utils.logging import (
    get_logger, setup_logging, log_processing_summary, 
    log_tweet_processing, ContextLogger, MetricsLogger
)


class XReplyService:
    """Main service orchestrator for automated tweet replies."""
    
    def __init__(self, config: Optional[Config] = None, dry_run: bool = False):
        """Initialize the X Reply Service.
        
        Args:
            config: Service configuration (loads from file if None)
            dry_run: If True, don't actually post replies
        """
        # Load configuration
        self.config = config or load_config()
        self.dry_run = dry_run or self.config.app.dry_run
        
        # Setup logging
        setup_logging(self.config.app.log_level, self.config.app.log_dir)
        self.logger = get_logger("x_reply_service")
        
        # Initialize components
        self.rate_limiter = RateLimiter(
            twitter_read_limit=self.config.rate_limits.twitter_read_per_15min,
            twitter_write_limit=self.config.rate_limits.twitter_write_per_15min,
            perplexity_limit=self.config.rate_limits.perplexity_per_hour
        )
        
        # Initialize API clients
        self.twitter_client = TwitterClient(
            bearer_token=self.config.api.twitter_bearer_token,
            api_key=self.config.api.twitter_api_key,
            api_secret=self.config.api.twitter_api_secret,
            access_token=self.config.api.twitter_access_token,
            access_token_secret=self.config.api.twitter_access_token_secret,
            rate_limiter=self.rate_limiter
        )
        
        self.perplexity_client = PerplexityClient(
            api_key=self.config.api.perplexity_api_key,
            rate_limiter=self.rate_limiter
        )
        
        # Initialize core components
        self.tweet_selector = TweetSelector(self.config.selection)
        self.reply_generator = ReplyGenerator(self.perplexity_client, self.config.reply)
        
        # State management
        self.data_dir = Path(self.config.app.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.processed_tweets_file = self.data_dir / "processed_tweets.jsonl"
        self.state_file = self.data_dir / "state.json"
        
        self.logger.info("X Reply Service initialized",
                        dry_run=self.dry_run,
                        max_tweets=self.config.selection.max_tweets_per_run)
    
    def run(self) -> ProcessingResult:
        """Run a complete processing cycle.
        
        Returns:
            Processing result with statistics and errors
        """
        run_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()
        
        with ContextLogger(self.logger, run_id=run_id) as logger:
            logger.info("Starting processing run")
            
            result = ProcessingResult(
                run_id=run_id,
                start_time=start_time
            )
            
            try:
                # Validate configuration
                config_errors = validate_config()
                if config_errors:
                    result.errors.extend(config_errors)
                    logger.error("Configuration validation failed", errors=config_errors)
                    return self._finalize_result(result)
                
                # Verify API credentials
                if not self._verify_credentials():
                    result.errors.append("API credential verification failed")
                    return self._finalize_result(result)
                
                # Fetch tweets
                tweets = self._fetch_tweets()
                result.tweets_fetched = len(tweets)
                logger.info("Tweets fetched", count=len(tweets))
                
                if not tweets:
                    logger.warning("No tweets fetched")
                    return self._finalize_result(result)
                
                # Select tweets
                selected_tweets = self._select_tweets(tweets)
                result.tweets_processed = len(selected_tweets)
                logger.info("Tweets selected", count=len(selected_tweets))
                
                if not selected_tweets:
                    logger.warning("No tweets selected")
                    return self._finalize_result(result)
                
                # Generate and post replies
                for tweet in selected_tweets:
                    try:
                        # Generate reply
                        reply = self._generate_reply(tweet)
                        if reply:
                            tweet.generated_reply = reply
                            result.replies_generated += 1
                            
                            # Post reply (unless dry run)
                            if not self.dry_run:
                                reply_id = self._post_reply(tweet, reply)
                                if reply_id:
                                    tweet.reply_posted = True
                                    tweet.reply_id = reply_id
                                    result.replies_posted += 1
                            else:
                                # In dry run, simulate successful posting
                                tweet.reply_posted = True
                                tweet.reply_id = f"dry_run_{uuid.uuid4().hex[:8]}"
                                result.replies_posted += 1
                                logger.info("Dry run - reply would be posted",
                                          tweet_id=tweet.id,
                                          reply=reply)
                        
                        result.processed_tweets.append(tweet)
                        
                    except Exception as e:
                        error_msg = f"Failed to process tweet {tweet.id}: {str(e)}"
                        result.errors.append(error_msg)
                        logger.error("Tweet processing failed", 
                                   tweet_id=tweet.id, error=str(e))
                        
                        tweet.error_message = str(e)
                        result.processed_tweets.append(tweet)
                
                # Save processing results
                self._save_processing_results(result)
                
                logger.info("Processing run completed successfully")
                
            except Exception as e:
                error_msg = f"Processing run failed: {str(e)}"
                result.errors.append(error_msg)
                logger.error("Processing run failed", error=str(e))
            
            finally:
                result = self._finalize_result(result)
                
                # Log summary
                log_processing_summary(
                    logger, run_id, result.tweets_fetched, result.tweets_processed,
                    result.replies_generated, result.replies_posted,
                    result.duration_seconds or 0, result.errors
                )
                
                return result
    
    def _verify_credentials(self) -> bool:
        """Verify API credentials for all services.
        
        Returns:
            True if all credentials are valid, False otherwise
        """
        try:
            self.logger.info("Verifying API credentials")
            
            # Verify Twitter credentials
            if not self.twitter_client.verify_credentials():
                self.logger.error("Twitter credential verification failed")
                return False
            
            # Verify Perplexity credentials
            if not self.perplexity_client.verify_credentials():
                self.logger.error("Perplexity credential verification failed")
                return False
            
            self.logger.info("All API credentials verified successfully")
            return True
            
        except Exception as e:
            self.logger.error("Credential verification failed", error=str(e))
            return False
    
    def _fetch_tweets(self) -> List[Tweet]:
        """Fetch tweets from Twitter API.
        
        Returns:
            List of fetched tweets
        """
        try:
            self.logger.info("Fetching tweets from Twitter")
            
            # Try to get home timeline first (closer to "For You" feed)
            try:
                tweets = self.twitter_client.get_home_timeline(
                    max_results=min(100, self.config.selection.max_tweets_per_run * 10)
                )
            except Exception as e:
                self.logger.warning("Failed to get home timeline, falling back to user timeline", 
                                  error=str(e))
                # Fallback to user timeline
                tweets = self.twitter_client.get_user_timeline(
                    max_results=min(100, self.config.selection.max_tweets_per_run * 10),
                    exclude_replies=self.config.selection.exclude_replies,
                    exclude_retweets=self.config.selection.exclude_retweets
                )
            
            # Filter out tweets we've already processed recently
            tweets = self._filter_recently_processed(tweets)
            
            self.logger.info("Tweets fetched successfully", count=len(tweets))
            return tweets
            
        except Exception as e:
            self.logger.error("Failed to fetch tweets", error=str(e))
            return []
    
    def _select_tweets(self, tweets: List[Tweet]) -> List[ProcessedTweet]:
        """Select the best tweets to reply to.
        
        Args:
            tweets: List of candidate tweets
            
        Returns:
            List of selected tweets
        """
        try:
            self.logger.info("Selecting tweets", candidate_count=len(tweets))
            
            selected_tweets = self.tweet_selector.select_tweets(tweets)
            
            # Log selection statistics
            stats = self.tweet_selector.get_selection_stats(tweets)
            self.logger.info("Tweet selection stats", **stats)
            
            return selected_tweets
            
        except Exception as e:
            self.logger.error("Tweet selection failed", error=str(e))
            return []
    
    def _generate_reply(self, tweet: ProcessedTweet) -> Optional[str]:
        """Generate a reply for a tweet.
        
        Args:
            tweet: Tweet to generate reply for
            
        Returns:
            Generated reply text, or None if failed
        """
        try:
            log_tweet_processing(self.logger, tweet.id, "reply_generation", True, 
                               {"author": tweet.author_username})
            
            reply = self.reply_generator.generate_reply(tweet)
            
            if reply:
                log_tweet_processing(self.logger, tweet.id, "reply_generated", True,
                                   {"reply_length": len(reply)})
            else:
                log_tweet_processing(self.logger, tweet.id, "reply_generated", False)
            
            return reply
            
        except Exception as e:
            log_tweet_processing(self.logger, tweet.id, "reply_generated", False,
                               {"error": str(e)})
            return None
    
    def _post_reply(self, tweet: ProcessedTweet, reply: str) -> Optional[str]:
        """Post a reply to a tweet.
        
        Args:
            tweet: Tweet to reply to
            reply: Reply text
            
        Returns:
            Reply ID if successful, None otherwise
        """
        try:
            log_tweet_processing(self.logger, tweet.id, "reply_posting", True,
                               {"reply_length": len(reply)})
            
            reply_id = self.twitter_client.post_reply(tweet.id, reply)
            
            if reply_id:
                log_tweet_processing(self.logger, tweet.id, "reply_posted", True,
                                   {"reply_id": reply_id})
            else:
                log_tweet_processing(self.logger, tweet.id, "reply_posted", False)
            
            return reply_id
            
        except Exception as e:
            log_tweet_processing(self.logger, tweet.id, "reply_posted", False,
                               {"error": str(e)})
            return None
    
    def _filter_recently_processed(self, tweets: List[Tweet]) -> List[Tweet]:
        """Filter out tweets that were processed recently.
        
        Args:
            tweets: List of tweets to filter
            
        Returns:
            List of tweets not processed recently
        """
        try:
            # Load recently processed tweet IDs
            recently_processed = set()
            
            if self.processed_tweets_file.exists():
                with open(self.processed_tweets_file, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            # Only consider tweets processed in the last 24 hours
                            processed_time = datetime.fromisoformat(data.get('processing_timestamp', ''))
                            if datetime.now() - processed_time < timedelta(hours=24):
                                recently_processed.add(data.get('id'))
                        except (json.JSONDecodeError, ValueError, KeyError):
                            continue
            
            # Filter tweets
            filtered_tweets = [tweet for tweet in tweets if tweet.id not in recently_processed]
            
            self.logger.info("Filtered recently processed tweets",
                           original_count=len(tweets),
                           filtered_count=len(filtered_tweets),
                           recently_processed_count=len(recently_processed))
            
            return filtered_tweets
            
        except Exception as e:
            self.logger.warning("Failed to filter recently processed tweets", error=str(e))
            return tweets
    
    def _save_processing_results(self, result: ProcessingResult) -> None:
        """Save processing results to disk.
        
        Args:
            result: Processing result to save
        """
        try:
            # Save processed tweets
            with open(self.processed_tweets_file, 'a') as f:
                for tweet in result.processed_tweets:
                    f.write(json.dumps(tweet.dict(), default=str) + '\n')
            
            # Save state
            state = {
                'last_run_id': result.run_id,
                'last_run_time': result.start_time.isoformat(),
                'last_run_stats': {
                    'tweets_fetched': result.tweets_fetched,
                    'tweets_processed': result.tweets_processed,
                    'replies_generated': result.replies_generated,
                    'replies_posted': result.replies_posted,
                    'error_count': len(result.errors)
                }
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            self.logger.info("Processing results saved")
            
        except Exception as e:
            self.logger.error("Failed to save processing results", error=str(e))
    
    def _finalize_result(self, result: ProcessingResult) -> ProcessingResult:
        """Finalize processing result.
        
        Args:
            result: Processing result to finalize
            
        Returns:
            Finalized processing result
        """
        result.end_time = datetime.now()
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service status.
        
        Returns:
            Dictionary with service status information
        """
        try:
            # Load last run state
            last_run_state = {}
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    last_run_state = json.load(f)
            
            # Get rate limiter status
            rate_limiter_status = self.rate_limiter.get_status()
            
            status = {
                'service': {
                    'initialized': True,
                    'dry_run': self.dry_run,
                    'config_valid': len(validate_config()) == 0
                },
                'last_run': last_run_state,
                'rate_limits': rate_limiter_status,
                'configuration': {
                    'max_tweets_per_run': self.config.selection.max_tweets_per_run,
                    'min_engagement_threshold': self.config.selection.min_engagement_threshold,
                    'max_tweet_age_hours': self.config.selection.max_tweet_age_hours
                }
            }
            
            return status
            
        except Exception as e:
            self.logger.error("Failed to get service status", error=str(e))
            return {'error': str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all service components.
        
        Returns:
            Dictionary with health check results
        """
        health = {
            'overall': 'healthy',
            'components': {},
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Check Twitter API
            health['components']['twitter'] = {
                'status': 'healthy' if self.twitter_client.verify_credentials() else 'unhealthy',
                'rate_limits': self.rate_limiter.get_status()['twitter_read']
            }
            
            # Check Perplexity API
            health['components']['perplexity'] = {
                'status': 'healthy' if self.perplexity_client.test_connection() else 'unhealthy',
                'rate_limits': self.rate_limiter.get_status()['perplexity']
            }
            
            # Check file system
            health['components']['filesystem'] = {
                'status': 'healthy' if self.data_dir.exists() and self.data_dir.is_dir() else 'unhealthy',
                'data_dir': str(self.data_dir)
            }
            
            # Overall health
            if any(comp['status'] == 'unhealthy' for comp in health['components'].values()):
                health['overall'] = 'unhealthy'
            
        except Exception as e:
            health['overall'] = 'unhealthy'
            health['error'] = str(e)
        
        return health

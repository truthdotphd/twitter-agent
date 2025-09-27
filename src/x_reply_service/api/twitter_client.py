"""Twitter API client for fetching tweets and posting replies."""

import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import tweepy
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..models import Tweet, PublicMetrics, ContextAnnotation, ReferencedTweet, APIError
from ..utils.logging import get_logger, log_api_call
from ..utils.rate_limiter import RateLimiter


class TwitterClient:
    """Twitter API client with rate limiting and error handling."""
    
    def __init__(self, bearer_token: str, api_key: str, api_secret: str, 
                 access_token: str, access_token_secret: str, rate_limiter: RateLimiter):
        """Initialize Twitter client.
        
        Args:
            bearer_token: Twitter Bearer Token
            api_key: Twitter API Key
            api_secret: Twitter API Secret
            access_token: Twitter Access Token
            access_token_secret: Twitter Access Token Secret
            rate_limiter: Rate limiter instance
        """
        self.rate_limiter = rate_limiter
        self.logger = get_logger("twitter_client")
        
        # Initialize Tweepy clients
        try:
            # Client for API v2 (reading tweets)
            self.client = tweepy.Client(
                bearer_token=bearer_token,
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
                wait_on_rate_limit=False  # We handle rate limiting ourselves
            )
            
            # API v1.1 client for additional functionality if needed
            auth = tweepy.OAuth1UserHandler(
                api_key, api_secret, access_token, access_token_secret
            )
            self.api_v1 = tweepy.API(auth, wait_on_rate_limit=False)
            
            self.logger.info("Twitter client initialized successfully")
            
        except Exception as e:
            self.logger.error("Failed to initialize Twitter client", error=str(e))
            raise
    
    def verify_credentials(self) -> bool:
        """Verify Twitter API credentials.
        
        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            start_time = time.time()
            
            def _verify():
                return self.client.get_me()
            
            user = self.rate_limiter.twitter_read_with_circuit_breaker(_verify)
            duration = time.time() - start_time
            
            if user.data:
                log_api_call(self.logger, "twitter", "verify_credentials", 
                           duration, True)
                self.logger.info("Credentials verified", 
                               username=user.data.username,
                               user_id=user.data.id)
                return True
            else:
                log_api_call(self.logger, "twitter", "verify_credentials", 
                           duration, False, "No user data returned")
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            log_api_call(self.logger, "twitter", "verify_credentials", 
                       duration, False, str(e))
            return False
    
    def get_user_timeline(self, max_results: int = 100, 
                         exclude_replies: bool = True, 
                         exclude_retweets: bool = True) -> List[Tweet]:
        """Get user's timeline (approximates 'For You' feed).
        
        Note: Twitter API v2 doesn't provide direct access to the 'For You' feed.
        This method fetches the user's timeline as an approximation.
        
        Args:
            max_results: Maximum number of tweets to fetch (5-100)
            exclude_replies: Whether to exclude replies
            exclude_retweets: Whether to exclude retweets
            
        Returns:
            List of Tweet objects
        """
        try:
            start_time = time.time()
            
            def _get_timeline():
                # Get authenticated user first
                me = self.client.get_me()
                if not me.data:
                    raise Exception("Could not get authenticated user")
                
                # Get user's timeline
                tweets = self.client.get_users_tweets(
                    id=me.data.id,
                    max_results=min(max_results, 100),
                    exclude_replies=exclude_replies,
                    exclude_retweets=exclude_retweets,
                    tweet_fields=['created_at', 'author_id', 'public_metrics', 
                                'context_annotations', 'referenced_tweets', 'lang'],
                    user_fields=['username', 'name'],
                    expansions=['author_id']
                )
                return tweets
            
            response = self.rate_limiter.twitter_read_with_circuit_breaker(_get_timeline)
            duration = time.time() - start_time
            
            if not response.data:
                log_api_call(self.logger, "twitter", "get_user_timeline", 
                           duration, True)
                return []
            
            # Convert to our Tweet model
            tweets = []
            users_dict = {user.id: user for user in (response.includes.get('users', []))}
            
            for tweet_data in response.data:
                try:
                    author = users_dict.get(tweet_data.author_id)
                    if not author:
                        continue
                    
                    tweet = self._convert_tweet(tweet_data, author)
                    tweets.append(tweet)
                    
                except Exception as e:
                    self.logger.warning("Failed to convert tweet", 
                                      tweet_id=tweet_data.id, error=str(e))
                    continue
            
            log_api_call(self.logger, "twitter", "get_user_timeline", 
                       duration, True)
            self.logger.info("Fetched user timeline", tweet_count=len(tweets))
            
            return tweets
            
        except Exception as e:
            duration = time.time() - start_time
            log_api_call(self.logger, "twitter", "get_user_timeline", 
                       duration, False, str(e))
            raise
    
    def get_home_timeline(self, max_results: int = 100) -> List[Tweet]:
        """Get home timeline (closer to 'For You' feed).
        
        Note: This requires Twitter API v1.1 and may not be available for all apps.
        
        Args:
            max_results: Maximum number of tweets to fetch
            
        Returns:
            List of Tweet objects
        """
        try:
            start_time = time.time()
            
            def _get_home_timeline():
                return self.api_v1.home_timeline(
                    count=min(max_results, 200),
                    include_rts=False,
                    exclude_replies=True,
                    tweet_mode='extended'
                )
            
            tweets_data = self.rate_limiter.twitter_read_with_circuit_breaker(_get_home_timeline)
            duration = time.time() - start_time
            
            tweets = []
            for tweet_data in tweets_data:
                try:
                    tweet = self._convert_tweet_v1(tweet_data)
                    tweets.append(tweet)
                except Exception as e:
                    self.logger.warning("Failed to convert tweet", 
                                      tweet_id=tweet_data.id, error=str(e))
                    continue
            
            log_api_call(self.logger, "twitter", "get_home_timeline", 
                       duration, True)
            self.logger.info("Fetched home timeline", tweet_count=len(tweets))
            
            return tweets
            
        except Exception as e:
            duration = time.time() - start_time
            log_api_call(self.logger, "twitter", "get_home_timeline", 
                       duration, False, str(e))
            # Fallback to user timeline
            self.logger.warning("Home timeline failed, falling back to user timeline")
            return self.get_user_timeline(max_results)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((tweepy.TooManyRequests, tweepy.ServiceUnavailable))
    )
    def post_reply(self, tweet_id: str, reply_text: str) -> Optional[str]:
        """Post a reply to a tweet.
        
        Args:
            tweet_id: ID of tweet to reply to
            reply_text: Reply text content
            
        Returns:
            ID of posted reply, or None if failed
        """
        try:
            start_time = time.time()
            
            def _post_reply():
                response = self.client.create_tweet(
                    text=reply_text,
                    in_reply_to_tweet_id=tweet_id
                )
                return response
            
            response = self.rate_limiter.twitter_write_with_circuit_breaker(_post_reply)
            duration = time.time() - start_time
            
            if response.data:
                reply_id = response.data['id']
                log_api_call(self.logger, "twitter", "post_reply", duration, True)
                self.logger.info("Reply posted successfully", 
                               original_tweet_id=tweet_id,
                               reply_id=reply_id,
                               reply_length=len(reply_text))
                return reply_id
            else:
                log_api_call(self.logger, "twitter", "post_reply", 
                           duration, False, "No response data")
                return None
                
        except tweepy.Forbidden as e:
            duration = time.time() - start_time
            log_api_call(self.logger, "twitter", "post_reply", 
                       duration, False, f"Forbidden: {str(e)}")
            self.logger.error("Reply forbidden", 
                            tweet_id=tweet_id, 
                            error=str(e))
            return None
            
        except tweepy.TooManyRequests as e:
            duration = time.time() - start_time
            log_api_call(self.logger, "twitter", "post_reply", 
                       duration, False, f"Rate limited: {str(e)}")
            raise  # Let retry decorator handle this
            
        except Exception as e:
            duration = time.time() - start_time
            log_api_call(self.logger, "twitter", "post_reply", 
                       duration, False, str(e))
            self.logger.error("Failed to post reply", 
                            tweet_id=tweet_id, 
                            error=str(e))
            return None
    
    def _convert_tweet(self, tweet_data: Any, author: Any) -> Tweet:
        """Convert Twitter API v2 tweet data to our Tweet model.
        
        Args:
            tweet_data: Tweet data from Twitter API
            author: Author data from Twitter API
            
        Returns:
            Tweet object
        """
        # Convert public metrics
        metrics_data = tweet_data.public_metrics or {}
        public_metrics = PublicMetrics(
            like_count=metrics_data.get('like_count', 0),
            retweet_count=metrics_data.get('retweet_count', 0),
            reply_count=metrics_data.get('reply_count', 0),
            quote_count=metrics_data.get('quote_count', 0)
        )
        
        # Convert context annotations
        context_annotations = None
        if tweet_data.context_annotations:
            context_annotations = [
                ContextAnnotation(
                    domain=ann.get('domain'),
                    entity=ann.get('entity')
                )
                for ann in tweet_data.context_annotations
            ]
        
        # Convert referenced tweets
        referenced_tweets = None
        if tweet_data.referenced_tweets:
            referenced_tweets = [
                ReferencedTweet(type=ref['type'], id=ref['id'])
                for ref in tweet_data.referenced_tweets
            ]
        
        return Tweet(
            id=tweet_data.id,
            text=tweet_data.text,
            author_id=tweet_data.author_id,
            author_username=author.username,
            author_name=author.name,
            created_at=tweet_data.created_at,
            public_metrics=public_metrics,
            context_annotations=context_annotations,
            referenced_tweets=referenced_tweets,
            lang=getattr(tweet_data, 'lang', None)
        )
    
    def _convert_tweet_v1(self, tweet_data: Any) -> Tweet:
        """Convert Twitter API v1.1 tweet data to our Tweet model.
        
        Args:
            tweet_data: Tweet data from Twitter API v1.1
            
        Returns:
            Tweet object
        """
        # Convert public metrics
        public_metrics = PublicMetrics(
            like_count=tweet_data.favorite_count or 0,
            retweet_count=tweet_data.retweet_count or 0,
            reply_count=0,  # Not available in v1.1
            quote_count=0   # Not available in v1.1
        )
        
        return Tweet(
            id=str(tweet_data.id),
            text=tweet_data.full_text,
            author_id=str(tweet_data.user.id),
            author_username=tweet_data.user.screen_name,
            author_name=tweet_data.user.name,
            created_at=tweet_data.created_at,
            public_metrics=public_metrics,
            lang=tweet_data.lang
        )

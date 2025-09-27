"""Tweet selection algorithm for identifying the best tweets to reply to."""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..models import Tweet, SelectionConfig, ProcessedTweet
from ..utils.logging import get_logger


@dataclass
class SelectionCriteria:
    """Criteria for tweet selection scoring."""
    engagement_weight: float = 0.4
    recency_weight: float = 0.25
    content_quality_weight: float = 0.2
    author_influence_weight: float = 0.15


class TweetSelector:
    """Selects the best tweets to reply to based on multiple criteria."""
    
    def __init__(self, config: SelectionConfig):
        """Initialize tweet selector.
        
        Args:
            config: Selection configuration
        """
        self.config = config
        self.logger = get_logger("tweet_selector")
        self.criteria = SelectionCriteria()
        
        # Compile regex patterns for efficiency
        self.question_pattern = re.compile(r'\?')
        self.controversy_patterns = [
            re.compile(r'\b(should|shouldn\'t|wrong|right|believe|think|opinion)\b', re.IGNORECASE),
            re.compile(r'\b(always|never|everyone|nobody|all|none)\b', re.IGNORECASE),
            re.compile(r'\b(best|worst|better|worse)\b', re.IGNORECASE)
        ]
        
        self.logger.info("Tweet selector initialized", 
                        max_tweets=config.max_tweets_per_run,
                        min_engagement=config.min_engagement_threshold)
    
    def select_tweets(self, tweets: List[Tweet]) -> List[ProcessedTweet]:
        """Select the best tweets to reply to.
        
        Args:
            tweets: List of candidate tweets
            
        Returns:
            List of selected tweets with scores, sorted by score (highest first)
        """
        if not tweets:
            self.logger.warning("No tweets provided for selection")
            return []
        
        self.logger.info("Starting tweet selection", candidate_count=len(tweets))
        
        # Filter tweets based on basic criteria
        filtered_tweets = self._filter_tweets(tweets)
        self.logger.info("Tweets after filtering", count=len(filtered_tweets))
        
        if not filtered_tweets:
            self.logger.warning("No tweets passed filtering criteria")
            return []
        
        # Score remaining tweets
        scored_tweets = []
        for tweet in filtered_tweets:
            try:
                score = self._calculate_tweet_score(tweet)
                processed_tweet = ProcessedTweet(
                    **tweet.dict(),
                    selection_score=score,
                    processing_timestamp=datetime.now()
                )
                scored_tweets.append(processed_tweet)
                
            except Exception as e:
                self.logger.warning("Failed to score tweet", 
                                  tweet_id=tweet.id, error=str(e))
                continue
        
        # Sort by score (highest first) and take top N
        scored_tweets.sort(key=lambda t: t.selection_score, reverse=True)
        selected_tweets = scored_tweets[:self.config.max_tweets_per_run]
        
        self.logger.info("Tweet selection completed",
                        selected_count=len(selected_tweets),
                        avg_score=sum(t.selection_score for t in selected_tweets) / len(selected_tweets) if selected_tweets else 0)
        
        # Log selection details
        for i, tweet in enumerate(selected_tweets, 1):
            self.logger.debug("Selected tweet",
                            rank=i,
                            tweet_id=tweet.id,
                            score=round(tweet.selection_score, 2),
                            author=tweet.author_username,
                            engagement=sum(tweet.public_metrics.dict().values()),
                            text_preview=tweet.text[:50] + "..." if len(tweet.text) > 50 else tweet.text)
        
        return selected_tweets
    
    def _filter_tweets(self, tweets: List[Tweet]) -> List[Tweet]:
        """Filter tweets based on basic criteria.
        
        Args:
            tweets: List of tweets to filter
            
        Returns:
            List of tweets that pass filtering criteria
        """
        filtered = []
        now = datetime.now()
        
        for tweet in tweets:
            # Check age
            age_hours = (now - tweet.created_at).total_seconds() / 3600
            if age_hours > self.config.max_tweet_age_hours:
                continue
            
            # Check engagement threshold
            total_engagement = sum(tweet.public_metrics.dict().values())
            if total_engagement < self.config.min_engagement_threshold:
                continue
            
            # Check if it's a retweet (and we want to exclude them)
            if self.config.exclude_retweets and tweet.referenced_tweets:
                if any(ref.type == 'retweeted' for ref in tweet.referenced_tweets):
                    continue
            
            # Check if it's a reply (and we want to exclude them)
            if self.config.exclude_replies and tweet.referenced_tweets:
                if any(ref.type == 'replied_to' for ref in tweet.referenced_tweets):
                    continue
            
            # Check blacklisted users
            if tweet.author_username.lower() in [u.lower() for u in self.config.blacklisted_users]:
                continue
            
            # Check blacklisted keywords
            if any(keyword.lower() in tweet.text.lower() 
                   for keyword in self.config.blacklisted_keywords):
                continue
            
            # Check for very short tweets (likely not worth replying to)
            if len(tweet.text.strip()) < 20:
                continue
            
            # Check for tweets that are mostly URLs or mentions
            if self._is_mostly_urls_or_mentions(tweet.text):
                continue
            
            filtered.append(tweet)
        
        return filtered
    
    def _calculate_tweet_score(self, tweet: Tweet) -> float:
        """Calculate selection score for a tweet.
        
        Args:
            tweet: Tweet to score
            
        Returns:
            Score from 0.0 to 100.0 (higher is better)
        """
        score = 0.0
        
        # Engagement Score (40% weight)
        engagement_score = self._calculate_engagement_score(tweet)
        score += engagement_score * self.criteria.engagement_weight
        
        # Recency Score (25% weight)
        recency_score = self._calculate_recency_score(tweet)
        score += recency_score * self.criteria.recency_weight
        
        # Content Quality Score (20% weight)
        content_score = self._calculate_content_quality_score(tweet)
        score += content_score * self.criteria.content_quality_weight
        
        # Author Influence Score (15% weight)
        author_score = self._calculate_author_influence_score(tweet)
        score += author_score * self.criteria.author_influence_weight
        
        return min(score * 100, 100.0)  # Scale to 0-100 and cap at 100
    
    def _calculate_engagement_score(self, tweet: Tweet) -> float:
        """Calculate engagement score (0.0 to 1.0).
        
        Args:
            tweet: Tweet to score
            
        Returns:
            Engagement score
        """
        metrics = tweet.public_metrics
        
        # Weighted engagement calculation
        weighted_engagement = (
            metrics.like_count * 1.0 +
            metrics.retweet_count * 2.0 +  # Retweets are more valuable
            metrics.reply_count * 1.5 +    # Replies indicate discussion
            metrics.quote_count * 1.8      # Quotes are highly valuable
        )
        
        # Normalize to 0-1 scale (using log scale for better distribution)
        import math
        if weighted_engagement <= 0:
            return 0.0
        
        # Use log scale with a reasonable maximum
        max_engagement = 1000  # Tweets with 1000+ weighted engagement get max score
        normalized_score = math.log(weighted_engagement + 1) / math.log(max_engagement + 1)
        
        return min(normalized_score, 1.0)
    
    def _calculate_recency_score(self, tweet: Tweet) -> float:
        """Calculate recency score (0.0 to 1.0).
        
        Args:
            tweet: Tweet to score
            
        Returns:
            Recency score
        """
        now = datetime.now()
        age_hours = (now - tweet.created_at).total_seconds() / 3600
        
        # Linear decay over max_tweet_age_hours
        if age_hours >= self.config.max_tweet_age_hours:
            return 0.0
        
        return (self.config.max_tweet_age_hours - age_hours) / self.config.max_tweet_age_hours
    
    def _calculate_content_quality_score(self, tweet: Tweet) -> float:
        """Calculate content quality score (0.0 to 1.0).
        
        Args:
            tweet: Tweet to score
            
        Returns:
            Content quality score
        """
        text = tweet.text.lower()
        score = 0.0
        
        # Length appropriateness (sweet spot: 50-200 characters)
        length = len(tweet.text)
        if 50 <= length <= 200:
            score += 0.3
        elif 20 <= length < 50 or 200 < length <= 280:
            score += 0.15
        
        # Question/discussion potential
        if self.question_pattern.search(text):
            score += 0.2
        
        # Controversy/opinion indicators
        controversy_count = sum(1 for pattern in self.controversy_patterns 
                              if pattern.search(text))
        score += min(controversy_count * 0.15, 0.3)
        
        # Educational potential (mentions of facts, studies, research)
        educational_keywords = ['study', 'research', 'data', 'fact', 'evidence', 
                              'according to', 'shows that', 'found that']
        educational_count = sum(1 for keyword in educational_keywords 
                              if keyword in text)
        score += min(educational_count * 0.1, 0.2)
        
        # Avoid purely promotional content
        promotional_keywords = ['buy', 'sale', 'discount', 'offer', 'deal', 
                              'click here', 'link in bio', 'dm me']
        if any(keyword in text for keyword in promotional_keywords):
            score -= 0.3
        
        # Avoid overly emotional/aggressive content
        aggressive_keywords = ['hate', 'stupid', 'idiot', 'moron', 'pathetic']
        if any(keyword in text for keyword in aggressive_keywords):
            score -= 0.2
        
        return max(score, 0.0)
    
    def _calculate_author_influence_score(self, tweet: Tweet) -> float:
        """Calculate author influence score (0.0 to 1.0).
        
        Currently returns a baseline score since we don't have follower data.
        In a full implementation, this would consider:
        - Follower count
        - Verification status
        - Account age
        - Historical engagement rates
        
        Args:
            tweet: Tweet to score
            
        Returns:
            Author influence score
        """
        # Baseline score for all authors
        score = 0.5
        
        # Small bonus for verified accounts (if we had that data)
        # This is a placeholder for future enhancement
        
        return score
    
    def _is_mostly_urls_or_mentions(self, text: str) -> bool:
        """Check if tweet is mostly URLs or mentions.
        
        Args:
            text: Tweet text
            
        Returns:
            True if tweet is mostly URLs/mentions, False otherwise
        """
        # Count URLs
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        urls = url_pattern.findall(text)
        
        # Count mentions
        mention_pattern = re.compile(r'@\w+')
        mentions = mention_pattern.findall(text)
        
        # Calculate character count of URLs and mentions
        url_chars = sum(len(url) for url in urls)
        mention_chars = sum(len(mention) for mention in mentions)
        
        # If more than 60% of the tweet is URLs/mentions, consider it low quality
        total_chars = len(text)
        if total_chars == 0:
            return True
        
        url_mention_ratio = (url_chars + mention_chars) / total_chars
        return url_mention_ratio > 0.6
    
    def get_selection_stats(self, tweets: List[Tweet]) -> Dict[str, Any]:
        """Get statistics about tweet selection process.
        
        Args:
            tweets: List of tweets that were considered
            
        Returns:
            Dictionary with selection statistics
        """
        if not tweets:
            return {"total_tweets": 0}
        
        now = datetime.now()
        
        # Age distribution
        ages = [(now - tweet.created_at).total_seconds() / 3600 for tweet in tweets]
        
        # Engagement distribution
        engagements = [sum(tweet.public_metrics.dict().values()) for tweet in tweets]
        
        # Language distribution
        languages = {}
        for tweet in tweets:
            lang = tweet.lang or 'unknown'
            languages[lang] = languages.get(lang, 0) + 1
        
        return {
            "total_tweets": len(tweets),
            "age_stats": {
                "min_hours": min(ages) if ages else 0,
                "max_hours": max(ages) if ages else 0,
                "avg_hours": sum(ages) / len(ages) if ages else 0
            },
            "engagement_stats": {
                "min": min(engagements) if engagements else 0,
                "max": max(engagements) if engagements else 0,
                "avg": sum(engagements) / len(engagements) if engagements else 0
            },
            "language_distribution": languages,
            "filtered_out": {
                "too_old": sum(1 for age in ages if age > self.config.max_tweet_age_hours),
                "low_engagement": sum(1 for eng in engagements if eng < self.config.min_engagement_threshold)
            }
        }

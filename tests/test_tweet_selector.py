"""Tests for tweet selector."""

import pytest
from datetime import datetime, timedelta

from src.x_reply_service.core.tweet_selector import TweetSelector
from src.x_reply_service.models import Tweet, PublicMetrics, SelectionConfig


class TestTweetSelector:
    """Test TweetSelector class."""
    
    @pytest.fixture
    def selector(self):
        """Create a tweet selector with default config."""
        config = SelectionConfig()
        return TweetSelector(config)
    
    @pytest.fixture
    def sample_tweets(self):
        """Create sample tweets for testing."""
        now = datetime.now()
        
        tweets = [
            # High engagement, recent tweet
            Tweet(
                id="1",
                text="This is an interesting discussion about AI and its impact on society. What do you think?",
                author_id="user1",
                author_username="user1",
                author_name="User One",
                created_at=now - timedelta(hours=1),
                public_metrics=PublicMetrics(like_count=100, retweet_count=50, reply_count=25, quote_count=10)
            ),
            
            # Medium engagement, older tweet
            Tweet(
                id="2",
                text="Just had coffee. It was good.",
                author_id="user2",
                author_username="user2",
                author_name="User Two",
                created_at=now - timedelta(hours=3),
                public_metrics=PublicMetrics(like_count=20, retweet_count=5, reply_count=3, quote_count=1)
            ),
            
            # Low engagement, recent tweet
            Tweet(
                id="3",
                text="Testing tweet with minimal engagement",
                author_id="user3",
                author_username="user3",
                author_name="User Three",
                created_at=now - timedelta(minutes=30),
                public_metrics=PublicMetrics(like_count=2, retweet_count=0, reply_count=1, quote_count=0)
            ),
            
            # Old tweet (should be filtered out)
            Tweet(
                id="4",
                text="This tweet is too old to be selected",
                author_id="user4",
                author_username="user4",
                author_name="User Four",
                created_at=now - timedelta(hours=6),
                public_metrics=PublicMetrics(like_count=50, retweet_count=10, reply_count=5, quote_count=2)
            ),
            
            # Very short tweet (should be filtered out)
            Tweet(
                id="5",
                text="Hi",
                author_id="user5",
                author_username="user5",
                author_name="User Five",
                created_at=now - timedelta(hours=1),
                public_metrics=PublicMetrics(like_count=10, retweet_count=2, reply_count=1, quote_count=0)
            )
        ]
        
        return tweets
    
    def test_select_tweets_basic(self, selector, sample_tweets):
        """Test basic tweet selection."""
        selected = selector.select_tweets(sample_tweets)
        
        # Should return ProcessedTweet objects
        assert len(selected) > 0
        assert all(hasattr(tweet, 'selection_score') for tweet in selected)
        
        # Should be sorted by score (highest first)
        scores = [tweet.selection_score for tweet in selected]
        assert scores == sorted(scores, reverse=True)
    
    def test_filter_old_tweets(self, selector, sample_tweets):
        """Test filtering of old tweets."""
        selected = selector.select_tweets(sample_tweets)
        
        # Tweet with id "4" (6 hours old) should be filtered out
        selected_ids = [tweet.id for tweet in selected]
        assert "4" not in selected_ids
    
    def test_filter_short_tweets(self, selector, sample_tweets):
        """Test filtering of very short tweets."""
        selected = selector.select_tweets(sample_tweets)
        
        # Tweet with id "5" ("Hi") should be filtered out
        selected_ids = [tweet.id for tweet in selected]
        assert "5" not in selected_ids
    
    def test_filter_low_engagement(self, selector, sample_tweets):
        """Test filtering of low engagement tweets."""
        # Set high engagement threshold
        selector.config.min_engagement_threshold = 50
        
        selected = selector.select_tweets(sample_tweets)
        
        # Only tweet "1" should pass the engagement threshold
        selected_ids = [tweet.id for tweet in selected]
        assert "3" not in selected_ids  # Low engagement tweet
    
    def test_blacklisted_users(self, sample_tweets):
        """Test blacklisted users filtering."""
        config = SelectionConfig(blacklisted_users=["user1", "@user2"])
        selector = TweetSelector(config)
        
        selected = selector.select_tweets(sample_tweets)
        
        # Tweets from user1 and user2 should be filtered out
        selected_usernames = [tweet.author_username for tweet in selected]
        assert "user1" not in selected_usernames
        assert "user2" not in selected_usernames
    
    def test_blacklisted_keywords(self, sample_tweets):
        """Test blacklisted keywords filtering."""
        config = SelectionConfig(blacklisted_keywords=["coffee", "testing"])
        selector = TweetSelector(config)
        
        selected = selector.select_tweets(sample_tweets)
        
        # Tweets containing "coffee" or "testing" should be filtered out
        selected_ids = [tweet.id for tweet in selected]
        assert "2" not in selected_ids  # Contains "coffee"
        assert "3" not in selected_ids  # Contains "testing"
    
    def test_max_tweets_limit(self, selector, sample_tweets):
        """Test maximum tweets per run limit."""
        selector.config.max_tweets_per_run = 2
        
        selected = selector.select_tweets(sample_tweets)
        
        # Should return at most 2 tweets
        assert len(selected) <= 2
    
    def test_engagement_score_calculation(self, selector):
        """Test engagement score calculation."""
        now = datetime.now()
        
        # High engagement tweet
        high_engagement_tweet = Tweet(
            id="high",
            text="High engagement tweet with lots of interaction",
            author_id="user",
            author_username="user",
            author_name="User",
            created_at=now - timedelta(hours=1),
            public_metrics=PublicMetrics(like_count=1000, retweet_count=500, reply_count=200, quote_count=100)
        )
        
        # Low engagement tweet
        low_engagement_tweet = Tweet(
            id="low",
            text="Low engagement tweet with minimal interaction",
            author_id="user",
            author_username="user",
            author_name="User",
            created_at=now - timedelta(hours=1),
            public_metrics=PublicMetrics(like_count=1, retweet_count=0, reply_count=0, quote_count=0)
        )
        
        high_score = selector._calculate_engagement_score(high_engagement_tweet)
        low_score = selector._calculate_engagement_score(low_engagement_tweet)
        
        assert high_score > low_score
        assert 0.0 <= high_score <= 1.0
        assert 0.0 <= low_score <= 1.0
    
    def test_recency_score_calculation(self, selector):
        """Test recency score calculation."""
        now = datetime.now()
        
        # Recent tweet
        recent_tweet = Tweet(
            id="recent",
            text="Recent tweet",
            author_id="user",
            author_username="user",
            author_name="User",
            created_at=now - timedelta(minutes=30),
            public_metrics=PublicMetrics()
        )
        
        # Older tweet
        old_tweet = Tweet(
            id="old",
            text="Older tweet",
            author_id="user",
            author_username="user",
            author_name="User",
            created_at=now - timedelta(hours=3),
            public_metrics=PublicMetrics()
        )
        
        recent_score = selector._calculate_recency_score(recent_tweet)
        old_score = selector._calculate_recency_score(old_tweet)
        
        assert recent_score > old_score
        assert 0.0 <= recent_score <= 1.0
        assert 0.0 <= old_score <= 1.0
    
    def test_content_quality_score(self, selector):
        """Test content quality score calculation."""
        now = datetime.now()
        
        # High quality tweet (question, good length, controversy)
        quality_tweet = Tweet(
            id="quality",
            text="What do you think about the impact of AI on traditional jobs? Should we be concerned?",
            author_id="user",
            author_username="user",
            author_name="User",
            created_at=now,
            public_metrics=PublicMetrics()
        )
        
        # Low quality tweet (short, no discussion potential)
        poor_tweet = Tweet(
            id="poor",
            text="Ok",
            author_id="user",
            author_username="user",
            author_name="User",
            created_at=now,
            public_metrics=PublicMetrics()
        )
        
        quality_score = selector._calculate_content_quality_score(quality_tweet)
        poor_score = selector._calculate_content_quality_score(poor_tweet)
        
        assert quality_score > poor_score
        assert 0.0 <= quality_score <= 1.0
        assert 0.0 <= poor_score <= 1.0
    
    def test_empty_tweet_list(self, selector):
        """Test handling of empty tweet list."""
        selected = selector.select_tweets([])
        assert selected == []
    
    def test_all_tweets_filtered(self, selector):
        """Test when all tweets are filtered out."""
        now = datetime.now()
        
        # Create tweets that will all be filtered out
        filtered_tweets = [
            # Too old
            Tweet(
                id="old",
                text="Old tweet",
                author_id="user",
                author_username="user",
                author_name="User",
                created_at=now - timedelta(hours=10),
                public_metrics=PublicMetrics(like_count=100)
            ),
            # Too short
            Tweet(
                id="short",
                text="Hi",
                author_id="user",
                author_username="user",
                author_name="User",
                created_at=now,
                public_metrics=PublicMetrics(like_count=100)
            )
        ]
        
        selected = selector.select_tweets(filtered_tweets)
        assert selected == []
    
    def test_selection_stats(self, selector, sample_tweets):
        """Test selection statistics generation."""
        stats = selector.get_selection_stats(sample_tweets)
        
        assert "total_tweets" in stats
        assert "age_stats" in stats
        assert "engagement_stats" in stats
        assert "language_distribution" in stats
        assert "filtered_out" in stats
        
        assert stats["total_tweets"] == len(sample_tweets)
        assert isinstance(stats["age_stats"]["avg_hours"], float)
        assert isinstance(stats["engagement_stats"]["avg"], float)

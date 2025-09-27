"""Tests for data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.x_reply_service.models import (
    Tweet, ProcessedTweet, PublicMetrics, Config, APIConfig,
    SelectionConfig, ReplyConfig, ProcessingResult, SafetyCheckResult
)


class TestPublicMetrics:
    """Test PublicMetrics model."""
    
    def test_default_values(self):
        """Test default metric values."""
        metrics = PublicMetrics()
        assert metrics.like_count == 0
        assert metrics.retweet_count == 0
        assert metrics.reply_count == 0
        assert metrics.quote_count == 0
    
    def test_custom_values(self):
        """Test custom metric values."""
        metrics = PublicMetrics(
            like_count=100,
            retweet_count=50,
            reply_count=25,
            quote_count=10
        )
        assert metrics.like_count == 100
        assert metrics.retweet_count == 50
        assert metrics.reply_count == 25
        assert metrics.quote_count == 10


class TestTweet:
    """Test Tweet model."""
    
    def test_valid_tweet(self):
        """Test creating a valid tweet."""
        tweet = Tweet(
            id="123456789",
            text="This is a test tweet",
            author_id="987654321",
            author_username="testuser",
            author_name="Test User",
            created_at=datetime.now(),
            public_metrics=PublicMetrics(like_count=10)
        )
        
        assert tweet.id == "123456789"
        assert tweet.text == "This is a test tweet"
        assert tweet.author_username == "testuser"
        assert tweet.public_metrics.like_count == 10
    
    def test_text_length_validation(self):
        """Test tweet text length validation."""
        # Text over 280 characters should fail
        long_text = "x" * 281
        
        with pytest.raises(ValidationError):
            Tweet(
                id="123",
                text=long_text,
                author_id="456",
                author_username="user",
                author_name="User",
                created_at=datetime.now(),
                public_metrics=PublicMetrics()
            )


class TestProcessedTweet:
    """Test ProcessedTweet model."""
    
    def test_processed_tweet_creation(self):
        """Test creating a processed tweet."""
        tweet = ProcessedTweet(
            id="123456789",
            text="This is a test tweet",
            author_id="987654321",
            author_username="testuser",
            author_name="Test User",
            created_at=datetime.now(),
            public_metrics=PublicMetrics(like_count=10),
            selection_score=75.5
        )
        
        assert tweet.selection_score == 75.5
        assert tweet.reply_posted is False
        assert tweet.generated_reply is None
    
    def test_selection_score_validation(self):
        """Test selection score validation."""
        # Score over 100 should fail
        with pytest.raises(ValidationError):
            ProcessedTweet(
                id="123",
                text="Test",
                author_id="456",
                author_username="user",
                author_name="User",
                created_at=datetime.now(),
                public_metrics=PublicMetrics(),
                selection_score=150.0
            )
        
        # Negative score should fail
        with pytest.raises(ValidationError):
            ProcessedTweet(
                id="123",
                text="Test",
                author_id="456",
                author_username="user",
                author_name="User",
                created_at=datetime.now(),
                public_metrics=PublicMetrics(),
                selection_score=-10.0
            )


class TestSelectionConfig:
    """Test SelectionConfig model."""
    
    def test_default_config(self):
        """Test default selection configuration."""
        config = SelectionConfig()
        
        assert config.max_tweets_per_run == 5
        assert config.min_engagement_threshold == 10
        assert config.max_tweet_age_hours == 4
        assert config.exclude_retweets is True
        assert config.exclude_replies is True
        assert config.blacklisted_users == []
        assert config.blacklisted_keywords == []
    
    def test_username_validation(self):
        """Test username validation and cleaning."""
        config = SelectionConfig(
            blacklisted_users=["@user1", "USER2", "@User3", ""]
        )
        
        # Should remove @ symbols, convert to lowercase, and remove empty strings
        assert config.blacklisted_users == ["user1", "user2", "user3"]
    
    def test_keyword_validation(self):
        """Test keyword validation and cleaning."""
        config = SelectionConfig(
            blacklisted_keywords=["CRYPTO", "Nft", "  spam  ", ""]
        )
        
        # Should convert to lowercase and strip whitespace
        assert config.blacklisted_keywords == ["crypto", "nft", "spam"]


class TestReplyConfig:
    """Test ReplyConfig model."""
    
    def test_default_config(self):
        """Test default reply configuration."""
        config = ReplyConfig()
        
        assert "{tweet_content}" in config.base_prompt
        assert config.max_reply_length == 280
        assert config.temperature == 0.7
        assert config.model == "llama-3.1-sonar-small-128k-online"
    
    def test_prompt_validation(self):
        """Test prompt validation."""
        # Prompt without placeholder should fail
        with pytest.raises(ValidationError):
            ReplyConfig(base_prompt="This prompt has no placeholder")
    
    def test_temperature_validation(self):
        """Test temperature validation."""
        # Temperature over 2.0 should fail
        with pytest.raises(ValidationError):
            ReplyConfig(temperature=3.0)
        
        # Negative temperature should fail
        with pytest.raises(ValidationError):
            ReplyConfig(temperature=-0.1)


class TestProcessingResult:
    """Test ProcessingResult model."""
    
    def test_processing_result_creation(self):
        """Test creating a processing result."""
        result = ProcessingResult(
            run_id="test_run_123",
            start_time=datetime.now()
        )
        
        assert result.run_id == "test_run_123"
        assert result.tweets_fetched == 0
        assert result.tweets_processed == 0
        assert result.replies_generated == 0
        assert result.replies_posted == 0
        assert result.errors == []
    
    def test_duration_calculation(self):
        """Test duration calculation."""
        start_time = datetime.now()
        result = ProcessingResult(
            run_id="test",
            start_time=start_time
        )
        
        # No end time should return None
        assert result.duration_seconds is None
        
        # With end time should calculate duration
        result.end_time = start_time
        assert result.duration_seconds == 0.0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        result = ProcessingResult(
            run_id="test",
            start_time=datetime.now(),
            tweets_processed=10,
            replies_posted=8
        )
        
        assert result.success_rate == 80.0
        
        # Zero processed tweets should return 0
        result.tweets_processed = 0
        assert result.success_rate == 0.0


class TestSafetyCheckResult:
    """Test SafetyCheckResult model."""
    
    def test_safety_result_creation(self):
        """Test creating a safety check result."""
        result = SafetyCheckResult(
            is_safe=True,
            reason="Content appears safe",
            confidence=0.95
        )
        
        assert result.is_safe is True
        assert result.reason == "Content appears safe"
        assert result.confidence == 0.95
    
    def test_confidence_validation(self):
        """Test confidence validation."""
        # Confidence over 1.0 should fail
        with pytest.raises(ValidationError):
            SafetyCheckResult(is_safe=True, confidence=1.5)
        
        # Negative confidence should fail
        with pytest.raises(ValidationError):
            SafetyCheckResult(is_safe=True, confidence=-0.1)

"""Data models for the X.com Auto-Reply Service."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
import re


class PublicMetrics(BaseModel):
    """Public engagement metrics for a tweet."""
    like_count: int = 0
    retweet_count: int = 0
    reply_count: int = 0
    quote_count: int = 0


class ContextAnnotation(BaseModel):
    """Context annotation for tweet topics."""
    domain: Optional[Dict[str, Any]] = None
    entity: Optional[Dict[str, Any]] = None


class ReferencedTweet(BaseModel):
    """Referenced tweet information."""
    type: str  # 'retweeted', 'quoted', 'replied_to'
    id: str


class Tweet(BaseModel):
    """Tweet data model."""
    id: str
    text: str
    author_id: str
    author_username: str
    author_name: str
    created_at: datetime
    public_metrics: PublicMetrics
    context_annotations: Optional[List[ContextAnnotation]] = None
    referenced_tweets: Optional[List[ReferencedTweet]] = None
    lang: Optional[str] = None
    
    @validator('text')
    def validate_text_length(cls, v):
        if len(v) > 280:
            raise ValueError('Tweet text cannot exceed 280 characters')
        return v


class ProcessedTweet(Tweet):
    """Tweet with processing information."""
    selection_score: float = Field(ge=0.0, le=100.0)
    generated_reply: Optional[str] = None
    reply_posted: bool = False
    processing_timestamp: datetime = Field(default_factory=datetime.now)
    error_message: Optional[str] = None
    reply_id: Optional[str] = None


class APIConfig(BaseModel):
    """API configuration for external services."""
    twitter_bearer_token: str
    twitter_api_key: str
    twitter_api_secret: str
    twitter_access_token: str
    twitter_access_token_secret: str
    perplexity_api_key: str
    
    class Config:
        # Don't include sensitive data in string representation
        repr_exclude = {
            'twitter_bearer_token', 'twitter_api_key', 'twitter_api_secret',
            'twitter_access_token', 'twitter_access_token_secret', 'perplexity_api_key'
        }


class SelectionConfig(BaseModel):
    """Configuration for tweet selection algorithm."""
    max_tweets_per_run: int = Field(default=5, ge=1, le=20)
    min_engagement_threshold: int = Field(default=10, ge=0)
    max_tweet_age_hours: int = Field(default=4, ge=1, le=24)
    exclude_retweets: bool = True
    exclude_replies: bool = True
    blacklisted_users: List[str] = Field(default_factory=list)
    blacklisted_keywords: List[str] = Field(default_factory=list)
    
    @validator('blacklisted_users')
    def validate_usernames(cls, v):
        """Ensure usernames are properly formatted."""
        cleaned = []
        for username in v:
            # Remove @ if present and convert to lowercase
            clean_username = username.lstrip('@').lower()
            if clean_username:
                cleaned.append(clean_username)
        return cleaned
    
    @validator('blacklisted_keywords')
    def validate_keywords(cls, v):
        """Convert keywords to lowercase for case-insensitive matching."""
        return [keyword.lower() for keyword in v if keyword.strip()]


class ReplyConfig(BaseModel):
    """Configuration for reply generation."""
    base_prompt: str = Field(
        default="write an impactful reply to the following so that it teaches something new and contrary to the status-quo views: {tweet_content}"
    )
    max_reply_length: int = Field(default=280, ge=1, le=280)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    model: str = "llama-3.1-sonar-small-128k-online"
    
    @validator('base_prompt')
    def validate_prompt_placeholder(cls, v):
        """Ensure the prompt contains the required placeholder."""
        if '{tweet_content}' not in v:
            raise ValueError('base_prompt must contain {tweet_content} placeholder')
        return v


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    twitter_read_per_15min: int = Field(default=240, ge=1, le=300)
    twitter_write_per_15min: int = Field(default=240, ge=1, le=300)
    perplexity_per_hour: int = Field(default=480, ge=1, le=600)


class AppConfig(BaseModel):
    """Main application configuration."""
    log_level: str = Field(default="INFO", regex=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    dry_run: bool = False
    data_dir: str = "data"
    log_dir: str = "logs"


class Config(BaseModel):
    """Complete application configuration."""
    api: APIConfig
    selection: SelectionConfig = Field(default_factory=SelectionConfig)
    reply: ReplyConfig = Field(default_factory=ReplyConfig)
    rate_limits: RateLimitConfig = Field(default_factory=RateLimitConfig)
    app: AppConfig = Field(default_factory=AppConfig)


class ProcessingResult(BaseModel):
    """Result of a processing run."""
    run_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    tweets_fetched: int = 0
    tweets_processed: int = 0
    replies_generated: int = 0
    replies_posted: int = 0
    errors: List[str] = Field(default_factory=list)
    processed_tweets: List[ProcessedTweet] = Field(default_factory=list)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate processing duration in seconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.tweets_processed == 0:
            return 0.0
        return (self.replies_posted / self.tweets_processed) * 100


class SafetyCheckResult(BaseModel):
    """Result of content safety check."""
    is_safe: bool
    reason: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class APIError(BaseModel):
    """API error information."""
    api_name: str
    error_type: str
    error_message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    retry_count: int = 0

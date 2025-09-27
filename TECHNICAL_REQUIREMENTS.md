# X.com Auto-Reply Service - Technical Requirements Document

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cron Scheduler │    │  Main Service   │    │   X.com API     │
│                 │───▶│                 │◄──▶│                 │
│  (Every Hour)   │    │  - Feed Reader  │    │  - Read Feed    │
└─────────────────┘    │  - Tweet Selector│    │  - Post Reply   │
                       │  - Reply Gen    │    └─────────────────┘
                       │  - Logger       │           │
                       └─────────────────┘           │
                              │                      │
                              ▼                      │
                       ┌─────────────────┐           │
                       │ Perplexity API  │           │
                       │                 │           │
                       │ - Web Search    │           │
                       │ - AI Generation │           │
                       └─────────────────┘           │
                              │                      │
                              ▼                      ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Local Storage   │    │   Logging       │
                       │                 │    │                 │
                       │ - Config Files  │    │ - Activity Log  │
                       │ - Tweet Cache   │    │ - Error Log     │
                       │ - State Data    │    │ - Metrics       │
                       └─────────────────┘    └─────────────────┘
```

### 1.2 Component Architecture

#### 1.2.1 Core Components
- **Main Service**: Orchestrates the entire workflow
- **Feed Reader**: Interfaces with X.com API to fetch "For You" feed
- **Tweet Selector**: Implements algorithm to select top 5 tweets
- **Reply Generator**: Interfaces with Perplexity API for content generation
- **Reply Poster**: Posts generated replies via X.com API
- **Configuration Manager**: Handles all configuration and settings
- **Logger**: Comprehensive logging and monitoring system

#### 1.2.2 Data Flow
1. **Initialization**: Load configuration and authenticate APIs
2. **Feed Retrieval**: Fetch latest tweets from "For You" feed
3. **Tweet Filtering**: Apply selection criteria and ranking algorithm
4. **Reply Generation**: Generate replies for selected tweets using Perplexity
5. **Content Validation**: Validate replies for safety and compliance
6. **Reply Posting**: Post replies to X.com
7. **Logging**: Record all activities and update metrics

## 2. Technology Stack

### 2.1 Programming Language
- **Primary**: Python 3.9+
- **Rationale**: 
  - Excellent API integration libraries
  - Strong text processing capabilities
  - Robust error handling and logging
  - Easy deployment and maintenance

### 2.2 Core Dependencies
```python
# API Integration
tweepy>=4.14.0          # X.com API client
requests>=2.31.0        # HTTP client for Perplexity API
aiohttp>=3.8.0         # Async HTTP for better performance

# Data Processing
pandas>=2.0.0          # Data manipulation and analysis
numpy>=1.24.0          # Numerical operations
python-dateutil>=2.8.0 # Date/time handling

# Configuration & Environment
python-dotenv>=1.0.0   # Environment variable management
pydantic>=2.0.0        # Configuration validation
PyYAML>=6.0            # YAML configuration files

# Logging & Monitoring
structlog>=23.1.0      # Structured logging
prometheus-client>=0.17.0 # Metrics collection

# Security
cryptography>=41.0.0   # Credential encryption
keyring>=24.0.0        # Secure credential storage

# Utilities
click>=8.1.0           # CLI interface
schedule>=1.2.0        # Backup scheduling (if cron fails)
tenacity>=8.2.0        # Retry logic with exponential backoff
```

### 2.3 External APIs
- **X.com API v2**: Tweet reading and posting
- **Perplexity API**: AI-powered reply generation with web search
- **System Cron**: Scheduling and automation

## 3. API Integration Specifications

### 3.1 X.com API Integration

#### 3.1.1 Authentication
```python
# OAuth 2.0 Bearer Token Authentication
TWITTER_BEARER_TOKEN = "your_bearer_token_here"
TWITTER_API_KEY = "your_api_key_here"
TWITTER_API_SECRET = "your_api_secret_here"
TWITTER_ACCESS_TOKEN = "your_access_token_here"
TWITTER_ACCESS_TOKEN_SECRET = "your_access_token_secret_here"
```

#### 3.1.2 Required Endpoints
- **GET /2/tweets/search/recent**: Fetch "For You" feed (alternative approach)
- **GET /2/users/me/timelines/reverse_chronological**: User timeline
- **POST /2/tweets**: Post replies
- **GET /2/tweets/:id**: Get tweet details
- **GET /2/users/me**: Get user information

#### 3.1.3 Rate Limits
- **Read Operations**: 300 requests per 15-minute window
- **Write Operations**: 300 tweets per 15-minute window
- **Implementation**: Conservative limits at 80% of maximum

#### 3.1.4 Required Permissions
- **Tweet.read**: Read tweets and user profiles
- **Tweet.write**: Post tweets and replies
- **Users.read**: Read user profiles and follower information

### 3.2 Perplexity API Integration

#### 3.2.1 Authentication
```python
# API Key Authentication
PERPLEXITY_API_KEY = "your_perplexity_api_key_here"
PERPLEXITY_BASE_URL = "https://api.perplexity.ai"
```

#### 3.2.2 API Endpoint
```python
# Chat Completions with Web Search
POST /chat/completions
{
    "model": "llama-3.1-sonar-small-128k-online",
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant that provides educational and contrarian perspectives."
        },
        {
            "role": "user", 
            "content": "write an impactful reply to the following so that it teaches something new and contrary to the status-quo views: {tweet_content}"
        }
    ],
    "max_tokens": 280,
    "temperature": 0.7,
    "search": true
}
```

#### 3.2.3 Rate Limits
- **Standard Plan**: 5,000 requests per month
- **Pro Plan**: 600 requests per hour
- **Implementation**: Track usage and implement queuing if needed

## 4. Data Models and Storage

### 4.1 Tweet Data Model
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class Tweet(BaseModel):
    id: str
    text: str
    author_id: str
    author_username: str
    author_name: str
    created_at: datetime
    public_metrics: dict  # likes, retweets, replies, quotes
    context_annotations: Optional[List[dict]] = None
    referenced_tweets: Optional[List[dict]] = None
    
class ProcessedTweet(Tweet):
    selection_score: float
    generated_reply: Optional[str] = None
    reply_posted: bool = False
    processing_timestamp: datetime
    error_message: Optional[str] = None
```

### 4.2 Configuration Model
```python
class APIConfig(BaseModel):
    twitter_bearer_token: str
    twitter_api_key: str
    twitter_api_secret: str
    twitter_access_token: str
    twitter_access_token_secret: str
    perplexity_api_key: str

class SelectionConfig(BaseModel):
    max_tweets_per_run: int = 5
    min_engagement_threshold: int = 10
    max_tweet_age_hours: int = 4
    exclude_retweets: bool = True
    exclude_replies: bool = True
    blacklisted_users: List[str] = []
    blacklisted_keywords: List[str] = []

class ReplyConfig(BaseModel):
    base_prompt: str = "write an impactful reply to the following so that it teaches something new and contrary to the status-quo views: {tweet_content}"
    max_reply_length: int = 280
    temperature: float = 0.7
    model: str = "llama-3.1-sonar-small-128k-online"

class AppConfig(BaseModel):
    api: APIConfig
    selection: SelectionConfig
    reply: ReplyConfig
    log_level: str = "INFO"
    dry_run: bool = False
```

### 4.3 Storage Strategy
```python
# File-based storage for simplicity and reliability
/app_data/
├── config/
│   ├── config.yaml          # Main configuration
│   ├── credentials.env      # Encrypted credentials
│   └── blacklist.json       # User/keyword blacklists
├── data/
│   ├── processed_tweets.jsonl  # Tweet processing history
│   ├── reply_cache.json        # Generated replies cache
│   └── state.json              # Application state
└── logs/
    ├── app.log              # Application logs
    ├── error.log            # Error logs
    └── metrics.log          # Performance metrics
```

## 5. Algorithm Specifications

### 5.1 Tweet Selection Algorithm

#### 5.1.1 Scoring Function
```python
def calculate_tweet_score(tweet: Tweet) -> float:
    """
    Calculate selection score for a tweet based on multiple factors
    Score range: 0.0 to 100.0 (higher is better)
    """
    score = 0.0
    
    # Engagement Score (40% weight)
    engagement = (
        tweet.public_metrics['like_count'] * 1.0 +
        tweet.public_metrics['retweet_count'] * 2.0 +
        tweet.public_metrics['reply_count'] * 1.5 +
        tweet.public_metrics['quote_count'] * 1.8
    )
    engagement_score = min(engagement / 100.0 * 40, 40)
    score += engagement_score
    
    # Recency Score (25% weight)
    hours_old = (datetime.now() - tweet.created_at).total_seconds() / 3600
    recency_score = max(0, (4 - hours_old) / 4 * 25)
    score += recency_score
    
    # Content Quality Score (20% weight)
    content_score = assess_content_quality(tweet.text)
    score += content_score * 20
    
    # Author Influence Score (15% weight)
    author_score = assess_author_influence(tweet.author_id)
    score += author_score * 15
    
    return min(score, 100.0)

def assess_content_quality(text: str) -> float:
    """Assess content quality (0.0 to 1.0)"""
    # Length appropriateness
    length_score = 1.0 if 50 <= len(text) <= 200 else 0.5
    
    # Question/discussion potential
    question_score = 0.3 if '?' in text else 0.0
    
    # Controversy indicators
    controversy_keywords = ['should', 'wrong', 'right', 'believe', 'think']
    controversy_score = min(sum(1 for word in controversy_keywords if word in text.lower()) * 0.2, 0.4)
    
    return min(length_score + question_score + controversy_score, 1.0)

def assess_author_influence(author_id: str) -> float:
    """Assess author influence (0.0 to 1.0)"""
    # This would integrate with X API to get follower count, verification status
    # For now, return baseline score
    return 0.5
```

#### 5.1.2 Filtering Rules
```python
def should_exclude_tweet(tweet: Tweet, config: SelectionConfig) -> bool:
    """Determine if tweet should be excluded from selection"""
    
    # Age filter
    hours_old = (datetime.now() - tweet.created_at).total_seconds() / 3600
    if hours_old > config.max_tweet_age_hours:
        return True
    
    # Engagement threshold
    total_engagement = sum(tweet.public_metrics.values())
    if total_engagement < config.min_engagement_threshold:
        return True
    
    # Content type filters
    if config.exclude_retweets and tweet.referenced_tweets:
        if any(ref['type'] == 'retweeted' for ref in tweet.referenced_tweets):
            return True
    
    if config.exclude_replies and tweet.referenced_tweets:
        if any(ref['type'] == 'replied_to' for ref in tweet.referenced_tweets):
            return True
    
    # Blacklist filters
    if tweet.author_username.lower() in [u.lower() for u in config.blacklisted_users]:
        return True
    
    if any(keyword.lower() in tweet.text.lower() for keyword in config.blacklisted_keywords):
        return True
    
    return False
```

### 5.2 Reply Generation Algorithm

#### 5.2.1 Prompt Engineering
```python
def generate_reply_prompt(tweet: Tweet, config: ReplyConfig) -> str:
    """Generate contextual prompt for Perplexity API"""
    
    # Extract context from tweet
    context = extract_tweet_context(tweet)
    
    # Build enhanced prompt
    enhanced_prompt = f"""
    {config.base_prompt}
    
    Tweet to reply to: "{tweet.text}"
    Author: @{tweet.author_username}
    Context: {context}
    
    Requirements:
    - Maximum {config.max_reply_length} characters
    - Provide educational value
    - Challenge conventional thinking
    - Be respectful but thought-provoking
    - Include relevant facts or data when possible
    - Avoid controversial political statements
    - Use engaging, conversational tone
    """
    
    return enhanced_prompt.format(tweet_content=tweet.text)

def extract_tweet_context(tweet: Tweet) -> str:
    """Extract contextual information from tweet"""
    context_parts = []
    
    # Topic detection from context annotations
    if tweet.context_annotations:
        topics = [ann.get('entity', {}).get('name', '') for ann in tweet.context_annotations]
        context_parts.append(f"Topics: {', '.join(topics[:3])}")
    
    # Engagement level
    total_engagement = sum(tweet.public_metrics.values())
    if total_engagement > 100:
        context_parts.append("High engagement tweet")
    
    # Time context
    hours_old = (datetime.now() - tweet.created_at).total_seconds() / 3600
    if hours_old < 1:
        context_parts.append("Recent tweet")
    
    return "; ".join(context_parts) if context_parts else "General discussion"
```

## 6. Error Handling and Resilience

### 6.1 Error Categories and Handling

#### 6.1.1 API Errors
```python
class APIErrorHandler:
    def __init__(self):
        self.retry_config = {
            'rate_limit': {'wait_time': 900, 'max_retries': 3},  # 15 minutes
            'server_error': {'wait_time': 60, 'max_retries': 5},
            'network_error': {'wait_time': 30, 'max_retries': 3},
            'auth_error': {'wait_time': 0, 'max_retries': 0}  # Don't retry auth errors
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException,))
    )
    def make_api_request(self, func, *args, **kwargs):
        """Make API request with retry logic"""
        try:
            return func(*args, **kwargs)
        except tweepy.TooManyRequests as e:
            logger.warning(f"Rate limit exceeded: {e}")
            raise
        except tweepy.Unauthorized as e:
            logger.error(f"Authentication failed: {e}")
            raise
        except Exception as e:
            logger.error(f"API request failed: {e}")
            raise
```

#### 6.1.2 Content Safety Errors
```python
class ContentSafetyFilter:
    def __init__(self):
        self.unsafe_patterns = [
            r'\b(hate|violence|threat)\b',
            r'\b(kill|die|death)\b',
            r'\b(racist|sexist|homophobic)\b'
        ]
        self.political_keywords = [
            'trump', 'biden', 'democrat', 'republican', 'liberal', 'conservative'
        ]
    
    def is_safe_content(self, text: str) -> tuple[bool, str]:
        """Check if generated content is safe to post"""
        text_lower = text.lower()
        
        # Check for unsafe patterns
        for pattern in self.unsafe_patterns:
            if re.search(pattern, text_lower):
                return False, f"Contains unsafe content: {pattern}"
        
        # Check for overly political content
        political_count = sum(1 for keyword in self.political_keywords if keyword in text_lower)
        if political_count > 2:
            return False, "Too much political content"
        
        # Check length
        if len(text) > 280:
            return False, "Exceeds character limit"
        
        return True, "Content is safe"
```

### 6.2 Circuit Breaker Pattern
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
            
            raise e
```

## 7. Security Requirements

### 7.1 Credential Management
```python
# Use environment variables and encryption for sensitive data
import os
from cryptography.fernet import Fernet

class SecureCredentialManager:
    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self):
        """Get encryption key from secure location"""
        key_file = os.path.expanduser('~/.x_reply_service_key')
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Read-only for owner
            return key
    
    def encrypt_credential(self, credential: str) -> str:
        """Encrypt a credential string"""
        return self.cipher.encrypt(credential.encode()).decode()
    
    def decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt a credential string"""
        return self.cipher.decrypt(encrypted_credential.encode()).decode()
```

### 7.2 Rate Limiting Implementation
```python
class RateLimiter:
    def __init__(self):
        self.twitter_read_limit = TokenBucket(300, 900)  # 300 per 15 min
        self.twitter_write_limit = TokenBucket(300, 900)  # 300 per 15 min
        self.perplexity_limit = TokenBucket(600, 3600)   # 600 per hour
    
    def can_make_twitter_read(self) -> bool:
        return self.twitter_read_limit.consume(1)
    
    def can_make_twitter_write(self) -> bool:
        return self.twitter_write_limit.consume(1)
    
    def can_make_perplexity_request(self) -> bool:
        return self.perplexity_limit.consume(1)

class TokenBucket:
    def __init__(self, capacity: int, refill_period: int):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_period = refill_period
        self.last_refill = time.time()
    
    def consume(self, tokens: int) -> bool:
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self):
        now = time.time()
        time_passed = now - self.last_refill
        tokens_to_add = int(time_passed / self.refill_period * self.capacity)
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
```

## 8. Monitoring and Logging

### 8.1 Logging Strategy
```python
import structlog
from datetime import datetime

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Usage examples
logger.info("Starting tweet processing", run_id=run_id, tweet_count=len(tweets))
logger.error("Failed to generate reply", tweet_id=tweet.id, error=str(e))
logger.info("Reply posted successfully", tweet_id=tweet.id, reply_id=reply.id)
```

### 8.2 Metrics Collection
```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Define metrics
tweets_processed = Counter('tweets_processed_total', 'Total tweets processed')
replies_generated = Counter('replies_generated_total', 'Total replies generated')
replies_posted = Counter('replies_posted_total', 'Total replies posted')
api_errors = Counter('api_errors_total', 'Total API errors', ['api', 'error_type'])
processing_time = Histogram('processing_time_seconds', 'Time spent processing tweets')
queue_size = Gauge('queue_size', 'Number of tweets in processing queue')

# Usage in code
with processing_time.time():
    # Process tweets
    tweets_processed.inc(len(selected_tweets))
    replies_generated.inc(len(generated_replies))
    replies_posted.inc(len(posted_replies))
```

## 9. Deployment and Operations

### 9.1 System Requirements
- **Operating System**: Linux/macOS with cron support
- **Python**: 3.9 or higher
- **Memory**: Minimum 512MB RAM
- **Storage**: 1GB free space for logs and data
- **Network**: Reliable internet connection with HTTPS support

### 9.2 Installation Process
```bash
# 1. Clone repository and setup environment
git clone <repository_url>
cd x-reply-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configuration setup
cp config/config.yaml.example config/config.yaml
# Edit config.yaml with your settings

# 3. Credential setup
python setup_credentials.py
# Follow prompts to enter API keys securely

# 4. Test installation
python -m x_reply_service --dry-run

# 5. Setup cron job
crontab -e
# Add: 0 * * * * /path/to/venv/bin/python /path/to/x-reply-service/main.py
```

### 9.3 Cron Configuration
```bash
# Run every hour at minute 0
0 * * * * cd /path/to/x-reply-service && /path/to/venv/bin/python main.py >> /var/log/x-reply-service.log 2>&1

# Alternative: Run every hour with 5-minute offset to avoid peak times
5 * * * * cd /path/to/x-reply-service && /path/to/venv/bin/python main.py >> /var/log/x-reply-service.log 2>&1

# For testing: Run every 15 minutes (remove after testing)
*/15 * * * * cd /path/to/x-reply-service && /path/to/venv/bin/python main.py --test-mode >> /var/log/x-reply-service.log 2>&1
```

### 9.4 Monitoring and Maintenance
```bash
# Daily log rotation
0 0 * * * /usr/sbin/logrotate /etc/logrotate.d/x-reply-service

# Weekly health check
0 0 * * 0 cd /path/to/x-reply-service && /path/to/venv/bin/python health_check.py

# Monthly cleanup of old data
0 0 1 * * cd /path/to/x-reply-service && /path/to/venv/bin/python cleanup.py --days 30
```

## 10. Testing Strategy

### 10.1 Unit Tests
```python
# Test tweet selection algorithm
def test_tweet_scoring():
    tweet = create_mock_tweet(likes=100, retweets=50, replies=25)
    score = calculate_tweet_score(tweet)
    assert 0 <= score <= 100
    assert score > 50  # High engagement should score well

# Test content safety filter
def test_content_safety():
    safe_content = "This is an interesting perspective on renewable energy."
    unsafe_content = "I hate this stupid idea and want to kill it."
    
    assert is_safe_content(safe_content)[0] == True
    assert is_safe_content(unsafe_content)[0] == False

# Test rate limiting
def test_rate_limiter():
    limiter = RateLimiter()
    # Should allow initial requests
    assert limiter.can_make_twitter_read() == True
    # Should eventually deny after limit reached
    for _ in range(300):
        limiter.can_make_twitter_read()
    assert limiter.can_make_twitter_read() == False
```

### 10.2 Integration Tests
```python
# Test API integrations with mock responses
@mock.patch('tweepy.API.user_timeline')
def test_twitter_integration(mock_timeline):
    mock_timeline.return_value = [create_mock_tweet()]
    tweets = fetch_user_timeline()
    assert len(tweets) > 0
    assert isinstance(tweets[0], Tweet)

@mock.patch('requests.post')
def test_perplexity_integration(mock_post):
    mock_post.return_value.json.return_value = {
        'choices': [{'message': {'content': 'Generated reply'}}]
    }
    reply = generate_reply("Test tweet content")
    assert reply == "Generated reply"
```

### 10.3 End-to-End Tests
```python
def test_full_workflow():
    """Test complete workflow in dry-run mode"""
    config = load_test_config()
    config.dry_run = True
    
    service = XReplyService(config)
    result = service.run()
    
    assert result.tweets_processed >= 0
    assert result.replies_generated >= 0
    assert len(result.errors) == 0
```

## 11. Performance Requirements

### 11.1 Response Time Targets
- **Feed Retrieval**: < 30 seconds
- **Tweet Selection**: < 10 seconds
- **Reply Generation**: < 60 seconds per reply
- **Reply Posting**: < 10 seconds per reply
- **Total Execution Time**: < 5 minutes per run

### 11.2 Throughput Requirements
- **Tweets Processed**: 50-100 tweets per hour (to select top 5)
- **Replies Generated**: 5 replies per hour
- **API Requests**: Stay within rate limits with 20% buffer

### 11.3 Resource Usage
- **Memory**: < 256MB during normal operation
- **CPU**: < 50% utilization during processing
- **Network**: < 10MB data transfer per hour
- **Storage**: < 100MB growth per month

## 12. Compliance and Legal Considerations

### 12.1 X.com Terms of Service Compliance
- Respect rate limits and API usage guidelines
- Avoid spam-like behavior patterns
- Maintain authentic engagement practices
- Follow community guidelines for content

### 12.2 Data Privacy
- Minimize data collection and storage
- Secure handling of API credentials
- No storage of personal user data beyond public tweet content
- Regular cleanup of processed data

### 12.3 Content Guidelines
- Avoid generating harmful, offensive, or misleading content
- Respect intellectual property rights
- Maintain educational and constructive tone
- Include disclaimers when appropriate

This technical requirements document provides a comprehensive foundation for implementing the X.com Auto-Reply Service with proper architecture, security, and operational considerations.

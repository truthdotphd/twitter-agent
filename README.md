# X.com Auto-Reply Service

An intelligent automated service that monitors your X.com "For You" feed, selects engaging tweets, and generates thoughtful, educational replies using Perplexity AI's web search capabilities.

## 🎯 Overview

This service automatically:
- Fetches tweets from your X.com "For You" feed every hour
- Selects the top 5 most engaging tweets using a sophisticated scoring algorithm
- Generates contrarian, educational replies using Perplexity AI with web search
- Posts replies automatically while respecting rate limits and safety guidelines

## 📋 Documentation

- **[Product Requirements Document](PRODUCT_REQUIREMENTS.md)** - Complete product specifications, features, and business requirements
- **[Technical Requirements Document](TECHNICAL_REQUIREMENTS.md)** - Detailed technical architecture, API specifications, and implementation details

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- X.com API access (API v2 with read/write permissions)
- Perplexity API subscription
- Unix-like system with cron support

### Required API Credentials

You'll need the following credentials:

#### X.com API Credentials
- Bearer Token
- API Key
- API Secret
- Access Token
- Access Token Secret

#### Perplexity API Credentials
- API Key

### Installation

```bash
# Clone the repository
git clone <repository_url>
cd x-reply-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup configuration
cp config/config.yaml.example config/config.yaml
# Edit config.yaml with your preferences

# Setup credentials securely
python setup_credentials.py
# Follow prompts to enter your API keys
```

### Configuration

Edit `config/config.yaml` to customize:

```yaml
selection:
  max_tweets_per_run: 5
  min_engagement_threshold: 10
  max_tweet_age_hours: 4
  exclude_retweets: true
  exclude_replies: true
  blacklisted_users: []
  blacklisted_keywords: []

reply:
  base_prompt: "write an impactful reply to the following so that it teaches something new and contrary to the status-quo views: {tweet_content}"
  max_reply_length: 280
  temperature: 0.7
  model: "llama-3.1-sonar-small-128k-online"

app:
  log_level: "INFO"
  dry_run: false  # Set to true for testing without posting
```

### Testing

```bash
# Test the service without posting replies
python main.py --dry-run

# Run with verbose logging
python main.py --verbose

# Test mode (processes fewer tweets for testing)
python main.py --test-mode
```

### Production Deployment

1. **Setup Cron Job**:
```bash
crontab -e
# Add this line to run every hour:
0 * * * * cd /path/to/x-reply-service && /path/to/venv/bin/python main.py >> /var/log/x-reply-service.log 2>&1
```

2. **Setup Log Rotation**:
```bash
sudo nano /etc/logrotate.d/x-reply-service
```

Add:
```
/var/log/x-reply-service.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 user user
}
```

## 🔧 Features

### Tweet Selection Algorithm
- **Engagement Scoring**: Weights likes, retweets, replies, and quotes
- **Recency Factor**: Prioritizes recent tweets (within 4 hours)
- **Content Quality Assessment**: Evaluates discussion potential
- **Author Influence**: Considers follower count and verification status
- **Smart Filtering**: Excludes inappropriate content and blacklisted users

### AI-Powered Reply Generation
- **Web Search Integration**: Uses Perplexity's real-time web search
- **Contrarian Perspectives**: Generates thoughtful counter-arguments
- **Educational Focus**: Provides valuable insights and information
- **Safety Filtering**: Prevents inappropriate or harmful content
- **Character Limit Compliance**: Ensures replies fit X.com's 280-character limit

### Safety & Compliance
- **Rate Limit Protection**: Stays well within API limits
- **Content Safety Filters**: Prevents posting harmful content
- **Account Protection**: Avoids behaviors that could lead to suspension
- **Comprehensive Logging**: Tracks all activities for monitoring

## 📊 Monitoring

### Logs
- **Application Log**: `/var/log/x-reply-service.log`
- **Error Log**: `logs/error.log`
- **Metrics Log**: `logs/metrics.log`

### Key Metrics
- Tweets processed per hour
- Replies generated and posted
- API error rates
- Processing time per run
- Content safety filter triggers

### Health Checks
```bash
# Check service status
python health_check.py

# View recent activity
tail -f /var/log/x-reply-service.log

# Check error rates
grep "ERROR" logs/error.log | tail -20
```

## 🛡️ Security

### Credential Protection
- Encrypted storage of API keys
- Environment variable isolation
- Secure file permissions (600)
- No credentials in logs or code

### Rate Limiting
- Conservative API usage (80% of limits)
- Exponential backoff on failures
- Circuit breaker pattern for API protection
- Token bucket rate limiting implementation

### Content Safety
- Multi-layer content filtering
- Blacklist support for users and keywords
- Political content detection and avoidance
- Harmful content pattern matching

## 🔍 Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify API credentials are correct
   - Check API permissions (read/write access)
   - Ensure tokens haven't expired

2. **Rate Limit Exceeded**
   - Service automatically handles rate limits
   - Check logs for excessive API usage
   - Verify rate limiting configuration

3. **No Tweets Selected**
   - Check feed access permissions
   - Verify selection criteria aren't too restrictive
   - Review blacklist settings

4. **Reply Generation Failures**
   - Verify Perplexity API key and quota
   - Check network connectivity
   - Review content safety filters

### Debug Mode
```bash
# Run with debug logging
python main.py --debug

# Check configuration
python -c "from src.config import load_config; print(load_config())"

# Test API connections
python test_apis.py
```

## 📈 Performance

### Expected Performance
- **Processing Time**: < 5 minutes per run
- **Memory Usage**: < 256MB
- **API Requests**: ~50-100 per hour
- **Success Rate**: > 95%

### Optimization Tips
- Adjust `min_engagement_threshold` to filter low-quality tweets
- Use `blacklisted_keywords` to avoid irrelevant topics
- Set appropriate `max_tweet_age_hours` to focus on recent content
- Monitor and adjust `temperature` for reply generation quality

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This service is designed to comply with X.com's Terms of Service and API guidelines. Users are responsible for:
- Ensuring their API usage complies with X.com's policies
- Monitoring generated content for appropriateness
- Respecting rate limits and community guidelines
- Using the service responsibly and ethically

The authors are not responsible for any account suspensions, API violations, or other consequences resulting from the use of this service.

## 🆘 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the documentation in `PRODUCT_REQUIREMENTS.md` and `TECHNICAL_REQUIREMENTS.md`
- Review logs for error details
- Test with `--dry-run` mode first

---

**Note**: This service requires active API subscriptions for both X.com and Perplexity. Ensure you understand the costs and rate limits before deploying to production.

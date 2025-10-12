# Twitter Agent Configuration Guide

This document describes all available environment variables for configuring the Twitter Agent.

## Quick Start

Copy the configuration below to your `.env` file and adjust values as needed:

```bash
# AI Service
AI_SERVICE=chatgpt
AI_WAIT_TIME=60
AI_RESPONSES_PER_CHAT=2

# Twitter
DELAY_BETWEEN_TWEETS=5
MAX_TWEETS_PER_SESSION=5
TWITTER_FEED_TYPE=following

# Browser
HEADLESS=false
DEBUG_MODE=false
CHROME_PROFILE_DIRECTORY=TwitterAgent
```

## Complete Configuration Reference

### AI Service Configuration

#### `AI_SERVICE`
**Default**: `perplexity`  
**Options**: `perplexity`, `chatgpt`, `gemini`  
**Description**: Which AI service to use for generating tweet responses.

```bash
AI_SERVICE=chatgpt
```

#### `AI_WAIT_TIME`
**Default**: `60`  
**Type**: Integer (seconds)  
**Description**: How long to wait for AI to generate a response.

```bash
AI_WAIT_TIME=60
```

#### `AI_RESPONSES_PER_CHAT`
**Default**: `2`  
**Type**: Integer  
**Description**: Number of responses to get before starting a fresh chat session. Helps avoid context pollution.

```bash
AI_RESPONSES_PER_CHAT=2
```

---

### Twitter Automation Configuration

#### `DELAY_BETWEEN_TWEETS`
**Default**: `5`  
**Type**: Integer (seconds)  
**Description**: Wait time between processing tweets. Set to 0 for no delay.

```bash
DELAY_BETWEEN_TWEETS=5
```

#### `MAX_TWEETS_PER_SESSION`
**Default**: `5`  
**Type**: Integer  
**Description**: Maximum number of tweets to process per session (currently runs indefinitely).

```bash
MAX_TWEETS_PER_SESSION=5
```

#### `TWITTER_FEED_TYPE`
**Default**: `following`  
**Options**: `following`, `for_you`  
**Description**: Which Twitter feed to process tweets from.

```bash
TWITTER_FEED_TYPE=following
```

---

### Browser Configuration

#### `HEADLESS`
**Default**: `false`  
**Options**: `true`, `false`  
**Description**: Run Chrome in headless mode (no visible browser window).

```bash
HEADLESS=false
```

#### `DEBUG_MODE`
**Default**: `false`  
**Options**: `true`, `false`  
**Description**: Enable verbose debug logging for troubleshooting.

```bash
DEBUG_MODE=true
```

#### `CHROME_PROFILE_DIRECTORY`
**Default**: `TwitterAgent`  
**Type**: String  
**Description**: Name of the Chrome profile subdirectory for login persistence.

```bash
CHROME_PROFILE_DIRECTORY=TwitterAgent
```

#### `CHROME_PROFILE_DIR`
**Default**: `.chrome_automation_profile_twitter`  
**Type**: String  
**Description**: Base directory name for Chrome profile (relative to home directory).

```bash
CHROME_PROFILE_DIR=.chrome_automation_profile_twitter
```

---

### Validation Configuration

#### `MIN_RESPONSE_LENGTH`
**Default**: `20`  
**Type**: Integer (characters)  
**Description**: Minimum length for valid AI responses. Shorter responses are rejected as errors.

```bash
MIN_RESPONSE_LENGTH=20
```

#### `MIN_TWEET_LENGTH`
**Default**: `30`  
**Type**: Integer (characters)  
**Description**: Minimum length for tweets to process. Shorter tweets are skipped.

```bash
MIN_TWEET_LENGTH=30
```

#### `MIN_UNIQUE_WORD_RATIO`
**Default**: `0.3`  
**Type**: Float (0.0-1.0)  
**Description**: Minimum ratio of unique words in AI responses. Responses with less unique words are considered repetitive and rejected.

Example: A response with 30% or more unique words passes, less than 30% fails.

```bash
MIN_UNIQUE_WORD_RATIO=0.3
```

#### `MIN_WORDS_FOR_REPETITION_CHECK`
**Default**: `3`  
**Type**: Integer  
**Description**: Minimum word count before checking for repetition. Responses with fewer words skip the repetition check.

```bash
MIN_WORDS_FOR_REPETITION_CHECK=3
```

---

### Retry Configuration

#### `MAX_AI_RETRIES`
**Default**: `3`  
**Type**: Integer  
**Description**: Maximum number of times to retry AI queries that return errors or invalid responses.

```bash
MAX_AI_RETRIES=3
```

#### `MAX_EXTRACTION_ATTEMPTS`
**Default**: `5`  
**Type**: Integer  
**Description**: Maximum attempts to extract tweets from timeline before giving up.

```bash
MAX_EXTRACTION_ATTEMPTS=5
```

#### `NO_TWEETS_THRESHOLD`
**Default**: `3`  
**Type**: Integer  
**Description**: Number of failed attempts to find tweets before refreshing Twitter tab.

```bash
NO_TWEETS_THRESHOLD=3
```

#### `SCROLL_ATTEMPTS`
**Default**: `3`  
**Type**: Integer  
**Description**: Number of times to scroll down when loading more tweets.

```bash
SCROLL_ATTEMPTS=3
```

#### `RETRY_WAIT_TIME`
**Default**: `2`  
**Type**: Integer (seconds)  
**Description**: Wait time between AI retry attempts.

```bash
RETRY_WAIT_TIME=2
```

---

### UI Interaction Configuration

#### `BUTTON_WAIT_TIMEOUT`
**Default**: `10`  
**Type**: Integer (seconds)  
**Description**: Maximum time to wait for reply button to become enabled after typing response.

```bash
BUTTON_WAIT_TIMEOUT=10
```

---

### Data Persistence Configuration

#### `PROCESSED_TWEETS_FILE`
**Default**: `processed_tweets.json`  
**Type**: String (filename)  
**Description**: Filename for storing processed tweet hashes to avoid duplicates.

```bash
PROCESSED_TWEETS_FILE=processed_tweets.json
```

#### `SAVE_FREQUENCY`
**Default**: `5`  
**Type**: Integer  
**Description**: How often to save processed tweets file (every N tweets).

```bash
SAVE_FREQUENCY=5
```

---

## Configuration Profiles

### Development Profile (Verbose Logging)
```bash
DEBUG_MODE=true
HEADLESS=false
AI_WAIT_TIME=30
MAX_AI_RETRIES=5
```

### Production Profile (Fast & Reliable)
```bash
DEBUG_MODE=false
HEADLESS=true
AI_WAIT_TIME=60
MAX_AI_RETRIES=3
SAVE_FREQUENCY=10
```

### Conservative Profile (Avoid Rate Limits)
```bash
DELAY_BETWEEN_TWEETS=30
AI_RESPONSES_PER_CHAT=1
MAX_AI_RETRIES=2
RETRY_WAIT_TIME=5
```

### Aggressive Profile (Maximum Throughput)
```bash
DELAY_BETWEEN_TWEETS=0
AI_RESPONSES_PER_CHAT=5
MAX_AI_RETRIES=3
RETRY_WAIT_TIME=1
```

---

## Tips & Best Practices

### 1. **AI Service Selection**
- **ChatGPT**: Best quality, slower, requires Thinking model
- **Perplexity**: Balanced quality and speed, good for factual content
- **Gemini**: Fast, good for general responses

### 2. **Response Quality**
- Increase `MIN_RESPONSE_LENGTH` for longer, more detailed responses
- Adjust `MIN_UNIQUE_WORD_RATIO` if getting too many rejections

### 3. **Performance**
- Set `HEADLESS=true` for faster performance in production
- Reduce `AI_WAIT_TIME` if responses are typically fast
- Increase `SAVE_FREQUENCY` to reduce I/O overhead

### 4. **Reliability**
- Increase `MAX_AI_RETRIES` if experiencing frequent errors
- Increase `BUTTON_WAIT_TIMEOUT` for slower machines
- Increase `NO_TWEETS_THRESHOLD` if tweets load slowly

### 5. **Rate Limiting**
- Increase `DELAY_BETWEEN_TWEETS` if hitting rate limits
- Reduce `AI_RESPONSES_PER_CHAT` to use fresh AI sessions more often
- Increase `RETRY_WAIT_TIME` to be more conservative

### 6. **Debugging**
- Enable `DEBUG_MODE=true` to see all validation checks
- Use `HEADLESS=false` to watch the automation in real-time
- Check logs for configuration values at startup

---

## Environment Variable Precedence

1. **.env file** (highest priority)
2. **System environment variables**
3. **Default values** (lowest priority)

To override a setting temporarily:
```bash
AI_SERVICE=gemini python3 twitter_agent_selenium.py
```

---

## Validation

All configuration values are validated at startup. Invalid values will use defaults:

```
⚙️ Twitter Agent Configuration:
   🤖 AI Service: CHATGPT
   📱 Tweet delay: 5s
   🎯 Max tweets per session: 5
   ⏱️ AI wait time: 60s
   💬 Responses per chat: 2
   👻 Headless mode: False
   📺 Twitter feed: Following

⚙️ Advanced Configuration:
   📏 Min response length: 20 chars
   📏 Min tweet length: 30 chars
   🔄 Max AI retries: 3
   🔄 Max extraction attempts: 5
   💾 Save frequency: every 5 tweets
   📁 Processed tweets file: processed_tweets.json
   📁 Chrome profile dir: .chrome_automation_profile_twitter
```

---

## See Also

- [Error Detection Guide](ERROR_DETECTION.md)
- [Profile Management Guide](PROFILE_MANAGEMENT.md)
- [AI Services Documentation](AI_SERVICES.md)

---

**Last Updated**: Configuration system refactored to use environment variables  
**Total Variables**: 20 configurable options


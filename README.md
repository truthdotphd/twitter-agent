# Twitter Agent Browser

An automated browser application that processes tweets from your X.com timeline and generates responses using Perplexity.ai.

## 🎯 What This Does

1. **Extracts Tweets**: Navigates to X.com and extracts tweets from your "For You" timeline
2. **Processes with Perplexity**: Sends each tweet content to Perplexity.ai with a custom prompt
3. **Posts Responses**: Takes the Perplexity response and posts it as a reply to the original tweet

## 🚀 Quick Start

### Prerequisites

- Python 3.11+ (installed via Homebrew)
- Google Chrome browser
- Active X.com (Twitter) account (logged in)
- Active Perplexity.ai account (logged in)

### Installation

1. **Clone/Navigate to the project directory**
   ```bash
   cd /Users/amirerfaneshratifar/workspace/twitter-agent-browser
   ```

2. **Activate the virtual environment**
   ```bash
   source .venv/bin/activate
   ```

3. **Configure settings (optional)**
   ```bash
   cp .env.example .env
   # Edit .env with your preferred settings
   ```

4. **Run the application**
   ```bash
   python run_agent.py
   ```

## ⚙️ Configuration

Edit the `.env` file to customize behavior:

```env
# Browser settings
HEADLESS=false                    # Set to true to run without visible browser

# Rate limiting (in seconds)
DELAY_BETWEEN_TWEETS=30          # Wait time between processing tweets
MAX_TWEETS_PER_SESSION=5         # Maximum tweets to process per run

# Perplexity settings
PERPLEXITY_WAIT_TIME=15          # Time to wait for Perplexity response
```

## 📂 Files

- `twitter_agent.py` - Basic implementation
- `twitter_agent_advanced.py` - Advanced implementation (recommended)
- `run_agent.py` - Interactive runner script
- `.env` - Configuration file
- `requirements.txt` - Python dependencies

## 🎨 The Prompt

The agent uses this prompt template for Perplexity:

```
Rules: Do NOT use double hyphens, do NOT use double dashes, do NOT use double stars at all!
Do not include citations or references. Limit the response length to 280 characters.
Write a concise impactful paragraph to the following so that it teaches something new and
contrary to the status-quo views:

Content:
{tweet_content}

I repeat the most important rule: Do NOT use double hyphens, do NOT use double dashes,
do NOT use double stars at all!
```

## 🔧 Advanced Features

The advanced agent (`twitter_agent_advanced.py`) includes:

- Better tweet extraction using HTML parsing
- Robust browser tab management
- Improved error handling
- Tweet deduplication
- More reliable element detection
- Contextual tweet posting when direct replies fail

## ✨ Recent Improvements

**Latest enhancements (see `IMPROVEMENTS.md` for details):**

- **100+ Character Filter**: Only processes substantial tweets (100+ characters)
- **Persistent Tweet Tracking**: Avoids reprocessing tweets across sessions using JSON storage
- **Enhanced Perplexity Integration**: Fixed "element not interactable" errors with multiple fallback methods

## ⚠️ Important Notes

### Before Running

1. **Log into X.com** in your default Chrome browser
2. **Log into Perplexity.ai** in the same browser
3. **Ensure you're on the "For You" timeline** on X.com

### Rate Limiting

- The app includes built-in delays to avoid rate limiting
- Default: 30 seconds between tweets, max 5 tweets per session
- Adjust these values in `.env` as needed

### Browser Behavior

- The browser will remain open after completion for inspection
- Press Enter in the terminal to close the browser when done
- The browser uses your existing Chrome profile to access logged-in accounts

## 🐛 Troubleshooting

### Common Issues

1. **"Not logged in" error**
   - Manually log into X.com and Perplexity.ai in Chrome
   - Restart the script

2. **No tweets extracted**
   - Ensure you're on the "For You" timeline
   - Try scrolling manually to load tweets
   - Check if the page has finished loading

3. **"Perplexity input field not found" error** ⭐ **FIXED**
   - The app now tries 11+ different ways to find the input field
   - Set `DEBUG_MODE=true` in `.env` for detailed troubleshooting
   - Run `python test_perplexity.py` to test just Perplexity integration
   - See `PERPLEXITY_FIXES.md` for detailed fix information

4. **Perplexity response not found**
   - Increase `PERPLEXITY_WAIT_TIME` in `.env`
   - The app now uses 15+ strategies to extract responses
   - Enable debug mode to see what's happening
   - Check if Perplexity.ai is accessible and working

5. **Failed to post replies**
   - The app will fall back to posting new tweets with context
   - Check X.com rate limits and posting restrictions

### Debug Mode

Set these in `.env` to debug issues:
```bash
HEADLESS=false     # Watch browser automation in real-time
DEBUG_MODE=true    # Enable detailed logging and troubleshooting
```

### Testing Individual Components

- **Test Perplexity only**: `python test_perplexity.py`
- **Test full setup**: `python test_setup.py`

## 🚨 Ethical Considerations

- **Use Responsibly**: This tool automates social media interactions
- **Respect Rate Limits**: Don't overwhelm platforms with requests
- **Content Quality**: Review generated responses for appropriateness
- **Platform Terms**: Ensure compliance with X.com and Perplexity.ai terms of service

## 📜 License

This project is for educational and personal use. Users are responsible for complying with all applicable terms of service and applicable laws.

## 🔄 Updates

To update dependencies:
```bash
source .venv/bin/activate
uv pip install --upgrade browser-use selenium python-dotenv aiohttp beautifulsoup4
```
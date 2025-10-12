# AI Services Configuration

The Twitter Agent now supports multiple AI services for generating tweet responses. You can choose between Perplexity, ChatGPT, and Google Gemini.

## Configuration

Set the following environment variables in your `.env` file:

### AI Service Selection

```bash
# Choose which AI service to use
# Options: perplexity, chatgpt, gemini
# Default: perplexity
AI_SERVICE=perplexity
```

### AI Service Settings

```bash
# Wait time for AI service to generate response (in seconds)
# For Perplexity with GPT-5 Thinking: 60s recommended
# For ChatGPT: 30s usually sufficient
# For Gemini: 30s usually sufficient
AI_WAIT_TIME=60

# Number of responses per chat session before refreshing
# Perplexity: 2 recommended (to avoid stale responses with GPT-5)
# ChatGPT: 5 recommended
# Gemini: 5 recommended
AI_RESPONSES_PER_CHAT=2
```

## Supported AI Services

### 1. Perplexity.ai (Default)
- **URL**: https://www.perplexity.ai/
- **Model**: GPT-5 Thinking (or o3)
- **Sources**: Web, Academic, Social, Finance (automatically configured)
- **Best for**: Research-heavy responses with citations
- **Recommended settings**:
  - `AI_WAIT_TIME=60` (GPT-5 Thinking is slower)
  - `AI_RESPONSES_PER_CHAT=2` (to avoid response staleness)

### 2. ChatGPT
- **URL**: https://chatgpt.com/
- **Model**: Latest GPT model with web search
- **Features**: Automatically enables web search mode
- **Best for**: Conversational, engaging responses
- **Recommended settings**:
  - `AI_WAIT_TIME=30`
  - `AI_RESPONSES_PER_CHAT=5`

### 3. Google Gemini
- **URL**: https://gemini.google.com/
- **Model**: Latest Gemini model
- **Best for**: Fast, high-quality responses
- **Recommended settings**:
  - `AI_WAIT_TIME=30`
  - `AI_RESPONSES_PER_CHAT=5`

## Setup Instructions

### First Time Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   Create a `.env` file with your preferred AI service:
   ```bash
   AI_SERVICE=perplexity  # or chatgpt or gemini
   AI_WAIT_TIME=60
   AI_RESPONSES_PER_CHAT=2
   ```

3. **Login to AI Service**
   - The agent will open the AI service in a browser
   - Log in manually on first run
   - Credentials will be saved in Chrome profile for future runs

### Switching Between Services

To switch AI services, simply update the `AI_SERVICE` in your `.env` file:

```bash
# Switch to ChatGPT
AI_SERVICE=chatgpt

# Or switch to Gemini
AI_SERVICE=gemini

# Or back to Perplexity
AI_SERVICE=perplexity
```

Then restart the agent.

## Architecture

The refactored code uses a service-based architecture:

### Service Modules

1. **`perplexity_service.py`** - Perplexity.ai integration
2. **`chatgpt_service.py`** - ChatGPT integration
3. **`gemini_service.py`** - Google Gemini integration

### Service Interface

Each service implements:
- `navigate_new_tab()` - Open AI service in new tab
- `check_login_status()` - Verify login
- `find_input_field()` - Locate input field
- `query(prompt)` - Submit query and get response
- `refresh()` - Start fresh chat session
- `switch_to_tab()` - Switch to AI service tab

### Main Agent

**`twitter_agent_selenium.py`** - Main Twitter agent that:
- Manages Twitter interactions
- Selects and initializes AI service
- Coordinates between Twitter and AI service
- Handles tweet processing workflow

## Response Quality

### Response Format

All AI services receive the same prompt template:
```
Rules: keep your response less than 500 characters. avoid all the followings in your response: avoid double dashes --, avoid double hyphens like --,avoid **,avoid references,avoid citations,avoid math formulas. Do NOT ask me anything further and only output the response and start the response with a full sentence that doesn't start with numbers. Write a short fact-based impactful, entertaining, fun and amusing response teaching a fresh, complementary insight about the following text in a human-like entertaining language: '{tweet_content}'
```

### Service-Specific Behaviors

**Perplexity (GPT-5 Thinking)**
- More detailed, research-backed responses
- Slower (60s wait recommended)
- May include citations (filtered out)
- Best for technical/factual content

**ChatGPT**
- Conversational and engaging
- Faster (30s wait)
- Web search enabled for current info
- Best for general engagement

**Gemini**
- Fast and efficient
- Good balance of detail and speed
- Versatile for all content types

## Troubleshooting

### Service Not Responding

1. Check if you're logged in
2. Increase `AI_WAIT_TIME` if responses are timing out
3. Check browser console for errors
4. Try refreshing with `AI_RESPONSES_PER_CHAT=1`

### Stale Responses

If you notice repeated responses:
1. Decrease `AI_RESPONSES_PER_CHAT` (forces more frequent refreshes)
2. Restart the agent
3. Check that response deduplication is working

### Login Issues

- Clear Chrome automation profile: `rm -rf ~/.chrome_automation_profile`
- Log in manually when prompted
- Disable 2FA if causing issues (not recommended for production)

## Best Practices

1. **Start with Perplexity** - It's the default and well-tested
2. **Monitor Response Quality** - Switch services if quality degrades
3. **Adjust Wait Times** - Based on your network speed and service performance
4. **Use Fresh Sessions** - Lower `AI_RESPONSES_PER_CHAT` for better quality
5. **Log and Review** - Enable `DEBUG_MODE=true` to see detailed logs

## Migration from Old Version

If you're upgrading from the old version:

**Old Configuration**:
```bash
PERPLEXITY_WAIT_TIME=60
PERPLEXITY_RESPONSES_PER_CHAT=2
```

**New Configuration** (backward compatible):
```bash
AI_SERVICE=perplexity  # New!
AI_WAIT_TIME=60  # Replaces PERPLEXITY_WAIT_TIME
AI_RESPONSES_PER_CHAT=2  # Replaces PERPLEXITY_RESPONSES_PER_CHAT
```

Old environment variables still work but are deprecated.



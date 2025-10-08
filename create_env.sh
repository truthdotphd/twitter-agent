#!/bin/bash

# Helper script to create .env file with correct Chrome profile path

echo "🔧 Creating .env file for Twitter Agent..."
echo ""

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    USER_HOME="$HOME"
    CHROME_DATA_DIR="$USER_HOME/Library/Application Support/Google/Chrome"
    echo "✅ Detected macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    USER_HOME="$HOME"
    CHROME_DATA_DIR="$USER_HOME/.config/google-chrome"
    echo "✅ Detected Linux"
else
    # Windows or other
    echo "⚠️  Windows detected or unknown OS"
    echo "Please manually create .env file with your Chrome profile path"
    echo "Example: C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Google\\Chrome\\User Data"
    exit 1
fi

# Check if Chrome profile exists
if [ ! -d "$CHROME_DATA_DIR" ]; then
    echo "❌ Chrome profile directory not found at: $CHROME_DATA_DIR"
    echo "Please install Chrome or update the path manually"
    exit 1
fi

echo "✅ Found Chrome profile at: $CHROME_DATA_DIR"
echo ""

# Create .env file
cat > .env << EOF
# Twitter Agent Configuration
# Generated automatically on $(date)

# Chrome Profile Settings (IMPORTANT for avoiding login issues)
# IMPORTANT: Close ALL Chrome windows before running the script!
CHROME_USER_DATA_DIR=$CHROME_DATA_DIR
CHROME_PROFILE_DIRECTORY=Default

# Twitter Settings
DELAY_BETWEEN_TWEETS=5
MAX_TWEETS_PER_SESSION=5
TWITTER_FEED_TYPE=following

# Perplexity Settings
PERPLEXITY_WAIT_TIME=60
PERPLEXITY_RESPONSES_PER_CHAT=2

# Display Settings
HEADLESS=false
DEBUG_MODE=false
EOF

echo "✅ Created .env file successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Make sure you're logged into X.com in Chrome"
echo "2. Close ALL Chrome windows"
echo "3. Run: python twitter_agent_selenium.py"
echo ""
echo "⚠️  IMPORTANT: You must close all Chrome windows before running the script!"

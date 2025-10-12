#!/bin/bash
# Clear old Chrome profiles for Twitter Agent
# This will force a fresh start with proper profile management

echo "🧹 Clearing old Chrome profiles for Twitter Agent..."
echo ""

# Remove old profile directory
if [ -d "$HOME/.chrome_automation_profile" ]; then
    echo "📁 Found old profile directory: $HOME/.chrome_automation_profile"
    rm -rf "$HOME/.chrome_automation_profile"
    echo "✅ Removed old profile directory"
else
    echo "ℹ️  No old profile directory found"
fi

# Remove new profile directory (for complete reset)
if [ -d "$HOME/.chrome_automation_profile_twitter" ]; then
    echo "📁 Found new profile directory: $HOME/.chrome_automation_profile_twitter"
    read -p "⚠️  Do you want to remove it too? This will require re-login. (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$HOME/.chrome_automation_profile_twitter"
        echo "✅ Removed new profile directory"
    else
        echo "⏭️  Keeping new profile directory"
    fi
else
    echo "ℹ️  No new profile directory found"
fi

echo ""
echo "✅ Profile cleanup complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Run: python3 twitter_agent_selenium.py"
echo "  2. Log into X.com when prompted"
echo "  3. Log into your AI service (ChatGPT/Perplexity/Gemini) when prompted"
echo "  4. After first successful run, logins will be remembered!"
echo ""


#!/bin/bash

echo "🔓 Approving ChromeDriver for macOS..."
echo ""

# Clear all extended attributes
echo "📝 Step 1: Clearing macOS security attributes..."
xattr -cr ~/bin/chromedriver
echo "✅ Attributes cleared"
echo ""

# Try to run chromedriver once to trigger approval
echo "📝 Step 2: Testing ChromeDriver..."
echo "If you see a security warning, do the following:"
echo "  1. Click 'Cancel' on the warning"
echo "  2. Go to System Settings > Privacy & Security"
echo "  3. Click 'Allow Anyway' next to the ChromeDriver message"
echo "  4. Run this script again"
echo ""
echo "Starting ChromeDriver test in 3 seconds..."
sleep 3

~/bin/chromedriver --version &
CHROME_PID=$!
sleep 2
kill $CHROME_PID 2>/dev/null

echo ""
echo "✅ If you saw the version number above, ChromeDriver is approved!"
echo "✅ If you saw a security warning, follow the steps above and run this again."
echo ""
echo "After approval, run: ./run_agent.sh"

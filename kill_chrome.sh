#!/bin/bash

echo "🔴 Closing all Chrome instances..."
echo ""

# Kill all Chrome processes
killall "Google Chrome" 2>/dev/null
killall "Google Chrome Helper" 2>/dev/null
killall "Google Chrome Helper (Renderer)" 2>/dev/null
killall "Google Chrome Helper (GPU)" 2>/dev/null

# Wait a moment
sleep 2

# Check if any Chrome processes are still running
CHROME_PROCS=$(ps aux | grep -i "Google Chrome" | grep -v grep | wc -l)

if [ $CHROME_PROCS -eq 0 ]; then
    echo "✅ All Chrome instances closed successfully"
    echo ""
    echo "You can now run: python twitter_agent_selenium.py"
else
    echo "⚠️  Some Chrome processes are still running:"
    ps aux | grep -i "Google Chrome" | grep -v grep
    echo ""
    echo "Try running this command manually:"
    echo "  killall -9 'Google Chrome'"
fi

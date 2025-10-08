#!/bin/bash

# Run the Twitter agent with the correct venv

echo "🚀 Starting Twitter Agent with venv..."
echo ""

# Check if venv exists
if [ ! -d "./venv" ]; then
    echo "❌ Error: venv not found at ./venv/"
    echo "Please create a virtual environment first:"
    echo "  python3 -m venv venv"
    exit 1
fi

# Activate venv and run the agent
source ./venv/bin/activate
python3 twitter_agent_selenium.py

# Deactivate when done (if script exits normally)
deactivate

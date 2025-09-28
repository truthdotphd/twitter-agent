#!/usr/bin/env python3
"""
Simple runner for the Twitter Agent
"""

import sys
import asyncio
import os

def print_banner():
    print("="*60)
    print("🤖 TWITTER AGENT BROWSER")
    print("="*60)
    print("This agent will:")
    print("1. Navigate to X.com and extract tweets from your timeline")
    print("2. Send each tweet to Perplexity.ai with a custom prompt")
    print("3. Post the Perplexity response as a reply")
    print("="*60)
    print()

def check_requirements():
    """Check if all requirements are met"""
    print("Checking requirements...")

    # Check if virtual environment is activated
    if not os.environ.get('VIRTUAL_ENV'):
        print("⚠️  WARNING: Virtual environment not detected.")
        print("   Consider activating with: source .venv/bin/activate")
        print()

    # Check if .env exists
    if not os.path.exists('.env'):
        print("⚠️  WARNING: .env file not found.")
        print("   Copy .env.example to .env and configure as needed.")
        print()

    print("✅ Requirements check complete")
    print()

def show_menu():
    print("Choose which version to run:")
    print("1. Selenium Agent (twitter_agent_selenium.py) - RECOMMENDED")
    print("2. Basic Agent (twitter_agent.py)")
    print("3. Advanced Agent (twitter_agent_advanced.py)")
    print("4. Exit")
    print()

def run_selenium_agent():
    from twitter_agent_selenium import main
    main()

async def run_basic_agent():
    from twitter_agent import main
    await main()

async def run_advanced_agent():
    from twitter_agent_advanced import main
    await main()

def main():
    print_banner()
    check_requirements()

    while True:
        show_menu()
        choice = input("Enter your choice (1-4): ").strip()

        if choice == '1':
            print("\n🚀 Starting Selenium Agent...")
            run_selenium_agent()
            break
        elif choice == '2':
            print("\n🚀 Starting Basic Agent...")
            asyncio.run(run_basic_agent())
            break
        elif choice == '3':
            print("\n🚀 Starting Advanced Agent...")
            asyncio.run(run_advanced_agent())
            break
        elif choice == '4':
            print("👋 Goodbye!")
            sys.exit(0)
        else:
            print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")
            print()

if __name__ == "__main__":
    main()
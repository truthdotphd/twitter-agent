#!/usr/bin/env python3
"""
Test script specifically for Perplexity.ai integration
"""

import os
import time
from dotenv import load_dotenv
from twitter_agent_selenium import SeleniumTwitterAgent
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_perplexity_integration():
    """Test only the Perplexity.ai integration"""
    print("="*60)
    print("🧪 TESTING PERPLEXITY.AI INTEGRATION")
    print("="*60)

    # Enable debug mode temporarily
    os.environ['DEBUG_MODE'] = 'true'

    agent = SeleniumTwitterAgent()

    # Setup driver
    if not agent.setup_driver():
        print("❌ Failed to setup Chrome driver")
        return False

    try:
        print("\n1. Testing Perplexity navigation...")
        if not agent.navigate_to_perplexity():
            print("❌ Failed to navigate to Perplexity")
            return False

        print("✅ Successfully navigated to Perplexity")

        print("\n2. Testing Perplexity query...")
        test_content = "The sky is blue because of Rayleigh scattering."

        response = agent.query_perplexity(test_content)

        if response:
            print(f"✅ Successfully got response from Perplexity:")
            print(f"   Length: {len(response)} characters")
            print(f"   Content: {response}")
            return True
        else:
            print("❌ Failed to get response from Perplexity")
            return False

    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

    finally:
        print("\nBrowser will remain open for manual inspection...")
        input("Press Enter to close browser...")
        if agent.driver:
            agent.driver.quit()

if __name__ == "__main__":
    success = test_perplexity_integration()

    if success:
        print("\n🎉 Perplexity integration test PASSED!")
    else:
        print("\n💥 Perplexity integration test FAILED!")
        print("\nTroubleshooting tips:")
        print("1. Make sure you're logged into Perplexity.ai in your default Chrome browser")
        print("2. Try manually visiting perplexity.ai and ensuring it works")
        print("3. Set DEBUG_MODE=true in .env for more detailed logging")
        print("4. Check if Perplexity.ai has changed their UI recently")
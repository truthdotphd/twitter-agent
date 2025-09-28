#!/usr/bin/env python3
"""
Quick test to verify the contenteditable fix works
"""

import time
import logging
from twitter_agent_selenium import SeleniumTwitterAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_quick_fix():
    """Quick test of the contenteditable fix"""
    
    agent = SeleniumTwitterAgent()
    agent.setup_driver()
    
    try:
        logger.info("🚀 Testing contenteditable fix...")
        
        # Navigate to Perplexity
        agent.driver.get("https://perplexity.ai")
        time.sleep(5)
        
        # Test the query method with a short prompt
        test_prompt = "What is 2+2?"
        
        logger.info("🧪 Testing query_perplexity method...")
        response = agent.query_perplexity(test_prompt)
        
        if response:
            logger.info(f"✅ SUCCESS! Got response: {response[:100]}...")
        else:
            logger.warning("⚠️ No response received")
        
        logger.info("🔍 Test completed - check logs above for 'Detected contenteditable div' message")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        agent.driver.quit()
        logger.info("🏁 Test finished")

if __name__ == "__main__":
    test_quick_fix()

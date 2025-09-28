#!/usr/bin/env python3
"""
Test script to verify the reply fixes work correctly
"""

import time
import logging
from twitter_agent_selenium import SeleniumTwitterAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_reply_fixes():
    """Test the reply fixes"""
    
    agent = SeleniumTwitterAgent()
    agent.setup_driver()
    
    try:
        logger.info("🚀 Testing reply fixes...")
        
        # Navigate to Perplexity first to test response extraction
        agent.driver.get("https://perplexity.ai")
        time.sleep(5)
        
        # Test query with a simple prompt
        test_prompt = "What are the benefits of renewable energy?"
        
        logger.info("🧪 Testing Perplexity response extraction...")
        response = agent.query_perplexity(test_prompt)
        
        if response:
            logger.info(f"✅ SUCCESS! Got response length: {len(response)} characters")
            logger.info(f"Response preview: {response[:200]}...")
            
            # Check if it's the prompt or actual response
            if "rules:" in response.lower() or "do not use double hyphens" in response.lower():
                logger.error("❌ PROBLEM: Got prompt instead of response!")
            else:
                logger.info("✅ Response looks correct (not the prompt)")
                
        else:
            logger.warning("⚠️ No response received")
        
        logger.info("🔍 Test completed - check logs for response extraction results")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        agent.driver.quit()
        logger.info("🏁 Test finished")

if __name__ == "__main__":
    test_reply_fixes()

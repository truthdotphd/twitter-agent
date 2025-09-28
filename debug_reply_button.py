#!/usr/bin/env python3
"""
Debug script to understand why the reply button is disabled
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_reply_button():
    """Debug the reply button issue"""
    
    # Setup Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        logger.info("🚀 Debugging reply button issue...")
        
        # Navigate to Twitter
        logger.info("📍 Navigating to Twitter...")
        driver.get("https://twitter.com")
        time.sleep(5)
        
        # Find a tweet and click reply
        logger.info("🔍 Looking for a tweet to reply to...")
        tweets = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')
        
        if not tweets:
            logger.error("No tweets found")
            return
            
        tweet = tweets[0]
        logger.info("Found tweet, looking for reply button...")
        
        # Find reply button
        reply_button = None
        reply_selectors = [
            '[data-testid="reply"]',
            '[aria-label*="Reply"]',
            'button[data-testid="reply"]'
        ]
        
        for selector in reply_selectors:
            try:
                reply_button = tweet.find_element(By.CSS_SELECTOR, selector)
                if reply_button.is_displayed():
                    logger.info(f"Found reply button using: {selector}")
                    break
            except:
                continue
        
        if not reply_button:
            logger.error("Could not find reply button")
            return
            
        # Click reply button
        reply_button.click()
        logger.info("Clicked reply button")
        time.sleep(3)
        
        # Find compose area
        compose_selectors = [
            '[data-testid="tweetTextarea_0"]',
            'div[contenteditable="true"]',
            'textarea'
        ]
        
        compose_element = None
        for selector in compose_selectors:
            try:
                compose_element = driver.find_element(By.CSS_SELECTOR, selector)
                if compose_element.is_displayed():
                    logger.info(f"Found compose area using: {selector}")
                    break
            except:
                continue
        
        if not compose_element:
            logger.error("Could not find compose area")
            return
            
        # Test different content setting methods
        test_content = "This is a test reply to debug the button issue."
        
        logger.info("🧪 Testing content setting methods...")
        
        # Method 1: textContent
        logger.info("Method 1: textContent")
        driver.execute_script("arguments[0].textContent = arguments[1];", compose_element, test_content)
        time.sleep(1)
        
        # Check content and button state
        content_check = driver.execute_script("return arguments[0].textContent;", compose_element)
        logger.info(f"Content after textContent: '{content_check[:50]}...'")
        
        # Find post button and check state
        post_button = None
        post_selectors = [
            '[data-testid="tweetButtonInline"]',
            '[data-testid="tweetButton"]',
            'button[data-testid="tweetButtonInline"]'
        ]
        
        for selector in post_selectors:
            try:
                post_button = driver.find_element(By.CSS_SELECTOR, selector)
                if post_button.is_displayed():
                    logger.info(f"Found post button using: {selector}")
                    break
            except:
                continue
        
        if post_button:
            enabled = post_button.is_enabled()
            disabled_attr = driver.execute_script("return arguments[0].disabled;", post_button)
            aria_disabled = driver.execute_script("return arguments[0].getAttribute('aria-disabled');", post_button)
            classes = driver.execute_script("return arguments[0].className;", post_button)
            
            logger.info(f"Button state - enabled: {enabled}, disabled attr: {disabled_attr}, aria-disabled: {aria_disabled}")
            logger.info(f"Button classes: {classes}")
            
            # Try triggering events
            logger.info("Triggering events...")
            driver.execute_script("""
                var element = arguments[0];
                element.focus();
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
            """, compose_element)
            
            time.sleep(2)
            
            # Check button state again
            enabled_after = post_button.is_enabled()
            logger.info(f"Button enabled after events: {enabled_after}")
            
        else:
            logger.error("Could not find post button")
        
        # Keep browser open for manual inspection
        logger.info("🔍 Browser will remain open for manual inspection...")
        input("Press Enter to close browser...")
        
    except Exception as e:
        logger.error(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()
        logger.info("🏁 Debug completed")

if __name__ == "__main__":
    debug_reply_button()

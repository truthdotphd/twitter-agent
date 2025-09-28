#!/usr/bin/env python3
"""
Test script specifically for debugging Perplexity SPA issues
"""

import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_perplexity_spa():
    """Test Perplexity SPA loading and element detection"""
    
    # Setup Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        logger.info("🚀 Starting Perplexity SPA test...")
        
        # Navigate to Perplexity
        logger.info("📍 Navigating to Perplexity.ai...")
        driver.get("https://perplexity.ai")
        
        # Wait for initial load
        time.sleep(3)
        logger.info(f"📄 Page title: {driver.title}")
        logger.info(f"🔗 Current URL: {driver.current_url}")
        
        # Check if SPA root exists
        try:
            root_element = driver.find_element(By.ID, "root")
            logger.info("✅ Found root element")
            
            # Wait for SPA to populate
            logger.info("⏳ Waiting for SPA to load content...")
            max_wait = 30
            wait_time = 0
            
            while wait_time < max_wait:
                root_text = root_element.text.strip()
                if len(root_text) > 100:  # Arbitrary threshold
                    logger.info(f"✅ SPA loaded! Root text length: {len(root_text)}")
                    logger.info(f"📝 Root text snippet: {root_text[:200]}...")
                    break
                
                time.sleep(1)
                wait_time += 1
                
                if wait_time % 5 == 0:
                    logger.info(f"⏳ Still waiting... ({wait_time}/{max_wait}s)")
            
            if wait_time >= max_wait:
                logger.warning("⚠️ SPA loading timeout")
                
        except Exception as e:
            logger.error(f"❌ Could not find root element: {e}")
        
        # Look for input elements
        logger.info("🔍 Searching for input elements...")
        
        # Check different element types
        textareas = driver.find_elements(By.TAG_NAME, "textarea")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        contenteditable_divs = driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true']")
        textbox_divs = driver.find_elements(By.CSS_SELECTOR, "div[role='textbox']")
        
        logger.info(f"📊 Found {len(textareas)} textareas")
        logger.info(f"📊 Found {len(inputs)} inputs")
        logger.info(f"📊 Found {len(contenteditable_divs)} contenteditable divs")
        logger.info(f"📊 Found {len(textbox_divs)} textbox role divs")
        
        # Check visible elements
        visible_textareas = [t for t in textareas if t.is_displayed()]
        visible_inputs = [i for i in inputs if i.is_displayed()]
        visible_contenteditable = [d for d in contenteditable_divs if d.is_displayed()]
        visible_textbox = [d for d in textbox_divs if d.is_displayed()]
        
        logger.info(f"👁️ {len(visible_textareas)} visible textareas")
        logger.info(f"👁️ {len(visible_inputs)} visible inputs")
        logger.info(f"👁️ {len(visible_contenteditable)} visible contenteditable divs")
        logger.info(f"👁️ {len(visible_textbox)} visible textbox divs")
        
        # Detailed analysis of visible elements
        all_interactive_elements = []
        
        for i, textarea in enumerate(visible_textareas):
            try:
                placeholder = textarea.get_attribute("placeholder") or ""
                aria_label = textarea.get_attribute("aria-label") or ""
                data_testid = textarea.get_attribute("data-testid") or ""
                rect = textarea.rect
                
                element_info = {
                    'type': 'textarea',
                    'index': i,
                    'placeholder': placeholder,
                    'aria_label': aria_label,
                    'data_testid': data_testid,
                    'rect': rect,
                    'element': textarea
                }
                all_interactive_elements.append(element_info)
                
                logger.info(f"🎯 Textarea {i+1}: placeholder='{placeholder}', aria-label='{aria_label}', data-testid='{data_testid}', size={rect['width']}x{rect['height']}")
            except Exception as e:
                logger.warning(f"⚠️ Error analyzing textarea {i+1}: {e}")
        
        for i, div in enumerate(visible_contenteditable):
            try:
                aria_label = div.get_attribute("aria-label") or ""
                data_testid = div.get_attribute("data-testid") or ""
                placeholder = div.get_attribute("placeholder") or ""
                rect = div.rect
                
                element_info = {
                    'type': 'contenteditable_div',
                    'index': i,
                    'placeholder': placeholder,
                    'aria_label': aria_label,
                    'data_testid': data_testid,
                    'rect': rect,
                    'element': div
                }
                all_interactive_elements.append(element_info)
                
                logger.info(f"🎯 Contenteditable div {i+1}: aria-label='{aria_label}', data-testid='{data_testid}', size={rect['width']}x{rect['height']}")
            except Exception as e:
                logger.warning(f"⚠️ Error analyzing contenteditable div {i+1}: {e}")
        
        # Try to interact with the most promising element
        if all_interactive_elements:
            logger.info("🧪 Testing interaction with elements...")
            
            for element_info in all_interactive_elements:
                element = element_info['element']
                logger.info(f"🧪 Testing {element_info['type']} {element_info['index']+1}...")
                
                try:
                    # Test focus
                    driver.execute_script("arguments[0].focus();", element)
                    logger.info("✅ Focus successful")
                    
                    # Test typing
                    test_text = "Hello, this is a test query"
                    driver.execute_script("arguments[0].value = arguments[1];", element, test_text)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", element)
                    logger.info("✅ Text input successful")
                    
                    # Test form submission
                    js_script = """
                    var event = new KeyboardEvent('keydown', {
                        key: 'Enter',
                        code: 'Enter',
                        keyCode: 13,
                        which: 13,
                        bubbles: true
                    });
                    arguments[0].dispatchEvent(event);
                    """
                    driver.execute_script(js_script, element)
                    logger.info("✅ Enter key event dispatched")
                    
                    # Wait a moment to see if anything happens
                    time.sleep(2)
                    
                    # Check if query was submitted (look for loading indicators, etc.)
                    page_text = driver.find_element(By.TAG_NAME, "body").text
                    if "loading" in page_text.lower() or "searching" in page_text.lower():
                        logger.info("🎉 Query submission appears successful!")
                        break
                    else:
                        logger.info("🤔 No obvious response to query submission")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Interaction test failed: {e}")
        else:
            logger.warning("❌ No interactive elements found to test")
        
        # Keep browser open for manual inspection
        logger.info("🔍 Browser will remain open for manual inspection...")
        input("Press Enter to close browser...")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
    
    finally:
        driver.quit()
        logger.info("🏁 Test completed")

if __name__ == "__main__":
    test_perplexity_spa()

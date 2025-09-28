#!/usr/bin/env python3
"""
Test script specifically for contenteditable div interaction with Perplexity
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_contenteditable_interaction():
    """Test contenteditable div interaction with Perplexity"""
    
    # Setup Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        logger.info("🚀 Testing contenteditable div interaction...")
        
        # Navigate to Perplexity
        logger.info("📍 Navigating to Perplexity.ai...")
        driver.get("https://perplexity.ai")
        time.sleep(5)
        
        # Find contenteditable div
        contenteditable_divs = driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true']")
        logger.info(f"Found {len(contenteditable_divs)} contenteditable divs")
        
        if not contenteditable_divs:
            logger.error("❌ No contenteditable divs found!")
            return
        
        input_div = contenteditable_divs[0]
        logger.info(f"✅ Using first contenteditable div: {input_div.rect}")
        
        # Test the enhanced interaction method
        test_prompt = "What is artificial intelligence?"
        
        logger.info("🧪 Testing enhanced contenteditable interaction...")
        
        # Step 1: Focus and clear
        logger.info("1️⃣ Focusing and clearing...")
        driver.execute_script("arguments[0].focus();", input_div)
        time.sleep(0.5)
        
        driver.execute_script("""
            arguments[0].textContent = '';
            arguments[0].innerHTML = '';
        """, input_div)
        time.sleep(0.5)
        
        # Step 2: Enhanced content setting
        logger.info("2️⃣ Enhanced content setting...")
        
        # Method 1: Try textContent
        driver.execute_script("arguments[0].textContent = arguments[1];", input_div, test_prompt)
        time.sleep(0.5)
        
        # Method 2: Try innerHTML if textContent didn't work
        content_check = driver.execute_script("return arguments[0].textContent;", input_div)
        if not content_check.strip():
            logger.info("textContent failed, trying innerHTML...")
            driver.execute_script("arguments[0].innerHTML = arguments[1];", input_div, test_prompt)
            time.sleep(0.5)
        
        # Method 3: Try simulated typing if innerHTML didn't work
        content_check = driver.execute_script("return arguments[0].textContent;", input_div)
        if not content_check.strip():
            logger.info("innerHTML failed, trying simulated typing...")
            # Clear first
            driver.execute_script("""
                arguments[0].focus();
                document.execCommand('selectAll', false, null);
                document.execCommand('delete', false, null);
            """, input_div)
            time.sleep(0.5)
            
            # Type character by character
            for char in test_prompt:
                driver.execute_script("""
                    arguments[0].focus();
                    document.execCommand('insertText', false, arguments[1]);
                """, input_div, char)
                time.sleep(0.01)  # Small delay between characters
        
        # Step 3: Trigger comprehensive events
        logger.info("3️⃣ Triggering comprehensive events...")
        driver.execute_script("""
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('focus', { bubbles: true }));
        """, input_div)
        time.sleep(1)
        
        # Verify content was set
        content = driver.execute_script("return arguments[0].textContent;", input_div)
        logger.info(f"📝 Content set: '{content}'")
        
        if content.strip() == test_prompt:
            logger.info("✅ Content setting successful!")
        else:
            logger.warning(f"⚠️ Content mismatch. Expected: '{test_prompt}', Got: '{content}'")
        
        # Step 4: Enhanced submission
        logger.info("4️⃣ Testing enhanced submission...")
        
        js_script = """
        // First, ensure the element is focused
        arguments[0].focus();
        
        // Try to find a submit button near the input
        var buttons = document.querySelectorAll('button');
        var inputRect = arguments[0].getBoundingClientRect();
        
        for (var i = 0; i < buttons.length; i++) {
            var btnRect = buttons[i].getBoundingClientRect();
            // Check if button is reasonably close to input (within 200px)
            if (Math.abs(inputRect.top - btnRect.top) < 200 && 
                Math.abs(inputRect.left - btnRect.left) < 500) {
                // Check if button looks like a submit button
                var btnText = buttons[i].textContent.toLowerCase();
                var hasSubmitIcon = buttons[i].querySelector('svg') !== null;
                
                console.log('Button found:', btnText, 'hasIcon:', hasSubmitIcon);
                
                if (btnText.includes('send') || btnText.includes('submit') || 
                    btnText.includes('ask') || hasSubmitIcon || btnText === '') {
                    buttons[i].click();
                    return 'button_click_' + i;
                }
            }
        }
        
        // Try keyboard events
        var events = ['keydown', 'keypress', 'keyup'];
        for (var j = 0; j < events.length; j++) {
            var event = new KeyboardEvent(events[j], {
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true,
                cancelable: true
            });
            arguments[0].dispatchEvent(event);
        }
        
        return 'keyboard_events';
        """
        
        result = driver.execute_script(js_script, input_div)
        logger.info(f"🎯 Submission result: {result}")
        
        # Wait and check for response
        logger.info("⏳ Waiting for response...")
        time.sleep(5)
        
        # Check if query was processed
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        response_indicators = ["loading", "searching", "thinking", "generating", "artificial intelligence"]
        
        found_indicators = [indicator for indicator in response_indicators if indicator in page_text]
        
        if found_indicators:
            logger.info(f"🎉 Response detected! Found indicators: {found_indicators}")
        else:
            logger.warning("🤔 No clear response indicators found")
            logger.info(f"📄 Page text snippet: {page_text[:500]}...")
        
        # Keep browser open for inspection
        logger.info("🔍 Browser will remain open for manual inspection...")
        input("Press Enter to close browser...")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()
        logger.info("🏁 Test completed")

if __name__ == "__main__":
    test_contenteditable_interaction()

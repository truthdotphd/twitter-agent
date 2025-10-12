#!/usr/bin/env python3
"""
Google Gemini Integration Module for Twitter Agent
Handles all Gemini-specific functionality
"""

import time
import logging
import re
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

logger = logging.getLogger(__name__)


class GeminiService:
    """Service class for Google Gemini integration in Twitter agent"""
    
    def __init__(self, driver, wait_time: int = 30, debug_mode: bool = False, responses_per_chat: int = 5):
        self.driver = driver
        self.wait_time = wait_time
        self.debug_mode = debug_mode
        self.responses_per_chat = responses_per_chat
        
        # Track responses in this chat session
        self.current_chat_response_count = 0
        self.last_response_text = None
        self.last_response_time = 0
    
    def navigate_new_tab(self) -> bool:
        """Navigate to Gemini in a new tab"""
        try:
            logger.info("Opening Gemini in new tab...")
            
            # Open new tab
            self.driver.execute_script("window.open('https://gemini.google.com/', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # Wait for page to load
            time.sleep(5)
            
            logger.info("Waiting for Gemini to load...")
            max_wait = 30
            wait_time = 0
            
            while wait_time < max_wait:
                try:
                    input_field = self.driver.find_element(By.CSS_SELECTOR, "rich-textarea")
                    if input_field:
                        logger.info("✅ Gemini loaded successfully")
                        break
                except:
                    pass
                
                time.sleep(1)
                wait_time += 1
                
                if wait_time % 5 == 0:
                    logger.info(f"Still waiting for Gemini to load... ({wait_time}/{max_wait}s)")
            
            if wait_time >= max_wait:
                logger.warning("⚠️ Gemini loading timeout, proceeding anyway...")
            
            time.sleep(2)
            
            # Check login status
            if not self.check_login_status():
                logger.warning("⚠️ May not be logged into Gemini")
                input("Please log into Gemini in this browser window and press Enter to continue...")
                time.sleep(2)
            
            return True
            
        except Exception as e:
            logger.error(f"Error navigating to Gemini: {e}")
            return False
    
    def check_login_status(self) -> bool:
        """Check if we're logged into Gemini"""
        try:
            logger.info("Checking Gemini login status...")
            
            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            
            # Check for logged-in indicators
            logged_in_indicators = ["gemini", "conversation", "profile"]
            
            for indicator in logged_in_indicators:
                if indicator in page_text:
                    logger.info(f"Found logged-in indicator: '{indicator}'")
                    return True
            
            # Check for input field presence
            try:
                input_field = self.driver.find_element(By.CSS_SELECTOR, "rich-textarea")
                if input_field:
                    logger.info("Found input field - appears to be logged in")
                    return True
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.warning(f"Could not determine login status: {e}")
            return True
    
    def find_input_field(self):
        """Find the Gemini input field"""
        logger.info("Looking for Gemini input field...")
        
        max_wait = 15
        wait_time = 0
        
        while wait_time < max_wait:
            input_selectors = [
                ("rich-textarea div.ql-editor[contenteditable='true']", "Rich textarea contenteditable"),
                ("div.ql-editor[contenteditable='true']", "Quill editor contenteditable"),
                ("div[contenteditable='true'][role='textbox']", "Contenteditable with textbox role"),
                ("div[contenteditable='true']", "Any contenteditable div"),
                ("textarea", "Generic textarea"),
            ]
            
            for selector, description in input_selectors:
                try:
                    logger.debug(f"Trying selector: {selector} ({description})")
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        if element and element.is_displayed() and element.is_enabled():
                            try:
                                self.driver.execute_script("arguments[0].focus();", element)
                                rect = element.rect
                                if rect['width'] > 0 and rect['height'] > 0:
                                    logger.info(f"✅ Found input field using: {description}")
                                    return element
                            except Exception as interact_error:
                                logger.debug(f"Element found but not interactable: {interact_error}")
                                continue
                except NoSuchElementException:
                    continue
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            if wait_time < max_wait - 1:
                logger.debug(f"No input field found, waiting... ({wait_time + 1}/{max_wait})")
                time.sleep(1)
                wait_time += 1
            else:
                break
        
        return None
    
    def query(self, tweet_content: str) -> Optional[str]:
        """Submit query to Gemini and get response"""
        try:
            logger.info("Querying Gemini...")
            
            # Check if we need a fresh chat
            if self.current_chat_response_count >= self.responses_per_chat:
                logger.info(f"🔄 Chat limit reached ({self.current_chat_response_count}/{self.responses_per_chat})")
                logger.info("💫 Starting fresh Gemini chat...")
                if not self.refresh():
                    logger.error("❌ Failed to refresh Gemini")
                    return None
            
            input_field = self.find_input_field()
            if not input_field:
                logger.error("❌ Could not find Gemini input field")
                return None
            
            logger.info("✅ Found input field, proceeding with query...")
            
            # Clear existing content
            try:
                self.driver.execute_script("arguments[0].focus();", input_field)
                time.sleep(0.5)
                
                self.driver.execute_script("arguments[0].textContent = '';", input_field)
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Could not clear input field: {e}")
            
            # Type the prompt
            prompt = tweet_content[:500]  # Truncate to 500 chars
            logger.info("Typing prompt...")
            try:
                input_field.click()
                time.sleep(1)
                
                self.driver.execute_script("arguments[0].focus();", input_field)
                time.sleep(0.5)
                
                self.driver.execute_script("arguments[0].textContent = arguments[1];", input_field, prompt)
                time.sleep(0.5)
                
                # Trigger input event
                self.driver.execute_script("""
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, input_field)
                time.sleep(1)
                
                # Verify content was set
                final_content = self.driver.execute_script("return arguments[0].textContent;", input_field)
                if final_content.strip():
                    logger.info(f"✅ Successfully typed prompt: '{final_content[:50]}...'")
                else:
                    logger.warning("⚠️ Content may not have been set properly")
                    input_field.send_keys(prompt)
                    logger.info("Used fallback send_keys method")
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Failed to type prompt: {e}")
                return None
            
            # Submit the query
            logger.info("Submitting query...")
            submitted = False
            
            # Method 1: Try to find and click send button
            try:
                send_button_selectors = [
                    "button[aria-label='Send message']",
                    "button.send-button",
                    "button[class*='send']",
                    "button[data-test-id*='send']",
                    "button mat-icon[fonticon='send']",
                ]
                
                for selector in send_button_selectors:
                    try:
                        send_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for btn in send_buttons:
                            if btn.is_displayed() and btn.is_enabled():
                                btn.click()
                                logger.info(f"✅ Query submitted using button: {selector}")
                                submitted = True
                                break
                        if submitted:
                            break
                    except:
                        continue
            except Exception as e:
                logger.warning(f"Failed to find send button: {e}")
            
            # Method 2: Try ENTER key if button failed
            if not submitted:
                try:
                    input_field.send_keys(Keys.RETURN)
                    logger.info("✅ Query submitted with RETURN key")
                    submitted = True
                except Exception as e:
                    logger.warning(f"Failed to submit with RETURN key: {e}")
            
            if not submitted:
                logger.error("Failed to submit query")
                return None
            
            # Wait for response
            logger.info(f"Waiting {self.wait_time} seconds for Gemini response...")
            time.sleep(self.wait_time)
            
            # Extract response
            logger.info("Extracting response from Gemini...")
            response_text = self._extract_response()
            
            if response_text:
                # Check for duplicates
                if (self.last_response_text and
                    response_text.strip() == self.last_response_text.strip()):
                    logger.error("❌ Response is identical to previous response!")
                    return None
                
                # Save and increment counter
                self.last_response_text = response_text
                self.last_response_time = time.time()
                self.current_chat_response_count += 1
                logger.info(f"📊 Chat usage: {self.current_chat_response_count}/{self.responses_per_chat}")
                
                # Clean up response
                response_text = re.sub(r'[•\-\*]{2,}', '', response_text)
                response_text = re.sub(r'\s+', ' ', response_text)
                response_text = re.sub(r'^\d+\.?\s*', '', response_text)
                response_text = response_text.strip()
                
                return response_text
            else:
                logger.warning("❌ No valid response found")
                return None
                
        except Exception as e:
            logger.error(f"Error querying Gemini: {e}")
            return None
    
    def _extract_response(self) -> Optional[str]:
        """Extract response from Gemini page - get the LAST conversation's response"""
        try:
            # Scroll to bottom
            logger.info("Scrolling to bottom to find latest response...")
            try:
                for i in range(3):
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.5)
                    
                    # Also scroll chat history container
                    self.driver.execute_script("""
                        var chatHistory = document.querySelector('.chat-history-scroll-container');
                        if (chatHistory) {
                            chatHistory.scrollTop = chatHistory.scrollHeight;
                        }
                    """)
                    time.sleep(0.5)
                
                logger.info("✅ Scrolled to bottom")
            except Exception as scroll_error:
                logger.warning(f"Scroll error: {scroll_error}")
            
            # Wait for content
            time.sleep(2)
            
            # Get all conversation containers and extract from THE LAST ONE
            logger.info("🔍 Finding conversation containers...")
            try:
                conversations = self.driver.find_elements(By.CSS_SELECTOR, ".conversation-container")
                if conversations:
                    logger.info(f"📊 Found {len(conversations)} conversation containers")
                    
                    # Get the LAST conversation
                    last_conversation = conversations[-1]
                    conversation_id = last_conversation.get_attribute('id')
                    logger.info(f"🎯 Targeting LAST conversation: {conversation_id}")
                    
                    # Look for model-response within this specific conversation
                    model_responses = last_conversation.find_elements(By.CSS_SELECTOR, "model-response")
                    if model_responses:
                        logger.info(f"📊 Found {len(model_responses)} model-response element(s)")
                        
                        last_model_response = model_responses[-1]
                        
                        # Try multiple selectors
                        text_selectors = [
                            "message-content code",
                            "message-content",
                            ".markdown",
                            "code-block code",
                        ]
                        
                        for selector in text_selectors:
                            try:
                                elements = last_model_response.find_elements(By.CSS_SELECTOR, selector)
                                if elements:
                                    response_text = elements[-1].text.strip()
                                    if len(response_text) > 20:
                                        logger.info(f"✅ Found response using selector: {selector}")
                                        logger.info(f"Response length: {len(response_text)} chars")
                                        return response_text
                            except Exception as selector_error:
                                logger.debug(f"Selector {selector} failed: {selector_error}")
                                continue
                        
                        # Fallback: Get text from model-response directly
                        response_text = last_model_response.text.strip()
                        if len(response_text) > 20:
                            logger.info(f"✅ Found response from model-response directly")
                            return response_text
                    
                    logger.warning(f"⚠️ No model-response found in last conversation")
                else:
                    logger.warning("⚠️ No conversation containers found")
                    
            except Exception as e:
                logger.error(f"Error finding conversation containers: {e}")
            
            # Fallback: Try direct message-content search
            logger.info("🔄 Trying fallback method...")
            try:
                all_message_contents = self.driver.find_elements(By.CSS_SELECTOR, "message-content")
                if all_message_contents:
                    logger.info(f"📊 Found {len(all_message_contents)} message-content elements")
                    
                    # Get the LAST displayed one
                    for msg_content in reversed(all_message_contents):
                        if msg_content.is_displayed():
                            text = msg_content.text.strip()
                            if len(text) > 20:
                                logger.info(f"✅ Found response using fallback")
                                return text
            except Exception as e:
                logger.debug(f"Fallback failed: {e}")
            
            logger.warning("❌ No valid response found from Gemini")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting response: {e}")
            return None
    
    def refresh(self) -> bool:
        """Refresh Gemini with new chat session"""
        try:
            logger.info("🔄 Starting fresh Gemini chat...")
            
            # Close current tab
            self.driver.close()
            time.sleep(1)
            
            # Switch back to Twitter
            if self.driver.window_handles:
                self.driver.switch_to.window(self.driver.window_handles[0])
            
            # Open fresh Gemini
            logger.info("🆕 Opening fresh Gemini...")
            if not self.navigate_new_tab():
                logger.error("❌ Failed to open fresh Gemini")
                return False
            
            # Reset counters
            self.current_chat_response_count = 0
            self.last_response_text = None
            self.last_response_time = 0
            logger.info("🔄 Reset chat response counter")
            
            logger.info("✅ Fresh Gemini ready!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error refreshing Gemini: {e}")
            return False
    
    def switch_to_tab(self) -> bool:
        """Switch to Gemini tab"""
        try:
            logger.info("Switching to Gemini tab...")
            
            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                current_url = self.driver.current_url
                if 'gemini.google.com' in current_url:
                    logger.info("Successfully switched to Gemini tab")
                    return True
            
            logger.error("Could not find Gemini tab")
            return False
            
        except Exception as e:
            logger.error(f"Error switching to Gemini tab: {e}")
            return False



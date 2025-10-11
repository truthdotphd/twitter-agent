#!/usr/bin/env python3
"""
Perplexity.ai Integration Module for Twitter Agent
Handles all Perplexity-specific functionality
"""

import time
import logging
import re
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

logger = logging.getLogger(__name__)


class PerplexityService:
    """Service class for Perplexity.ai integration in Twitter agent"""
    
    def __init__(self, driver, wait_time: int = 60, debug_mode: bool = False, responses_per_chat: int = 2):
        self.driver = driver
        self.wait_time = wait_time
        self.debug_mode = debug_mode
        self.responses_per_chat = responses_per_chat
        
        # Track responses in this chat session
        self.current_chat_response_count = 0
        self.last_response_text = None
        self.last_response_time = 0
    
    def navigate_new_tab(self) -> bool:
        """Navigate to Perplexity.ai in a new tab"""
        try:
            logger.info("Opening Perplexity.ai in new tab...")
            
            # Open new tab
            self.driver.execute_script("window.open('https://www.perplexity.ai/', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # Wait for initial page load
            time.sleep(3)
            
            # Wait for SPA to load
            logger.info("Waiting for Perplexity SPA to load...")
            max_wait = 30
            wait_time = 0
            
            while wait_time < max_wait:
                try:
                    root_element = self.driver.find_element(By.ID, "root")
                    if root_element and len(root_element.text.strip()) > 0:
                        logger.info("✅ Perplexity SPA loaded successfully")
                        break
                    
                    inputs = self.driver.find_elements(By.TAG_NAME, "textarea")
                    if inputs:
                        logger.info("✅ Found input elements, SPA likely loaded")
                        break
                except:
                    pass
                
                time.sleep(1)
                wait_time += 1
                
                if wait_time % 5 == 0:
                    logger.info(f"Still waiting for SPA to load... ({wait_time}/{max_wait}s)")
            
            if wait_time >= max_wait:
                logger.warning("⚠️ SPA loading timeout, proceeding anyway...")
            
            # Additional wait for elements to be interactive
            time.sleep(2)
            
            # Check login status
            if not self.check_login_status():
                logger.warning("⚠️  May not be logged into Perplexity.ai")
                logger.warning("Please log into Perplexity.ai in this browser window")
                input("Press Enter after logging into Perplexity.ai...")
                time.sleep(2)
            
            # Configure GPT-5 Thinking and sources
            self.select_gpt5_and_sources()
            
            # Try to find input field
            input_field = self.find_input_field()
            if input_field:
                logger.info("✅ Successfully found Perplexity input field")
                return True
            else:
                logger.error("❌ Could not find Perplexity input field")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to Perplexity.ai: {e}")
            return False
    
    def check_login_status(self) -> bool:
        """Check if we're logged into Perplexity.ai"""
        try:
            logger.info("Checking Perplexity.ai login status...")
            
            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            
            # Check for logged-in indicators
            logged_in_indicators = ["pro", "profile", "settings", "upgrade"]
            
            logged_in_found = False
            for indicator in logged_in_indicators:
                if indicator in page_text:
                    logger.info(f"Found logged-in indicator: '{indicator}'")
                    logged_in_found = True
                    break
            
            return logged_in_found
            
        except Exception as e:
            logger.warning(f"Could not determine login status: {e}")
            return True  # Assume logged in if we can't determine
    
    def debug_ui_elements(self):
        """Debug helper to see what UI elements are available"""
        try:
            logger.info("🔍 DEBUG: Scanning Perplexity UI elements...")
            
            # Find all buttons with their text
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            visible_buttons = [b for b in buttons if b.is_displayed()]
            logger.info(f"📊 Found {len(visible_buttons)} visible buttons:")
            for i, btn in enumerate(visible_buttons[:20]):
                try:
                    text = btn.text.strip()
                    aria_label = btn.get_attribute('aria-label')
                    class_name = btn.get_attribute('class')
                    if text or aria_label:
                        logger.info(f"   Button {i+1}: text='{text[:50]}', aria-label='{aria_label}', class='{class_name[:50] if class_name else ''}'")
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Debug failed: {e}")
    
    def select_gpt5_and_sources(self) -> bool:
        """Select GPT-5 Thinking model and configure sources"""
        try:
            logger.info("🤖 Configuring Perplexity: GPT-5 Thinking + Sources (Web, Academic, Social, Finance)")
            
            # Wait for UI to load
            logger.info("⏱️ Waiting for Perplexity UI to fully load...")
            time.sleep(5)
            
            # Debug if needed
            if self.debug_mode:
                self.debug_ui_elements()
            
            # STEP 1: Select model
            logger.info("🔍 Step 1: Looking for model selector button...")
            model_button = None
            
            try:
                logger.info("   Searching for model selector button...")
                model_keywords = ['gpt', 'claude', 'gemini', 'sonar', 'thinking', 'grok', 'auto', 'o3']
                all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                
                for btn in all_buttons:
                    if not btn.is_displayed():
                        continue
                    
                    aria_label = (btn.get_attribute('aria-label') or '').lower()
                    
                    if aria_label and any(keyword in aria_label for keyword in model_keywords):
                        if 'submit' not in aria_label and 'attach' not in aria_label and 'dictation' not in aria_label:
                            model_button = btn
                            logger.info(f"✅ Found model selector button with aria-label='{btn.get_attribute('aria-label')}'")
                            break
            except Exception as search_error:
                logger.warning(f"⚠️ Model button search failed: {search_error}")
            
            if model_button and model_button.is_displayed():
                try:
                    logger.info("🖱️ Clicking model selector...")
                    model_button.click()
                    time.sleep(3)
                    
                    # Look for GPT-5 Thinking
                    logger.info("🔍 Step 2: Looking for GPT-5 Thinking in dropdown...")
                    time.sleep(2)
                    
                    menu_items = self.driver.find_elements(By.CSS_SELECTOR, "div[role='menuitem']")
                    logger.info(f"📊 Found {len(menu_items)} menu items")
                    
                    found_model = False
                    for item in menu_items:
                        try:
                            if not item.is_displayed():
                                continue
                            
                            spans = item.find_elements(By.TAG_NAME, "span")
                            model_name = ""
                            
                            for span in spans:
                                span_text = span.text.strip()
                                if span_text and span_text.lower() not in ['new', 'max']:
                                    model_name = span_text
                                    break
                            
                            if model_name.lower() == 'gpt-5 thinking':
                                logger.info(f"🎯 Found GPT-5 Thinking option")
                                
                                try:
                                    clickable_div = item.find_element(By.CSS_SELECTOR, "div.cursor-pointer")
                                    clickable_div.click()
                                    logger.info(f"✅ Selected model: GPT-5 Thinking")
                                    time.sleep(2)
                                    found_model = True
                                    break
                                except:
                                    try:
                                        item.click()
                                        logger.info(f"✅ Selected model: GPT-5 Thinking (via menuitem)")
                                        time.sleep(2)
                                        found_model = True
                                        break
                                    except:
                                        try:
                                            self.driver.execute_script("arguments[0].click();", item)
                                            logger.info(f"✅ Selected model: GPT-5 Thinking (via JavaScript)")
                                            time.sleep(2)
                                            found_model = True
                                            break
                                        except:
                                            logger.warning("Failed to click GPT-5 Thinking option")
                        except Exception as e:
                            logger.debug(f"Error checking menu item: {e}")
                            continue
                    
                    if not found_model:
                        logger.warning("⚠️ Could not find or click GPT-5 Thinking option")
                        logger.info("💡 Please manually select GPT-5 Thinking")
                        try:
                            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                            time.sleep(1)
                        except:
                            pass
                            
                except Exception as e:
                    logger.warning(f"Error during model selection: {e}")
            else:
                logger.warning("⚠️ Model selector button not found or not visible")
            
            # STEP 3: Configure sources
            time.sleep(2)
            logger.info("🔍 Step 3: Looking for sources selector button...")
            source_button = None
            
            try:
                source_button = self.driver.find_element(By.CSS_SELECTOR, 'button[data-testid="sources-switcher-button"]')
                logger.info("✅ Found sources selector")
            except:
                logger.warning("⚠️ Could not find sources button")
            
            if source_button and source_button.is_displayed():
                try:
                    logger.info("🖱️ Clicking sources selector...")
                    source_button.click()
                    time.sleep(3)
                    
                    # Enable sources
                    sources_to_enable = {
                        'academic': 'source-toggle-scholar',
                        'social': 'source-toggle-social',
                        'finance': 'source-toggle-edgar'
                    }
                    
                    logger.info(f"🔍 Step 4: Enabling sources: {', '.join(sources_to_enable.keys())}")
                    enabled_sources = []
                    
                    for source_name, testid in sources_to_enable.items():
                        try:
                            source_elem = self.driver.find_element(By.CSS_SELECTOR, f'div[data-testid="{testid}"]')
                            
                            if source_elem and source_elem.is_displayed():
                                try:
                                    switch = source_elem.find_element(By.CSS_SELECTOR, 'button[role="switch"]')
                                    aria_checked = switch.get_attribute('aria-checked')
                                    
                                    if aria_checked == 'true':
                                        logger.info(f"ℹ️  {source_name.title()}: Already enabled")
                                        enabled_sources.append(source_name)
                                    else:
                                        logger.info(f"🎯 Clicking to enable: {source_name.title()}")
                                        source_elem.click()
                                        time.sleep(0.5)
                                        logger.info(f"✅ Enabled source: {source_name.title()}")
                                        enabled_sources.append(source_name)
                                except:
                                    source_elem.click()
                                    time.sleep(0.5)
                                    logger.info(f"✅ Clicked source: {source_name.title()}")
                                    enabled_sources.append(source_name)
                        except Exception as e:
                            logger.warning(f"⚠️ Could not enable {source_name}: {e}")
                    
                    logger.info(f"📊 Configured sources: Web (default), {', '.join([s.title() for s in enabled_sources])}")
                    
                    # Close selector
                    try:
                        self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        time.sleep(1)
                    except:
                        pass
                        
                except Exception as e:
                    logger.warning(f"Error during source configuration: {e}")
            
            logger.info("✅ Perplexity configuration completed")
            return True
            
        except Exception as e:
            logger.error(f"Error configuring Perplexity: {e}")
            logger.warning("⚠️ Continuing anyway - you may need to configure manually")
            return False
    
    def find_input_field(self):
        """Find the Perplexity input field"""
        logger.info("Looking for Perplexity input field...")
        
        max_wait = 15
        wait_time = 0
        
        while wait_time < max_wait:
            input_selectors = [
                ("div[contenteditable='true']", "Content editable div"),
                ("div[role='textbox']", "Textbox role div"),
                ("textarea", "Generic textarea"),
                ("textarea[placeholder*='Ask']", "Textarea with 'Ask' placeholder"),
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
        """Submit query to Perplexity and get response"""
        try:
            logger.info("Querying Perplexity...")
            
            # Check if we need a fresh chat
            if self.current_chat_response_count >= self.responses_per_chat:
                logger.info(f"🔄 Chat limit reached ({self.current_chat_response_count}/{self.responses_per_chat})")
                logger.info("💫 Starting fresh Perplexity chat session...")
                if not self.refresh():
                    logger.error("❌ Failed to refresh Perplexity")
                    return None
            
            input_field = self.find_input_field()
            if not input_field:
                logger.error("❌ Could not find Perplexity input field")
                return None
            
            logger.info("✅ Found input field, proceeding with query...")
            
            # Clear existing content
            try:
                self.driver.execute_script("arguments[0].focus();", input_field)
                time.sleep(0.5)
                
                is_contenteditable = input_field.get_attribute("contenteditable") == "true"
                
                if is_contenteditable:
                    self.driver.execute_script("arguments[0].textContent = '';", input_field)
                    time.sleep(0.5)
                else:
                    input_field.clear()
                    time.sleep(1)
            except Exception as e:
                logger.warning(f"Could not clear input field: {e}")
            
            # Type the prompt  
            prompt = tweet_content[:500]  # Truncate to 500 chars
            logger.info("Typing prompt...")
            try:
                input_field.click()
                time.sleep(1)
                
                is_contenteditable = input_field.get_attribute("contenteditable") == "true"
                
                if is_contenteditable:
                    self.driver.execute_script("arguments[0].focus();", input_field)
                    time.sleep(0.5)
                    
                    self.driver.execute_script("arguments[0].textContent = arguments[1];", input_field, prompt)
                    time.sleep(0.5)
                    
                    self.driver.execute_script("""
                        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                    """, input_field)
                    time.sleep(1)
                    
                    final_content = self.driver.execute_script("return arguments[0].textContent;", input_field)
                    if final_content.strip():
                        logger.info(f"✅ Successfully typed prompt: '{final_content[:50]}...'")
                    else:
                        logger.warning("⚠️ Content may not have been set properly")
                        input_field.send_keys(prompt)
                        logger.info("Used fallback send_keys method")
                else:
                    input_field.send_keys(prompt)
                    time.sleep(2)
                    logger.info("✅ Successfully typed prompt")
                    
            except Exception as e:
                logger.error(f"Failed to type prompt: {e}")
                return None
            
            # Submit
            logger.info("Submitting query...")
            submitted = False
            
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
            query_submit_time = time.time()
            logger.info(f"Waiting {self.wait_time} seconds for Perplexity response...")
            
            # Track initial prose count
            initial_prose_count = 0
            try:
                initial_prose_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.prose")
                initial_prose_count = len(initial_prose_elements)
                logger.info(f"📊 Initial prose count: {initial_prose_count}")
            except:
                pass
            
            time.sleep(self.wait_time)
            
            # Check for new response
            try:
                final_prose_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.prose")
                final_prose_count = len(final_prose_elements)
                logger.info(f"📊 Final prose count: {final_prose_count}")
                
                if final_prose_count > initial_prose_count:
                    logger.info(f"✅ New response detected!")
                else:
                    logger.warning(f"⚠️ No new prose elements detected")
            except:
                pass
            
            # Ultra-aggressive scrolling
            logger.info("🔄 Scrolling to bottom...")
            try:
                for i in range(3):
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.5)
            except:
                pass
            
            # Extract response
            logger.info("Extracting response from Perplexity...")
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
                
                return response_text
            else:
                logger.warning("❌ No valid response found")
                return None
                
        except Exception as e:
            logger.error(f"Error querying Perplexity: {e}")
            return None
    
    def _extract_response(self) -> Optional[str]:
        """Extract response from Perplexity page"""
        try:
            # Get all prose elements
            prose_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.prose")
            logger.info(f"📊 Found {len(prose_elements)} prose elements")
            
            if prose_elements:
                # Get the last displayed element
                for element in reversed(prose_elements):
                    if element.is_displayed():
                        text = element.text.strip()
                        if len(text) > 20:
                            logger.info(f"✅ Found response ({len(text)} chars): {text[:100]}...")
                            
                            # Clean up response
                            text = re.sub(r'[•\-\*]{2,}', '', text)
                            text = re.sub(r'\s+', ' ', text)
                            text = re.sub(r'^\d+\.?\s*', '', text)
                            text = text.strip()
                            
                            return text
            
            logger.warning("❌ No valid response found")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting response: {e}")
            return None
    
    def refresh(self) -> bool:
        """Refresh Perplexity with new chat session"""
        try:
            logger.info("🔄 Starting fresh Perplexity chat session...")
            
            # Close current tab
            self.driver.close()
            time.sleep(1)
            
            # Switch back to Twitter (should be first remaining tab)
            if self.driver.window_handles:
                self.driver.switch_to.window(self.driver.window_handles[0])
            
            # Open fresh Perplexity
            logger.info("🆕 Opening fresh Perplexity...")
            if not self.navigate_new_tab():
                logger.error("❌ Failed to open fresh Perplexity")
                return False
            
            # Reset counters
            self.current_chat_response_count = 0
            self.last_response_text = None
            self.last_response_time = 0
            logger.info("🔄 Reset chat response counter")
            
            logger.info("✅ Fresh Perplexity chat ready!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error refreshing Perplexity: {e}")
            return False
    
    def switch_to_tab(self) -> bool:
        """Switch to Perplexity tab"""
        try:
            logger.info("Switching to Perplexity tab...")
            
            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                current_url = self.driver.current_url
                if 'perplexity.ai' in current_url:
                    logger.info("Successfully switched to Perplexity tab")
                    return True
            
            logger.error("Could not find Perplexity tab")
            return False
            
        except Exception as e:
            logger.error(f"Error switching to Perplexity tab: {e}")
            return False


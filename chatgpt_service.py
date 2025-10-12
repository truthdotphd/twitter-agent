#!/usr/bin/env python3
"""
ChatGPT Integration Module for Twitter Agent  
Handles all ChatGPT-specific functionality
"""

import time
import logging
import re
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException

logger = logging.getLogger(__name__)


class ChatGPTService:
    """Service class for ChatGPT integration in Twitter agent"""
    
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
        """Navigate to ChatGPT in a new tab"""
        try:
            logger.info("Opening ChatGPT in new tab...")
            
            # Open new tab
            self.driver.execute_script("window.open('https://chatgpt.com/', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # Wait for page to load
            time.sleep(5)
            
            logger.info("Waiting for ChatGPT to load...")
            max_wait = 30
            wait_time = 0
            
            while wait_time < max_wait:
                try:
                    input_field = self.driver.find_element(By.ID, "prompt-textarea")
                    if input_field:
                        logger.info("✅ ChatGPT loaded successfully")
                        break
                except:
                    pass
                
                time.sleep(1)
                wait_time += 1
                
                if wait_time % 5 == 0:
                    logger.info(f"Still waiting for ChatGPT to load... ({wait_time}/{max_wait}s)")
            
            if wait_time >= max_wait:
                logger.warning("⚠️ ChatGPT loading timeout, proceeding anyway...")
            
            time.sleep(2)
            
            # Check login status
            if not self.check_login_status():
                logger.warning("⚠️ May not be logged into ChatGPT")
                input("Please log into ChatGPT in this browser window and press Enter to continue...")
                time.sleep(2)
            
            # Enable web search mode
            self.enable_web_search()
            
            # Select Thinking model
            self.select_thinking_model()
            
            return True
            
        except Exception as e:
            logger.error(f"Error navigating to ChatGPT: {e}")
            return False
    
    def check_login_status(self) -> bool:
        """Check if we're logged into ChatGPT"""
        try:
            logger.info("Checking ChatGPT login status...")
            
            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            
            # Check for logged-in indicators
            logged_in_indicators = ["chatgpt", "new chat", "upgrade"]
            
            for indicator in logged_in_indicators:
                if indicator in page_text:
                    logger.info(f"Found logged-in indicator: '{indicator}'")
                    return True
            
            # Check for input field presence
            try:
                input_field = self.driver.find_element(By.ID, "prompt-textarea")
                if input_field:
                    logger.info("Found input field - appears to be logged in")
                    return True
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.warning(f"Could not determine login status: {e}")
            return True
    
    def enable_web_search(self) -> bool:
        """Enable web search mode by clicking + button, More, then Web search"""
        try:
            logger.info("🔍 Enabling ChatGPT Web Search mode...")
            
            # Wait for UI to be ready
            time.sleep(2)
            
            # STEP 1: Click the "+" button
            logger.info("🖱️  Step 1: Looking for + button...")
            plus_button = None
            
            try:
                plus_button = self.driver.find_element(By.CSS_SELECTOR, 'button[data-testid="composer-plus-btn"]')
                logger.info("✅ Found + button")
            except:
                try:
                    plus_button = self.driver.find_element(By.ID, "composer-plus-btn")
                    logger.info("✅ Found + button by ID")
                except:
                    logger.warning("⚠️ Could not find + button")
            
            if plus_button and plus_button.is_displayed():
                try:
                    logger.info("🖱️  Clicking + button...")
                    plus_button.click()
                    time.sleep(2)
                    
                    # STEP 2: Look for "More" menu item
                    logger.info("🔍 Step 2: Looking for 'More' menu item...")
                    more_button = None
                    
                    menu_items = self.driver.find_elements(By.CSS_SELECTOR, "div[role='menuitem']")
                    logger.info(f"📊 Found {len(menu_items)} menu items")
                    
                    for item in menu_items:
                        try:
                            if not item.is_displayed():
                                continue
                            
                            text = item.text.strip()
                            if text.lower() == "more":
                                more_button = item
                                logger.info(f"✅ Found 'More' menu item")
                                break
                        except Exception as e:
                            logger.debug(f"Error checking menu item: {e}")
                            continue
                    
                    if more_button:
                        try:
                            # Hover on More to open submenu
                            logger.info("🖱️  Hovering on 'More'...")
                            actions = ActionChains(self.driver)
                            actions.move_to_element(more_button).perform()
                            time.sleep(1)
                            
                            # STEP 3: Look for "Web search" in submenu
                            logger.info("🔍 Step 3: Looking for 'Web search' option...")
                            time.sleep(1)
                            
                            # Find menuitemradio elements (submenu items)
                            menu_radios = self.driver.find_elements(By.CSS_SELECTOR, "[role='menuitemradio']")
                            visible_radios = [r for r in menu_radios if r.is_displayed()]
                            logger.info(f"📊 Found {len(visible_radios)} visible submenu items")
                            
                            web_search_button = None
                            for radio in visible_radios:
                                try:
                                    text = radio.text.strip()
                                    if "web search" in text.lower():
                                        web_search_button = radio
                                        logger.info(f"✅ Found 'Web search' option")
                                        break
                                except Exception as e:
                                    logger.debug(f"Error checking menu radio: {e}")
                            
                            if web_search_button:
                                try:
                                    logger.info("🖱️  Clicking 'Web search'...")
                                    web_search_button.click()
                                    time.sleep(2)
                                    logger.info("✅ Web search mode enabled!")
                                    return True
                                except Exception as e:
                                    logger.warning(f"Failed to click Web search: {e}")
                                    try:
                                        self.driver.execute_script("arguments[0].click();", web_search_button)
                                        time.sleep(2)
                                        logger.info("✅ Web search mode enabled (via JavaScript)!")
                                        return True
                                    except:
                                        logger.warning("Could not enable web search mode")
                            else:
                                logger.warning("⚠️ Could not find 'Web search' option")
                                
                        except Exception as e:
                            logger.warning(f"Error during submenu navigation: {e}")
                    else:
                        logger.warning("⚠️ Could not find 'More' menu item")
                    
                except Exception as e:
                    logger.warning(f"Error during menu navigation: {e}")
            else:
                logger.warning("⚠️ + button not found or not visible")
            
            logger.info("💡 Continuing - you may need to enable web search manually")
            return False
            
        except Exception as e:
            logger.error(f"Error enabling web search: {e}")
            return False
    
    def select_thinking_model(self) -> bool:
        """Select the 'Thinking' model from the model switcher dropdown"""
        try:
            logger.info("🧠 Selecting 'Thinking' model...")
            
            # Wait for UI to be ready
            time.sleep(2)
            
            # STEP 1: Click the model switcher button
            logger.info("🖱️  Step 1: Looking for model switcher button...")
            model_button = None
            
            button_selectors = [
                'button[data-testid="model-switcher-dropdown-button"]',
                'button[id^="radix"][aria-haspopup="menu"]',
                'button[aria-label*="Model selector"]'
            ]
            
            for selector in button_selectors:
                try:
                    model_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if model_button.is_displayed():
                        logger.info(f"✅ Found model switcher button using: {selector}")
                        break
                except:
                    continue
            
            if not model_button or not model_button.is_displayed():
                logger.warning("⚠️ Could not find model switcher button")
                return False
            
            # Check if already on Thinking model
            try:
                button_text = model_button.text.lower()
                if "thinking" in button_text:
                    logger.info("✅ Already using Thinking model - no need to switch")
                    return True
            except:
                pass
            
            # Click the button to open dropdown
            try:
                logger.info("🖱️  Clicking model switcher button...")
                model_button.click()
                time.sleep(2)
                
                # STEP 2: Look for "Thinking" option in the dropdown
                logger.info("🔍 Step 2: Looking for 'Thinking' option...")
                
                thinking_selectors = [
                    'div[data-testid="model-switcher-gpt-5-thinking"]',
                    '[role="menuitem"][data-testid*="thinking"]',
                    'div[role="menuitem"]'
                ]
                
                thinking_option = None
                
                # Try specific selector first
                try:
                    thinking_option = self.driver.find_element(By.CSS_SELECTOR, 'div[data-testid="model-switcher-gpt-5-thinking"]')
                    if thinking_option.is_displayed():
                        logger.info("✅ Found 'Thinking' option")
                except:
                    pass
                
                # Fallback: search through all menu items
                if not thinking_option:
                    try:
                        menu_items = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="menuitem"]')
                        logger.info(f"📊 Found {len(menu_items)} menu items")
                        
                        for item in menu_items:
                            try:
                                if not item.is_displayed():
                                    continue
                                
                                text = item.text.strip().lower()
                                if "thinking" in text and "thinks longer" in text:
                                    thinking_option = item
                                    logger.info("✅ Found 'Thinking' option via text search")
                                    break
                            except:
                                continue
                    except Exception as e:
                        logger.debug(f"Error searching menu items: {e}")
                
                if thinking_option:
                    # Check if already selected (has checkmark)
                    try:
                        # Look for checkmark icon
                        checkmark = thinking_option.find_element(By.CSS_SELECTOR, 'svg.icon-sm')
                        if checkmark:
                            logger.info("✅ Thinking model is already selected")
                            # Close the dropdown by pressing ESC
                            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                            time.sleep(1)
                            return True
                    except:
                        pass  # No checkmark, need to select
                    
                    # Click the Thinking option
                    try:
                        logger.info("🖱️  Clicking 'Thinking' option...")
                        thinking_option.click()
                        time.sleep(2)
                        logger.info("✅ Successfully selected Thinking model!")
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to click Thinking option: {e}")
                        try:
                            self.driver.execute_script("arguments[0].click();", thinking_option)
                            time.sleep(2)
                            logger.info("✅ Successfully selected Thinking model (via JavaScript)!")
                            return True
                        except:
                            logger.warning("Could not select Thinking model")
                else:
                    logger.warning("⚠️ Could not find 'Thinking' option in menu")
                    # Close dropdown
                    try:
                        self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        time.sleep(1)
                    except:
                        pass
                    
            except Exception as e:
                logger.warning(f"Error during model selection: {e}")
            
            logger.info("💡 Continuing - you may need to select Thinking model manually")
            return False
            
        except Exception as e:
            logger.error(f"Error selecting Thinking model: {e}")
            return False
    
    def find_input_field(self):
        """Find the ChatGPT input field"""
        logger.info("Looking for ChatGPT input field...")
        
        max_wait = 15
        wait_time = 0
        
        while wait_time < max_wait:
            input_selectors = [
                ("div#prompt-textarea[contenteditable='true']", "Main prompt textarea"),
                ("div.ProseMirror[contenteditable='true']", "ProseMirror contenteditable"),
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
        """Submit query to ChatGPT and get response"""
        try:
            logger.info("Querying ChatGPT...")
            
            # Check if we need a fresh chat
            if self.current_chat_response_count >= self.responses_per_chat:
                logger.info(f"🔄 Chat limit reached ({self.current_chat_response_count}/{self.responses_per_chat})")
                logger.info("💫 Starting fresh ChatGPT chat...")
                if not self.refresh():
                    logger.error("❌ Failed to refresh ChatGPT")
                    return None
            
            # Ensure Thinking model is selected before querying
            logger.info("Ensuring Thinking model is selected...")
            self.select_thinking_model()
            time.sleep(1)
            
            input_field = self.find_input_field()
            if not input_field:
                logger.error("❌ Could not find ChatGPT input field")
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
            
            # Type the prompt (don't truncate - full prompt needed)
            prompt = tweet_content
            logger.info(f"Typing prompt ({len(prompt)} characters)...")
            try:
                input_field.click()
                time.sleep(0.5)
                
                self.driver.execute_script("arguments[0].focus();", input_field)
                time.sleep(0.5)
                
                # Method 1: Use comprehensive JavaScript injection for ProseMirror/contenteditable
                logger.info("Setting prompt using JavaScript injection...")
                success = self.driver.execute_script("""
                    const element = arguments[0];
                    const text = arguments[1];
                    
                    try {
                        // Focus the element
                        element.focus();
                        
                        // Clear existing content completely
                        element.textContent = '';
                        element.innerHTML = '';
                        
                        // Method 1: Try setting textContent directly (works for most contenteditable)
                        element.textContent = text;
                        
                        // Trigger comprehensive events for React/ProseMirror to recognize the change
                        const events = [
                            new InputEvent('beforeinput', { bubbles: true, cancelable: true, inputType: 'insertText', data: text }),
                            new Event('input', { bubbles: true, cancelable: true }),
                            new Event('change', { bubbles: true, cancelable: true }),
                            new KeyboardEvent('keydown', { bubbles: true, key: 'a' }),
                            new KeyboardEvent('keyup', { bubbles: true, key: 'a' })
                        ];
                        
                        events.forEach(event => element.dispatchEvent(event));
                        
                        // Force React update by deleting value tracker
                        if (element._valueTracker) {
                            delete element._valueTracker;
                        }
                        
                        // Return the actual content length for verification
                        return element.textContent.length;
                    } catch (e) {
                        console.error('Error setting content:', e);
                        return 0;
                    }
                """, input_field, prompt)
                
                logger.info(f"JavaScript injection result: {success} characters")
                time.sleep(1)
                
                # Verify content was set
                final_content = self.driver.execute_script("return arguments[0].textContent || arguments[0].innerText || '';", input_field)
                logger.info(f"Content verification: {len(final_content)} characters")
                
                if len(final_content) < len(prompt) * 0.8:  # Less than 80% of prompt
                    logger.warning(f"⚠️ Content appears truncated ({len(final_content)}/{len(prompt)} chars), trying character-by-character typing...")
                    
                    # Clear and retry with send_keys character by character
                    input_field.clear()
                    time.sleep(0.5)
                    
                    # Type in chunks to avoid overwhelming the input field
                    chunk_size = 100
                    for i in range(0, len(prompt), chunk_size):
                        chunk = prompt[i:i+chunk_size]
                        input_field.send_keys(chunk)
                        time.sleep(0.1)  # Small delay between chunks
                    
                    logger.info("✅ Used character-by-character typing method")
                    time.sleep(1)
                    
                    # Final verification
                    final_content = self.driver.execute_script("return arguments[0].textContent || arguments[0].innerText || '';", input_field)
                    logger.info(f"Final content length: {len(final_content)} characters")
                
                if len(final_content) > 20:
                    logger.info(f"✅ Successfully typed prompt: '{final_content[:50]}...'")
                    logger.info(f"✅ Full prompt length: {len(final_content)} characters")
                else:
                    logger.error(f"❌ Failed to set prompt content properly")
                    return None
                    
            except Exception as e:
                logger.error(f"Failed to type prompt: {e}")
                return None
            
            # Submit the query
            logger.info("Submitting query...")
            submitted = False
            
            # Method 1: Try to find and click send button
            try:
                send_button_selectors = [
                    "button[data-testid='send-button']",
                    "button[data-testid='composer-send-button']",
                    "button[aria-label*='Send']",
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
            logger.info(f"Waiting {self.wait_time} seconds for ChatGPT response...")
            time.sleep(self.wait_time)
            
            # Extract response
            logger.info("Extracting response from ChatGPT...")
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
            logger.error(f"Error querying ChatGPT: {e}")
            return None
    
    def _extract_response(self) -> Optional[str]:
        """Extract response from ChatGPT page - ALWAYS get the LAST (most recent) assistant message"""
        try:
            # Scroll to bottom to ensure we can see the latest response
            logger.info("📜 Scrolling to bottom to find LATEST response...")
            try:
                for i in range(3):
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.5)
                logger.info("✅ Scrolled to bottom")
            except Exception as scroll_error:
                logger.warning(f"Scroll error: {scroll_error}")
            
            # Wait for content to render
            time.sleep(2)
            
            # STRATEGY: Find all assistant messages and pick the LAST one
            logger.info("🔍 Finding all assistant messages to pick the LAST one...")
            try:
                # ChatGPT uses data-message-author-role attribute
                assistant_messages = self.driver.find_elements(By.CSS_SELECTOR, "[data-message-author-role='assistant']")
                
                if assistant_messages and len(assistant_messages) > 0:
                    total_messages = len(assistant_messages)
                    logger.info(f"📊 Found {total_messages} assistant message(s) in total")
                    
                    # CRITICAL: Always get the LAST assistant message (index -1)
                    last_message = assistant_messages[-1]
                    logger.info(f"🎯 Picking message #{total_messages} (the LAST one)")
                    
                    # Try to extract text from various possible containers within the last message
                    text_selectors = [
                        ".markdown",                    # Most common container
                        "[data-message-text]",          # Explicit text container
                        ".text-message",                # Alternative text container
                        "div.whitespace-pre-wrap",      # Formatted text
                        "div[class*='markdown']",       # Wildcard markdown
                        "div.text-base",                # Base text style
                        "div[data-testid*='message']",  # Test ID pattern
                    ]
                    
                    for selector in text_selectors:
                        try:
                            elements = last_message.find_elements(By.CSS_SELECTOR, selector)
                            if elements:
                                response_text = elements[0].text.strip()
                                if len(response_text) > 20:
                                    logger.info(f"✅ Extracted LAST response using selector: {selector}")
                                    logger.info(f"📏 Response length: {len(response_text)} chars")
                                    logger.info(f"📝 Response preview: {response_text[:100]}...")
                                    return response_text
                        except Exception as selector_error:
                            logger.debug(f"Selector {selector} failed: {selector_error}")
                            continue
                    
                    # Fallback: Get text from the last message element directly
                    response_text = last_message.text.strip()
                    if len(response_text) > 20:
                        logger.info(f"✅ Extracted LAST response from message element directly")
                        logger.info(f"📏 Response length: {len(response_text)} chars")
                        logger.info(f"📝 Response preview: {response_text[:100]}...")
                        return response_text
                    else:
                        logger.warning(f"⚠️ Last message text too short ({len(response_text)} chars): {response_text}")
                else:
                    logger.warning("⚠️ No assistant messages found with data-message-author-role='assistant'")
                    
            except Exception as e:
                logger.error(f"Error finding assistant messages: {e}")
            
            # FALLBACK STRATEGY: Try to find any markdown elements and pick the LAST one
            logger.info("🔄 Trying fallback: searching for markdown elements...")
            try:
                all_markdown = self.driver.find_elements(By.CSS_SELECTOR, ".markdown")
                if all_markdown:
                    total_markdown = len(all_markdown)
                    logger.info(f"📊 Found {total_markdown} markdown elements")
                    
                    # Iterate from LAST to first
                    for idx, markdown in enumerate(reversed(all_markdown)):
                        position = total_markdown - idx  # Calculate position for logging
                        try:
                            if markdown.is_displayed():
                                text = markdown.text.strip()
                                if len(text) > 20:
                                    logger.info(f"✅ Extracted response from markdown #{position} (LAST visible)")
                                    logger.info(f"📏 Response length: {len(text)} chars")
                                    logger.info(f"📝 Response preview: {text[:100]}...")
                                    return text
                                else:
                                    logger.debug(f"Markdown #{position} too short: {len(text)} chars")
                        except Exception as markdown_error:
                            logger.debug(f"Error with markdown #{position}: {markdown_error}")
                            continue
            except Exception as e:
                logger.debug(f"Fallback failed: {e}")
            
            # LAST RESORT: Try any visible text container
            logger.info("🔄 Last resort: searching for any text containers...")
            try:
                text_containers = self.driver.find_elements(By.CSS_SELECTOR, "div.text-base, div.whitespace-pre-wrap, div[class*='text']")
                if text_containers:
                    logger.info(f"📊 Found {len(text_containers)} text containers")
                    
                    # Check from last to first
                    for container in reversed(text_containers):
                        try:
                            if container.is_displayed():
                                text = container.text.strip()
                                if len(text) > 20:
                                    logger.info(f"✅ Extracted response from text container (last resort)")
                                    logger.info(f"📏 Response length: {len(text)} chars")
                                    return text
                        except:
                            continue
            except Exception as e:
                logger.debug(f"Last resort failed: {e}")
            
            logger.warning("❌ No valid response found from ChatGPT")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting response: {e}")
            return None
    
    def refresh(self) -> bool:
        """Refresh ChatGPT with new chat session"""
        try:
            logger.info("🔄 Starting fresh ChatGPT chat...")
            
            # Close current tab
            self.driver.close()
            time.sleep(1)
            
            # Switch back to Twitter
            if self.driver.window_handles:
                self.driver.switch_to.window(self.driver.window_handles[0])
            
            # Open fresh ChatGPT
            logger.info("🆕 Opening fresh ChatGPT...")
            if not self.navigate_new_tab():
                logger.error("❌ Failed to open fresh ChatGPT")
                return False
            
            # Reset counters
            self.current_chat_response_count = 0
            self.last_response_text = None
            self.last_response_time = 0
            logger.info("🔄 Reset chat response counter")
            
            logger.info("✅ Fresh ChatGPT ready!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error refreshing ChatGPT: {e}")
            return False
    
    def switch_to_tab(self) -> bool:
        """Switch to ChatGPT tab"""
        try:
            logger.info("Switching to ChatGPT tab...")
            
            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                current_url = self.driver.current_url
                if 'chatgpt.com' in current_url or 'chat.openai.com' in current_url:
                    logger.info("Successfully switched to ChatGPT tab")
                    return True
            
            logger.error("Could not find ChatGPT tab")
            return False
            
        except Exception as e:
            logger.error(f"Error switching to ChatGPT tab: {e}")
            return False


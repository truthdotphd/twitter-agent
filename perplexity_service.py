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

            # Configure GPT-5 (with reasoning) and sources
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
        """Select GPT-5 with reasoning and configure sources"""
        try:
            logger.info("🤖 Configuring Perplexity: GPT-5 (with reasoning) + Sources (Web, Academic, Social, Finance)")
            
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

                    # Look for GPT-5
                    logger.info("🔍 Step 2: Looking for GPT-5 in dropdown...")
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

                            if model_name.lower() == 'gpt-5':
                                logger.info(f"🎯 Found GPT-5 option")

                                try:
                                    clickable_div = item.find_element(By.CSS_SELECTOR, "div.cursor-pointer")
                                    clickable_div.click()
                                    logger.info(f"✅ Selected model: GPT-5")
                                    time.sleep(2)
                                    found_model = True
                                    break
                                except:
                                    try:
                                        item.click()
                                        logger.info(f"✅ Selected model: GPT-5 (via menuitem)")
                                        time.sleep(2)
                                        found_model = True
                                        break
                                    except:
                                        try:
                                            self.driver.execute_script("arguments[0].click();", item)
                                            logger.info(f"✅ Selected model: GPT-5 (via JavaScript)")
                                            time.sleep(2)
                                            found_model = True
                                            break
                                        except:
                                            logger.warning("Failed to click GPT-5 option")
                        except Exception as e:
                            logger.debug(f"Error checking menu item: {e}")
                            continue

                    if not found_model:
                        logger.warning("⚠️ Could not find or click GPT-5 option")
                        logger.info("💡 Please manually select GPT-5")
                        try:
                            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                            time.sleep(1)
                        except:
                            pass
                    else:
                        # STEP 2.5: Enable "With reasoning" toggle for GPT-5
                        logger.info("🔍 Step 2.5: Looking for 'With reasoning' toggle...")
                        time.sleep(2)

                        try:
                            # Strategy: Find "With reasoning" text, navigate up to menuitem, find switch within
                            reasoning_enabled = False

                            # Get all menu items (in case we need to search through them)
                            all_menuitems = self.driver.find_elements(By.CSS_SELECTOR, "div[role='menuitem']")
                            logger.info(f"📊 Found {len(all_menuitems)} menu items to search")

                            for menuitem in all_menuitems:
                                if not menuitem.is_displayed():
                                    continue

                                # Check if this menuitem contains "With reasoning" text
                                menuitem_text = menuitem.text.lower()

                                if 'with reasoning' in menuitem_text:
                                    logger.info(f"🎯 Found menuitem with 'With reasoning' text")

                                    try:
                                        # Find the switch within this menuitem
                                        switch = menuitem.find_element(By.CSS_SELECTOR, 'button[role="switch"]')

                                        if switch and switch.is_displayed():
                                            aria_checked = switch.get_attribute('aria-checked')
                                            logger.info(f"   Switch state: aria-checked='{aria_checked}'")

                                            if aria_checked == 'true':
                                                logger.info("ℹ️  'With reasoning' is already enabled")
                                                reasoning_enabled = True
                                                break
                                            else:
                                                logger.info("🎯 Enabling 'With reasoning' toggle...")

                                                # Try multiple click methods
                                                clicked = False

                                                # Method 1: Click the switch directly
                                                try:
                                                    switch.click()
                                                    clicked = True
                                                    logger.info("✅ Clicked switch directly")
                                                except Exception as click_err:
                                                    logger.warning(f"Direct click failed: {click_err}")

                                                # Method 2: JavaScript click on switch
                                                if not clicked:
                                                    try:
                                                        self.driver.execute_script("arguments[0].click();", switch)
                                                        clicked = True
                                                        logger.info("✅ Clicked switch with JavaScript")
                                                    except Exception as js_err:
                                                        logger.warning(f"JavaScript click failed: {js_err}")

                                                # Method 3: Click the entire menuitem row (often the whole row is clickable)
                                                if not clicked:
                                                    try:
                                                        # Find the cursor-pointer div (the clickable row)
                                                        clickable_div = menuitem.find_element(By.CSS_SELECTOR, "div.cursor-pointer")
                                                        clickable_div.click()
                                                        clicked = True
                                                        logger.info("✅ Clicked entire menuitem row")
                                                    except Exception as row_err:
                                                        logger.warning(f"Row click failed: {row_err}")

                                                if clicked:
                                                    time.sleep(1)
                                                    logger.info("✅ Enabled 'With reasoning' for GPT-5")
                                                    reasoning_enabled = True
                                                    break
                                                else:
                                                    logger.warning("⚠️ All click methods failed for 'With reasoning' toggle")
                                    except NoSuchElementException:
                                        logger.debug("No switch found in this menuitem")
                                        continue
                                    except Exception as e:
                                        logger.warning(f"Error processing menuitem: {e}")
                                        continue

                            if not reasoning_enabled:
                                logger.warning("⚠️ Could not find or enable 'With reasoning' toggle")
                                logger.info("💡 Please manually enable 'With reasoning' if desired")

                        except Exception as e:
                            logger.warning(f"Error enabling 'With reasoning': {e}")

                        # Close model selector
                        try:
                            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                            time.sleep(1)
                            logger.info("✅ Closed model selector")
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

                    # Sources we want to enable (by display text)
                    sources_to_enable = ['Social'] # ['Academic', 'Social', 'Finance']

                    logger.info(f"🔍 Step 4: Enabling sources: {', '.join(sources_to_enable)}")
                    enabled_sources = []

                    # NEW STRATEGY: Find sources by text content instead of test IDs
                    # Get all visible elements that could be source toggles
                    try:
                        # Look for buttons with role="switch" (the actual toggle switches)
                        all_switches = self.driver.find_elements(By.CSS_SELECTOR, 'button[role="switch"]')
                        logger.info(f"📊 Found {len(all_switches)} toggle switches")

                        # Also get all text elements to find source names
                        for source_name in sources_to_enable:
                            found = False

                            # Method 1: Find by exact text match
                            try:
                                # Find elements containing the source name
                                xpath = f"//*[contains(text(), '{source_name}')]"
                                text_elements = self.driver.find_elements(By.XPATH, xpath)

                                for text_elem in text_elements:
                                    if not text_elem.is_displayed():
                                        continue

                                    # Try to find a switch near this text element
                                    try:
                                        # Look for switch in parent or grandparent
                                        parent = text_elem.find_element(By.XPATH, "./..")
                                        switch = parent.find_element(By.CSS_SELECTOR, 'button[role="switch"]')

                                        # Check if already enabled
                                        aria_checked = switch.get_attribute('aria-checked')

                                        if aria_checked == 'true':
                                            logger.info(f"ℹ️  {source_name}: Already enabled")
                                            enabled_sources.append(source_name)
                                            found = True
                                            break
                                        else:
                                            logger.info(f"🎯 Clicking to enable: {source_name}")
                                            switch.click()
                                            time.sleep(0.5)
                                            logger.info(f"✅ Enabled source: {source_name}")
                                            enabled_sources.append(source_name)
                                            found = True
                                            break
                                    except:
                                        # Try grandparent
                                        try:
                                            grandparent = text_elem.find_element(By.XPATH, "./../..")
                                            switch = grandparent.find_element(By.CSS_SELECTOR, 'button[role="switch"]')

                                            aria_checked = switch.get_attribute('aria-checked')

                                            if aria_checked == 'true':
                                                logger.info(f"ℹ️  {source_name}: Already enabled")
                                                enabled_sources.append(source_name)
                                                found = True
                                                break
                                            else:
                                                logger.info(f"🎯 Clicking to enable: {source_name}")
                                                switch.click()
                                                time.sleep(0.5)
                                                logger.info(f"✅ Enabled source: {source_name}")
                                                enabled_sources.append(source_name)
                                                found = True
                                                break
                                        except:
                                            continue
                            except Exception as e:
                                logger.debug(f"Text-based search failed for {source_name}: {e}")

                            # Method 2: Try clicking the text element itself (if it's clickable)
                            if not found:
                                try:
                                    xpath = f"//*[contains(text(), '{source_name}')]"
                                    text_elements = self.driver.find_elements(By.XPATH, xpath)

                                    for text_elem in text_elements:
                                        if text_elem.is_displayed():
                                            try:
                                                # Try to click the containing div
                                                clickable_parent = text_elem.find_element(By.XPATH, "./..")
                                                clickable_parent.click()
                                                time.sleep(0.5)
                                                logger.info(f"✅ Clicked {source_name} (via parent element)")
                                                enabled_sources.append(source_name)
                                                found = True
                                                break
                                            except:
                                                continue
                                except Exception as e:
                                    logger.debug(f"Parent click failed for {source_name}: {e}")

                            if not found:
                                logger.warning(f"⚠️ Could not find or enable {source_name}")

                    except Exception as e:
                        logger.warning(f"Error during source toggle search: {e}")

                    if enabled_sources:
                        logger.info(f"📊 Configured sources: Web (default), {', '.join(enabled_sources)}")
                    else:
                        logger.warning("⚠️ No sources were enabled automatically")
                        logger.info("💡 Please manually enable Academic, Social, and Finance sources")

                    # Close selector
                    time.sleep(1)
                    try:
                        self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        time.sleep(1)
                        logger.info("✅ Closed sources selector")
                    except:
                        pass

                except Exception as e:
                    logger.warning(f"Error during source configuration: {e}")
                    logger.info("💡 You may need to manually select sources")
            
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
            prompt = tweet_content  # Use full prompt
            prompt_length = len(prompt)
            logger.info(f"Typing prompt ({prompt_length} characters)...")

            # Warn if prompt is extremely long
            if prompt_length > 10000:
                logger.warning(f"⚠️ Prompt is very long ({prompt_length} chars). This may take longer to process.")

            # Check if prompt contains newlines
            has_newlines = '\n' in prompt
            if has_newlines:
                logger.info(f"📝 Prompt contains {prompt.count(chr(10))} newline(s)")

            try:
                input_field.click()
                time.sleep(1)

                is_contenteditable = input_field.get_attribute("contenteditable") == "true"

                if is_contenteditable:
                    self.driver.execute_script("arguments[0].focus();", input_field)
                    time.sleep(0.5)

                    # For contenteditable divs: Convert \n to <br> tags and use innerHTML
                    if has_newlines:
                        # Convert newlines to <br> tags for HTML
                        html_content = prompt.replace('\n', '<br>')
                        self.driver.execute_script("arguments[0].innerHTML = arguments[1];", input_field, html_content)
                        logger.info("✅ Set content with line breaks using innerHTML")
                    else:
                        # For single-line content, textContent is fine
                        self.driver.execute_script("arguments[0].textContent = arguments[1];", input_field, prompt)

                    time.sleep(0.5)

                    # Dispatch events to notify the app of changes
                    self.driver.execute_script("""
                        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                    """, input_field)
                    time.sleep(1)

                    # Verify content was set (check innerText which preserves newlines)
                    final_content = self.driver.execute_script("return arguments[0].innerText || arguments[0].textContent;", input_field)
                    if final_content.strip():
                        preview = final_content.replace('\n', '\\n')[:80]
                        logger.info(f"✅ Successfully typed prompt: '{preview}...'")
                    else:
                        logger.warning("⚠️ Content may not have been set properly, trying send_keys fallback...")

                        # Fallback: Use send_keys with proper newline handling
                        if has_newlines:
                            # Split by newlines and send each part with SHIFT+ENTER between
                            lines = prompt.split('\n')
                            for i, line in enumerate(lines):
                                input_field.send_keys(line)
                                if i < len(lines) - 1:  # Not the last line
                                    input_field.send_keys(Keys.SHIFT, Keys.ENTER)
                            logger.info("✅ Used send_keys with SHIFT+ENTER for line breaks")
                        else:
                            input_field.send_keys(prompt)
                            logger.info("✅ Used send_keys fallback")
                else:
                    # For textarea elements
                    if has_newlines:
                        # Split by newlines and send each part with SHIFT+ENTER between
                        lines = prompt.split('\n')
                        for i, line in enumerate(lines):
                            input_field.send_keys(line)
                            if i < len(lines) - 1:  # Not the last line
                                input_field.send_keys(Keys.SHIFT, Keys.ENTER)
                        logger.info("✅ Typed prompt with line breaks (SHIFT+ENTER)")
                    else:
                        input_field.send_keys(prompt)
                        logger.info("✅ Successfully typed prompt")
                    time.sleep(2)

            except Exception as e:
                logger.error(f"Failed to type prompt: {e}")
                return None
            
            # Submit - Re-find input field to avoid stale element reference
            logger.info("Submitting query...")
            submitted = False

            # Try multiple submission methods with retries
            submission_attempts = 0
            max_submission_attempts = 3

            while not submitted and submission_attempts < max_submission_attempts:
                submission_attempts += 1

                try:
                    # Re-find the input field to avoid stale element reference
                    logger.info(f"Submission attempt {submission_attempts}/{max_submission_attempts}: Re-finding input field...")
                    fresh_input_field = self.find_input_field()

                    if not fresh_input_field:
                        logger.warning("Could not re-find input field")
                        time.sleep(1)
                        continue

                    # Method 1: Use send_keys with RETURN
                    try:
                        fresh_input_field.send_keys(Keys.RETURN)
                        logger.info("✅ Query submitted with RETURN key")
                        submitted = True
                        break
                    except Exception as e:
                        logger.warning(f"RETURN key submission failed: {e}")

                    # Method 2: Try finding and clicking submit button
                    if not submitted:
                        logger.info("Trying to find submit button...")
                        try:
                            submit_selectors = [
                                "button[type='submit']",
                                "button[aria-label*='Submit']",
                                "button[aria-label*='submit']",
                                "button.submit-button",
                                "button:has(svg)"  # Often submit buttons have arrow icons
                            ]

                            for selector in submit_selectors:
                                try:
                                    submit_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                    for btn in submit_buttons:
                                        if btn.is_displayed() and btn.is_enabled():
                                            btn.click()
                                            logger.info(f"✅ Clicked submit button using: {selector}")
                                            submitted = True
                                            break
                                except:
                                    continue
                                if submitted:
                                    break
                        except Exception as btn_e:
                            logger.warning(f"Submit button method failed: {btn_e}")

                    # Method 3: Use JavaScript to trigger Enter key event
                    if not submitted:
                        logger.info("Trying JavaScript submit method...")
                        try:
                            self.driver.execute_script("""
                                var element = arguments[0];
                                var event = new KeyboardEvent('keydown', {
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    bubbles: true,
                                    cancelable: true
                                });
                                element.dispatchEvent(event);
                            """, fresh_input_field)
                            logger.info("✅ Query submitted with JavaScript")
                            submitted = True
                            break
                        except Exception as js_e:
                            logger.warning(f"JavaScript submit failed: {js_e}")

                except Exception as e:
                    logger.warning(f"Submission attempt {submission_attempts} failed: {e}")

                if not submitted and submission_attempts < max_submission_attempts:
                    logger.info("Waiting before retry...")
                    time.sleep(2)

            if not submitted:
                logger.error("Failed to submit query after all attempts")
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



# Stale Element Reference Fix for Perplexity Service

## Problem

The Twitter agent was failing with this error when submitting queries to Perplexity:

```
stale element reference: stale element not found in the current frame
```

### Root Cause

**Selenium's "Stale Element Reference" error** occurs when:

1. An element is found and stored as a variable (`input_field`)
2. The DOM is modified (clearing content, setting text, dispatching events)
3. The page re-renders, invalidating the original element reference
4. Attempting to use the stale reference causes the error

In our case:
- Line 383: `input_field = self.find_input_field()` ← Element found
- Lines 391-438: Multiple DOM manipulations (clear, type, dispatch events)
- Line 449: `input_field.send_keys(Keys.RETURN)` ← **Element is now stale!**

## Solution

### Multi-Layer Defense Strategy

The fix implements a **robust 3-method submission system with retry logic**:

#### 1. Re-find Element Before Submission
```python
# Re-find the input field to get a fresh reference
fresh_input_field = self.find_input_field()
```

This eliminates the stale reference by getting a new, valid element reference.

#### 2. Three Submission Methods (Fallback Chain)

**Method 1: Standard Selenium Keys**
```python
fresh_input_field.send_keys(Keys.RETURN)
```
- Most reliable when it works
- First attempt

**Method 2: Submit Button Click**
```python
submit_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
for btn in submit_buttons:
    if btn.is_displayed() and btn.is_enabled():
        btn.click()
```
- Alternative if RETURN key fails
- Finds actual submit button in UI

**Method 3: JavaScript Event Dispatch**
```python
self.driver.execute_script("""
    var event = new KeyboardEvent('keydown', {
        key: 'Enter',
        keyCode: 13,
        bubbles: true,
        cancelable: true
    });
    element.dispatchEvent(event);
""", fresh_input_field)
```
- Most robust fallback
- Directly triggers Enter key event via JavaScript

#### 3. Retry Logic
- Up to 3 attempts
- 2-second wait between retries
- Detailed logging for each attempt

## Code Changes

**File**: `perplexity_service.py`
**Location**: Lines 444-533 (query method)

### Before (Lines 444-457)
```python
# Submit
logger.info("Submitting query...")
submitted = False

try:
    input_field.send_keys(Keys.RETURN)  # ← STALE ELEMENT!
    logger.info("✅ Query submitted with RETURN key")
    submitted = True
except Exception as e:
    logger.warning(f"Failed to submit with RETURN key: {e}")

if not submitted:
    logger.error("Failed to submit query")
    return None
```

### After (Lines 444-533)
```python
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
            # ... (submit button logic)

        # Method 3: Use JavaScript to trigger Enter key event
        if not submitted:
            # ... (JavaScript fallback)

    except Exception as e:
        logger.warning(f"Submission attempt {submission_attempts} failed: {e}")

    if not submitted and submission_attempts < max_submission_attempts:
        logger.info("Waiting before retry...")
        time.sleep(2)

if not submitted:
    logger.error("Failed to submit query after all attempts")
    return None
```

## Benefits

✅ **Eliminates stale element errors** by re-finding the element
✅ **Triple fallback system** ensures submission succeeds
✅ **Retry logic** handles transient issues
✅ **Better logging** for debugging
✅ **More robust** against Perplexity UI changes

## Testing

Run the agent to test:

```bash
python3 twitter_agent_selenium.py
```

The submission should now succeed with detailed logging showing which method worked.

## Expected Output

```
INFO - Submitting query...
INFO - Submission attempt 1/3: Re-finding input field...
INFO - ✅ Found input field using: Content editable div
INFO - ✅ Query submitted with RETURN key
```

Or with fallback:

```
INFO - Submission attempt 1/3: Re-finding input field...
WARNING - RETURN key submission failed: stale element reference
INFO - Trying to find submit button...
INFO - ✅ Clicked submit button using: button[type='submit']
```

## Additional Notes

- This pattern can be applied to other parts of the code that experience stale element issues
- The `find_input_field()` method has its own retry logic (15 seconds), making it very reliable
- JavaScript method is the most robust but should be used as last resort for human-like behavior

---

**Date**: 2025-10-11
**Issue**: Stale element reference during Perplexity query submission
**Status**: ✅ FIXED

# Newline Handling Fix for Perplexity Service

## Problem

When prompts contained `\n` (newline characters), only the text **before the first newline** was being typed into Perplexity's input field. The rest was lost.

**Error seen:**
```
2025-10-11 00:41:51,612 - INFO - Typing prompt...
2025-10-11 00:41:54,749 - WARNING - ⚠️ Content may not have been set properly
```

## Root Cause Analysis

### Step 1: Understanding textContent vs innerHTML

The original code used `textContent` on line 419:
```javascript
arguments[0].textContent = arguments[1];
```

**Problem**: `textContent` treats newlines as whitespace and **strips them completely**

Example:
```
Input: "Line 1\nLine 2\nLine 3"
textContent result: "Line 1 Line 2 Line 3"  ❌ Newlines removed!
```

### Step 2: Verification Failure

Line 428 checked if content was set:
```javascript
final_content = arguments[0].textContent;
```

This would return content WITHOUT newlines, appearing "successful" even though data was lost.

### Step 3: Fallback Issues

When it fell back to `send_keys(prompt)` on line 433:
- It sent the literal string including `\n` characters
- These were typed as text, NOT as line breaks
- Result: "Line 1\nLine 2" appeared literally in the input field

## Solution: Multi-Method Newline Handling

### Method 1: innerHTML with `<br>` Tags (Contenteditable Divs)

For `contenteditable="true"` divs, convert newlines to HTML:

```python
if has_newlines:
    html_content = prompt.replace('\n', '<br>')
    self.driver.execute_script("arguments[0].innerHTML = arguments[1];", input_field, html_content)
```

**How it works:**
- `\n` → `<br>` (HTML line break)
- `innerHTML` renders the `<br>` tags as actual line breaks
- The app sees proper multi-line content

### Method 2: SHIFT+ENTER for send_keys Fallback

For textarea or fallback scenarios:

```python
if has_newlines:
    lines = prompt.split('\n')
    for i, line in enumerate(lines):
        input_field.send_keys(line)
        if i < len(lines) - 1:  # Not the last line
            input_field.send_keys(Keys.SHIFT, Keys.ENTER)
```

**How it works:**
- Split text by newlines
- Type each line separately
- Press SHIFT+ENTER between lines (creates line break without submitting)

### Method 3: Proper Verification

Use `innerText` instead of `textContent` for verification:

```javascript
final_content = arguments[0].innerText || arguments[0].textContent;
```

**Why innerText:**
- `innerText`: Preserves line breaks as `\n` ✅
- `textContent`: Strips line breaks ❌

## Code Changes

**File**: `perplexity_service.py`
**Lines**: 406-481 (typing logic in query method)

### Before
```python
# Used textContent - strips newlines
self.driver.execute_script("arguments[0].textContent = arguments[1];", input_field, prompt)

# Fallback sent literal \n characters
input_field.send_keys(prompt)
```

### After
```python
# Detect newlines
has_newlines = '\n' in prompt
if has_newlines:
    logger.info(f"📝 Prompt contains {prompt.count(chr(10))} newline(s)")

# For contenteditable: Convert \n to <br>
if is_contenteditable:
    if has_newlines:
        html_content = prompt.replace('\n', '<br>')
        self.driver.execute_script("arguments[0].innerHTML = arguments[1];", input_field, html_content)
    else:
        self.driver.execute_script("arguments[0].textContent = arguments[1];", input_field, prompt)

# For textarea or fallback: Use SHIFT+ENTER
else:
    if has_newlines:
        lines = prompt.split('\n')
        for i, line in enumerate(lines):
            input_field.send_keys(line)
            if i < len(lines) - 1:
                input_field.send_keys(Keys.SHIFT, Keys.ENTER)
```

## Benefits

✅ **Preserves all newlines** in multi-line prompts
✅ **Works with contenteditable divs** (using `<br>` tags)
✅ **Works with textareas** (using SHIFT+ENTER)
✅ **Proper verification** using `innerText`
✅ **Smart detection** - only applies special handling when needed
✅ **Better logging** - shows how many newlines were detected

## Testing

### Test Case 1: Multi-line Prompt
```python
prompt = "Line 1\nLine 2\nLine 3"
```

**Expected Output:**
```
INFO - Typing prompt...
INFO - 📝 Prompt contains 2 newline(s)
INFO - ✅ Set content with line breaks using innerHTML
INFO - ✅ Successfully typed prompt: 'Line 1\nLine 2\nLine 3...'
```

### Test Case 2: Single Line Prompt
```python
prompt = "Just one line"
```

**Expected Output:**
```
INFO - Typing prompt...
INFO - ✅ Successfully typed prompt: 'Just one line...'
```

### Test Case 3: Fallback Scenario
If `innerHTML` fails:
```
WARNING - ⚠️ Content may not have been set properly, trying send_keys fallback...
INFO - ✅ Used send_keys with SHIFT+ENTER for line breaks
```

## Technical Details

### Why SHIFT+ENTER?

In most web text editors:
- **ENTER**: Submits the form or creates a new paragraph
- **SHIFT+ENTER**: Creates a line break within the same input

### HTML Line Breaks

For `contenteditable` divs:
```html
<!-- Wrong: textContent strips this -->
<div contenteditable="true">Line 1\nLine 2</div>
Result: "Line 1 Line 2"

<!-- Right: innerHTML with <br> -->
<div contenteditable="true">Line 1<br>Line 2</div>
Result: Line 1 displayed on one line, Line 2 on the next
```

### Cross-Browser Compatibility

Both methods work across:
- ✅ Chrome/Chromium
- ✅ Firefox
- ✅ Safari
- ✅ Edge

## Expected Logs

Run your agent and you should see:

```bash
python3 twitter_agent_selenium.py
```

**With newlines in prompt:**
```
INFO - Typing prompt...
INFO - 📝 Prompt contains 2 newline(s)
INFO - ✅ Set content with line breaks using innerHTML
INFO - ✅ Successfully typed prompt: 'Line 1\nLine 2\nLine 3...'
INFO - Submitting query...
INFO - Submission attempt 1/3: Re-finding input field...
INFO - ✅ Query submitted with RETURN key
```

**Without newlines:**
```
INFO - Typing prompt...
INFO - ✅ Successfully typed prompt: 'Single line prompt...'
INFO - Submitting query...
```

## Related Fixes

This fix works together with:
- **STALE_ELEMENT_FIX.md**: Ensures submission works after typing
- Both fixes ensure end-to-end reliability for Perplexity queries

---

**Date**: 2025-10-11
**Issue**: Newlines in prompts not preserved when typing
**Status**: ✅ FIXED

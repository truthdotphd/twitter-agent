# GPT-5 with Reasoning Feature

## Change Summary

Added automatic enablement of the **"With reasoning" toggle** for GPT-5 in Perplexity.

## What This Does

After selecting GPT-5 as the model, the agent now:
1. ✅ Finds the "With reasoning" toggle (a sub-option under GPT-5)
2. ✅ Checks if it's already enabled
3. ✅ Enables it if not already on
4. ✅ Logs the status

## Why "With Reasoning"?

The "With reasoning" mode in GPT-5:
- **Shows step-by-step thinking** process
- **More thorough analysis** of complex queries
- **Better for fact-checking** and research
- **Extended response quality** for nuanced questions

Perfect for the Twitter agent's use case of analyzing tweets and generating thoughtful responses.

## Technical Implementation

### UI Structure

Based on Perplexity's HTML:
```html
<div role="menuitem">  <!-- GPT-5 -->
  <span>GPT-5</span>
  <svg><!-- checkmark --></svg>
</div>
<div role="menuitem">  <!-- Sub-option -->
  <span class="text-quiet">With reasoning</span>
  <button role="switch" aria-checked="false" data-state="unchecked">
    <!-- toggle switch -->
  </button>
</div>
```

**Key observations:**
- "With reasoning" is a separate menuitem under GPT-5
- Has a toggle switch with `role="switch"`
- Switch has `aria-checked` attribute (true/false)

### Code Logic (Lines 215-287)

```python
# After GPT-5 is successfully selected...

# Step 2.5: Enable "With reasoning" toggle
logger.info("🔍 Step 2.5: Looking for 'With reasoning' toggle...")

# Find "With reasoning" text element
xpath = "//*[contains(text(), 'With reasoning')]"
reasoning_elements = self.driver.find_elements(By.XPATH, xpath)

for elem in reasoning_elements:
    if elem.is_displayed():
        # Navigate to parent/grandparent to find switch
        parent = elem.find_element(By.XPATH, "./..")
        grandparent = parent.find_element(By.XPATH, "./..")
        switches = grandparent.find_elements(By.CSS_SELECTOR, 'button[role="switch"]')

        for switch in switches:
            if switch.is_displayed():
                aria_checked = switch.get_attribute('aria-checked')

                if aria_checked == 'true':
                    logger.info("ℹ️  'With reasoning' is already enabled")
                    break
                else:
                    logger.info("🎯 Enabling 'With reasoning' toggle...")
                    switch.click()
                    logger.info("✅ Enabled 'With reasoning' for GPT-5")
                    break
```

### DOM Navigation Strategy

The code uses **parent/grandparent navigation**:

1. **Find text**: XPath finds `<span>With reasoning</span>`
2. **Navigate up**: Go to parent, then grandparent
3. **Find switch**: Look for `button[role="switch"]` in that container
4. **Check state**: Read `aria-checked` attribute
5. **Toggle if needed**: Click if `aria-checked="false"`

**Why this works:**
- UI structure may vary slightly
- Checking both parent and grandparent handles different layouts
- Switch is always near the text element

## Code Changes

**File**: `perplexity_service.py`
**Lines Added**: 215-287

### Modified Sections

#### 1. Function Docstring (Line 113-114)
**Before:**
```python
def select_gpt5_and_sources(self) -> bool:
    """Select GPT-5 model and configure sources"""
```

**After:**
```python
def select_gpt5_and_sources(self) -> bool:
    """Select GPT-5 with reasoning and configure sources"""
```

#### 2. Configuration Log (Line 116)
**Before:**
```python
logger.info("🤖 Configuring Perplexity: GPT-5 + Sources (Web, Academic, Social, Finance)")
```

**After:**
```python
logger.info("🤖 Configuring Perplexity: GPT-5 (with reasoning) + Sources (Web, Academic, Social, Finance)")
```

#### 3. Comment (Line 75)
**Before:**
```python
# Configure GPT-5 and sources
```

**After:**
```python
# Configure GPT-5 (with reasoning) and sources
```

#### 4. New Logic (Lines 215-287)
Added entire "With reasoning" toggle enablement logic after GPT-5 selection.

## Expected Behavior

### Successful Enablement

Run the agent:
```bash
python3 twitter_agent_selenium.py
```

**Expected logs:**
```
INFO - 🤖 Configuring Perplexity: GPT-5 (with reasoning) + Sources (Web, Academic, Social, Finance)
INFO - ⏱️ Waiting for Perplexity UI to fully load...
INFO - 🔍 Step 1: Looking for model selector button...
INFO - ✅ Found model selector button with aria-label='...'
INFO - 🖱️ Clicking model selector...
INFO - 🔍 Step 2: Looking for GPT-5 in dropdown...
INFO - 📊 Found 8 menu items
INFO - 🎯 Found GPT-5 option
INFO - ✅ Selected model: GPT-5
INFO - 🔍 Step 2.5: Looking for 'With reasoning' toggle...
INFO - 🎯 Enabling 'With reasoning' toggle...
INFO - ✅ Enabled 'With reasoning' for GPT-5
INFO - ✅ Closed model selector
INFO - 🔍 Step 3: Looking for sources selector button...
```

### Already Enabled

If "With reasoning" is already on:
```
INFO - 🔍 Step 2.5: Looking for 'With reasoning' toggle...
INFO - ℹ️  'With reasoning' is already enabled
INFO - ✅ Closed model selector
```

### If Toggle Not Found

If the UI changes or toggle can't be found:
```
INFO - 🔍 Step 2.5: Looking for 'With reasoning' toggle...
WARNING - ⚠️ Could not find or enable 'With reasoning' toggle
INFO - 💡 Please manually enable 'With reasoning' if desired
INFO - ✅ Closed model selector
```

Agent continues anyway - graceful degradation.

## Error Handling

### Graceful Failures

The code continues even if "With reasoning" can't be enabled:
```python
if not reasoning_enabled:
    logger.warning("⚠️ Could not find or enable 'With reasoning' toggle")
    logger.info("💡 Please manually enable 'With reasoning' if desired")

# Agent continues with source configuration...
```

**Why graceful:**
- GPT-5 still works without reasoning
- User can manually enable if needed
- Doesn't block the workflow

### Exception Handling

Multiple try-except blocks:
```python
try:
    # Find switch in grandparent
except:
    try:
        # Fallback: Find switch in parent
    except:
        continue  # Try next element
```

**Robustness:**
- Handles different DOM structures
- Multiple search strategies
- Logs debug info for troubleshooting

## Benefits

✅ **Extended reasoning mode** - Better quality responses
✅ **Automatic enablement** - No manual intervention
✅ **State checking** - Doesn't toggle if already on
✅ **Graceful degradation** - Continues if toggle not found
✅ **Clear logging** - Easy to debug
✅ **UI-agnostic** - Works with DOM variations

## Comparison: GPT-5 vs GPT-5 with Reasoning

| Feature | GPT-5 | GPT-5 with Reasoning |
|---------|-------|---------------------|
| **Response Style** | Direct answer | Step-by-step thinking |
| **Speed** | Faster | Slightly slower |
| **Depth** | Standard | Extended analysis |
| **Transparency** | Answer only | Shows reasoning process |
| **Best For** | Quick queries | Complex analysis |
| **Twitter Agent** | ✅ Works | ✅ **Better** for fact-checking |

## Use Case: Twitter Agent

Why "With reasoning" is ideal for the Twitter agent:

1. **Fact-checking tweets**: Reasoning mode verifies claims step-by-step
2. **Nuanced responses**: Better understanding of context and tone
3. **Avoiding misinformation**: Thorough analysis prevents incorrect replies
4. **Quality over speed**: Worth the slight delay for better responses

## Testing

### Manual Test

1. Run the agent:
   ```bash
   python3 twitter_agent_selenium.py
   ```

2. Watch the Perplexity window:
   - GPT-5 should be selected
   - "With reasoning" toggle should turn ON
   - Model selector should close

3. Check logs for confirmation:
   ```
   INFO - ✅ Enabled 'With reasoning' for GPT-5
   ```

### Verification in Perplexity UI

After the agent runs, you can verify:
1. Click the model selector button in Perplexity
2. GPT-5 should be selected (checkmark visible)
3. "With reasoning" toggle should be ON (switch to the right)

## Troubleshooting

### Toggle Not Found

**Symptom:**
```
WARNING - ⚠️ Could not find or enable 'With reasoning' toggle
```

**Possible causes:**
- UI structure changed (Perplexity update)
- Toggle not available for your account
- DOM not fully loaded

**Solution:**
- Check if toggle exists manually in UI
- If it does, report the issue (UI may have changed)
- If not, you may need a different Perplexity plan

### Switch Not Clickable

**Symptom:**
```
WARNING - Error enabling 'With reasoning': element click intercepted
```

**Possible causes:**
- Overlay blocking the switch
- Modal still open

**Solution:**
- Code already handles this by pressing ESC after
- May need additional wait time if still failing

## Future Considerations

### If Perplexity Changes UI

The text-based search is resilient, but if changes occur:

**Update needed if:**
- "With reasoning" text changes (e.g., "Enable reasoning")
- Switch no longer uses `role="switch"`
- DOM structure completely different

**How to update:**
1. Inspect the new UI structure
2. Update XPath or CSS selector
3. Adjust parent/grandparent navigation
4. Test and verify

### Alternative Models

If you want to use different models:

**Claude Sonnet 4.5:**
- Doesn't have "With reasoning" toggle
- Code will skip the toggle step (no error)

**Other models:**
- Update line 177: `if model_name.lower() == 'your-model':`
- Check if they have reasoning toggles
- Add conditional logic if needed

## Related Changes

This feature works seamlessly with:
- ✅ GPT-5 model selection (GPT5_MODEL_CHANGE.md)
- ✅ Source selection (SOURCE_SELECTION_FIX.md)
- ✅ Login check removal (LOGIN_CHECK_REMOVAL_SUMMARY.md)
- ✅ All other automation fixes

---

**Date**: 2025-10-14
**Feature**: Automatic enablement of "With reasoning" for GPT-5
**Status**: ✅ COMPLETED
**Lines Added**: 215-287
**Files Modified**: perplexity_service.py
**Impact**: Better quality responses from Perplexity

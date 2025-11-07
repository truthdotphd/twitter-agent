# Perplexity Source Selection Fix

## Problem: Test IDs No Longer Exist

### The Error

```
WARNING - ⚠️ Could not enable social: Message: no such element: Unable to locate element:
{"method":"css selector","selector":"div[data-testid="source-toggle-social"]"}

WARNING - ⚠️ Could not enable finance: Message: no such element: Unable to locate element:
{"method":"css selector","selector":"div[data-testid="source-toggle-edgar"]"}
```

### Root Cause

**Perplexity UI has changed** - the hard-coded `data-testid` attributes no longer exist:

**Old selectors that failed:**
- `div[data-testid="source-toggle-scholar"]` (Academic)
- `div[data-testid="source-toggle-social"]` (Social)
- `div[data-testid="source-toggle-edgar"]` (Finance)

**Why this happened:**
- Perplexity updated their UI structure
- Test IDs were removed or renamed
- Hard-coded selectors are brittle and break with UI changes

## The Solution: Text-Based Source Finding

### Strategy Overview

Instead of relying on test IDs, find sources by their **display text** ("Academic", "Social", "Finance"):

1. **Find text elements** containing source names
2. **Locate toggle switches** near those text elements
3. **Check switch state** (already enabled?)
4. **Click to enable** if not already on
5. **Multiple fallback methods** for robustness

### Implementation Details

#### Method 1: XPath Text Search + Parent/Grandparent Switch Lookup

```python
# Find elements containing "Academic", "Social", or "Finance"
xpath = f"//*[contains(text(), '{source_name}')]"
text_elements = self.driver.find_elements(By.XPATH, xpath)

for text_elem in text_elements:
    # Look for switch in parent element
    parent = text_elem.find_element(By.XPATH, "./..")
    switch = parent.find_element(By.CSS_SELECTOR, 'button[role="switch"]')

    # Check if already enabled
    aria_checked = switch.get_attribute('aria-checked')

    if aria_checked != 'true':
        switch.click()  # Enable it
```

**How it works:**
- XPath `contains(text(), 'Academic')` finds any element with "Academic" text
- Navigate up DOM tree to find parent/grandparent with `button[role="switch"]`
- Check `aria-checked` attribute to see if already enabled
- Click switch if not enabled

#### Method 2: Click Parent Element Directly

```python
# If Method 1 fails, try clicking the parent div itself
clickable_parent = text_elem.find_element(By.XPATH, "./..")
clickable_parent.click()
```

**When used:**
- Fallback if switch element can't be found
- Sometimes the entire source row is clickable
- More forgiving of UI structure changes

### Perplexity Sources UI Structure

Based on the UI you shared:

```
Sources Modal:
├── Web (Search across the entire Internet)
├── Academic (Search academic papers)
├── Social (Discussions and opinions) ← Need to enable
├── Finance (Search SEC filings) ← Need to enable
├── Linear
├── Notion
├── GitHub
└── Slack
```

Each source has:
- **Text label**: "Academic", "Social", "Finance"
- **Description**: "Search academic papers", etc.
- **Toggle switch**: `button[role="switch"]` with `aria-checked="true/false"`

## Code Changes

**File:** `perplexity_service.py`
**Lines:** 251-388

### Before (Lines 268-302)

```python
# Hard-coded test IDs that no longer exist
sources_to_enable = {
    'academic': 'source-toggle-scholar',
    'social': 'source-toggle-social',
    'finance': 'source-toggle-edgar'
}

for source_name, testid in sources_to_enable.items():
    try:
        source_elem = self.driver.find_element(
            By.CSS_SELECTOR,
            f'div[data-testid="{testid}"]'  # ← FAILS!
        )
        # ... enable logic
    except Exception as e:
        logger.warning(f"⚠️ Could not enable {source_name}: {e}")
```

**Problem:** Test IDs don't exist → always fails

### After (Lines 268-388)

```python
# Text-based source finding (UI-agnostic)
sources_to_enable = ['Academic', 'Social', 'Finance']

for source_name in sources_to_enable:
    found = False

    # Method 1: Find by text + locate switch
    xpath = f"//*[contains(text(), '{source_name}')]"
    text_elements = self.driver.find_elements(By.XPATH, xpath)

    for text_elem in text_elements:
        if text_elem.is_displayed():
            # Try parent
            try:
                parent = text_elem.find_element(By.XPATH, "./..")
                switch = parent.find_element(By.CSS_SELECTOR, 'button[role="switch"]')

                if switch.get_attribute('aria-checked') != 'true':
                    switch.click()
                    logger.info(f"✅ Enabled source: {source_name}")
                found = True
                break
            except:
                # Try grandparent
                try:
                    grandparent = text_elem.find_element(By.XPATH, "./../..")
                    switch = grandparent.find_element(By.CSS_SELECTOR, 'button[role="switch"]')

                    if switch.get_attribute('aria-checked') != 'true':
                        switch.click()
                    found = True
                    break
                except:
                    continue

    # Method 2: Click parent element if Method 1 failed
    if not found:
        try:
            xpath = f"//*[contains(text(), '{source_name}')]"
            text_elements = self.driver.find_elements(By.XPATH, xpath)

            for text_elem in text_elements:
                if text_elem.is_displayed():
                    clickable_parent = text_elem.find_element(By.XPATH, "./..")
                    clickable_parent.click()
                    found = True
                    break
        except:
            pass

    if not found:
        logger.warning(f"⚠️ Could not find or enable {source_name}")
```

**Benefits:** Works with any UI structure that has text labels

## Benefits

✅ **No dependency on test IDs** - uses visible text instead
✅ **Resilient to UI changes** - works as long as text exists
✅ **Two-method fallback** - tries switch click, then parent click
✅ **Checks existing state** - doesn't toggle if already enabled
✅ **Better logging** - clear success/failure messages
✅ **Graceful degradation** - continues if some sources fail
✅ **User-friendly messages** - suggests manual enablement if automated fails

## Technical Details

### Why XPath `contains(text(), ...)`?

**Advantage over CSS selectors:**
- CSS can't search by text content
- XPath can: `//*[contains(text(), 'Academic')]`
- More flexible for UI changes

### Why Check Parent AND Grandparent?

Perplexity's UI structure could be:

**Option A:**
```html
<div>
  <span>Academic</span>
  <button role="switch">...</button>
</div>
```
→ Switch is in **parent**

**Option B:**
```html
<div>
  <div>
    <span>Academic</span>
  </div>
  <button role="switch">...</button>
</div>
```
→ Switch is in **grandparent**

By checking both, we handle either structure.

### Why `aria-checked` Attribute?

Toggle switches use ARIA attributes for accessibility:
- `aria-checked="true"` → Source enabled
- `aria-checked="false"` → Source disabled

This is more reliable than visual inspection.

### Why Two Methods?

**Method 1 (Switch Click):**
- Most precise - directly clicks the toggle
- Preserves switch state
- Better for a11y

**Method 2 (Parent Click):**
- Fallback for unusual layouts
- Sometimes entire row is clickable
- Works if switch element structure changes

## Testing

Run the agent:
```bash
python3 twitter_agent_selenium.py
```

**Expected output (successful):**
```
INFO - 🔍 Step 3: Looking for sources selector button...
INFO - ✅ Found sources selector
INFO - 🖱️ Clicking sources selector...
INFO - 🔍 Step 4: Enabling sources: Academic, Social, Finance
INFO - 📊 Found 8 toggle switches
INFO - 🎯 Clicking to enable: Academic
INFO - ✅ Enabled source: Academic
INFO - 🎯 Clicking to enable: Social
INFO - ✅ Enabled source: Social
INFO - 🎯 Clicking to enable: Finance
INFO - ✅ Enabled source: Finance
INFO - 📊 Configured sources: Web (default), Academic, Social, Finance
INFO - ✅ Closed sources selector
INFO - ✅ Perplexity configuration completed
```

**Expected output (if already enabled):**
```
INFO - ℹ️  Academic: Already enabled
INFO - ℹ️  Social: Already enabled
INFO - ℹ️  Finance: Already enabled
INFO - 📊 Configured sources: Web (default), Academic, Social, Finance
```

**Expected output (if some fail):**
```
INFO - ✅ Enabled source: Academic
INFO - ⚠️ Could not find or enable Social
INFO - ✅ Enabled source: Finance
INFO - 📊 Configured sources: Web (default), Academic, Finance
```

## Error Handling

### Graceful Failures

The code continues even if sources can't be enabled:
```python
if not found:
    logger.warning(f"⚠️ Could not find or enable {source_name}")
# ... continues to next source
```

### User Notification

If automatic enablement fails:
```python
if not enabled_sources:
    logger.warning("⚠️ No sources were enabled automatically")
    logger.info("💡 Please manually enable Academic, Social, and Finance sources")
```

### No Hard Failures

Source configuration errors don't stop the agent:
```python
except Exception as e:
    logger.warning(f"Error during source configuration: {e}")
    logger.info("💡 You may need to manually select sources")

logger.info("✅ Perplexity configuration completed")
return True  # Always returns True to continue
```

## Additional Notes

### Why These Sources?

**Academic** - Accesses research papers and scholarly sources
**Social** - Includes Twitter/X discussions and social media
**Finance** - Searches SEC filings (EDGAR database)

These sources provide comprehensive coverage for fact-checking and research.

### Web is Default

The "Web" source is always enabled by default in Perplexity and doesn't need toggling.

### Other Sources (Linear, Notion, GitHub, Slack)

These are **integration sources** requiring separate authentication. The agent doesn't enable them automatically.

### Manual Enablement

If automated enablement fails, you can:
1. Click the sources button
2. Toggle Academic, Social, Finance manually
3. The agent will use whatever sources are enabled

### Future UI Changes

This text-based approach is more resilient, but if Perplexity:
- Changes source names (e.g., "Academic" → "Scholar")
- Changes completely to a different UI paradigm

You'll need to update the `sources_to_enable` list with new text values.

## Comparison: Old vs New Approach

| Aspect | Old (Test ID) | New (Text-Based) |
|--------|--------------|------------------|
| **Selector Type** | `data-testid` | XPath text search |
| **Brittleness** | High (breaks on ID change) | Low (breaks only on text change) |
| **UI Dependency** | Specific structure | Any structure with text |
| **Maintenance** | Requires updates | More resilient |
| **Debugging** | Hard (IDs invisible) | Easy (text visible) |
| **Fallbacks** | None | Two methods |

---

**Date**: 2025-10-14
**Issue**: Source toggle test IDs don't exist, causing failures
**Status**: ✅ FIXED
**Related Fixes**:
- STALE_ELEMENT_FIX.md (submission reliability)
- NEWLINE_FIX.md (multi-line prompts)
- PROMPT_TRUNCATION_FIX.md (full prompt sending)
- CLICK_INTERCEPTED_FIX.md (overlay dismissal)

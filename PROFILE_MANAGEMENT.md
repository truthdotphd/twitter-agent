# Chrome Profile Management for Twitter Agent

## Overview

The Twitter Agent now uses persistent Chrome profiles to remember your logins across sessions. This means you **won't need to re-login** every time you run the script!

## Changes Made

### 1. **Profile Directory Structure**
- **Old**: `~/.chrome_automation_profile/TwitterAgent/`
- **New**: `~/.chrome_automation_profile_twitter/TwitterAgent/`

### 2. **Simplified Profile Handling**
- Follows the proven pattern from `stock_analyzer.py`
- Uses `mkdir(exist_ok=True)` instead of `mkdir(parents=True, exist_ok=True)`
- Uses `str()` directly without `.absolute()`
- Cleaner argument passing to Chrome

### 3. **Optimized Chrome Options**
- Added `--no-sandbox` for better profile persistence
- Simplified preferences configuration
- Kept credentials **ENABLED** for login persistence
- Removed unnecessary profile exit preferences

## How It Works

### First Run
1. Chrome will open with a **fresh profile**
2. You'll need to log into:
   - X.com (Twitter)
   - Your AI service (ChatGPT/Perplexity/Gemini)
3. Chrome will **automatically save** these logins to the profile

### Subsequent Runs
1. Chrome will load your **saved profile**
2. You'll be **automatically logged in** to X.com
3. You'll be **automatically logged in** to your AI service
4. No manual login required! 🎉

## Setup Instructions

### Option 1: Clean Start (Recommended)

Run the cleanup script to remove old profiles and start fresh:

```bash
./clear_chrome_profiles.sh
```

Then run the Twitter Agent:

```bash
python3 twitter_agent_selenium.py
```

### Option 2: Manual Cleanup

Remove old profile directories:

```bash
# Remove old profile directory
rm -rf ~/.chrome_automation_profile

# Optional: Remove new profile directory (forces fresh start)
rm -rf ~/.chrome_automation_profile_twitter
```

Then run the Twitter Agent:

```bash
python3 twitter_agent_selenium.py
```

## Custom Profile Directory

You can customize the profile directory name using an environment variable:

```bash
# In your .env file
CHROME_PROFILE_DIRECTORY=MyCustomProfile
```

Or run directly:

```bash
CHROME_PROFILE_DIRECTORY=MyCustomProfile python3 twitter_agent_selenium.py
```

## Profile Location

Your Chrome profile data is stored at:

```
~/.chrome_automation_profile_twitter/TwitterAgent/
```

This includes:
- 🔐 Login sessions (cookies, tokens)
- ⚙️ Browser preferences
- 📝 Form data (if enabled)
- 🎨 UI customizations

## Troubleshooting

### Still Seeing Login Prompts?

1. **Check profile directory exists:**
   ```bash
   ls -la ~/.chrome_automation_profile_twitter/TwitterAgent/
   ```

2. **Look for Preferences file:**
   ```bash
   ls ~/.chrome_automation_profile_twitter/TwitterAgent/Preferences
   ```
   If this file exists, the profile is set up correctly.

3. **Clear and start fresh:**
   ```bash
   ./clear_chrome_profiles.sh
   python3 twitter_agent_selenium.py
   ```

4. **Check Chrome isn't running:**
   ```bash
   ./kill_chrome.sh
   ```
   Then try again.

### Profile Not Saving?

If your profile isn't persisting:

1. **Ensure clean exit**: Let Chrome close properly (don't kill the process)
2. **Check permissions**: Make sure you have write access to `~/.chrome_automation_profile_twitter/`
3. **Try without headless**: Set `HEADLESS=false` in `.env` to see what's happening
4. **Check logs**: Look for profile-related messages in the console output

### Different AI Services

Each AI service (ChatGPT, Perplexity, Gemini) will have its login saved to the **same profile**. You can switch AI services without re-logging in:

```bash
# In .env file
AI_SERVICE=chatgpt   # or perplexity, or gemini
```

## Technical Details

### Chrome Options Used

```python
--user-data-dir=~/.chrome_automation_profile_twitter
--profile-directory=TwitterAgent
--no-sandbox
--disable-dev-shm-usage
--no-first-run
--no-default-browser-check
--disable-popup-blocking
```

### Preferences

```python
"credentials_enable_service": True,        # Store credentials
"profile.password_manager_enabled": True,  # Enable password manager
"profile.default_content_setting_values.notifications": 2  # Block notifications
```

## Comparison with stock_analyzer.py

| Feature | stock_analyzer.py | twitter_agent_selenium.py |
|---------|-------------------|---------------------------|
| Chrome Driver | Regular `webdriver.Chrome()` | `undetected_chromedriver` |
| Profile Dir | `.chrome_automation_profile_stock_analyzer` | `.chrome_automation_profile_twitter` |
| Credentials | Disabled | **Enabled** (for login persistence) |
| Purpose | Stock analysis | Twitter automation |

## Security Notes

⚠️ **Important Security Information:**

- Your profile contains **sensitive login data**
- The profile is stored locally at `~/.chrome_automation_profile_twitter/`
- **Never commit** this directory to git (it's in `.gitignore`)
- **Never share** your profile directory with others
- If compromised, delete the profile and re-login:
  ```bash
  rm -rf ~/.chrome_automation_profile_twitter/
  ```

## Questions?

If you're still experiencing re-login issues:

1. Run `./clear_chrome_profiles.sh` for a clean start
2. Check the console logs for profile-related messages
3. Verify Chrome is using the correct profile directory
4. Ensure Chrome exits cleanly (don't force-kill)

---

**Last Updated**: Based on pattern from `stock_analyzer.py`  
**Status**: ✅ Tested and working


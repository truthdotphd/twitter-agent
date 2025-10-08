# Fixing X.com Login Issues

## The Problem
X.com (Twitter) detects automated browsers and blocks login attempts. You're seeing:
```
Could not log you in now. Please try again later.
```

## Solution 1: Use Your Chrome Profile (Recommended)

This allows the script to use your already-logged-in Chrome browser.

### Step 1: Find Your Chrome User Data Directory

**macOS:**
```
/Users/YOUR_USERNAME/Library/Application Support/Google/Chrome
```

**Linux:**
```
/home/YOUR_USERNAME/.config/google-chrome
```

**Windows:**
```
C:\Users\YOUR_USERNAME\AppData\Local\Google\Chrome\User Data
```

### Step 2: Create/Update `.env` File

Create a `.env` file in this directory with:

```env
# IMPORTANT: Replace YOUR_USERNAME with your actual username
CHROME_USER_DATA_DIR=/Users/YOUR_USERNAME/Library/Application Support/Google/Chrome
CHROME_PROFILE_DIRECTORY=Default

# Other settings
DELAY_BETWEEN_TWEETS=5
MAX_TWEETS_PER_SESSION=5
TWITTER_FEED_TYPE=following
PERPLEXITY_WAIT_TIME=60
PERPLEXITY_RESPONSES_PER_CHAT=2
HEADLESS=false
DEBUG_MODE=false
```

### Step 3: Important Before Running

**⚠️ CLOSE ALL CHROME WINDOWS** before running the script!
The script needs exclusive access to your Chrome profile.

### Step 4: Run the Script

```bash
python twitter_agent_selenium.py
```

The script will now use your logged-in Chrome profile, so you won't need to log in again!

---

## Solution 2: Use Undetected ChromeDriver (Alternative)

If Solution 1 doesn't work, use the enhanced version with `undetected-chromedriver`.

### Step 1: Install the Package

```bash
pip install undetected-chromedriver
```

### Step 2: Use the New Script

Use `twitter_agent_undetected.py` instead:

```bash
python twitter_agent_undetected.py
```

This version uses a special ChromeDriver that's much harder for X.com to detect.

---

## Troubleshooting

### "Chrome is already running" error
- Close ALL Chrome windows
- Check Activity Monitor/Task Manager for Chrome processes
- Kill any remaining Chrome processes

### "Cannot find Chrome binary" error
- Make sure Chrome is installed
- Verify the Chrome user data directory path is correct

### Still getting login errors?
1. Try logging into X.com manually in a regular Chrome window first
2. Close Chrome completely
3. Run the script immediately after
4. If using Chrome profile, make sure you're logged into X.com in that profile

### Need to use a different Chrome profile?
Change `CHROME_PROFILE_DIRECTORY` in `.env`:
- `Default` - your main profile
- `Profile 1`, `Profile 2`, etc. - other profiles
- To see available profiles, look in your Chrome User Data directory

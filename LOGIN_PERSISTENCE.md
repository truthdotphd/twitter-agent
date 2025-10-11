# Login Persistence Guide

## Overview
The Twitter Agent now uses a **dedicated Chrome profile** to save your login sessions. This means you only need to log in once, and your credentials will be remembered for future runs.

## How It Works

### Profile Location
The agent uses a persistent Chrome profile stored at:
```
~/.chrome_automation_profile/TwitterAgent/
```

This profile stores:
- Login cookies and sessions
- Browser preferences
- Extension data
- Form autofill data

### First Run
On your first run, you'll need to:
1. ✅ Log into X.com (Twitter) manually
2. ✅ Log into your chosen AI service (Perplexity/ChatGPT/Gemini) manually

The agent will show:
```
ℹ️  First time: You'll need to log into X.com and AI service manually
ℹ️  After that: Logins will be remembered!
```

### Subsequent Runs
On subsequent runs, the agent will automatically:
- ✅ Use saved X.com login
- ✅ Use saved AI service login
- ✅ No manual login required!

You'll see:
```
✅ Found existing profile - logins should be remembered
```

## Configuration

### Custom Profile Name
You can use a different profile name via environment variable:
```bash
# In your .env file
CHROME_PROFILE_DIRECTORY=MyTwitterBot
```

This creates a profile at: `~/.chrome_automation_profile/MyTwitterBot/`

### Multiple Profiles
You can run multiple agents with different accounts by using different profile names:

**Agent 1:**
```bash
CHROME_PROFILE_DIRECTORY=Account1
```

**Agent 2:**
```bash
CHROME_PROFILE_DIRECTORY=Account2
```

## Troubleshooting

### Login Not Persisting
If logins are not being remembered:

1. **Check profile exists:**
   ```bash
   ls -la ~/.chrome_automation_profile/TwitterAgent/
   ```
   
2. **Look for Preferences file:**
   ```bash
   ls -la ~/.chrome_automation_profile/TwitterAgent/Preferences
   ```
   If missing, the profile wasn't saved properly.

3. **Clear and recreate profile:**
   ```bash
   rm -rf ~/.chrome_automation_profile/TwitterAgent/
   ```
   Then run the agent again and log in.

### Profile Corruption
If the profile becomes corrupted:

```bash
# Delete the corrupted profile
rm -rf ~/.chrome_automation_profile/

# Run the agent - it will create a fresh profile
python3 twitter_agent_selenium.py
```

### Still Asking for Login
If the agent still asks for login after first run:

1. **Ensure you closed the agent properly** (Ctrl+C, then Enter to close browser)
2. **Check Chrome is not running** in the background:
   ```bash
   ps aux | grep Chrome
   ```
3. **Try running without headless mode** to see what's happening:
   ```bash
   # In .env file
   HEADLESS=false
   ```

## Security Notes

### Profile Storage
The profile stores sensitive data including:
- Login cookies
- Session tokens
- Saved passwords (if enabled)

**Protect your profile directory:**
```bash
chmod 700 ~/.chrome_automation_profile/
```

### Sharing Profiles
⚠️ **Never share your profile directory** - it contains your login credentials!

### Production Use
For production use, consider:
- Using separate accounts for automation
- Implementing 2FA with app passwords where possible
- Regularly rotating credentials
- Monitoring for suspicious activity

## Benefits

✅ **Time Saving**: No manual login each time  
✅ **Automation**: Truly hands-off operation  
✅ **Multiple Accounts**: Run different profiles simultaneously  
✅ **Reliability**: Consistent login state across sessions  

## Profile Contents

What's stored in the profile:
```
~/.chrome_automation_profile/TwitterAgent/
├── Cookies                  # Login cookies
├── Preferences              # Browser settings
├── Local Storage/           # Local storage data
├── Session Storage/         # Session data
└── ...                      # Other Chrome data
```

## Clean Shutdown

To ensure profile is saved properly:

1. **Stop with Ctrl+C** (KeyboardInterrupt)
2. **Wait for save message**: `💾 Saving processed tweets...`
3. **Press Enter** when prompted: `Press Enter to close browser...`
4. **Chrome will close cleanly**, saving all session data

## Tips

### First Time Setup
- ✅ Use a stable internet connection
- ✅ Complete all login flows (including 2FA if required)
- ✅ Let Chrome fully save the session (wait for disk activity to stop)
- ✅ Close the agent cleanly (Ctrl+C, then Enter)

### Best Practices
- 🔒 Keep profile directory secure
- 📁 Backup profile before major updates
- 🔄 Recreate profile if issues persist
- 📊 Monitor disk space (profiles can grow to 100MB+)

---

**Need help?** Check the main README or open an issue on GitHub.

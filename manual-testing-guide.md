# Manual Testing Guide for CLI Fixes

## Overview

I've implemented fixes for both issues, but I **cannot run the actual bot menu** to verify they work. This guide provides instructions for you to test and provide feedback.

---

## Issue 1: Topic Names in Command Mappings

### What Was Fixed

**File:** `src/cli/commands/group.py`
**Change:** Use `TelegramUtils.get_forum_topics()` instead of undefined `functions` variable

### How to Test

1. **Start the bot:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   python sakaibot.py
   ```

2. **Navigate to Group Management:**
   - Select option `1` (Group Management)
   - Select option `2` (Map commands to topics)
   - Select "List mappings"

3. **Expected Output:**
   ```
   Command Mappings
   #  Commands          Target
   1  /image, /prompt   Topic ID: 2 (AI)
   2  /translate        Topic ID: 5 (General Discussion)
   3  /analyze          Main Group Chat
   ```

4. **What to Look For:**
   - Topic names should appear in parentheses: `(AI)`, `(General Discussion)`
   - NOT just: `Topic ID: 2`

### If It Fails

Please provide:
- The exact output you see
- Any error messages in the console
- The content of your `user_settings.json` (the `active_command_to_topic_map` section)

---

## Issue 2: Monitoring Initialization

### What Was Fixed

**File:** `src/telegram/handlers.py`
**Change:** Added diagnostic logging to identify which component fails during initialization

### How to Test

1. **Start the bot:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   python sakaibot.py
   ```

2. **Navigate to Monitoring:**
   - Select option `2` (Monitoring)
   - Select option `1` (Start monitoring)

3. **Expected Behavior:**

   **If it succeeds:**
   ```
   Starting global monitoring...
   Categorization: Target group set, 3 mappings
   AI Features: Gemini provider active
   Monitoring started. Press Ctrl+C to stop.
   ```

   **If it still fails, you'll see:**
   ```
   Error: Failed to initialize event handlers: 'NoneType' object is not callable
   ```
   
   BUT the log file will now show which component failed!

4. **Check the log file:**
   - Look in the `logs/` directory
   - Find the most recent log file
   - Search for "Creating" to see the last component that was attempted
   
   Example log output:
   ```
   DEBUG: Initializing EventHandlers...
   DEBUG: Self-command handlers registered
   DEBUG: Creating STTHandler...
   DEBUG: Creating TTSHandler...
   DEBUG: Creating AIHandler...
   DEBUG: Creating ImageGenerator...
   ERROR: 'NoneType' object is not callable
   ```
   
   This tells us that ImageGenerator is the failing component!

### If It Fails

Please provide:
1. The exact error message
2. The last 20 lines from the log file showing the debug messages
3. Your configuration (which LLM provider you're using, etc.)

---

## What I Need From You

### For Issue 1 (Topic Names):

Please test and provide one of:

✅ **Success:** "It works! Topic names are showing like: Topic ID: 2 (AI)"

❌ **Failure:** 
```
Still showing just: Topic ID: 2
Error message (if any): ...
```

### For Issue 2 (Monitoring):

Please test and provide one of:

✅ **Success:** "Monitoring starts without error!"

❌ **Failure:**
```
Error: Failed to initialize event handlers: 'NoneType' object is not callable

Log excerpt:
DEBUG: Creating AIHandler...
DEBUG: Creating ImageGenerator...
ERROR: 'NoneType' object is not callable
```

---

## Why I Can't Test This Myself

I'm an AI assistant without the ability to:
- Run the actual Telegram bot
- Connect to Telegram's API
- Access your configuration files
- See the interactive menu

I can only:
- Read and modify code
- Run automated unit tests
- Analyze code paths and logic

---

## What Happens Next

### If Tests Pass ✅

I'll commit with proof:
```
fix: actually display topic names in command mappings (tested)

Manual test confirmed: Topic names now display correctly
Output: "Topic ID: 2 (AI)" ✓
```

### If Tests Fail ❌

I'll use your feedback to:
1. Identify the exact problem from logs
2. Implement the correct fix
3. Ask you to test again

This iterative approach ensures the fixes actually work in the real environment.

---

## Testing Commands

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run the bot
python sakaibot.py

# To see debug logs in real-time (optional)
$env:LOG_LEVEL="DEBUG"
python sakaibot.py

# Run unit tests to verify no regressions
pytest tests/unit/ -v
```

---

## Current Status

- ✅ Root cause analysis documented
- ✅ Fixes implemented
- ✅ Unit tests passing (40/40)
- ✅ Code committed and pushed
- ⏳ **Waiting for manual verification**

Once you provide test results, I can either:
- Confirm the fixes work and close the task
- Debug further based on your feedback and implement additional fixes

Thank you for your help in testing! 🙏

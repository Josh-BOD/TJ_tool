# Configuration Guide 🔧

This guide will walk you through setting up the TrafficJunky Automation Tool step-by-step.

## Prerequisites Checklist

Before starting, make sure you have:

- [ ] **Python 3.9+** installed
  ```bash
  python3 --version  # Should show 3.9 or higher
  ```

- [ ] **TrafficJunky Account** with advertiser access
- [ ] **Campaign ID(s)** you want to upload to
- [ ] **CSV file(s)** with ad specifications
- [ ] **Terminal/Command Line** access

---

## Step-by-Step Setup

### 1️⃣ Navigate to Project Directory

```bash
cd /Users/joshb/Desktop/Dev/TJ_tool
```

### 2️⃣ Create Virtual Environment

A virtual environment keeps project dependencies isolated.

```bash
# Create virtual environment
python3 -m venv venv

# Activate it (macOS/Linux)
source venv/bin/activate

# You should see (venv) in your terminal prompt
```

**Troubleshooting**:
- If `python3` command not found, try `python` instead
- On Windows, use: `venv\Scripts\activate`

### 3️⃣ Install Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install all required packages
pip install -r requirements.txt

# This will install:
# - playwright (browser automation)
# - pandas (CSV processing)
# - python-dotenv (environment variables)
# - colorama (colored output)
# - and more...
```

### 4️⃣ Install Playwright Browsers

Playwright needs to download browser binaries.

```bash
playwright install chromium

# Optional: Install all browsers
# playwright install
```

### 5️⃣ Create Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Now edit the `.env` file with your actual credentials:

```bash
# Use your preferred text editor
nano .env
# or
open .env  # Opens in default editor on macOS
# or
code .env  # If you have VS Code
```

### 6️⃣ Configure `.env` File

Update these required values:

```env
# ====================================
# TrafficJunky Credentials (REQUIRED)
# ====================================
TJ_USERNAME=your_actual_username_here
TJ_PASSWORD=your_actual_password_here

# ====================================
# Campaign Configuration (REQUIRED)
# ====================================
# Single campaign:
CAMPAIGN_IDS=1013017411

# Multiple campaigns (comma-separated):
# CAMPAIGN_IDS=1013017411,1013017412,1013017413

# ====================================
# Important Settings
# ====================================
# Keep these for first-time setup:
DRY_RUN=True          # Test mode (won't actually upload)
HEADLESS_MODE=False   # Show browser window
TAKE_SCREENSHOTS=True # Save screenshots for debugging
LOG_LEVEL=INFO        # Logging detail level
```

**Security Note**: NEVER commit the `.env` file to git! It's already in `.gitignore`.

---

## 📋 Validation Checklist

Before running the tool, verify:

### Configuration
- [ ] `.env` file exists and contains your credentials
- [ ] `TJ_USERNAME` is set
- [ ] `TJ_PASSWORD` is set
- [ ] `CAMPAIGN_IDS` contains at least one valid campaign ID
- [ ] `DRY_RUN=True` for first test

### Files & Folders
- [ ] Virtual environment created (`venv` folder exists)
- [ ] Dependencies installed (`pip list` shows playwright, pandas, etc.)
- [ ] CSV file exists in `data/input/` folder
- [ ] CSV follows the correct format (see Gay.csv example)

### Test Login
- [ ] Can log into TrafficJunky manually with these credentials
- [ ] Have access to the campaign ID(s) in `.env`
- [ ] Campaign has "Mass Create with CSV" option

---

## 🧪 First Test Run

Once everything is configured, test the tool:

```bash
# Make sure virtual environment is activated
# You should see (venv) in your prompt

# Run a dry run (won't actually upload)
python main.py

# What you should see:
# - Tool banner
# - Configuration loaded
# - Browser opens
# - Logs into TrafficJunky
# - Navigates to campaign
# - Simulates upload (but doesn't actually upload)
# - Closes browser
# - Shows summary
```

**Expected Output**:
```
╔══════════════════════════════════════════════════════════════╗
║          TrafficJunky Automation Tool v1.0.0                ║
╚══════════════════════════════════════════════════════════════╝

✓ Configuration loaded
✓ Logging into TrafficJunky...
✓ Login successful
✓ Navigating to campaign 1013017411...
ℹ DRY RUN MODE: Would upload CSV but skipping...
✓ Process completed successfully

Summary:
- Campaigns processed: 1
- Mode: Dry Run
- Duration: 1m 23s
```

---

## ⚙️ Configuration Options Explained

### Browser Settings

```env
# HEADLESS_MODE
# True  = Browser runs invisibly (faster, for production)
# False = Browser window visible (debugging, learning)
HEADLESS_MODE=False

# BROWSER_TYPE
# chromium = Default, most compatible
# firefox  = Alternative
# webkit   = Safari engine
BROWSER_TYPE=chromium

# TIMEOUT (milliseconds)
# How long to wait for pages to load
TIMEOUT=30000  # 30 seconds

# SLOW_MO (milliseconds)
# Adds delay between actions (makes it easier to watch)
SLOW_MO=500  # 0.5 seconds
```

### Automation Settings

```env
# DRY_RUN
# True  = Simulate upload (safe for testing)
# False = Actually upload (use after testing)
DRY_RUN=True

# TAKE_SCREENSHOTS
# True  = Save screenshot at each step
# False = No screenshots (faster)
TAKE_SCREENSHOTS=True

# MAX_RETRIES
# How many times to retry on failure
MAX_RETRIES=3

# RETRY_DELAY (seconds)
# Wait time between retries
RETRY_DELAY=5
```

### Logging Settings

```env
# LOG_LEVEL
# DEBUG    = Very detailed (for troubleshooting)
# INFO     = Normal detail (recommended)
# WARNING  = Only warnings and errors
# ERROR    = Only errors
LOG_LEVEL=INFO

# LOG_TO_FILE / LOG_TO_CONSOLE
# Where to output logs
LOG_TO_FILE=True
LOG_TO_CONSOLE=True
```

---

## 🔍 Troubleshooting Setup

### Virtual Environment Issues

**Problem**: `venv` command not found
```bash
# Try this instead:
python3 -m pip install virtualenv
python3 -m virtualenv venv
```

**Problem**: Can't activate virtual environment
```bash
# macOS/Linux
source venv/bin/activate

# Windows (Command Prompt)
venv\Scripts\activate.bat

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

### Installation Issues

**Problem**: `pip install` fails
```bash
# Update pip first
pip install --upgrade pip

# Try installing packages one by one
pip install playwright
pip install pandas
pip install python-dotenv
```

**Problem**: Playwright install fails
```bash
# Use full path
python -m playwright install chromium

# Or with force flag
playwright install --force chromium
```

### Configuration Issues

**Problem**: "TJ_USERNAME not set" error
- Check `.env` file exists (not `.env.example`)
- No quotes needed: `TJ_USERNAME=myuser` ✅
- Not: `TJ_USERNAME="myuser"` ❌

**Problem**: Can't find `.env` file
- File must be in project root: `/Users/joshb/Desktop/Dev/TJ_tool/.env`
- File is hidden (starts with dot)
- To see hidden files: `ls -la`

---

## 🎯 Next Steps

After successful setup:

1. ✅ **Dry run completed** - Browser opened, logged in, navigated correctly
2. ⬜ **Review logs** - Check `logs/` folder for detailed execution log
3. ⬜ **Review screenshots** - Check `screenshots/` folder to see each step
4. ⬜ **Test with small CSV** - Use CSV with just 2-3 ads first
5. ⬜ **Go live** - Set `DRY_RUN=False` for actual upload

---

## 📚 Additional Resources

- [Plan.md](Plan.md) - Detailed project plan
- [../README.md](../README.md) - User guide
- [Playwright Python Docs](https://playwright.dev/python/)
- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)

---

## 🆘 Getting Help

If you encounter issues:

1. **Check logs**: `logs/upload_log_[timestamp].txt`
2. **Check screenshots**: `screenshots/` folder
3. **Enable DEBUG logging**: Set `LOG_LEVEL=DEBUG` in `.env`
4. **Run dry run**: Always test with `DRY_RUN=True` first

---

**Setup Complete?** ✅

Once you've completed all steps above, you're ready to run the tool!

Proceed to testing as outlined in [Plan.md](Plan.md).


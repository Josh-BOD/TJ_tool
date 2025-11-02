# TrafficJunky Automation Tool - Project Plan

## 📋 Project Overview

**Goal**: Automate the bulk upload of ad creatives to TrafficJunky campaigns using browser automation, since the TrafficJunky API does not support creative uploads.

**Problem**: TrafficJunky API only supports:
- ✅ Viewing ads/campaigns
- ✅ Updating existing ads (PATCH)
- ✅ Pausing/activating ads
- ❌ **NO** POST endpoint for creating/uploading new ads

**Solution**: Build a Python-based browser automation tool using Playwright to:
1. Log into TrafficJunky advertiser platform
2. Navigate to specific campaigns
3. Use the "Mass Create with CSV" feature
4. Upload creatives in bulk
5. Log results and handle errors

---

## 🎯 User Workflow (Manual Process to Automate)

### Current Manual Steps:
1. Navigate to campaign overview: `https://advertiser.trafficjunky.com/campaign/overview/{CAMPAIGN_ID}`
2. Click **"Edit"** button
3. Navigate to Ad Settings: `https://advertiser.trafficjunky.com/campaign/{CAMPAIGN_ID}/ad-settings#section_adSpecs`
4. Select **"Mass Create with CSV"** option
5. Upload CSV file with ad specifications
6. Confirm upload and wait for processing

### Our Automation Will:
- Read campaign IDs from configuration
- Automatically navigate through these steps
- Upload the CSV programmatically
- Handle multiple campaigns sequentially
- Log all actions and results

---

## 🛠 Technology Stack

| Component | Technology | Why? |
|-----------|-----------|------|
| **Language** | Python 3.9+ | Easy to learn, great automation libraries |
| **Browser Automation** | Playwright | Modern, reliable, multi-browser, handles file uploads |
| **Data Handling** | Pandas | CSV processing made simple |
| **Configuration** | python-dotenv | Secure credential storage |
| **Logging** | Python logging | Track all actions and errors |
| **File Management** | pathlib, os | Clean file operations |

---

## 📁 Project Structure

```
TJ_tool/
├── .env                          # Credentials (NEVER commit)
├── .gitignore                   # Ignore sensitive files
├── requirements.txt             # Python dependencies
├── README.md                    # User documentation
│
├── Setup/
│   ├── Plan.md                  # This file
│   └── Configuration.md         # Setup instructions (to be created)
│
├── config/
│   ├── __init__.py
│   └── config.py                # Load settings from .env
│
├── data/
│   ├── input/                   # Input CSV files
│   │   ├── Gay.csv             # Example file provided
│   │   └── [other_campaigns].csv
│   ├── output/                  # Results/reports
│   │   └── upload_results.csv
│   └── creatives/              # Local creative files (if downloaded from Drive)
│       ├── images/
│       ├── videos/
│       └── banners/
│
├── logs/
│   └── upload_log_{timestamp}.txt
│
├── src/
│   ├── __init__.py
│   ├── auth.py                  # Handle login/authentication
│   ├── navigator.py             # Navigate to campaign pages
│   ├── uploader.py              # Main CSV upload logic
│   ├── validator.py             # Validate CSV format
│   └── utils.py                 # Helper functions
│
├── tests/                       # Unit tests (optional but recommended)
│   └── test_validator.py
│
└── main.py                      # Entry point with CLI
```

---

## 📊 CSV Format Understanding

### Current CSV Structure (from Gay.csv):

| Column | Description | Example |
|--------|-------------|---------|
| `Ad Name` | Name of the ad creative | `TALKINGAD_GAY` |
| `Target URL` | Landing page URL with tracking params | `https://clk.ourdream.ai/...` |
| `Creative ID` | TrafficJunky creative ID | `1032473171` |
| `Custom CTA Text` | Call-to-action button text | `Create Your Cum Slut` |
| `Custom CTA URL` | CTA destination URL | Same as Target URL |
| `Banner CTA Creative ID` | (Optional) Banner CTA creative ID | Empty in examples |
| `Banner CTA Title` | (Optional) Banner title | Empty in examples |
| `Banner CTA Subtitle` | (Optional) Banner subtitle | Empty in examples |
| `Banner CTA URL` | (Optional) Banner URL | Empty in examples |
| `Tracking Pixel` | (Optional) Tracking pixel URL | Empty in examples |

### Key Observations:
- ✅ **Creative IDs already exist** - These are pre-uploaded creatives in TJ system
- ✅ CSV is used to **associate creatives with campaigns**
- ✅ All tracking parameters are embedded in URLs
- ⚠️ Creative files are NOT in the CSV - they're referenced by ID

---

## 🔐 Security & Configuration

### Environment Variables (.env file):

```env
# TrafficJunky Credentials
TJ_USERNAME=your_username_here
TJ_PASSWORD=your_password_here

# Campaign Configuration
CAMPAIGN_IDS=1013017411,1013017412,1013017413

# File Paths
CSV_INPUT_DIR=./data/input
CSV_OUTPUT_DIR=./data/output
LOG_DIR=./logs

# Browser Settings
HEADLESS_MODE=False  # Set to True for production, False for debugging
BROWSER_TYPE=chromium  # chromium, firefox, or webkit
TIMEOUT=30000  # Timeout in milliseconds

# Dry Run Mode
DRY_RUN=True  # Set to False to actually upload
```

---

## 🚀 Workflow Steps (Detailed)

### Phase 1: Setup & Initialization
1. **Load environment variables** from `.env`
2. **Validate CSV file** exists and has correct format
3. **Initialize Playwright** browser instance
4. **Configure logging** with timestamp

### Phase 2: Authentication
1. Navigate to login page: `https://advertiser.trafficjunky.com/campaigns`
2. Handle cookie consent popup (if appears)
3. Enter username and password
4. Handle reCAPTCHA (may require manual intervention)
5. Verify successful login (check for specific element)
6. Save session/cookies for reuse

### Phase 3: Campaign Upload (Per Campaign)
For each campaign ID in configuration:

1. **Navigate to campaign overview**
   - URL: `https://advertiser.trafficjunky.com/campaign/overview/{CAMPAIGN_ID}`
   - Wait for page load
   - Take screenshot (for debugging)

2. **Click Edit button**
   - Locate "Edit" button
   - Click and wait for navigation

3. **Navigate to Ad Settings**
   - URL: `https://advertiser.trafficjunky.com/campaign/{CAMPAIGN_ID}/ad-settings#section_adSpecs`
   - Wait for section to load
   - Scroll to "Mass Create with CSV" section

4. **Upload CSV**
   - Locate "Mass Create with CSV" button/input
   - Select CSV file from `data/input/` folder
   - Upload file
   - Wait for upload confirmation

5. **Verify Upload**
   - Check for success message
   - Log result
   - Take screenshot
   - Wait for processing to complete

6. **Handle Errors**
   - Capture any error messages
   - Log detailed error info
   - Take error screenshot
   - Continue to next campaign or retry

### Phase 4: Cleanup & Reporting
1. Close browser session
2. Generate summary report:
   - Total campaigns processed
   - Successful uploads
   - Failed uploads with reasons
   - Total ads uploaded
3. Save report to `data/output/upload_results_{timestamp}.csv`
4. Display summary in console

---

## 🧪 Dry Run Mode

When `DRY_RUN=True`:
- ✅ Browser will open (visible)
- ✅ Login will execute
- ✅ Navigate through all pages
- ✅ Locate upload elements
- ✅ Take screenshots
- ❌ **Will NOT actually upload CSV**
- ✅ Log what would have been uploaded
- ✅ Allow manual inspection

**Benefits**:
- Test authentication
- Verify page navigation
- Identify element selectors
- Debug issues without affecting production
- Learn the UI flow

---

## 📝 Command Line Interface (CLI)

### Basic Usage:
```bash
# Activate virtual environment
source venv/bin/activate

# Run with default settings (dry run)
python main.py

# Run with specific campaign
python main.py --campaign 1013017411

# Run with specific CSV
python main.py --csv ./data/input/Gay.csv --campaign 1013017411

# Disable dry run (LIVE MODE)
python main.py --live --campaign 1013017411

# Run in headless mode
python main.py --headless
```

### Advanced Options:
```bash
# Multiple campaigns
python main.py --campaigns 1013017411,1013017412,1013017413

# Custom log file
python main.py --log-file ./logs/custom_upload.log

# Verbose mode
python main.py --verbose

# Skip authentication (reuse session)
python main.py --skip-auth
```

---

## 🎨 Feature Roadmap

### Phase 1: MVP (Minimum Viable Product)
- ✅ Browser automation setup
- ✅ Login functionality
- ✅ Navigate to campaign ad settings
- ✅ Upload single CSV
- ✅ Basic logging
- ✅ Dry run mode

### Phase 2: Enhancement
- ⬜ Multiple campaign support
- ⬜ Error recovery and retry logic
- ⬜ Session persistence (avoid repeated logins)
- ⬜ Progress bar for multiple uploads
- ⬜ Email notifications on completion

### Phase 3: Advanced (Future)
- ⬜ Google Drive integration (download CSVs automatically)
- ⬜ Schedule uploads (cron job)
- ⬜ Web dashboard to monitor uploads
- ⬜ Parallel campaign uploads (if safe)
- ⬜ CSV validation against TJ requirements
- ⬜ Automatic creative upload to TJ first (if needed)

---

## ⚠️ Important Considerations

### Creative Management
**QUESTION**: The CSV references Creative IDs (like `1032473171`), which suggests:
- Creatives are **already uploaded** to TrafficJunky
- CSV just **associates** creatives with campaigns
- We're NOT uploading creative **files** (images/videos)

**If creatives need to be uploaded first**:
- Need to understand TJ's creative upload process
- May need to automate creative upload separately
- Then generate CSV with returned Creative IDs

### Google Drive Integration
**Current Challenge**: Creative files are stored in Google Drive, not locally.

**Options**:
1. **Manual download** (simplest): Download creatives to `data/creatives/` before running
2. **Automate download**: Use Google Drive API to download creatives
3. **Direct upload**: Upload from Google Drive to TJ (complex)

**Recommendation**: Start with manual download for MVP, automate later.

### Rate Limiting & Detection
- TrafficJunky may have bot detection
- Solution: Add random delays between actions
- Use realistic mouse movements
- Rotate user agents if needed

### reCAPTCHA Handling
- If reCAPTCHA appears on login, automation may pause
- Options:
  - Manual intervention (pause and let user solve)
  - Use CAPTCHA solving service (costs money)
  - Save session cookies to avoid repeated CAPTCHAs

---

## 🛑 Questions to Resolve Before Implementation

### 1. Creative Upload Confusion
**Q**: Do the Creative IDs in the CSV refer to creatives that are **already uploaded** to TrafficJunky?
- [ ] Yes - Creatives are pre-uploaded, CSV just associates them
- [ ] No - We need to upload creative files first, then use returned IDs

**Impact**: This changes the entire workflow significantly.

### 2. Google Drive Access
**Q**: How should we handle creative files from Google Drive?
- [ ] Download manually to local folder before running
- [ ] Automate download using Google Drive API
- [ ] Not needed (creatives already in TJ)

### 3. Multiple Campaigns
**Q**: Will you upload the same CSV to multiple campaigns, or different CSVs per campaign?
- [ ] Same CSV for all campaigns
- [ ] Different CSV per campaign (need naming convention)

### 4. Campaign ID Source
**Q**: How will you provide campaign IDs?
- [ ] Hardcoded in .env file
- [ ] CSV with campaign list
- [ ] User input each time

### 5. Success Verification
**Q**: How do we know upload succeeded?
- Need to identify success message/element on page
- [ ] Can you provide a screenshot of successful upload?

---

## 📚 Next Steps

### Immediate Actions:
1. ✅ **Review this plan** - Ensure all details are correct
2. ⬜ **Answer questions above** - Critical for implementation
3. ⬜ **Create .env file** - Add your TJ credentials
4. ⬜ **Create virtual environment** - Isolate Python dependencies
5. ⬜ **Install dependencies** - Run `pip install -r requirements.txt`

### Before First Run:
6. ⬜ **Test login manually** - Ensure credentials work
7. ⬜ **Understand Creative IDs** - Clarify if creatives are pre-uploaded
8. ⬜ **Prepare test campaign** - Use a non-critical campaign for testing
9. ⬜ **Create test CSV** - Small CSV with 2-3 ads for initial test

### Development Sequence:
1. **Week 1**: Setup, authentication, basic navigation
2. **Week 2**: CSV upload automation, error handling
3. **Week 3**: Multiple campaigns, logging, dry-run testing
4. **Week 4**: Live testing, bug fixes, documentation

---

## 🎓 Learning Resources

Since you're new to development, here are helpful resources:

### Python Basics:
- [Python Official Tutorial](https://docs.python.org/3/tutorial/)
- [Real Python](https://realpython.com/)

### Playwright:
- [Playwright Python Docs](https://playwright.dev/python/)
- [Playwright Selectors Guide](https://playwright.dev/python/docs/selectors)

### Environment Setup:
- [Virtual Environments](https://docs.python.org/3/tutorial/venv.html)
- [python-dotenv Guide](https://pypi.org/project/python-dotenv/)

---

## 📞 Support & Questions

As we work through this project, we'll:
1. Take it **step-by-step** (no rush)
2. **Explain each part** in detail
3. **Debug together** when issues arise
4. **Document learnings** for future reference

---

## ✅ Sign-Off

This plan is ready for review. Once you've:
- [ ] Read through the entire plan
- [ ] Answered the questions in the "Questions to Resolve" section
- [ ] Confirmed the approach makes sense

We can proceed to:
1. Create the project structure
2. Set up the development environment
3. Start implementing Phase 1 (MVP)

**Ready to proceed?** Let me know if you have any questions or need clarification on any part of this plan! 🚀


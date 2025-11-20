# Campaign Creation Tool - Testing Guide

## 🧪 Testing Levels

### Level 1: Unit Tests (No Browser) ✅ DONE
### Level 2: Integration Tests (Dry-Run) ✅ DONE
### Level 3: UI Automation Tests (Browser Required) ← YOU ARE HERE
### Level 4: End-to-End Test (Real Campaign Creation)

---

## 📋 Level 1: Unit Tests (Already Passed)

```bash
python3 test_campaign_creation.py
```

**Results:**
- ✅ CSV Parsing
- ✅ Validation
- ✅ Campaign Naming
- ✅ Data Models
- ✅ Checkpoint Manager

---

## 📋 Level 2: Integration Tests (Already Passed)

```bash
python3 create_campaigns.py --input data/input/example_campaigns.csv --dry-run
```

**Results:**
- ✅ Parses 5 campaigns
- ✅ Validates all settings
- ✅ Shows 9 variants would be created
- ✅ Estimates ~41 minutes

---

## 📋 Level 3: UI Automation Tests (Browser Required)

These tests require a TrafficJunky session to verify the Playwright automation works.

### Step 1: Create Session File

**Option A: Use Existing Session**
If you already have `session.json` from the native uploader:
```bash
# Check if it exists
ls -l session.json

# It should be from your previous work with the native uploader
```

**Option B: Create New Session**
```bash
# If you don't have a session file, create one
python3 main.py --create-session

# This will open a browser where you:
# 1. Log in to TrafficJunky
# 2. Solve the reCAPTCHA
# 3. Session is saved to session.json
```

### Step 2: Create Test Campaign CSV

Create a minimal test file with just 1 campaign:

```bash
cat > data/input/test_single_campaign.csv << 'EOF'
group,keywords,keyword_matches,geo,csv_file,target_cpa,per_source_budget,max_bid,frequency_cap,max_daily_budget,gender,variants,enabled
TestCampaign,test keyword,broad,US,test_ads.csv,50,200,10,2,250,male,desktop,true
EOF
```

Create test ad CSV:
```bash
cat > data/input/test_ads.csv << 'EOF'
Ad Name,Target URL,Creative ID,Custom CTA Text,Custom CTA URL,Banner CTA Creative ID,Banner CTA Title,Banner CTA Subtitle,Banner CTA URL,Tracking Pixel
TEST_AD,https://example.com?sub11=CAMPAIGN_NAME,1032539101,Click Here,https://example.com?sub11=CAMPAIGN_NAME,,,,,
EOF
```

### Step 3: Run Dry-Run Test

```bash
python3 create_campaigns.py --input data/input/test_single_campaign.csv --dry-run
```

**Expected Output:**
```
✓ File parsed successfully
✓ No errors found
✓ No warnings

Campaign Set 1: TestCampaign
  Will create 1 campaign(s):
    1. US_EN_NATIVE_CPA_ALL_KEY-TestKeyword_DESK_M_JB
```

### Step 4: Test Browser Connection (No Campaign Creation)

Let's create a simple browser test script:

```bash
cat > test_browser_connection.py << 'EOF'
#!/usr/bin/env python3
"""Test browser connection and session."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from campaign_automation.creator import CampaignCreator

async def test_connection():
    session_file = Path("session.json")
    
    if not session_file.exists():
        print("✗ Session file not found: session.json")
        print("  Run: python3 main.py --create-session")
        return False
    
    print("Testing browser connection...")
    
    async with CampaignCreator(session_file, headless=False, slow_mo=1000) as creator:
        # Navigate to campaigns page
        await creator.page.goto("https://advertiser.trafficjunky.com/campaigns")
        await creator.page.wait_for_load_state("networkidle")
        
        # Check if logged in
        title = await creator.page.title()
        print(f"✓ Connected to TrafficJunky")
        print(f"  Page title: {title}")
        
        if "Login" in title or "Sign In" in title:
            print("✗ Not logged in - session may have expired")
            return False
        
        print("✓ Session is valid")
        return True

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1)
EOF

chmod +x test_browser_connection.py
python3 test_browser_connection.py
```

**Expected:**
- Browser opens (visible)
- Goes to TrafficJunky campaigns page
- Shows you're logged in
- Closes automatically

### Step 5: Test Campaign Filtering (Read-Only)

Test the campaign filter functionality without creating anything:

```bash
cat > test_campaign_filter.py << 'EOF'
#!/usr/bin/env python3
"""Test campaign filtering functionality."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from campaign_automation.creator import CampaignCreator

async def test_filter():
    session_file = Path("session.json")
    
    print("Testing campaign filter...")
    
    async with CampaignCreator(session_file, headless=False, slow_mo=1000) as creator:
        await creator.page.goto("https://advertiser.trafficjunky.com/campaigns")
        await creator.page.wait_for_load_state("networkidle")
        
        # Test filtering by template ID
        template_id = "1013076141"
        print(f"\nFiltering for campaign ID: {template_id}")
        
        await creator.page.fill('input[name="id"]', template_id)
        await creator.page.keyboard.press("Enter")
        await asyncio.sleep(2)
        
        # Check if filter worked
        campaign_rows = await creator.page.query_selector_all('tr[data-campaign-id]')
        print(f"✓ Found {len(campaign_rows)} matching campaign(s)")
        
        # Get campaign name
        name_elem = await creator.page.query_selector('.campaignName')
        if name_elem:
            name = await name_elem.text_content()
            print(f"  Campaign: {name}")
        
        print("\n✓ Filter test passed")
        
        # Wait to see the result
        await asyncio.sleep(3)
        
        return True

if __name__ == "__main__":
    result = asyncio.run(test_filter())
    sys.exit(0 if result else 1)
EOF

chmod +x test_campaign_filter.py
python3 test_campaign_filter.py
```

---

## 📋 Level 4: End-to-End Test (Real Campaign)

⚠️ **WARNING:** This will create an actual campaign in TrafficJunky!

### Safety First: Test Campaign Configuration

```bash
cat > data/input/test_real_campaign.csv << 'EOF'
group,keywords,keyword_matches,geo,csv_file,target_cpa,per_source_budget,max_bid,frequency_cap,max_daily_budget,gender,variants,enabled
TEST_DELETE_ME,test,broad,US,test_ads.csv,50,200,10,2,250,male,desktop,true
EOF
```

**Important Notes:**
- Group name: `TEST_DELETE_ME` (easy to identify and delete)
- Only 1 variant: `desktop` (quickest test)
- 1 keyword: `test` (simple)

### Dry-Run First
```bash
python3 create_campaigns.py --input data/input/test_real_campaign.csv --dry-run
```

**Expected:**
```
Campaign Set 1: TEST_DELETE_ME
  Will create 1 campaign(s):
    1. US_EN_NATIVE_CPA_ALL_KEY-Test_DESK_M_JB
```

### Create Test Campaign (Visible Browser)

```bash
# Run with visible browser so you can watch
python3 create_campaigns.py \
  --input data/input/test_real_campaign.csv \
  --no-headless \
  --slow-mo 1000 \
  --verbose
```

**What to Watch For:**
1. Browser opens
2. Goes to campaigns page
3. Filters for template campaign
4. Clicks "Clone"
5. Updates campaign name
6. Creates/selects group
7. Saves & continues
8. Configures geo
9. Configures keywords
10. Configures tracking & bids
11. Configures schedule & budget
12. Uploads ad CSV
13. Saves campaign

**Expected Duration:** ~5 minutes

### Verify Results

After it completes:
1. Check the terminal output for success/failure
2. Go to TrafficJunky campaigns page manually
3. Search for campaign: `US_EN_NATIVE_CPA_ALL_KEY-Test_DESK_M_JB`
4. Verify campaign exists and has correct settings
5. Verify ads were uploaded

### Clean Up Test Campaign

After verifying it worked:
1. Go to TrafficJunky
2. Find the test campaign
3. Delete it

---

## 📋 Comprehensive Test Checklist

### ✅ Pre-Testing
- [ ] `session.json` exists and is valid
- [ ] Test CSV files created
- [ ] Test ad CSV files created
- [ ] Template campaigns still exist (1013076141, 1013076221)

### ✅ Unit Tests
- [ ] `python3 test_campaign_creation.py` passes

### ✅ Integration Tests
- [ ] Dry-run with example CSV works
- [ ] Dry-run with test CSV works
- [ ] Validation catches errors correctly

### ✅ UI Automation Tests
- [ ] Browser connection test passes
- [ ] Campaign filter test passes
- [ ] Session is valid and working

### ✅ End-to-End Test (Optional)
- [ ] Single desktop campaign created successfully
- [ ] Campaign has correct name
- [ ] Campaign has correct settings
- [ ] Ads uploaded correctly
- [ ] Test campaign deleted

---

## 🐛 Common Issues & Fixes

### Issue: Session Expired
**Error:** `Not logged in` or stuck at login page

**Fix:**
```bash
python3 main.py --create-session
```

### Issue: Template Campaign Not Found
**Error:** `Campaign template not found`

**Fix:** Check if template IDs are still valid:
- Desktop: 1013076141
- iOS: 1013076221

### Issue: Playwright Not Installed
**Error:** `playwright not found`

**Fix:**
```bash
pip install playwright
python3 -m playwright install chromium
```

### Issue: CSV Validation Fails
**Error:** Various validation errors

**Fix:** Run dry-run to see specific errors:
```bash
python3 create_campaigns.py --input your_file.csv --dry-run
```

### Issue: Browser Timeout
**Error:** `Timeout waiting for element`

**Fix:** Increase slow-mo and watch what's happening:
```bash
python3 create_campaigns.py \
  --input your_file.csv \
  --no-headless \
  --slow-mo 2000
```

---

## 📊 What Each Test Validates

### Unit Tests
- ✅ CSV parsing logic
- ✅ Validation rules
- ✅ Campaign naming
- ✅ Data models
- ✅ Checkpoint serialization

### Integration Tests
- ✅ End-to-end CSV processing
- ✅ Multi-campaign handling
- ✅ Error detection
- ✅ Preview generation

### UI Automation Tests
- ✅ Browser connection
- ✅ Session persistence
- ✅ TrafficJunky navigation
- ✅ Element selectors

### End-to-End Tests
- ✅ Campaign creation workflow
- ✅ Settings configuration
- ✅ Ad upload integration
- ✅ Error handling
- ✅ Progress tracking

---

## 🎯 Recommended Testing Sequence

### For Initial Testing:
1. ✅ Run unit tests (`test_campaign_creation.py`) - **DONE**
2. ✅ Run dry-run tests - **DONE**
3. ▶️ **YOU ARE HERE:** Test browser connection
4. Test campaign filtering
5. Create 1 test campaign (desktop only)
6. Verify and delete test campaign
7. Create 1 test campaign with iOS
8. Create 1 test campaign with Android (after iOS)
9. Full batch test with 2-3 campaign sets

### For Production Use:
1. Always dry-run first
2. Start with small batch (2-3 campaigns)
3. Monitor progress
4. Verify results in TrafficJunky
5. Scale up to larger batches

---

## 💡 Testing Tips

1. **Always use `--no-headless` initially** - See what's happening
2. **Use `--slow-mo 1000` or higher** - Easier to follow
3. **Test with single desktop variant first** - Fastest feedback
4. **Keep test campaigns clearly labeled** - Easy to identify and delete
5. **Watch the terminal output** - Progress bars show exactly where it is
6. **Check TrafficJunky UI manually** - Verify campaigns are correct

---

## 🚀 Next Steps

Run these commands in order:

```bash
# 1. Verify unit tests still pass
python3 test_campaign_creation.py

# 2. Create test files (if not already done)
# [See Step 2 above]

# 3. Test browser connection
python3 test_browser_connection.py

# 4. Test campaign filtering
python3 test_campaign_filter.py

# 5. If all pass, create a real test campaign
python3 create_campaigns.py \
  --input data/input/test_real_campaign.csv \
  --no-headless \
  --slow-mo 1000 \
  --verbose
```

---

**Ready to start testing?** Let me know which level you want to test first!


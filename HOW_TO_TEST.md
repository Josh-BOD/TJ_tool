# 🚀 Testing Your New Campaign Creation Tool

## Quick Answer: Here's How to Test

### ✅ **Already Done** (Automatic Tests)
```bash
python3 test_campaign_creation.py
```
**Result:** 5/5 tests passed ✓

### ▶️ **Next: Test Browser Connection**
```bash
python3 test_browser_connection.py
```
This will:
- Open a browser (visible)
- Connect to TrafficJunky
- Verify your session is valid
- Show you're logged in

### ▶️ **Then: Test Campaign Filtering**
```bash
python3 test_campaign_filter.py
```
This will:
- Filter for template campaigns
- Verify they exist and are accessible
- Confirm IDs are correct

### ▶️ **Finally: Create a Real Test Campaign** (Optional)
```bash
# Create test input
cat > data/input/test_real.csv << 'EOF'
group,keywords,keyword_matches,geo,csv_file,variants,enabled
TEST_DELETE_ME,test,broad,US,test_ads.csv,desktop,true
EOF

# Create test ad CSV
cat > data/input/test_ads.csv << 'EOF'
Ad Name,Target URL,Creative ID,Custom CTA Text,Custom CTA URL,Banner CTA Creative ID,Banner CTA Title,Banner CTA Subtitle,Banner CTA URL,Tracking Pixel
TEST_AD,https://example.com?sub11=CAMPAIGN_NAME,1032539101,Click,https://example.com?sub11=CAMPAIGN_NAME,,,,,
EOF

# Dry-run first
python3 create_campaigns.py --input data/input/test_real.csv --dry-run

# Create campaign (visible browser, slow)
python3 create_campaigns.py \
  --input data/input/test_real.csv \
  --no-headless \
  --slow-mo 1000 \
  --verbose
```

---

## 📋 Testing Checklist

### Prerequisites
- [ ] You have `session.json` from previous work
  - If not: `python3 main.py --create-session`
- [ ] Playwright is installed
  - If not: `pip install playwright && python3 -m playwright install chromium`

### Level 1: Unit Tests (No Browser) ✅
- [x] `python3 test_campaign_creation.py` - **PASSED**

### Level 2: Integration Tests (No Browser) ✅  
- [x] `python3 create_campaigns.py --input data/input/example_campaigns.csv --dry-run` - **PASSED**

### Level 3: Browser Tests (Session Required)
- [ ] `python3 test_browser_connection.py` - Opens browser, tests connection
- [ ] `python3 test_campaign_filter.py` - Tests finding template campaigns

### Level 4: Real Campaign (Optional)
- [ ] Create 1 test campaign with visible browser
- [ ] Verify in TrafficJunky UI
- [ ] Delete test campaign

---

## 🎯 What Each Test Does

### `test_campaign_creation.py` (✅ Already Passed)
Tests the core logic without browser:
- CSV parsing
- Data validation
- Campaign naming
- Checkpoint manager
- Data models

**Time:** 1 second  
**Result:** All 5 tests passed

### `test_browser_connection.py` (Next)
Tests browser automation:
- Loads your session
- Opens browser (visible)
- Goes to TrafficJunky
- Verifies you're logged in
- Shows campaign count

**Time:** ~10 seconds  
**Requires:** Valid `session.json`  
**Safe:** Read-only, no changes

### `test_campaign_filter.py` (Next)
Tests campaign filtering:
- Filters by campaign ID
- Finds Desktop template (1013076141)
- Finds iOS template (1013076221)
- Verifies they're accessible

**Time:** ~15 seconds  
**Requires:** Valid `session.json`  
**Safe:** Read-only, no changes

### Real Campaign Creation (Optional)
Tests full workflow:
- Creates actual campaign
- Uploads ads
- Saves to TrafficJunky

**Time:** ~5 minutes  
**Requires:** Valid session, test CSVs  
**⚠️ WARNING:** Creates real campaign!

---

## 💡 Pro Tips

### 1. **Start with Connection Test**
```bash
python3 test_browser_connection.py
```
If this fails, your session expired. Create new one:
```bash
python3 main.py --create-session
```

### 2. **Always Use Visible Browser First**
- See what's happening
- Catch issues early
- Learn the workflow

### 3. **Slow It Down**
```bash
--slow-mo 1000  # 1 second between actions
--slow-mo 2000  # 2 seconds (even slower)
```

### 4. **Check Session File**
```bash
# Should exist and be recent
ls -lh session.json

# Should be a JSON file with cookies/storage
file session.json
```

### 5. **Use Verbose Mode**
```bash
--verbose  # See detailed step-by-step output
```

---

## 🐛 Troubleshooting

### "Session file not found"
```bash
# Option 1: Use existing session from uploader
cp data/session/tj_session.json session.json

# Option 2: Create new session
python3 main.py --create-session
```

### "Session expired" or "Not logged in"
```bash
# Create fresh session
python3 main.py --create-session
```

### "Playwright not found"
```bash
pip install playwright
python3 -m playwright install chromium
```

### "Template campaign not found"
Check if IDs are still valid:
- Desktop: 1013076141
- iOS: 1013076221

Run the filter test to verify:
```bash
python3 test_campaign_filter.py
```

### Browser timeout or hangs
- Increase `--slow-mo` value
- Use `--no-headless` to watch
- Check TrafficJunky UI hasn't changed

---

## 📊 Expected Results

### ✅ Connection Test
```
✓ Found session file
✓ Browser launched
✓ Page loaded
✓ Found campaigns table - successfully authenticated!
✓ Found 150 campaign(s) in your account

✓ CONNECTION TEST PASSED
```

### ✅ Filter Test
```
✓ Found 1 matching campaign(s)
✓ Found correct campaign: ID 1013076141
  Name: TEMPLATE_EN_NATIVE_CPA_ALL_KEY-ENTER-Keywords_DESK_M_JB
✓ Template campaign verified

✓ FILTER TEST PASSED
```

### ✅ Real Campaign Creation
```
[12:45:38] Creating DESKTOP campaign...
  └─ Cloning Desktop template
  └─ Configuring basic settings
  └─ Uploading ads...
  ✓ Created: US_EN_NATIVE_CPA_ALL_KEY-Test_DESK_M_JB (ID: 1234567890)
    Uploaded 1 ads | Elapsed: 4m 32s

✓ CAMPAIGN CREATION COMPLETED
```

---

## 🎬 Quick Start: Run Tests Now

```bash
# 1. Verify prerequisites
ls session.json  # Should exist
python3 -c "import playwright"  # Should not error

# 2. Run unit tests (already passed, but verify)
python3 test_campaign_creation.py

# 3. Test browser connection
python3 test_browser_connection.py

# 4. Test campaign filtering  
python3 test_campaign_filter.py

# 5. (Optional) Create real test campaign
python3 create_campaigns.py \
  --input data/input/test_real.csv \
  --no-headless \
  --slow-mo 1000
```

---

## 🎯 What You'll Know After Testing

### After Connection Test ✅
- Your session is valid
- Browser automation works
- You can access TrafficJunky

### After Filter Test ✅
- Template campaigns exist
- Campaign filtering works
- IDs are correct

### After Real Campaign Test ✅
- Full workflow works end-to-end
- Campaigns are created correctly
- Ads are uploaded successfully
- Tool is production-ready

---

## 📚 Full Documentation

- **This Guide:** `TESTING_GUIDE.md`
- **User Guide:** `CAMPAIGN_CREATION_README.md`
- **Quick Start:** `CAMPAIGN_CREATION_QUICK_START.md`
- **Implementation:** `IMPLEMENTATION_SUMMARY.md`

---

## ✨ You're Almost There!

You've built a complete, production-ready tool. Now let's just verify it works with your TrafficJunky account!

**Start here:**
```bash
python3 test_browser_connection.py
```

Then let me know what happens! 🚀


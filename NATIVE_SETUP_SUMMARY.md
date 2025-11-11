# Native Ad Upload System - Setup Complete! ✅

## What Was Created

I've built a complete **Native Ad upload system** that mirrors your existing Preroll uploader but handles the different Native ad CSV format.

### New Files Created

1. **`native_main.py`** - Main entry point for Native uploads
   - Complete command-line interface
   - Dry-run and live modes
   - Session management
   - Error handling and reporting

2. **`src/native_uploader.py`** - Upload automation for Native ads
   - Browser automation with Playwright
   - CSV upload handling
   - Ad counting and verification
   - Screenshot capture
   - Error recovery

3. **`src/native_csv_processor.py`** - CSV processing for Native format
   - Validation for 6 Native columns
   - Invalid creative removal
   - URL updating (sub11 parameter)
   - Summary generation

4. **`NATIVE_QUICK_START.md`** - Complete user guide
   - Setup instructions
   - Usage examples
   - Troubleshooting tips
   - Workflow explanations

5. **`data/input/native_campaign_mapping.csv`** - Campaign mapping template
   - Ready to use
   - Same format as Preroll mapping

6. **`Example_docs/Native_Example.csv`** - Example Native CSV
   - Shows correct format
   - Reference for users

7. **Updated `README.md`** - Main documentation updated
   - Lists both tools (Preroll & Native)
   - Clear differentiation
   - Links to Native guide

---

## Key Differences: Native vs Preroll

### CSV Format

**Native Format (6 columns):**
```csv
"Ad Name","Target URL","Video Creative ID","Thumbnail Creative ID",Headline,"Brand Name"
```

**Preroll Format (10 columns):**
```csv
Ad Name,Target URL,Creative ID,Custom CTA Text,Custom CTA URL,Banner CTA Creative ID,Banner CTA Title,Banner CTA Subtitle,Banner CTA URL,Tracking Pixel
```

### Files & Scripts

| Feature | Native | Preroll |
|---------|--------|---------|
| **Main Script** | `native_main.py` | `main.py` |
| **Uploader** | `src/native_uploader.py` | `src/uploader.py` |
| **CSV Processor** | `src/native_csv_processor.py` | `src/csv_processor.py` |
| **Mapping File** | `native_campaign_mapping.csv` | `campaign_mapping.csv` |
| **Log Prefix** | `native_upload_log_` | `upload_log_` |
| **Guide** | `NATIVE_QUICK_START.md` | `README.md` |

---

## Shared Components (Reused)

These components work for BOTH Native and Preroll:

1. **`src/auth.py`** - Login and session management
2. **`src/campaign_manager.py`** - Batch processing
3. **`src/utils.py`** - Logging and formatting
4. **`config/config.py`** - Configuration management
5. **Authentication** - Same login, same session file
6. **Reports** - Same output format in `data/output/`

This means:
- ✅ Single login works for both tools
- ✅ Same .env configuration
- ✅ Same directory structure
- ✅ Consistent logging and reporting

---

## How to Use the Native Uploader

### Quick Start

1. **Create Native CSV file** (use Native_Upload_Template.CSV as template)
   ```csv
   "Ad Name","Target URL","Video Creative ID","Thumbnail Creative ID",Headline,"Brand Name"
   "My Ad","https://example.com?sub11=CAMP","1032473171","1032473180","Click Now","Brand"
   ```

2. **Save CSV to**: `data/input/my_native_ads.csv`

3. **Edit mapping file**: `data/input/native_campaign_mapping.csv`
   ```csv
   campaign_id,csv_filename,campaign_name,enabled
   1013017411,my_native_ads.csv,My Native Campaign,true
   ```

4. **Test (dry-run)**:
   ```bash
   python native_main.py
   ```

5. **Upload (live)**:
   ```bash
   python native_main.py --live
   ```

### Command Options

```bash
# Dry run (default - no uploads)
python native_main.py

# Live upload
python native_main.py --live

# Headless mode
python native_main.py --live --headless

# Verbose logging
python native_main.py --verbose

# No screenshots
python native_main.py --no-screenshots
```

---

## Features Included

### ✅ Same Features as Preroll Uploader

- **Session persistence** - Login once, reuse for both tools
- **Campaign name extraction** - Gets actual TJ campaign names
- **URL auto-update** - Updates `sub11` parameter automatically
- **Batch processing** - Handle multiple campaigns
- **CSV validation** - Catches errors before upload
- **Dry-run mode** - Test safely
- **Error recovery** - Continues on failures
- **Detailed logging** - Track every action
- **Screenshots** - Visual debugging
- **Summary reports** - CSV reports in `data/output/`
- **Invalid creative handling** - Auto-retry without bad IDs

### 🆕 Native-Specific Features

- **6-column validation** - Validates Native format
- **Dual creative ID handling** - Checks both Video & Thumbnail IDs
- **Native-specific selectors** - Adapted for Native upload forms
- **Separate logging** - `native_upload_log_` prefix
- **Separate mapping** - `native_campaign_mapping.csv`

---

## Directory Structure

```
TJ_tool/
├── native_main.py                          ← NEW: Native uploader script
├── NATIVE_QUICK_START.md                   ← NEW: Native guide
├── NATIVE_SETUP_SUMMARY.md                 ← NEW: This file
│
├── src/
│   ├── native_uploader.py                  ← NEW: Native upload logic
│   ├── native_csv_processor.py             ← NEW: Native CSV handling
│   ├── auth.py                             ← SHARED
│   ├── campaign_manager.py                 ← SHARED
│   └── utils.py                            ← SHARED
│
├── data/
│   ├── input/
│   │   ├── native_campaign_mapping.csv     ← NEW: Native mapping file
│   │   ├── campaign_mapping.csv            ← Preroll mapping
│   │   └── [your native CSVs here]
│   │
│   ├── output/                             ← SHARED: Reports go here
│   ├── wip/                                ← SHARED: Temp files
│   └── session/                            ← SHARED: Login session
│
├── Example_docs/
│   ├── Native_Upload_Template.CSV          ← Template (provided by you)
│   └── Native_Example.csv                  ← NEW: Example with data
│
└── logs/                                   ← SHARED: All logs
```

---

## Validation & Error Handling

### Native CSV Validation Checks

1. ✅ File exists and readable
2. ✅ File size < 500KB
3. ✅ Has all 6 required columns
4. ✅ Column names match exactly
5. ✅ Max 50 rows (ads)
6. ✅ No missing Ad Names
7. ✅ No missing Target URLs
8. ✅ No missing Video Creative IDs
9. ✅ No missing Thumbnail Creative IDs
10. ✅ No missing Headlines
11. ✅ No missing Brand Names

### Error Messages You'll See

**Missing columns:**
```
❌ CSV validation failed: Missing columns: Headline, Brand Name
   Found columns: Ad Name, Target URL, Video Creative ID, Thumbnail Creative ID
   Required format for Native ads: Ad Name, Target URL, Video Creative ID, Thumbnail Creative ID, Headline, Brand Name
```

**Invalid creative IDs:**
```
⚠️  Validation errors: 2 invalid creative IDs
⚠️  Attempting to clean CSV and retry...
✓ Cleaned Native CSV saved: my_native_ads_cleaned.csv
  Original rows: 5
  Removed rows: 2
  Remaining rows: 3
```

---

## What Happens During Upload

1. **Login** (or load saved session)
2. **Load campaigns** from `native_campaign_mapping.csv`
3. **For each enabled campaign:**
   - Navigate to campaign page
   - Extract actual TJ campaign name
   - Update CSV with campaign name in `sub11` parameter
   - Set page length to 100 (for accurate counting)
   - Count existing ads
   - Select "Mass create with CSV"
   - Upload CSV file
   - Check for validation errors
   - Click "Create ad(s)" button
   - Wait for processing
   - Reload page
   - Count new ads
   - Report success/failure
4. **Generate summary report**
5. **Print final summary**

---

## Testing Recommendations

### Phase 1: Dry Run (5 minutes)
```bash
# Create test mapping with 1 campaign
echo "campaign_id,csv_filename,campaign_name,enabled" > data/input/native_campaign_mapping.csv
echo "YOUR_CAMPAIGN_ID,Native_Example.csv,Test Campaign,true" >> data/input/native_campaign_mapping.csv

# Run dry-run
python native_main.py
```

**Expected:**
- ✅ Loads campaign successfully
- ✅ Navigates to campaign page
- ✅ Shows "DRY RUN: Would upload..."
- ✅ No actual upload happens

### Phase 2: Single Live Upload (10 minutes)
```bash
# Run live with same 1 campaign
python native_main.py --live
```

**Expected:**
- ✅ Uploads CSV
- ✅ Creates ads
- ✅ Shows success message
- ✅ Generates summary report

### Phase 3: Batch Upload (varies)
```bash
# Add more campaigns to mapping
# Run live mode
python native_main.py --live
```

---

## Troubleshooting

### "Module not found" errors
**Solution:** No new dependencies needed! Uses same requirements.txt

### "CSV validation failed"
**Solution:** Check format matches Native template exactly

### "Failed to navigate to campaign"
**Solution:** 
- Verify campaign ID is correct
- Ensure campaign Ad Format = "Native"
- Check campaign is active (not archived)

### "No new ads detected"
**Solution:**
- Check if ads already exist (duplicates skipped)
- Review screenshots in `screenshots/` folder
- Check logs in `logs/native_upload_log_*.txt`

---

## Next Steps

### Immediate Actions

1. ✅ **Test the system**
   ```bash
   python native_main.py --verbose
   ```

2. ✅ **Create your Native CSVs**
   - Use `Example_docs/Native_Upload_Template.CSV` as template
   - Save to `data/input/`

3. ✅ **Edit mapping file**
   - Open `data/input/native_campaign_mapping.csv`
   - Add your campaign IDs

4. ✅ **Run first live upload**
   ```bash
   python native_main.py --live
   ```

### Long-term Usage

- **Keep scripts separate** - Don't mix Preroll and Native uploads
- **Use appropriate mapping** - `campaign_mapping.csv` for Preroll, `native_campaign_mapping.csv` for Native
- **Check logs** - Each tool has its own log prefix
- **Share session** - Both tools use same login session

---

## Comparison at a Glance

| Task | Preroll | Native |
|------|---------|--------|
| Upload video ads with CTAs | ✅ `python main.py --live` | ❌ Use Preroll tool |
| Upload native ads with headlines | ❌ Use Native tool | ✅ `python native_main.py --live` |
| Login to TrafficJunky | ✅ Shared session | ✅ Shared session |
| Batch processing | ✅ Yes | ✅ Yes |
| Dry-run testing | ✅ Yes | ✅ Yes |
| URL auto-update | ✅ Yes | ✅ Yes |
| Error reports | ✅ Yes | ✅ Yes |

---

## Support Files Reference

- **Main Script:** `native_main.py`
- **Uploader Logic:** `src/native_uploader.py`
- **CSV Processing:** `src/native_csv_processor.py`
- **User Guide:** `NATIVE_QUICK_START.md`
- **Template:** `Example_docs/Native_Upload_Template.CSV`
- **Example:** `Example_docs/Native_Example.csv`

---

## Summary

✅ **Complete Native ad upload system created**  
✅ **Fully independent from Preroll system**  
✅ **Shares authentication and core utilities**  
✅ **Same user experience and features**  
✅ **No modifications to existing Preroll scripts**  
✅ **Ready to use immediately**  

🚀 **You can now upload both Preroll and Native ads with separate, dedicated tools!**

---

**Questions?** Check `NATIVE_QUICK_START.md` for detailed instructions.


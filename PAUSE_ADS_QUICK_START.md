# Pause Ads V1 - Quick Start Guide

Mass pause specific Creative IDs across multiple TrafficJunky campaigns.

---

## 🎯 What This Tool Does

Pause specific ads (Creative IDs) across multiple campaigns automatically. Perfect for:
- Pausing seasonal promotions (Black Friday, holidays, etc.)
- Disabling underperforming creatives across all campaigns
- Bulk pausing specific ad sets

---

## 📋 Prerequisites

1. **Python 3.9+** with virtual environment activated
2. **Playwright** installed (`pip install playwright && playwright install chromium`)
3. **TrafficJunky credentials** set in `.env` file
4. **Two CSV files**:
   - Creative IDs to pause
   - Campaign IDs to search in

---

## 📂 CSV Format

### Creative IDs CSV

**Required Column:** `Creative ID`

Optional columns (for your reference): `Ad Name`, `Notes`

```csv
Creative ID,Ad Name,Notes
2212936201,Black Friday Ad 1,Holiday promo - pause after BF
2212936202,Black Friday Ad 2,Holiday promo - pause after BF
2212936203,Black Friday Ad 3,Holiday promo - pause after BF
```

**Example Template:** `Example_docs/Creative_IDs_Template.csv`

---

### Campaign IDs CSV

**Required Column:** `Campaign ID`

Optional columns (for your reference): `Campaign Name`, `Notes`

```csv
Campaign ID,Campaign Name,Notes
1012927602,Desktop-Stepmom-US,Main campaign
1012927603,iOS-Stepmom-US,Mobile iOS
1012927604,Android-Stepmom-US,Mobile Android
```

**Example Template:** `Example_docs/Campaign_IDs_Template.csv`

---

## 🚀 Usage

### Single Instance Mode (1 Browser)

#### Step 1: Prepare Your CSV Files

1. Create or download the Creative IDs CSV with the ads you want to pause
2. Create or download the Campaign IDs CSV with campaigns to search in
3. Save both files to `data/input/Ad_Pause/` (organized folder for pause operations)

#### Step 2: Dry Run (Recommended First!)

**Always test with dry run first** to see what would be paused without actually pausing:

```bash
python Pause_ads_V1.py \
    --creatives data/input/Ad_Pause/black_friday_creatives.csv \
    --campaigns data/input/Ad_Pause/all_campaigns.csv \
    --dry-run
```

This will:
- ✓ Show which Creative IDs would be paused in each campaign
- ✓ Show which Creative IDs are not found
- ✓ Generate a preview report
- ✗ **NOT** actually pause any ads

#### Step 3: Actual Pause

Once you've verified the dry run looks correct:

```bash
python Pause_ads_V1.py \
    --creatives data/input/Ad_Pause/black_friday_creatives.csv \
    --campaigns data/input/Ad_Pause/all_campaigns.csv
```

---

### ⚡ Parallel Mode (Multiple Browsers - FASTER!)

**Recommended for 100+ campaigns**

Parallel mode splits your Campaign IDs CSV among multiple workers, each running its own browser instance.

#### Run with 2 workers (safest)
```bash
python3 run_parallel_ad_pauser.py \
    --creatives data/input/Ad_Pause/creatives.csv \
    --campaigns data/input/Ad_Pause/campaigns.csv \
    --workers 2
```

#### Run with 3 workers (fastest)
```bash
python3 run_parallel_ad_pauser.py \
    --creatives data/input/Ad_Pause/creatives.csv \
    --campaigns data/input/Ad_Pause/campaigns.csv \
    --workers 3
```

#### Parallel Dry Run
```bash
python3 run_parallel_ad_pauser.py \
    --creatives data/input/Ad_Pause/creatives.csv \
    --campaigns data/input/Ad_Pause/campaigns.csv \
    --workers 2 \
    --dry-run
```

**How Parallel Mode Works:**
1. Splits your Campaign IDs CSV into N groups
2. Launches N browser instances (one per worker)
3. Each worker gets the same Creative IDs CSV
4. All workers run simultaneously
5. Each worker generates its own report

**Worker Logs:** `logs/ad_pauser_worker_1.log`, `logs/ad_pauser_worker_2.log`, etc.

**💡 Tip:** Use 2-3 workers for best results. More than 3 may cause browser conflicts.

---

### Step 4: Solve reCAPTCHA

1. Browser window will open automatically
2. Script will pre-fill your credentials
3. **Solve the reCAPTCHA** if prompted
4. Script will auto-click LOGIN and proceed

### Step 5: Watch the Process

The script will:
1. Navigate to each campaign's ad page
2. Set pagination to 100 ads per page
3. Go through all pages
4. Find and select Creative IDs from your CSV
5. Click the pause button
6. Move to next campaign

---

## 🎨 Advanced Options

### With Screenshots (for debugging)

Take screenshots of each step:

```bash
python Pause_ads_V1.py \
    --creatives data/input/Ad_Pause/creatives.csv \
    --campaigns data/input/Ad_Pause/campaigns.csv \
    --screenshots
```

Screenshots saved to: `data/screenshots/pause_{timestamp}/`

### Headless Mode (no browser window)

Run without visible browser:

```bash
python Pause_ads_V1.py \
    --creatives data/input/Ad_Pause/creatives.csv \
    --campaigns data/input/Ad_Pause/campaigns.csv \
    --headless
```

**Note:** Headless mode may have issues with reCAPTCHA. Recommended for testing only.

---

## 📊 Understanding the Report

After completion, a report is generated at: `data/reports/pause_report_{timestamp}.md`

### Report Sections:

#### 1. Summary
- Total campaigns processed
- Total ads paused
- Duration
- Success/partial/failed counts

#### 2. Campaign Results
For each campaign:
- Status (✓ success, ⚠ partial, ✗ failed)
- Time taken
- Pages processed
- List of paused Creative IDs
- List of Creative IDs not found in that campaign
- Any errors encountered

#### 3. Creative IDs Not Found Across All Campaigns
Lists Creative IDs that weren't found in any campaign (possible typos or deleted ads)

#### 4. Detailed Statistics
- Success rate
- Average time per ad
- Average time per campaign

---

## 🔍 Console Output Example

```
======================================================================
PAUSE ADS V1 - MASS AD PAUSING TOOL
======================================================================

Creative IDs CSV: data/input/black_friday_creatives.csv
Campaign IDs CSV: data/input/all_campaigns.csv

Parsing CSV files...
✓ Loaded 15 Creative IDs
✓ Loaded 3 Campaign IDs

======================================================================
BROWSER AUTHENTICATION
======================================================================

Logging in (solve reCAPTCHA manually if prompted)...
✓ Logged in successfully

======================================================================
PROCESSING CAMPAIGNS
======================================================================

[1/3] Processing: Desktop-Stepmom-US
Campaign ID: 1012927602
  ✓ SUCCESS - Paused 12/15 ads
  Time: 45.2s | Pages: 2

[2/3] Processing: iOS-Stepmom-US
Campaign ID: 1012927603
  ⚠ PARTIAL - Paused 8/10 ads
  Note: 5 Creative IDs not found in this campaign
  Time: 32.1s | Pages: 1

[3/3] Processing: Android-Stepmom-US
Campaign ID: 1012927604
  ✓ SUCCESS - Paused 10/15 ads
  Time: 38.7s | Pages: 2

======================================================================
GENERATING REPORT
======================================================================

✓ Report saved to: data/reports/pause_report_20251202_143022.md

======================================================================
PAUSE OPERATION SUMMARY
======================================================================

Campaigns Processed: 3
Ads Paused: 30
Duration: 2m 16s

✓ 2 campaign(s) - FULL SUCCESS
  • Desktop-Stepmom-US - 12 ads paused
  • Android-Stepmom-US - 10 ads paused

⚠ 1 campaign(s) - PARTIAL SUCCESS
  • iOS-Stepmom-US - 8/10 ads paused

⚠ 3 Creative ID(s) not found in any campaign:
  • 2212936299
  • 2212936300
  • 2212936301

======================================================================
```

---

## ⚠️ Troubleshooting

### "Creative ID column not found"
- Check your CSV has the **exact** column name: `Creative ID`
- No extra spaces, correct capitalization

### "Campaign ID column not found"
- Check your CSV has the **exact** column name: `Campaign ID`
- No extra spaces, correct capitalization

### "Login failed"
- Check credentials in `.env` file
- Make sure to solve reCAPTCHA within 3 minutes
- Check internet connection

### "No ads were paused"
Possible reasons:
- Creative IDs don't exist in those campaigns
- Creative IDs are typos
- Campaigns have no ads
- Check the report for details

### "Failed to navigate to campaign ads page"
- Campaign ID might be invalid or deleted
- Network issues
- Check logs in `logs/pause_ads_{timestamp}.log`

### Pagination not working
- Script will continue with first 100 ads only
- Check logs for details
- Try with `--screenshots` to see what's happening

---

## 🛡️ Safety Features

### Dry Run Mode
- Preview everything before pausing
- No actual changes made
- Full report generated

### Retry Logic
- 3 retry attempts with exponential backoff
- Handles temporary network issues
- Continues to next campaign on failure

### Error Handling
- Detailed error messages
- Logs all issues
- Continues processing other campaigns

### Comprehensive Reporting
- Know exactly what was paused
- Know what wasn't found
- Track time per campaign

---

## 💡 Tips & Best Practices

### 1. Always Dry Run First
```bash
# Preview first
python Pause_ads_V1.py --creatives ... --campaigns ... --dry-run

# If it looks good, run for real
python Pause_ads_V1.py --creatives ... --campaigns ...
```

### 2. Start Small
Test with 1-2 campaigns and 1-2 Creative IDs first.

### 3. Use Descriptive Filenames
```
black_friday_creatives_2025.csv
all_stepmom_campaigns.csv
```

### 4. Keep Your CSVs
Save them for future reference or to undo (by re-uploading ads).

### 5. Check Reports
Review the generated reports to ensure everything worked as expected.

### 6. Use Screenshots for Debugging
If something goes wrong, run with `--screenshots` to see exactly what happened.

---

## 📁 File Locations

| Item | Location |
|------|----------|
| Main Script | `Pause_ads_V1.py` |
| Input CSVs | `data/input/Ad_Pause/` (organized folder) |
| Reports | `data/reports/Ad_Pause/pause_report_{timestamp}.md` |
| Logs | `logs/pause_ads_{timestamp}.log` |
| Screenshots | `data/screenshots/` (if enabled) |
| Example Templates | `Example_docs/Creative_IDs_Template.csv`<br>`Example_docs/Campaign_IDs_Template.csv` |

---

## 🆘 Need Help?

1. **Check the logs:** `logs/pause_ads_{timestamp}.log`
2. **Run dry run with screenshots:** See exactly what the script is doing
3. **Check the report:** Detailed info on what succeeded/failed
4. **Verify CSV format:** Use the templates in `Example_docs/`

---

## 🔄 Related Tools

- **Campaign Creation V2:** `create_campaigns_v2_sync.py` - Create campaigns
- **Native Upload:** `native_main.py` - Upload native ads
- **Campaign Rename:** `rename_campaigns.py` - Rename campaigns

---

## ⚡ Quick Reference

### Single Instance Mode
```bash
# Dry run (preview)
python Pause_ads_V1.py --creatives CREATIVES.csv --campaigns CAMPAIGNS.csv --dry-run

# Actual pause
python Pause_ads_V1.py --creatives CREATIVES.csv --campaigns CAMPAIGNS.csv

# With screenshots
python Pause_ads_V1.py --creatives CREATIVES.csv --campaigns CAMPAIGNS.csv --screenshots

# Headless mode
python Pause_ads_V1.py --creatives CREATIVES.csv --campaigns CAMPAIGNS.csv --headless

# Help
python Pause_ads_V1.py --help
```

### Parallel Mode (FASTER for 100+ campaigns)
```bash
# 2 workers (safest)
python3 run_parallel_ad_pauser.py --creatives CREATIVES.csv --campaigns CAMPAIGNS.csv --workers 2

# 3 workers (fastest)
python3 run_parallel_ad_pauser.py --creatives CREATIVES.csv --campaigns CAMPAIGNS.csv --workers 3

# Parallel dry run
python3 run_parallel_ad_pauser.py --creatives CREATIVES.csv --campaigns CAMPAIGNS.csv --workers 2 --dry-run

# Help
python3 run_parallel_ad_pauser.py --help
```

---

**Created:** December 2, 2025  
**Version:** 1.0  
**Tool:** Pause_ads_V1.py


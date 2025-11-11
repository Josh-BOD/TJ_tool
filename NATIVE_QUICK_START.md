# Native Ad Upload - Quick Start Guide

## Overview

This tool automates the upload of **Native ads** to TrafficJunky campaigns using CSV files. It's a separate system from the Preroll uploader and uses a different CSV format.

## Native vs Preroll Differences

### Native Ad Format
Native ads require:
- **Ad Name** - Name for the ad
- **Target URL** - Click destination URL with tracking parameters
- **Video Creative ID** - TrafficJunky video creative ID
- **Thumbnail Creative ID** - TrafficJunky thumbnail/image creative ID
- **Headline** - Ad headline text
- **Brand Name** - Brand name to display

### Preroll Ad Format (for reference)
Preroll ads require different fields like Creative ID, Custom CTA fields, Banner CTA fields, etc.

## Setup

### 1. Prepare Your Native CSV File

Create a CSV file with the following columns in this exact order:

```csv
"Ad Name","Target URL","Video Creative ID","Thumbnail Creative ID",Headline,"Brand Name"
```

**Example:**
```csv
"Ad Name","Target URL","Video Creative ID","Thumbnail Creative ID",Headline,"Brand Name"
"My Native Ad 1","https://example.com?sub11=CAMPAIGN_NAME","1032473171","1032473180","Click Here Now","MyBrand"
"My Native Ad 2","https://example.com?sub11=CAMPAIGN_NAME","1032468251","1032468260","Amazing Offer","MyBrand"
```

**Important Notes:**
- Save your CSV file to: `data/input/`
- Use the Native_Upload_Template.CSV as a starting template
- Maximum 50 ads per CSV
- Maximum file size: 500KB
- Ensure all Creative IDs are valid in TrafficJunky

### 2. Create Campaign Mapping File

Create `data/input/native_campaign_mapping.csv`:

```csv
campaign_id,csv_filename,campaign_name,enabled
1013017411,my_native_ads.csv,My Native Campaign 1,true
1013017412,my_native_ads.csv,My Native Campaign 2,true
```

**Columns:**
- `campaign_id` - TrafficJunky campaign ID (required)
- `csv_filename` - Name of CSV file in data/input/ (required)
- `campaign_name` - Friendly name for logging (optional)
- `enabled` - Set to `true` to process, `false` to skip (optional, defaults to true)

### 3. Configure Environment

Make sure your `.env` file has:

```bash
# TrafficJunky credentials
TJ_USERNAME=your_email@example.com
TJ_PASSWORD=your_password

# Settings
DRY_RUN=True  # Set to False for live uploads
HEADLESS_MODE=False  # Set to True to hide browser
```

## Usage

### Dry Run (Test Mode - Recommended First)

Test without actually uploading:

```bash
python native_main.py
```

This will:
- ✅ Validate your CSVs
- ✅ Log into TrafficJunky
- ✅ Navigate to campaigns
- ✅ Show what WOULD be uploaded
- ❌ NOT actually upload any ads

### Live Upload

When ready to upload for real:

```bash
python native_main.py --live
```

### Additional Options

```bash
# Headless mode (no browser window)
python native_main.py --live --headless

# Verbose logging (debugging)
python native_main.py --verbose

# No screenshots
python native_main.py --no-screenshots
```

## Workflow

1. **Prepare Native CSVs** - Create your Native ad CSVs with correct format
2. **Create Mapping** - Map campaign IDs to CSV files
3. **Dry Run** - Test with `python native_main.py`
4. **Review Logs** - Check `logs/native_upload_log_*.txt`
5. **Live Upload** - Run with `--live` flag
6. **Check Reports** - Review `data/output/upload_summary_*.csv`

## Output Files

### Success Reports
- `data/output/upload_summary_YYYYMMDD_HHMMSS.csv` - Summary of all uploads

### Invalid Creatives Report
- `data/output/invalid_creatives_YYYYMMDD_HHMMSS.csv` - Lists any invalid creative IDs

### Logs
- `logs/native_upload_log_YYYYMMDD_HHMMSS.txt` - Detailed execution log

### Screenshots
- `screenshots/` - Screenshots of each step (if enabled)

### Work In Progress
- `data/wip/` - Temporary modified CSVs (with campaign names inserted)

## Troubleshooting

### "CSV validation failed: Missing columns"
- ✅ Check your CSV has all 6 required columns
- ✅ Use the Native_Upload_Template.CSV as a template
- ✅ Column names must match exactly (case-sensitive)

### "Validation errors: X invalid creative IDs"
- ✅ Verify creative IDs exist in TrafficJunky
- ✅ Check creative IDs are marked with correct content category
- ✅ The tool will automatically retry without invalid IDs

### "Failed to navigate to campaign"
- ✅ Verify campaign ID is correct
- ✅ Check campaign exists and you have access
- ✅ Ensure campaign is Active (not archived)

### "No new Native ads detected"
- ✅ Check if ads already exist (duplicates are skipped)
- ✅ Review screenshots in `screenshots/` folder
- ✅ Check TrafficJunky campaign page manually

## Campaign Name in URLs (sub11 Parameter)

The tool automatically:
1. Gets the actual campaign name from TrafficJunky
2. Updates the `sub11` parameter in your Target URLs with the campaign name
3. Saves the modified CSV to `data/wip/` folder

This ensures proper tracking in your analytics.

## Batch Processing

The tool processes campaigns sequentially:
1. Loads all campaigns from `native_campaign_mapping.csv`
2. Processes enabled campaigns one by one
3. Generates summary report at the end
4. Shows success/failure count

## Tips

1. **Start Small** - Test with 1-2 campaigns first
2. **Use Dry Run** - Always test before live uploads
3. **Check Logs** - Review logs for any warnings
4. **Verify Creatives** - Ensure all creative IDs are valid before uploading
5. **Monitor First Upload** - Watch the browser during first run to understand the process

## Comparison with Preroll Uploader

| Feature | Native Uploader | Preroll Uploader |
|---------|----------------|------------------|
| **Script** | `native_main.py` | `main.py` |
| **CSV Format** | Native format (6 columns) | Preroll format (10 columns) |
| **Mapping File** | `native_campaign_mapping.csv` | `campaign_mapping.csv` |
| **Ad Type** | Native ads | Preroll/Video ads |
| **Template** | Native_Upload_Template.CSV | (Preroll format) |

## Next Steps

1. ✅ Create your Native CSV files
2. ✅ Set up `native_campaign_mapping.csv`
3. ✅ Run a dry-run test
4. ✅ Review logs and screenshots
5. ✅ Run live upload with `--live` flag
6. ✅ Check upload summary report

## Support Files

- `native_main.py` - Main script
- `src/native_uploader.py` - Upload logic
- `src/native_csv_processor.py` - CSV validation and processing
- `Example_docs/Native_Upload_Template.CSV` - CSV template

## Questions?

Check the main README.md for general setup instructions and troubleshooting tips.


# Managing 400+ Campaigns

## Overview

This tool is designed to handle hundreds of campaigns efficiently using a CSV-based approach. Here's how to manage large-scale uploads.

## Setup for Large Scale

### 1. Campaign Mapping CSV

Your **primary control file** is `data/input/campaign_mapping.csv`:

```csv
campaign_id,csv_filename,campaign_name,enabled
1013017411,Gay.csv,US_EN_Gay_Desktop,true
1013017412,Straight.csv,US_EN_Straight_Desktop,true
1013017413,Trans.csv,US_EN_Trans_Desktop,true
... (397 more campaigns)
```

**Key Features:**
- **Same CSV for multiple campaigns**: You can use `Gay.csv` for 100 different campaigns
- **Enable/Disable control**: Set `enabled=false` to skip campaigns without deleting rows
- **Descriptive names**: Use campaign_name to organize and track campaigns
- **Easy management**: Use Excel/Google Sheets to manage this file

### 2. Creative CSV Files

Keep your creative CSVs in `data/input/`:

```
data/input/
  ├── campaign_mapping.csv  ← Your master control file
  ├── Gay.csv               ← Creative definitions
  ├── Straight.csv
  ├── Trans.csv
  └── Lesbian.csv
```

Each creative CSV has your ad specs:
```csv
Ad Name,Image creative Id,Video creative Id,Video creative cover Id,Banner creative Id,Landing Page URL,Landing Page Title
2257,,,,,https://example.com,Example Title
```

## Running Large-Scale Uploads

### Test First (Dry Run)

```bash
# Test the entire process without uploading
python main.py
```

This will:
- Load all enabled campaigns from your mapping file
- Navigate to each campaign
- Simulate the upload process
- Generate a report of what would happen

### Live Upload to All Campaigns

```bash
# Upload to ALL enabled campaigns
python main.py --live
```

### Selective Processing

**Option 1: Use enabled flag**
```csv
# In campaign_mapping.csv
1013017411,Gay.csv,Test Campaign,true      ← Will process
1013017412,Gay.csv,Paused Campaign,false   ← Will skip
```

**Option 2: Test specific campaigns**
```bash
# Test just 3 campaigns
python main.py --campaigns 1013017411,1013017412,1013017413
```

## Best Practices

### 1. Batch Processing Strategy

For 400 campaigns, consider processing in batches:

**Day 1: Test batch (10 campaigns)**
```csv
campaign_id,csv_filename,campaign_name,enabled
1013017411,Gay.csv,US_EN_Gay_Desktop,true
1013017412,Gay.csv,US_EN_Straight_Desktop,true
... (8 more)
... (390 campaigns set to enabled=false)
```

**Day 2: First 100**
```bash
# Update mapping file: enable first 100 campaigns
python main.py --live
```

**Day 3-5: Remaining campaigns**
```bash
# Update mapping file: enable next batch
python main.py --live
```

### 2. Organize by Groups

Use campaign_name to group similar campaigns:

```csv
campaign_id,csv_filename,campaign_name,enabled
# US English campaigns
1013017411,Gay.csv,US_EN_Gay_Desktop,true
1013017412,Straight.csv,US_EN_Straight_Desktop,true
1013017413,Trans.csv,US_EN_Trans_Desktop,true

# US Spanish campaigns
1013017420,Gay.csv,US_ES_Gay_Desktop,true
1013017421,Straight.csv,US_ES_Straight_Desktop,true

# Canada campaigns
1013017430,Gay.csv,CA_EN_Gay_Desktop,true
1013017431,Gay.csv,CA_FR_Gay_Desktop,true
```

### 3. Error Recovery

The tool automatically:
- Skips failed campaigns and continues
- Logs all errors
- Generates detailed reports
- Saves cleaned CSVs for invalid creatives

After a run, check:
```bash
data/output/
  ├── summary_report_20251102_143022.csv      ← Overall results
  ├── invalid_creatives_20251102_143022.csv   ← Failed creative IDs
  └── Gay_cleaned_20251102_143022.csv         ← Auto-cleaned CSV
```

### 4. Resume Failed Campaigns

After a run, you'll get a summary report showing which campaigns failed. To retry:

```csv
# In campaign_mapping.csv, set failed campaigns to enabled=true, successful to false
campaign_id,csv_filename,campaign_name,enabled
1013017411,Gay.csv,SUCCESS - Skip,false
1013017412,Gay.csv,FAILED - Retry,true
1013017413,Gay.csv,SUCCESS - Skip,false
```

## Performance Tips

### Speed Up Processing

```bash
# Run headless (faster)
python main.py --live --headless

# Disable screenshots (faster)
python main.py --live --no-screenshots
```

### Monitor Progress

```bash
# Verbose logging
python main.py --live --verbose
```

Watch the logs in real-time:
```bash
tail -f logs/upload_log_20251102_143022.txt
```

## Managing Your CSV in Excel/Google Sheets

1. Open `campaign_mapping.csv` in Excel/Google Sheets
2. Sort by `enabled` column to see what's queued
3. Use filters to find specific campaigns
4. Use formulas to generate campaign names:
   ```
   =CONCATENATE(A2, "_", B2, "_", C2)
   ```
5. Export as CSV when done

## Troubleshooting 400 Campaigns

### "Too many campaigns taking too long"
- Process in batches of 50-100
- Use `--headless` mode
- Run overnight

### "Some campaigns have invalid creatives"
- Check `invalid_creatives_report.csv`
- Update your creative CSVs to remove invalid IDs
- Re-enable those campaigns and retry

### "Need to update one CSV used by 100 campaigns"
- Update the single CSV file (e.g., `Gay.csv`)
- All 100 campaigns will use the updated version
- Set those 100 campaigns to `enabled=true`

### "Want to test changes on a few campaigns first"
- Keep production campaigns at `enabled=false`
- Enable 2-3 test campaigns
- Run with `--live`
- If successful, enable the rest

## Example: Full Workflow for 400 Campaigns

```bash
# Step 1: Setup (one time)
./setup.sh
# Edit .env with credentials
# Create campaign_mapping.csv with 400 campaigns

# Step 2: Test with 5 campaigns
# Set 5 campaigns to enabled=true in mapping file
python main.py  # dry run first
python main.py --live  # then live

# Step 3: If successful, process all 400
# Set all 400 campaigns to enabled=true
python main.py --live --headless

# Step 4: Check results
cat data/output/summary_report_*.csv

# Step 5: Handle failures (if any)
# Check invalid_creatives_report.csv
# Update creative CSVs
# Set failed campaigns to enabled=true, successful to false
# Retry
python main.py --live
```

## Summary

✓ Use `campaign_mapping.csv` as your master control file  
✓ Same creative CSV can be used for many campaigns  
✓ Process in batches for safety  
✓ Use `enabled` flag to control which campaigns run  
✓ Always dry-run first, then go live  
✓ Check reports after each run  
✓ Retry failed campaigns separately  


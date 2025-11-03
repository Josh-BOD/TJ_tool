# Testing the Campaign Performance Analysis Tool

## Prerequisites

1. ✅ All dependencies installed (`requests` added)
2. ✅ TrafficJunky API key obtained
3. ✅ `.env` file updated with `TJ_API_KEY`

---

## Step 1: Get Your API Key

1. Log into TrafficJunky dashboard
2. Click your profile name (top right)
3. Scroll to **API Token** section
4. Click **Generate New Token** (if needed)
5. Copy the token

---

## Step 2: Add API Key to .env

Edit `.env` file:

```bash
# TrafficJunky API Key
TJ_API_KEY=your_actual_api_key_here
```

---

## Step 3: Test API Connection

```bash
# Activate virtual environment
source venv/bin/activate

# Test connection (no data fetch, just validates auth)
python analyze.py --test-api
```

**Expected output:**
```
============================================================
TrafficJunky Campaign Performance Analysis Tool
============================================================

✓ Configuration valid
✓ API client initialized
ℹ Testing API connection...
✓ API connection successful!
```

---

## Step 4: Run Your First Analysis

```bash
# Analyze today's performance
python analyze.py --period today
```

**Expected output:**
```
============================================================
TrafficJunky Campaign Performance Analysis Tool
============================================================

✓ Configuration valid
✓ API client initialized
ℹ Analyzing period: today
ℹ   Start: 03/11/2025
ℹ   End: 03/11/2025
ℹ Fetching campaign data from TrafficJunky API...
✓ Fetched 45 campaigns
ℹ Processing and categorizing campaigns...
✓ Categorization complete:
  What to do more of: 8 campaigns
  To Watch: 12 campaigns
  Scaled: 3 campaigns
  Killed: 5 campaigns
ℹ Generating markdown report...
✓ Report saved to: data/reports/tj_analysis_03-11-2025.md

============================================================
Analysis complete!
============================================================

Report ready for Slack Canvas: tj_analysis_03-11-2025.md
```

---

## Step 5: Review the Report

```bash
# Open the report
cat data/reports/tj_analysis_03-11-2025.md
```

Or open it in your editor to copy to Slack Canvas.

---

## Test Different Periods

```bash
# Yesterday
python analyze.py --period yesterday

# Last 7 days
python analyze.py --period last7days

# Last 30 days
python analyze.py --period last30days
```

---

## Troubleshooting

### Error: "TJ_API_KEY not set"

**Fix:** Add API key to `.env` file

### Error: "API connection failed"

**Possible causes:**
1. Invalid API key
2. Network issues
3. TrafficJunky API is down

**Fix:** 
- Verify API key in TJ dashboard
- Check internet connection
- Try again in a few minutes

### Error: "No campaign data found"

**Possible causes:**
1. No campaigns active during period
2. All campaigns have zero spend
3. Date range outside available data

**Fix:**
- Try different time period
- Verify campaigns are active in TJ dashboard
- Check if campaigns have spend

### Empty Categories

This is normal! Categories are only populated if campaigns meet the thresholds:
- **What to do more of:** eCPA < $50, Conv > 5, Spend > $250
- **To Watch:** eCPA $100-$200, Conv > 3, Spend > $250, Velocity 70-90%
- **Scaled:** eCPA < $60, Velocity > 95%
- **Killed:** eCPA > $120, Spend > $250, Velocity < 60%

---

## Customizing Thresholds

Edit `src/data_processor.py`:

```python
CATEGORY_RULES = {
    'what_to_do_more_of': {
        'ecpa_max': 50.0,          # Change to your target
        'conversions_min': 5,       # Change minimum conversions
        'spend_min': 250.0          # Change minimum spend
    },
    # ... etc
}
```

After editing, re-run:
```bash
python analyze.py
```

---

## Verbose Logging

For detailed debugging:

```bash
python analyze.py --verbose
```

This will show:
- API request URLs
- Raw response data
- Detailed categorization logic
- Individual campaign processing

---

## Next Steps

Once testing is successful:

1. **Schedule daily runs** (optional):
   ```bash
   # Add to crontab (macOS/Linux)
   # Run every day at 9 AM
   0 9 * * * cd /Users/joshb/Desktop/Dev/TJ_tool && source venv/bin/activate && python analyze.py --period yesterday
   ```

2. **Integrate with Slack** (V2):
   - Add Slack webhook URL
   - Auto-post reports

3. **Historical tracking** (V2):
   - Store data in SQLite
   - Show trends over time

---

**Ready to test! Run `python analyze.py --test-api` to begin.** 🚀


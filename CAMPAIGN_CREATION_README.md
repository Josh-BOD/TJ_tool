# Campaign Creation Tool

Automated end-to-end campaign creation for TrafficJunky Native campaigns.

## Overview

This tool automates the entire campaign creation workflow:
1. **Parses CSV input** with campaign definitions
2. **Creates campaigns** via TrafficJunky UI (Desktop, iOS, Android)
3. **Uploads ads** from CSV files
4. **Tracks progress** with checkpoints and resume capability
5. **Handles errors** gracefully and continues processing

## Features

- ✅ **CSV Input Format** - Simple spreadsheet-based campaign definitions
- ✅ **Smart Cloning** - Desktop/iOS from templates, Android from iOS
- ✅ **Batch Creation** - Create multiple campaigns simultaneously
- ✅ **Progress Tracking** - Visual progress bars and status updates
- ✅ **Checkpoint/Resume** - Recover from interruptions
- ✅ **Dry-Run Mode** - Validate and preview before creating
- ✅ **Error Handling** - Continue processing if one campaign fails
- ✅ **Customizable Settings** - Per-campaign budgets, bids, targeting

## Quick Start

### 1. Install Dependencies

```bash
pip install playwright pandas
python -m playwright install chromium
```

### 2. Create Session File

You need an authenticated browser session:

```bash
python main.py --create-session
```

This will open a browser where you log in to TrafficJunky. The session is saved to `session.json`.

### 3. Create Input CSV

Create a CSV file with your campaign definitions (see [CSV Format](#csv-format) below).

Example: `data/input/my_campaigns.csv`

```csv
group,keywords,keyword_matches,geo,csv_file,target_cpa,per_source_budget,max_bid,frequency_cap,max_daily_budget,gender,variants,enabled
Milfs,milfs;milf porn;cougar,broad;exact;exact,US,Milfs.csv,55,100,11,1,275,male,"desktop,ios,android",true
```

### 4. Dry-Run (Validate)

```bash
python create_campaigns.py --input data/input/my_campaigns.csv --dry-run
```

This validates your configuration and shows what would be created.

### 5. Create Campaigns

```bash
python create_campaigns.py --input data/input/my_campaigns.csv
```

## CSV Format

### Required Columns

| Column | Description | Example |
|--------|-------------|---------|
| `group` | Campaign group name | `Milfs` |
| `keywords` | Semicolon-separated keywords | `milfs;milf porn;cougar` |
| `keyword_matches` | Match types for each keyword | `broad;exact;exact` |
| `csv_file` | CSV file with ads | `Milfs.csv` |
| `variants` | Comma-separated devices | `desktop,ios,android` |
| `enabled` | Create this campaign? | `true` or `false` |

### Optional Columns (with defaults)

| Column | Description | Default |
|--------|-------------|---------|
| `geo` | Semicolon-separated country codes | `US` |
| `target_cpa` | Target CPA ($) | `50.0` |
| `per_source_budget` | Per Source Test Budget ($) | `200.0` |
| `max_bid` | Maximum Bid ($) | `10.0` |
| `frequency_cap` | Frequency cap (1-99) | `2` |
| `max_daily_budget` | Max Daily Budget ($) | `250.0` |
| `gender` | Gender targeting | `male` |

### Example CSV

```csv
group,keywords,keyword_matches,geo,csv_file,target_cpa,per_source_budget,max_bid,frequency_cap,max_daily_budget,gender,variants,enabled
Milfs,milfs;milf porn;cougar,broad;exact;exact,US,Milfs.csv,55,100,11,1,275,male,"desktop,ios,android",true
Cougars,"cougar;cougars;mature women",broad;exact;exact,"AU;NZ",Cougars.csv,,,,,male,"desktop,ios",true
Mature,"mature moms;mom porn",broad;exact,US,MatureMoms.csv,45,,,3,,male,desktop,true
```

**Notes:**
- Leave optional columns blank to use defaults
- Multiple geo codes: `"US;CA;UK"`
- Multiple keywords: `"milfs;milf porn;cougar"`
- Match types must match keyword count: `broad;exact;exact`
- Variants: `desktop`, `ios`, `android` (comma-separated)

## Campaign Naming Convention

Campaigns are automatically named using this pattern:

```
{GEO}_{LANG}_{FORMAT}_{BIDTYPE}_{SOURCE}_KEY-{Keyword}_{DEVICE}_{GENDER}_{INITIALS}
```

Example: `US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB`

- **GEO**: Country code (US, CA, AU, etc.)
- **LANG**: Language (EN)
- **FORMAT**: Ad format (NATIVE)
- **BIDTYPE**: Bid type (CPA)
- **SOURCE**: Traffic source (ALL)
- **Keyword**: Primary keyword (capitalized)
- **DEVICE**: DESK, iOS, or AND
- **GENDER**: M, F, or ALL
- **INITIALS**: User initials (JB)

## Usage Examples

### Basic Usage

```bash
# Dry-run to validate
python create_campaigns.py --input campaigns.csv --dry-run

# Create campaigns
python create_campaigns.py --input campaigns.csv
```

### Advanced Options

```bash
# Specify CSV directory
python create_campaigns.py --input campaigns.csv --csv-dir /path/to/csvs/

# Use custom session file
python create_campaigns.py --input campaigns.csv --session my_session.json

# Visible browser (not headless)
python create_campaigns.py --input campaigns.csv --no-headless

# Verbose output
python create_campaigns.py --input campaigns.csv --verbose

# Custom checkpoint directory
python create_campaigns.py --input campaigns.csv --checkpoint-dir /path/to/checkpoints/
```

### Resume After Interruption

If the process is interrupted, you can resume:

```bash
# The tool will show the session ID when interrupted
python create_campaigns.py --input campaigns.csv --resume 20251120_124538
```

### List Available Checkpoints

```bash
python -c "from pathlib import Path; from src.campaign_automation.checkpoint import CheckpointManager; mgr = CheckpointManager(Path('data/checkpoints')); print('\n'.join(str(c) for c in mgr.list_checkpoints()))"
```

## Workflow Details

### Campaign Creation Order

For each campaign set, the tool creates variants in this order:

1. **Desktop** - Cloned from Desktop template (ID: 1013076141)
2. **iOS** - Cloned from iOS template (ID: 1013076221)
3. **Android** - Cloned from the iOS campaign created in step 2

**Why this order?** Android campaigns clone from iOS (not the template) to inherit all settings, requiring only OS changes. This is much faster than configuring from scratch.

### Steps Per Campaign

Each campaign goes through these steps:

1. **Clone Template/Campaign**
2. **Configure Basic Settings** (name, group, gender)
3. **Configure Geo Targeting**
4. **Configure OS Targeting** (iOS/Android only)
5. **Configure Keywords** (add keywords, set match types)
6. **Configure Tracking & Bids** (CPA, budget, max bid, sources)
7. **Configure Schedule & Budget** (frequency cap, daily budget)
8. **Upload Ads** (from CSV file)
9. **Save Campaign**

### Time Estimates

- **Desktop**: ~5 minutes per campaign
- **iOS**: ~5 minutes per campaign
- **Android**: ~3 minutes per campaign (faster due to cloning iOS)

Example: 3 campaign sets with all variants (9 total campaigns) = ~41 minutes

## Progress Tracking

The tool shows real-time progress:

```
[12:45:38] Creating DESKTOP campaign...
  └─ Cloning Desktop template
  └─ Configuring basic settings
  └─ Configuring geo targeting
  └─ Configuring keywords
  └─ Uploading ads...
  ✓ Created: US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB (ID: 1234567890)
    Uploaded 5 ads | Elapsed: 4m 32s

[████████████████████░░░░░░░░░░░░░░░░░░░░] 3/9 (33.3%) | 13m 45s | ETA: 27m 30s
```

## Error Handling

The tool handles errors gracefully:

- **Validation Errors**: Caught before any campaigns are created
- **Campaign Creation Errors**: Logged, other campaigns continue
- **Network Errors**: Retries with exponential backoff
- **Interruptions**: Progress saved to checkpoint

### Failed Campaign Recovery

If a campaign fails:
1. Check the error message in the summary
2. Fix the issue (e.g., CSV file, settings)
3. Update the input CSV to disable successful campaigns
4. Re-run the tool

Or use `--resume` to skip completed campaigns.

## Checkpoint System

Checkpoints are automatically saved:
- **After each campaign** is created
- **On interruption** (Ctrl+C)
- **On error** (before continuing to next campaign)

Checkpoint files: `data/checkpoints/checkpoint_{SESSION_ID}.json`

To resume: `--resume {SESSION_ID}`

## Troubleshooting

### Session File Issues

**Problem**: `Session file not found`

**Solution**: Create a session file:
```bash
python main.py --create-session
```

### CSV Validation Errors

**Problem**: `CSV file not found` or `Invalid column`

**Solution**: 
- Check CSV file paths in `csv_file` column
- Ensure all required columns are present
- Verify column names match exactly (case-sensitive)

### Campaign Already Exists

**Problem**: Campaign with the same name already exists

**Solution**: 
- Delete the existing campaign in TrafficJunky UI
- Or change the input CSV to create a different campaign name

### Browser Timeout

**Problem**: `Timeout waiting for element`

**Solution**:
- Use `--no-headless` to see what's happening
- Increase `--slow-mo` value (e.g., `--slow-mo 1000`)
- Check if TrafficJunky UI has changed

### Playwright Not Installed

**Problem**: `playwright not found`

**Solution**:
```bash
pip install playwright
python -m playwright install chromium
```

## Template Campaign IDs

**IMPORTANT**: These template IDs are hardcoded and should not change:

- **Desktop**: `1013076141` - TEMPLATE_EN_NATIVE_CPA_ALL_KEY-ENTER-Keywords_DESK_M_JB
- **iOS**: `1013076221` - TEMPLATE_EN_NATIVE_CPA_ALL_KEY-ENTERKEYWORDS_iOS_M_JB

If templates are updated or renamed, the IDs remain the same.

## Best Practices

1. **Always dry-run first** - Catch issues before creating campaigns
2. **Start small** - Test with 1-2 campaigns before bulk creation
3. **Use visible mode initially** - `--no-headless` helps debug issues
4. **Keep CSV files organized** - Use consistent naming and location
5. **Monitor progress** - Watch for errors in real-time
6. **Use checkpoints** - Don't restart from scratch if interrupted
7. **Validate settings** - Double-check budgets and bids before running

## Limitations

- **API doesn't support campaign creation** - Must use UI automation
- **Requires authenticated session** - Session expires after ~24 hours
- **Sequential processing** - Campaigns created one at a time
- **Browser-based** - Requires Playwright and Chromium

## Files Structure

```
TJ_tool/
├── create_campaigns.py          # Main CLI
├── data/
│   ├── input/
│   │   ├── my_campaigns.csv     # Campaign definitions
│   │   ├── Milfs.csv           # Ad CSV files
│   │   └── Cougars.csv
│   └── checkpoints/             # Progress checkpoints
├── src/
│   ├── campaign_automation/
│   │   ├── csv_parser.py       # Parse CSV input
│   │   ├── validator.py        # Validate campaigns
│   │   ├── models.py           # Data models
│   │   ├── creator.py          # Playwright automation
│   │   ├── orchestrator.py     # Workflow coordinator
│   │   ├── progress.py         # Progress tracking
│   │   └── checkpoint.py       # Checkpoint manager
│   ├── campaign_templates.py   # Constants and naming
│   └── native_uploader.py      # Ad CSV uploader
└── session.json                 # Browser session
```

## Related Tools

- **Native Ad Uploader** (`main.py --native`) - Upload ads to existing campaigns
- **Campaign Renamer** (`rename_campaigns.py`) - Bulk rename campaigns
- **Campaign URL Updater** (`update_campaign_urls.py`) - Update campaign URLs

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review error messages and logs
3. Use `--verbose` for detailed output
4. Try `--no-headless` to see browser behavior

## Version

Version: 1.0.0


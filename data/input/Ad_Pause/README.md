# Ad Pause Input Folder

This folder contains CSV files for the Mass Ad Pausing Tool (`Pause_ads_V1.py`).

## Required CSV Files

### 1. Creative IDs CSV
Lists the Creative IDs you want to pause across campaigns.

**Required Column:** `Creative ID`

**Example:**
```csv
Creative ID,Ad Name,Notes
1032539111,Black Friday Ad 1,Holiday promo
1032539112,Black Friday Ad 2,Holiday promo
```

### 2. Campaign IDs CSV
Lists the Campaign IDs where you want to search for and pause the Creative IDs.

**Required Column:** `Campaign ID`

**Example:**
```csv
Campaign ID,Campaign Name,Notes
1012927602,Desktop-Stepmom-US,Main campaign
1012927603,iOS-Stepmom-US,Mobile campaign
```

## Templates

See `Example_docs/` folder for template CSV files:
- `Creative_IDs_Template.csv`
- `Campaign_IDs_Template.csv`

## Test Files

- `test_creative_ids.csv` - Contains Creative ID: 1032539111
- `test_campaign_ids.csv` - Contains Campaign ID: 1012927602

## Usage

```bash
python Pause_ads_V1.py \
    --creatives data/input/Ad_Pause/YOUR_CREATIVES.csv \
    --campaigns data/input/Ad_Pause/YOUR_CAMPAIGNS.csv \
    --dry-run
```

See `PAUSE_ADS_QUICK_START.md` for full documentation.


# Campaign Creation V3 - From Scratch Quick Start

## Overview

V3 creates campaigns from scratch instead of cloning templates. This gives you full control over all first-page settings that are normally locked when cloning.

## Folder Structure

```
data/
├── input/
│   ├── Blank_Campaign_Creation/    <- V3 campaign definition CSVs go here
│   │   └── my_campaigns.csv
│   └── Campaign_Creation/          <- Ad CSVs (creatives) are still here
│       └── Native_Femdom_Dec25.csv
└── output/
    └── Blank_Campaign_Creation/    <- Reports are saved here
        └── my_campaigns_report_20241210_120000.csv
```

## Why V3?

When you clone from a template, these settings are **locked**:
- Device (All/Desktop/Mobile)
- Ad Format (Display/In-Stream Video/Pop)
- Format Type (Banner/Native)
- Ad Type (Static Banner/Video Banner/Rollover)
- Ad Dimensions
- Content Category (Straight/Gay/Trans)
- Labels

V3 creates campaigns from scratch, allowing you to configure ALL these settings via CSV.

## Quick Start

### 1. Prepare Your CSV

Place your campaign definition CSV in `data/input/Blank_Campaign_Creation/`

Add the new V3 columns to your campaign definition CSV:

| Column | Values | Default |
|--------|--------|---------|
| `labels` | Comma-separated (e.g., "Native,Test") | (empty) |
| `device` | all, desktop, mobile | desktop |
| `ad_format_type` | display, instream, pop | display |
| `format_type` | banner, native | native |
| `ad_type` | static_banner, video_banner, rollover | rollover |
| `ad_dimensions` | 300x250, 950x250, 468x60, 305x99, 300x100, 970x90, 320x480, 640x360 | 640x360 |
| `content_category` | straight, gay, trans | straight |

### 2. Validate Your CSV (Dry Run)

```bash
python create_campaigns_v3_scratch.py data/input/Blank_Campaign_Creation/my_campaigns.csv --dry-run
```

This will:
- Parse and validate the CSV
- Show all campaigns that would be created
- Display all V3 settings for each campaign
- NOT create any campaigns

### 3. Create Campaigns

```bash
python create_campaigns_v3_scratch.py data/input/Blank_Campaign_Creation/my_campaigns.csv
```

This will:
- Open a browser (not headless)
- Prompt you to log in (solve CAPTCHA if needed)
- Create each campaign from scratch
- Upload ads from the specified CSV file (from `data/input/Campaign_Creation/`)
- Save a report to `data/output/Blank_Campaign_Creation/`
- Show a summary when complete

## Example CSV

```csv
group,keywords,keyword_matches,gender,geo,multi_geo,csv_file,target_cpa,per_source_budget,max_bid,frequency_cap,max_daily_budget,variants,ios_version,android_version,ad_format,enabled,test_number,labels,device,ad_format_type,format_type,ad_type,ad_dimensions,content_category
TestNative,test keyword,,male,US,,ads.csv,50,100,10,2,50,desktop,,,NATIVE,TRUE,V3,"Native,Test",desktop,display,native,rollover,640x360,straight
TestBanner,banner test,,male,US,,ads.csv,50,100,10,2,50,desktop,,,NATIVE,TRUE,V3B,,desktop,display,banner,static_banner,300x250,straight
TestGay,gay test,,male,US,,ads.csv,50,100,10,2,50,desktop,,,NATIVE,TRUE,V3G,Gay,desktop,display,native,rollover,640x360,gay
```

## Column Reference

### Existing V2 Columns (still required)
- `group` - Campaign group name
- `keywords` - Semicolon-separated keywords
- `keyword_matches` - Match types (broad/exact)
- `gender` - Demographic targeting (male/female/all)
- `geo` - Country codes
- `csv_file` - Path to ad CSV file
- `target_cpa`, `per_source_budget`, `max_bid` - Bidding settings
- `frequency_cap`, `max_daily_budget` - Budget settings
- `variants` - Device variants (desktop, ios, android, all mobile)
- `enabled` - TRUE/FALSE

### New V3 Columns
- `labels` - Comma-separated labels (optional)
- `device` - Device targeting: all, desktop, mobile
- `ad_format_type` - Format: display, instream, pop
- `format_type` - For display: banner, native
- `ad_type` - Type: static_banner, video_banner, rollover
- `ad_dimensions` - Ad size (e.g., 640x360, 300x250)
- `content_category` - Category: straight, gay, trans

## Troubleshooting

### "CSV parse error"
Check that all required columns are present and values are valid. Use `--dry-run` to validate.

### "Login failed"
Make sure your TJ credentials are correct in `.env` or `config/config.py`.

### "Could not set [field]"
The script will log warnings for non-critical fields. Check the browser to see what's happening.

## Tips

1. **Start small** - Test with 1-2 campaigns first
2. **Use dry-run** - Always validate with `--dry-run` before creating
3. **Watch the browser** - Run in non-headless mode to see what's happening
4. **Check logs** - The script logs every action for debugging

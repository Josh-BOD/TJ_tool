# Campaign Creation Tool V2 - Multi-Format Support

## Overview

Version 2 of the campaign creation tool adds support for both **NATIVE** and **IN-STREAM** (Preroll) ad formats in a single unified workflow.

## What's New in V2?

### Multi-Format Support
- **Native ads**: Image/video ads with thumbnails, headlines, and brand names
- **In-Stream ads**: Pre-roll video ads with CTAs and banner overlays

### Ad Format Selection
- Add `ad_format` column to your CSV to specify format per campaign
- Defaults to `NATIVE` for backward compatibility with V1 files
- Auto-selects correct template and uploader based on format

### Unified Workflow
- Single script handles both formats
- Uses correct templates automatically
- Applies appropriate CSV validation
- Uploads with format-specific uploader

## How to Use

### 1. Update Your CSV with Ad Format

Add the optional `ad_format` column to your campaign CSV:

```csv
group,keywords,keyword_matches,gender,geo,multi_geo,csv_file,target_cpa,per_source_budget,max_bid,frequency_cap,max_daily_budget,variants,ad_format,enabled
Milfs,"milf;milfs;mature",broad,male,,CA;AUS,milf_native.csv,50,100,10,1,250,"desktop,ios,android",NATIVE,TRUE
Cougars,"cougar;cougars",broad,female,US,,cougar_instream.csv,60,150,12,2,300,"desktop,ios",INSTREAM,TRUE
```

**Important:**
- `ad_format` can be `NATIVE` or `INSTREAM`
- If omitted, defaults to `NATIVE` (V1 compatible)
- Format is case-insensitive

### 2. Prepare Your Template IDs

**Update `src/campaign_templates.py`** with your in-stream template IDs:

```python
"INSTREAM": {
    "desktop": {
        "id": "YOUR_INSTREAM_DESKTOP_TEMPLATE_ID",  # Add your ID here
        ...
    },
    "ios": {
        "id": "YOUR_INSTREAM_IOS_TEMPLATE_ID",  # Add your ID here
        ...
    },
}
```

### 3. Run V2 Script

```bash
# Dry-run to preview
python create_campaigns_v2.py --input campaigns.csv --dry-run

# Create campaigns
python create_campaigns_v2.py --input campaigns.csv

# With visible browser (debug)
python create_campaigns_v2.py --input campaigns.csv --no-headless
```

## CSV Format Differences

### Native Format CSV
```csv
"Ad Name","Target URL","Video Creative ID","Thumbnail Creative ID",Headline,"Brand Name"
"My Ad","https://example.com?sub11=CAMPAIGN_NAME","1032473171","1032473180","Click Here","MyBrand"
```

### In-Stream Format CSV
```csv
Ad Name,Target URL,Creative ID,Custom CTA Text,Custom CTA URL,Banner CTA Creative ID,Banner CTA Title,Banner CTA Subtitle,Banner CTA URL,Tracking Pixel
Video_1,https://example.com?sub11=CAMPAIGN_NAME,1032473171,Click Here,https://example.com,,,,, 
```

## Templates Required

You need to create template campaigns for each format:

### Native Templates (Already Set)
- Desktop: `1013076141`
- iOS: `1013076221`

### In-Stream Templates (Need to Add)
- Desktop: **YOUR_TEMPLATE_ID**
- iOS: **YOUR_TEMPLATE_ID**

**To find your in-stream template IDs:**
1. Go to TrafficJunky campaigns
2. Find your in-stream template campaigns
3. Copy the campaign IDs
4. Update `src/campaign_templates.py`

## Backward Compatibility

V2 is **100% backward compatible** with V1:

- Old CSV files work without changes (default to NATIVE)
- V1 script (`create_campaigns.py`) still works
- All V1 features preserved

## Examples

### Example 1: Mixed Format Campaigns

```csv
group,keywords,csv_file,variants,ad_format,enabled
Milfs,"milf;milfs",native_ads.csv,"desktop,ios,android",NATIVE,TRUE
Teens,"teen;teens",instream_ads.csv,"desktop,ios,android",INSTREAM,TRUE
```

This creates:
- 3 Native campaigns (Milfs-Desktop, Milfs-iOS, Milfs-Android)
- 3 In-Stream campaigns (Teens-Desktop, Teens-iOS, Teens-Android)

### Example 2: All Native (V1 Compatible)

```csv
group,keywords,csv_file,variants,enabled
Milfs,"milf;milfs",ads.csv,"desktop,ios,android",TRUE
Cougars,"cougar;cougars",ads.csv,"desktop,ios",TRUE
```

Omitting `ad_format` defaults to NATIVE, works exactly like V1.

## Migration from V1 to V2

### Option 1: Keep Using V1
If you only work with Native ads, keep using `create_campaigns.py`.

### Option 2: Migrate to V2
1. Add your in-stream template IDs to `campaign_templates.py`
2. Optionally add `ad_format` column to CSVs (or use default)
3. Use `create_campaigns_v2.py` instead

## Troubleshooting

### "Invalid ad format" Error
- Check `ad_format` column value (must be NATIVE or INSTREAM)
- Verify capitalization doesn't matter (auto-uppercased)

### "Template ID not found"
- Ensure you've added your in-stream template IDs to `campaign_templates.py`
- Check template IDs are correct (10-digit numbers)

### Wrong Uploader Used
- V2 auto-selects uploader based on `ad_format` column
- Native ads use `NativeUploader`
- In-Stream ads use `TJUploader`

## Next Steps

1. **Add your in-stream template IDs** to `src/campaign_templates.py`
2. **Test with dry-run** first: `python create_campaigns_v2.py --input test.csv --dry-run`
3. **Create campaigns**: `python create_campaigns_v2.py --input campaigns.csv`

## Questions?

- See `docs/CSV_FORMAT.md` for CSV column details
- See `CAMPAIGN_CREATION_README.md` for general workflow
- V1 documentation still valid for Native-only workflows


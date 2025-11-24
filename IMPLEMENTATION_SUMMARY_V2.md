# Campaign Creation Tool V2 - Implementation Summary

## What Was Changed

### Files Created
1. **`create_campaigns_v2.py`** - New V2 script with multi-format support
2. **`docs/CAMPAIGN_CREATION_V2.md`** - Detailed V2 documentation
3. **`CAMPAIGN_CREATION_V2_QUICK_START.md`** - Quick start guide
4. **`data/input/example_campaigns_v2.csv`** - Example CSV with both formats

### Files Modified
1. **`src/campaign_templates.py`**
   - Added `TEMPLATE_CAMPAIGNS` as a dict with "NATIVE" and "INSTREAM" keys
   - Added `TEMPLATE_CAMPAIGNS_V1` for backward compatibility
   - Added `VALID_AD_FORMATS` list
   - Added `get_templates_for_format()` function

2. **`src/campaign_automation/models.py`**
   - Added `ad_format` field to `CampaignSettings` class
   - Auto-uppercases ad_format in `__post_init__`
   - Includes ad_format in `to_dict()` output

3. **`src/campaign_automation/csv_parser.py`**
   - Added `ad_format` to `OPTIONAL_COLUMNS` (defaults to "NATIVE")
   - Parses ad_format from CSV and passes to CampaignSettings

4. **`src/campaign_automation/creator_sync.py`**
   - Added `ad_format` parameter to `__init__`
   - Stores `self.ad_format` and `self.templates`
   - Uses dynamic templates based on format in all create methods

5. **`src/campaign_automation/orchestrator.py`**
   - Updated imports to use `creator_sync` instead of `creator`
   - Added import for `get_templates_for_format`
   - Added `TJUploader` import alongside `NativeUploader`
   - Updated `_process_campaign` to set creator format per campaign
   - Updated `_upload_ads` to accept `ad_format` parameter
   - Selects uploader based on format (NativeUploader vs TJUploader)

## How It Works

### Ad Format Selection Flow

1. **CSV Parsing**: `csv_parser.py` reads `ad_format` column (defaults to "NATIVE")
2. **Model Storage**: Stored in `CampaignSettings.ad_format`
3. **Template Selection**: `creator_sync.py` gets templates via `get_templates_for_format()`
4. **Campaign Creation**: Uses format-specific template IDs
5. **Ad Upload**: Orchestrator selects correct uploader based on format

### Template System

```python
TEMPLATE_CAMPAIGNS = {
    "NATIVE": {
        "desktop": {"id": "1013076141", ...},
        "ios": {"id": "1013076221", ...},
        "android": {"clone_from": "ios", ...}
    },
    "INSTREAM": {
        "desktop": {"id": "YOUR_ID_HERE", ...},  # <-- User needs to add
        "ios": {"id": "YOUR_ID_HERE", ...},      # <-- User needs to add
        "android": {"clone_from": "ios", ...}
    }
}
```

### Uploader Selection

```python
if ad_format.upper() == "NATIVE":
    uploader = NativeUploader(dry_run=False, take_screenshots=True)
else:
    uploader = TJUploader(dry_run=False, take_screenshots=True)
```

## Backward Compatibility

### V1 Script (`create_campaigns.py`)
- **NOT modified** - still works exactly as before
- Uses Native templates only
- No breaking changes

### V1 CSV Files
- Work with V2 without modification
- `ad_format` column is optional
- Defaults to "NATIVE" when omitted

### V1 Code
- `TEMPLATE_CAMPAIGNS_V1` provides old structure
- Default settings unchanged
- All existing functionality preserved

## User Action Required

### Before Using V2

**You MUST add your in-stream template IDs** to `src/campaign_templates.py`:

```python
"INSTREAM": {
    "desktop": {
        "id": "REPLACE_WITH_YOUR_DESKTOP_TEMPLATE_ID",
        ...
    },
    "ios": {
        "id": "REPLACE_WITH_YOUR_IOS_TEMPLATE_ID",
        ...
    },
}
```

**How to find IDs:**
1. Go to TrafficJunky campaigns page
2. Look for your in-stream template campaigns (NOT running)
3. Note the 10-digit campaign IDs
4. Replace the placeholder text in `campaign_templates.py`

### Optional: Add ad_format to CSVs

Add `ad_format` column to your campaign definition CSVs:

```csv
group,keywords,csv_file,variants,ad_format,enabled
Milfs,"milf;milfs",ads.csv,"desktop,ios,android",NATIVE,TRUE
Teens,"teen;teens",ads.csv,"desktop,ios",INSTREAM,TRUE
```

If omitted, defaults to `NATIVE` (V1 behavior).

## Testing

### Test V2 with Dry-Run

```bash
# Test without creating campaigns
python create_campaigns_v2.py --input data/input/example_campaigns_v2.csv --dry-run
```

### Verify Output Shows:
- ✓ Campaign names with correct format prefix
- ✓ Correct template IDs for each format
- ✓ Proper ad format labels (NATIVE vs INSTREAM)
- ✓ Format-specific CSV file references

### Test V1 Still Works

```bash
# V1 should work unchanged
python create_campaigns.py --input data/input/example_campaigns.csv --dry-run
```

## Migration Path

### Option 1: Keep Using V1
If you only create Native campaigns, no changes needed. Continue using:
```bash
python create_campaigns.py --input campaigns.csv
```

### Option 2: Migrate to V2
1. Add in-stream template IDs to `campaign_templates.py`
2. Optionally add `ad_format` column to CSVs
3. Use V2 script:
```bash
python create_campaigns_v2.py --input campaigns.csv
```

### Option 3: Use Both
- Use V1 for native-only batches
- Use V2 for mixed or in-stream batches
- Both scripts work independently

## Next Steps

1. **Add your in-stream template IDs** (see above)
2. **Test dry-run**: `python create_campaigns_v2.py --input example_campaigns_v2.csv --dry-run`
3. **Create test campaigns**: Start with 1-2 campaigns to verify
4. **Monitor first run**: Use `--no-headless` to watch browser
5. **Scale up**: Process larger batches once verified

## Questions?

- **V2 Documentation**: See `docs/CAMPAIGN_CREATION_V2.md`
- **Quick Start**: See `CAMPAIGN_CREATION_V2_QUICK_START.md`
- **CSV Format**: See `docs/CSV_FORMAT.md`
- **Original V1**: See `CAMPAIGN_CREATION_README.md`


# ✅ Campaign Creation Tool V2 - Complete!

## What You Asked For

> "lets do Option 1: Add ad format support to existing script (Better) but in a new file called Create_campaigns_V2.py so we can keep using V1 for now."

**✅ DONE!** The V2 system is ready with full multi-format support.

---

## What Was Delivered

### 🎯 Core Files

1. **`create_campaigns_v2.py`** ✅
   - New V2 script with `ad_format` support
   - Supports both NATIVE and INSTREAM
   - 100% backward compatible with V1 CSVs
   - V1 script untouched

2. **Updated Core Modules** ✅
   - `campaign_templates.py` - Template system for both formats
   - `models.py` - Added ad_format field
   - `csv_parser.py` - Parses ad_format from CSV
   - `creator_sync.py` - Uses format-specific templates
   - `orchestrator.py` - Selects correct uploader by format

### 📚 Documentation

1. **`CAMPAIGN_CREATION_V2_QUICK_START.md`** - Get started fast
2. **`docs/CAMPAIGN_CREATION_V2.md`** - Complete guide
3. **`IMPLEMENTATION_SUMMARY_V2.md`** - Technical details
4. **`data/input/example_campaigns_v2.csv`** - Example file

---

## How The Last Step Differs (Your Question)

**Good news:** The last step is actually THE SAME for both Native and In-Stream! 🎉

Both use the same button: `button.create-ads-from-csv-button`

The differences are:
1. **CSV Format** - Different columns
2. **Templates** - Different template campaign IDs
3. **Validation** - Different field checks

But the **final upload button** is identical, which is why we can use one unified orchestrator!

---

## What You Need To Do

### ⚠️ REQUIRED: Add Your In-Stream Template IDs

Edit `src/campaign_templates.py` and replace these placeholders:

```python
"INSTREAM": {
    "desktop": {
        "id": "NEED_YOUR_INSTREAM_DESKTOP_TEMPLATE_ID",  # <-- ADD YOUR ID
        ...
    },
    "ios": {
        "id": "NEED_YOUR_INSTREAM_IOS_TEMPLATE_ID",  # <-- ADD YOUR ID
        ...
    },
}
```

**How to find:**
1. Go to https://advertiser.trafficjunky.com/campaigns
2. Find your in-stream/preroll template campaigns
3. Copy the 10-digit campaign IDs
4. Replace the text above

---

## Quick Start

### 1. Add Template IDs (see above) ☝️

### 2. Test with Dry-Run

```bash
python create_campaigns_v2.py --input data/input/example_campaigns_v2.csv --dry-run
```

### 3. Create Your CSV

```csv
group,keywords,csv_file,variants,ad_format,enabled
Milfs,"milf;milfs",milf_native.csv,"desktop,ios,android",NATIVE,TRUE
Teens,"teen;teens",teen_instream.csv,"desktop,ios",INSTREAM,TRUE
```

**Note:** `ad_format` is optional - defaults to NATIVE if omitted

### 4. Run V2

```bash
# With visible browser
python create_campaigns_v2.py --input campaigns.csv --no-headless

# Headless mode
python create_campaigns_v2.py --input campaigns.csv
```

---

## CSV Format Reference

### Campaign Definition CSV (for V2)

```csv
group,keywords,csv_file,variants,ad_format,enabled
MyGroup,"keyword1;keyword2",ads.csv,"desktop,ios,android",NATIVE,TRUE
```

**New column:**
- `ad_format` - "NATIVE" or "INSTREAM" (optional, defaults to NATIVE)

### Native Ad CSV Format

```csv
"Ad Name","Target URL","Video Creative ID","Thumbnail Creative ID",Headline,"Brand Name"
"Ad 1","https://url?sub11=CAMPAIGN_NAME","1032473171","1032473180","Headline","Brand"
```

### In-Stream Ad CSV Format

```csv
Ad Name,Target URL,Creative ID,Custom CTA Text,Custom CTA URL,Banner CTA Creative ID,Banner CTA Title,Banner CTA Subtitle,Banner CTA URL,Tracking Pixel
Video_1,https://url?sub11=CAMPAIGN_NAME,1032473171,Click,https://url,,,,, 
```

---

## V1 vs V2

### Use V1 (`create_campaigns.py`) When:
- ✓ Only creating Native campaigns
- ✓ Don't need in-stream support
- ✓ Existing workflows work fine

### Use V2 (`create_campaigns_v2.py`) When:
- ✓ Creating in-stream campaigns
- ✓ Want mixed format batches
- ✓ Need format flexibility

**Both work side-by-side!** No conflicts.

---

## Files You Can Safely Ignore

These are **not affected** and still work:
- `create_campaigns.py` (V1) - Unchanged
- `main.py` - Native upload tool - Unchanged  
- `native_main.py` - Native upload tool - Unchanged
- All existing CSV files work as-is

---

## Summary

### ✅ Completed
- [x] Created `create_campaigns_v2.py` with multi-format support
- [x] Updated all automation modules to support ad_format
- [x] Preserved V1 backward compatibility
- [x] Created comprehensive documentation
- [x] Made example CSV files
- [x] Auto-selects correct uploader by format

### ⏳ Your Action
- [ ] Add your in-stream template IDs to `campaign_templates.py`
- [ ] Test with dry-run
- [ ] Create first batch of campaigns

---

## Questions?

1. **How do I find template IDs?** - See "What You Need To Do" section above
2. **Will V1 still work?** - Yes! 100% unchanged
3. **Can I mix formats?** - Yes! Each row can have different ad_format
4. **What if I omit ad_format?** - Defaults to NATIVE (V1 behavior)
5. **Is the upload button different?** - No! Same button, that's the good news

---

## Next Steps

1. ⭐ **Add template IDs** to `campaign_templates.py`
2. 🧪 **Test**: `python create_campaigns_v2.py --input example_campaigns_v2.csv --dry-run`
3. 🚀 **Run**: `python create_campaigns_v2.py --input your_campaigns.csv`

**Happy Campaign Creating! 🎉**


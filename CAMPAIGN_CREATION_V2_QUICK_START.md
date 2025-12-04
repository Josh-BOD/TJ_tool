# Campaign Creation Tool V2 - Quick Start

## Folder Structure

```
data/input/Campaign_Creation/     <- Campaign definition CSVs + Ad CSVs
data/output/Campaign_Creation/    <- Output logs and summaries
```

## Quick Start Guide

### Step 1: Add Your In-Stream Template IDs

Edit `src/campaign_templates.py` and find this section:

```python
"INSTREAM": {
    "desktop": {
        "id": "NEED_YOUR_INSTREAM_DESKTOP_TEMPLATE_ID",  # <-- Replace with your ID
        ...
    },
    "ios": {
        "id": "NEED_YOUR_INSTREAM_IOS_TEMPLATE_ID",  # <-- Replace with your ID
        ...
    },
}
```

**How to find your template IDs:**
1. Go to https://advertiser.trafficjunky.com/campaigns
2. Look for your in-stream/preroll template campaigns
3. The campaign ID is in the URL or campaign list
4. Copy the 10-digit ID

### Step 2: Create Your Campaign CSV

Use the example file as a template: `data/input/Campaign_Creation/example_campaigns.csv`

**Key Points:**
- Add `ad_format` column with value `NATIVE` or `INSTREAM`
- If omitted, defaults to `NATIVE`
- Each row can have a different format!

**Example:**
```csv
group,keywords,csv_file,variants,ad_format,enabled
Milfs-Native,"milf;milfs",native_ads.csv,"desktop,ios,android",NATIVE,TRUE
Cougars-InStream,"cougar",instream_ads.csv,"desktop,ios",INSTREAM,TRUE
```

### Step 3: Dry-Run Test

```bash
python create_campaigns_v2.py --input data/input/Campaign_Creation/example_campaigns.csv --dry-run
```

This will:
- ✓ Validate your CSV
- ✓ Show which campaigns will be created
- ✓ Display template IDs for each format
- ✓ Estimate time needed

### Step 4: Create Campaigns

```bash
python create_campaigns_v2.py --input data/input/Campaign_Creation/your_campaigns.csv --no-headless
```

**Flags:**
- `--no-headless` - See the browser (recommended for first run)
- `--verbose` - See detailed logs
- `--resume SESSION_ID` - Resume if interrupted

## CSV Format Per Ad Type

### For Native Campaigns (`ad_format: NATIVE`)

Your CSV file (e.g., `native_ads.csv`) should have:

```csv
"Ad Name","Target URL","Video Creative ID","Thumbnail Creative ID",Headline,"Brand Name"
"Ad 1","https://example.com?sub11=CAMPAIGN_NAME","1032473171","1032473180","Click Now","MyBrand"
```

### For In-Stream Campaigns (`ad_format: INSTREAM`)

Your CSV file (e.g., `instream_ads.csv`) should have:

```csv
Ad Name,Target URL,Creative ID,Custom CTA Text,Custom CTA URL,Banner CTA Creative ID,Banner CTA Title,Banner CTA Subtitle,Banner CTA URL,Tracking Pixel
Video_1,https://example.com?sub11=CAMPAIGN_NAME,1032473171,Click Here,https://example.com,,,,, 
```

## Complete Example

### 1. Campaign definition CSV:
```csv
group,keywords,csv_file,variants,ad_format,enabled
Milfs,"milf;milfs",milf_native.csv,"desktop,ios,android",NATIVE,TRUE
Teens,"teen;teens",teen_instream.csv,"desktop,ios",INSTREAM,TRUE
```

### 2. `milf_native.csv` (Native format):
```csv
"Ad Name","Target URL","Video Creative ID","Thumbnail Creative ID",Headline,"Brand Name"
"Milf Ad 1","https://clk.example.com?sub11=CAMPAIGN_NAME","1032473171","1032473180","Hot Milfs","Brand"
"Milf Ad 2","https://clk.example.com?sub11=CAMPAIGN_NAME","1032468251","1032468260","Mature Women","Brand"
```

### 3. `teen_instream.csv` (In-Stream format):
```csv
Ad Name,Target URL,Creative ID,Custom CTA Text,Custom CTA URL,Banner CTA Creative ID,Banner CTA Title,Banner CTA Subtitle,Banner CTA URL,Tracking Pixel
Teen_Video_1,https://clk.example.com?sub11=CAMPAIGN_NAME,1032473171,Click Here,https://clk.example.com,,,,, 
Teen_Video_2,https://clk.example.com?sub11=CAMPAIGN_NAME,1032468251,Watch Now,https://clk.example.com,,,,, 
```

### 4. Run:
```bash
python create_campaigns_v2.py --input data/input/Campaign_Creation/campaigns.csv
```

This creates:
- 3 Native campaigns (Milfs-Desktop, Milfs-iOS, Milfs-Android)
- 2 In-Stream campaigns (Teens-Desktop, Teens-iOS)

## Troubleshooting

### "NEED_YOUR_INSTREAM_DESKTOP_TEMPLATE_ID" Error
You forgot to add your in-stream template IDs. See Step 1.

### Wrong CSV Format Uploaded
Make sure:
- Native campaigns point to Native CSV files
- In-Stream campaigns point to In-Stream CSV files
- Check the `ad_format` column matches your CSV format

### Template Not Found
- Verify template campaign IDs are correct
- Check templates exist in TrafficJunky
- Ensure templates are NOT running (should be paused)

## Next Steps

1. ✓ Add template IDs to `campaign_templates.py`
2. ✓ Test with `--dry-run`
3. ✓ Run actual campaign creation
4. ✓ Monitor first few campaigns in browser
5. ✓ Let it run unattended once verified

## Still Using V1?

If you only need Native ads, you can continue using:
```bash
python create_campaigns.py --input campaigns.csv
```

V1 is still fully supported!


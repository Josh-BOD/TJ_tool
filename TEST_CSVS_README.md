# Test CSV Files Guide

## 📁 Test Files Created

### For IN-STREAM/PREROLL Videos (Use V2)

**Campaign Definition:**
- `data/input/test_instream_v2.csv` - Defines the campaign (use with V2)

**Ad Creatives:**
- `data/input/test_preroll_ads.csv` - Contains video ads

**Test Command:**
```bash
# Dry-run first
python create_campaigns_v2.py --input data/input/test_instream_v2.csv --dry-run

# Actual run
python create_campaigns_v2.py --input data/input/test_instream_v2.csv --no-headless
```

**Before running:**
1. ✅ Add your in-stream template IDs to `src/campaign_templates.py`
2. ✅ Replace `YOUR_CREATIVE_ID_1`, `YOUR_CREATIVE_ID_2` in `test_preroll_ads.csv`
3. ✅ Replace `YOUR_LINK` with your actual tracking URL

---

### For NATIVE Ads (Use V1)

**Campaign Definition:**
- `data/input/test_native_v1.csv` - Defines the campaign (use with V1)

**Ad Creatives:**
- `data/input/test_native_ads.csv` - Contains native ads

**Test Command:**
```bash
# Dry-run first
python create_campaigns.py --input data/input/test_native_v1.csv --dry-run

# Actual run  
python create_campaigns.py --input data/input/test_native_v1.csv --no-headless
```

**Before running:**
1. ✅ Replace `YOUR_VIDEO_CREATIVE_ID_1`, `YOUR_THUMBNAIL_CREATIVE_ID_1` etc. in `test_native_ads.csv`
2. ✅ Replace `YOUR_LINK` with your actual tracking URL
3. ✅ Replace `YourBrand` with your brand name

---

## 🎯 Which Script To Use?

### Use V1 (`create_campaigns.py`)
- ✅ Testing **Native ads**
- ✅ CSV: `test_native_v1.csv`
- ✅ Ads: `test_native_ads.csv`

### Use V2 (`create_campaigns_v2.py`)
- ✅ Testing **In-Stream/Preroll videos**
- ✅ CSV: `test_instream_v2.csv`
- ✅ Ads: `test_preroll_ads.csv`

---

## 📝 What to Replace

### In test_preroll_ads.csv (In-Stream)
```csv
Creative ID            → Already filled with example: 1032539101, 1032539111
                         (Replace with your own creative IDs if needed)
YOUR_LINK              → Your tracking domain (e.g., clk.ourdream.ai)
```

### In test_native_ads.csv (Native)
```csv
YOUR_VIDEO_CREATIVE_ID_1      → Your video creative ID
YOUR_THUMBNAIL_CREATIVE_ID_1  → Your thumbnail/image creative ID
YOUR_LINK                     → Your tracking domain
YourBrand                     → Your brand name
```

---

## 🧪 Test Flow

### Step 1: Choose Your Format

**Testing In-Stream (Preroll)?**
→ Use `test_instream_v2.csv` with **V2 script**

**Testing Native?**
→ Use `test_native_v1.csv` with **V1 script**

### Step 2: Update Creative IDs

Edit the appropriate ad CSV and replace placeholders.

### Step 3: Dry-Run

```bash
# For In-Stream
python create_campaigns_v2.py --input data/input/test_instream_v2.csv --dry-run

# For Native
python create_campaigns.py --input data/input/test_native_v1.csv --dry-run
```

### Step 4: Real Run

```bash
# For In-Stream
python create_campaigns_v2.py --input data/input/test_instream_v2.csv --no-headless

# For Native
python create_campaigns.py --input data/input/test_native_v1.csv --no-headless
```

---

## 📋 CSV Format Quick Reference

### In-Stream Ad CSV Format
```csv
Ad Name,Target URL,Creative ID,Custom CTA Text,Custom CTA URL,Banner CTA Creative ID,Banner CTA Title,Banner CTA Subtitle,Banner CTA URL,Tracking Pixel
```

### Native Ad CSV Format
```csv
"Ad Name","Target URL","Video Creative ID","Thumbnail Creative ID",Headline,"Brand Name"
```

---

## ⚠️ Common Issues

### "Template ID not found" (In-Stream)
**Solution:** Add your in-stream template IDs to `src/campaign_templates.py`

### "Invalid creative ID"
**Solution:** Replace `YOUR_CREATIVE_ID_X` with real TrafficJunky creative IDs

### CSV Format Error
**Solution:** Make sure you're using the right ad CSV format for your ad type:
- In-Stream → Use preroll format (no quotes on first row)
- Native → Use native format (quotes on all text fields)

---

## 💡 Pro Tips

1. **Start with 1 campaign** - Test with `desktop` only first
2. **Use --no-headless** - Watch the browser to catch issues
3. **Check dry-run output** - Verify template IDs are correct
4. **Keep test short** - Use 2-3 ads max for first test

---

## 🎉 Ready to Test!

Choose your format and run the appropriate command above!


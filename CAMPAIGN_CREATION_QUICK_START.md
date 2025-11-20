# Campaign Creation Tool - Quick Reference

## 🚀 Quick Start

```bash
# 1. Dry-run (validate)
python create_campaigns.py --input my_campaigns.csv --dry-run

# 2. Create campaigns
python create_campaigns.py --input my_campaigns.csv

# 3. Resume if interrupted
python create_campaigns.py --input my_campaigns.csv --resume SESSION_ID
```

## 📄 CSV Template

```csv
group,keywords,keyword_matches,geo,csv_file,target_cpa,per_source_budget,max_bid,frequency_cap,max_daily_budget,gender,variants,enabled
Milfs,milfs;milf porn;cougar,broad;exact;exact,US,Milfs.csv,55,100,11,1,275,male,"desktop,ios,android",true
```

### Required Columns
- `group` - Campaign group name
- `keywords` - Semicolon-separated (`milfs;milf porn;cougar`)
- `keyword_matches` - Match types (`broad;exact;exact`)
- `csv_file` - Ad CSV filename
- `variants` - Comma-separated (`desktop,ios,android`)
- `enabled` - `true` or `false`

### Optional Columns (leave blank for defaults)
- `geo` - Country codes (`US` or `US;CA;UK`)
- `target_cpa` - Default: 50
- `per_source_budget` - Default: 200
- `max_bid` - Default: 10
- `frequency_cap` - Default: 2
- `max_daily_budget` - Default: 250
- `gender` - `male`, `female`, or `all` (default: male)

## 🎯 Campaign Naming

Auto-generated: `{GEO}_{LANG}_{FORMAT}_{BIDTYPE}_{SOURCE}_KEY-{Keyword}_{DEVICE}_{GENDER}_{INITIALS}`

Examples:
- Desktop: `US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB`
- iOS: `US_EN_NATIVE_CPA_ALL_KEY-Milfs_iOS_M_JB`
- Android: `US_EN_NATIVE_CPA_ALL_KEY-Milfs_AND_M_JB`

## ⚡ Common Commands

```bash
# Visible browser (see what's happening)
python create_campaigns.py --input campaigns.csv --no-headless

# Verbose output
python create_campaigns.py --input campaigns.csv --verbose

# Custom CSV directory
python create_campaigns.py --input campaigns.csv --csv-dir /path/to/csvs/

# Custom session file
python create_campaigns.py --input campaigns.csv --session my_session.json

# Slower operations (for debugging)
python create_campaigns.py --input campaigns.csv --slow-mo 1000
```

## ⏱️ Time Estimates

Per campaign:
- **Desktop**: ~5 minutes
- **iOS**: ~5 minutes
- **Android**: ~3 minutes (faster - clones from iOS!)

Example: 3 campaign sets with all variants = 9 campaigns = ~41 minutes

## 🔄 Workflow Order

For each campaign set:
1. Desktop (if enabled) → Clone Desktop template
2. iOS (if enabled) → Clone iOS template
3. Android (if enabled) → Clone iOS campaign (not template!)

## ✅ Pre-Flight Checklist

Before running:
- [ ] CSV input file exists
- [ ] All ad CSV files exist in `data/input/`
- [ ] Session file exists (`session.json`)
- [ ] Required columns present
- [ ] Ran dry-run successfully
- [ ] Checked campaign names are unique

## 🐛 Troubleshooting

### Session File Missing
```bash
python main.py --create-session
```

### CSV Validation Errors
- Check all required columns exist
- Verify CSV files referenced exist
- Ensure keywords count matches match types count
- Use dry-run to see detailed errors

### Campaign Already Exists
- Check TrafficJunky for duplicate names
- Disable already-created campaigns in CSV
- Use `--resume` to skip completed ones

### Browser Timeout
- Use `--no-headless` to watch browser
- Increase `--slow-mo` value
- Check TrafficJunky UI hasn't changed

## 📊 Progress Output

```
[12:45:38] Creating DESKTOP campaign...
  ✓ Created: US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB (ID: 1234567890)
    Uploaded 5 ads | Elapsed: 4m 32s

[████████████░░░░░░░░] 3/9 (33.3%) | 13m 45s | ETA: 27m 30s
```

## 🔖 Template IDs (Hardcoded)

- **Desktop**: `1013076141`
- **iOS**: `1013076221`
- **Android**: Clones from iOS campaign

## 📁 File Structure

```
data/
├── input/
│   ├── my_campaigns.csv      # Campaign definitions
│   ├── Milfs.csv             # Ad CSVs
│   └── Cougars.csv
└── checkpoints/              # Auto-saved progress
```

## 💡 Tips

1. **Always dry-run first** - Catches 99% of issues
2. **Start small** - Test with 1-2 campaigns first
3. **Use visible mode** - `--no-headless` for debugging
4. **Monitor progress** - Watch for errors in real-time
5. **Save checkpoints** - Don't restart from scratch
6. **Android is faster** - Clones from iOS, not template

## 🆘 Quick Help

```bash
python create_campaigns.py --help
```

## 📚 Full Documentation

- **Complete Guide**: [CAMPAIGN_CREATION_README.md](CAMPAIGN_CREATION_README.md)
- **Workflow Details**: [docs/CAMPAIGN_CLONE_WORKFLOW.md](docs/CAMPAIGN_CLONE_WORKFLOW.md)
- **Implementation**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

---

**Remember:** Campaigns are created in PAUSED state (they auto-activate in TJ)


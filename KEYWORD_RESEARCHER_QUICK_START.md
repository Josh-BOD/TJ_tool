# Keyword Researcher - Quick Start Guide

Discover related keywords by searching TrafficJunky's keyword selector. Takes seed keywords from a CSV and outputs discovered keywords in the same format.

## Directory Structure

```
data/
├── input/
│   └── Keyword_Researcher/    # Put your seed keyword CSVs here
│       └── seeds.csv
├── output/
│   └── Keyword_Researcher/    # Discovered keywords saved here
│       └── discovered.csv
```

## Input CSV Format

Use the same format as `Niche-Findom_v2.csv`:

```csv
group,keywords,keyword_matches,gender,geo,multi_geo,csv_file,target_cpa,per_source_budget,max_bid,frequency_cap,max_daily_budget,variants,ios_version,android_version,ad_format,enabled
Milfs,stepmom,,all,US;CA,,stepmom.csv,50,100,10,2,100,"desktop, all mobile",>18.4,>11.0,Native,TRUE
Milfs,step mom,,all,US;CA,,stepmom.csv,50,100,10,2,100,"desktop, all mobile",>18.4,>11.0,Native,TRUE
```

The tool will:
1. Read all unique keywords from the `keywords` column
2. Search each in TJ's keyword selector
3. Capture all suggested keywords
4. Output in the same format (inheriting settings from seed row)

## Basic Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Run keyword research
python Keyword_Researcher.py \
    --input data/input/Keyword_Researcher/seeds.csv \
    --output data/output/Keyword_Researcher/discovered.csv
```

## Command Options

| Option | Description |
|--------|-------------|
| `--input` | Path to input CSV with seed keywords (required) |
| `--output` | Path to output CSV for discovered keywords (required) |
| `--screenshots` | Take screenshots during research |
| `--headless` | Run browser without visible window |
| `--include-originals` | Include original seed keywords in output |
| `--delay N` | Seconds between searches (default: 2.0) |
| `--simple-output PATH` | Also output simple CSV (keyword, source_seed) |

## Examples

### Basic Research

```bash
python Keyword_Researcher.py \
    --input data/input/Keyword_Researcher/stepmom_seeds.csv \
    --output data/output/Keyword_Researcher/stepmom_discovered.csv
```

### Include Original Seeds in Output

```bash
python Keyword_Researcher.py \
    --input data/input/Keyword_Researcher/seeds.csv \
    --output data/output/Keyword_Researcher/all_keywords.csv \
    --include-originals
```

### With Screenshots for Debugging

```bash
python Keyword_Researcher.py \
    --input data/input/Keyword_Researcher/seeds.csv \
    --output data/output/Keyword_Researcher/discovered.csv \
    --screenshots
```

### Also Output Simple List

```bash
python Keyword_Researcher.py \
    --input data/input/Keyword_Researcher/seeds.csv \
    --output data/output/Keyword_Researcher/discovered.csv \
    --simple-output data/output/Keyword_Researcher/keyword_list.csv
```

## Workflow

1. **Login** - Browser opens, solve reCAPTCHA if prompted
2. **Navigate** - Tool navigates to keyword selector in campaign creation
3. **Research** - For each seed keyword:
   - Types keyword into search
   - Waits for suggestions
   - Captures all suggested keywords
4. **Deduplicate** - Removes keywords already in input
5. **Export** - Writes to output CSV in same format

## Output Format

Output matches input format exactly. Discovered keywords:
- Inherit all settings from their seed keyword row (group, geo, target_cpa, etc.)
- Have `enabled` set to `FALSE` by default (so you can review before creating campaigns)

Example output:
```csv
group,keywords,keyword_matches,gender,geo,...,enabled
Milfs,stepmom creampie,,all,US;CA,...,FALSE
Milfs,hot stepmom,,all,US;CA,...,FALSE
Milfs,stepmom pov,,all,US;CA,...,FALSE
```

## Tips

1. **Start Small** - Test with 5-10 seed keywords first
2. **Review Output** - Discovered keywords have `enabled=FALSE` - review and enable ones you want
3. **Delay Setting** - Increase `--delay` if you get rate limited (default is 2 seconds)
4. **Screenshots** - Use `--screenshots` if you need to debug issues

## Troubleshooting

### "Login failed"
- Make sure TJ credentials are correct in `.env` file
- Browser window should appear - solve reCAPTCHA manually

### "Failed to navigate to keyword selector"
- TJ's UI may have changed
- Try running with `--screenshots` to see what's happening
- Check if you can manually navigate to campaign creation

### "No keyword suggestions found"
- Some keywords may not have suggestions in TJ
- This is normal - the tool will continue to next keyword

## Logs

Logs are saved to `logs/keyword_research_YYYYMMDD_HHMMSS.log`


# Keyword Researcher - Input Files

Place your seed keyword CSV files here.

## Format

Use the same format as `Niche-Findom_v2.csv`:

```csv
group,keywords,keyword_matches,gender,geo,multi_geo,csv_file,target_cpa,per_source_budget,max_bid,frequency_cap,max_daily_budget,variants,ios_version,android_version,ad_format,enabled
Milfs,stepmom,,all,US;CA,,stepmom.csv,50,100,10,2,100,"desktop, all mobile",>18.4,>11.0,Native,TRUE
```

## Example Files

- `example_seeds.csv` - Sample file to get started

## Usage

```bash
python Keyword_Researcher.py \
    --input data/input/Keyword_Researcher/your_file.csv \
    --output data/output/Keyword_Researcher/discovered.csv
```


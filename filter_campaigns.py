"""Quick script to filter out already processed campaigns"""
import pandas as pd

# Campaigns that were successfully processed (from the truncated output shown)
# These are the ones I saw in the output up to where it was interrupted
processed = [
    '1012924872', '1013050271', '1012915962', '1012951671', '1012916082',
    '1012811822', '1013046671', '1012750572', '1012866672', '1013040561',
    '1013028571', '1013046221', '1013046761', '1013054451', '1012750982',
    '1013025101', '1011813382', '1012811992', '1012811972', '1012924922',
    '1012812112', '1012854342', '1012927672', '1012927692', '1012905942',
    '1013050321', '1013024831', '1012866372', '1013046251', '1013013561',
    '1012711012', '1013013651', '1013013641', '1012915712'
]

# Read the CSV
df = pd.read_csv('data/input/Campaign_TrackerUpdate.csv')

# Filter out processed campaigns
df_remaining = df[~df['Campaign ID'].astype(str).isin(processed)]

# Save to CSV
df_remaining.to_csv('data/input/Campaign_TrackerUpdate.csv', index=False)

print(f"Removed {len(processed)} processed campaigns")
print(f"Remaining campaigns: {len(df_remaining)}")


# TrafficJunky Automation Tool 🚀

Automate bulk ad creative uploads to TrafficJunky campaigns using browser automation.

## 📌 Why This Tool?

TrafficJunky's API doesn't support uploading new ad creatives (only viewing and updating existing ones). This tool automates the manual process of:
1. Logging into TrafficJunky advertiser platform
2. Navigating to campaign ad settings
3. Uploading CSV files with ad specifications using the "Mass Create with CSV" feature

## ✨ Features

- ✅ **Automated Login** - Securely log into TrafficJunky
- ✅ **Bulk Upload** - Process multiple campaigns automatically
- ✅ **CSV Support** - Upload ad specifications from CSV files
- ✅ **Dry Run Mode** - Test without actually uploading
- ✅ **Smart Logging** - Track every action and error
- ✅ **Error Handling** - Retry failed uploads automatically
- ✅ **Screenshots** - Visual debugging at each step

## 🛠 Prerequisites

- Python 3.9 or higher
- TrafficJunky advertiser account
- Basic command line knowledge

## 📦 Installation

### 1. Clone the Repository

```bash
cd ~/Desktop/Dev/TJ_tool
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it (macOS/Linux)
source venv/bin/activate

# Activate it (Windows)
# venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browsers

```bash
playwright install chromium
```

### 5. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use any text editor
```

Update these values in `.env`:
```env
TJ_USERNAME=your_actual_username
TJ_PASSWORD=your_actual_password
CAMPAIGN_IDS=1013017411  # Your campaign ID(s)
DRY_RUN=True  # Keep True for testing
```

## 📋 Usage

### Quick Start (Dry Run)

```bash
# This will navigate through the process without uploading
python main.py
```

### Upload to Specific Campaign

```bash
# Make sure to set DRY_RUN=False in .env first!
python main.py --campaign 1013017411 --csv ./data/input/Gay.csv
```

### Multiple Campaigns

```bash
python main.py --campaigns 1013017411,1013017412,1013017413
```

### Advanced Options

```bash
# Run in headless mode (no browser window)
python main.py --headless

# Verbose logging
python main.py --verbose

# Custom log file
python main.py --log-file ./logs/custom_run.log

# Skip authentication (reuse session)
python main.py --skip-auth
```

## 📁 Project Structure

```
TJ_tool/
├── .env                    # Your credentials (DO NOT COMMIT)
├── .env.example           # Example environment file
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── main.py               # Entry point
│
├── Setup/
│   └── Plan.md           # Detailed project plan
│
├── config/
│   └── config.py         # Configuration loader
│
├── data/
│   ├── input/            # CSV files to upload
│   ├── output/           # Upload results
│   └── creatives/        # Creative files (if needed)
│
├── logs/                 # Log files
│
└── src/
    ├── auth.py          # Authentication logic
    ├── navigator.py     # Page navigation
    ├── uploader.py      # CSV upload logic
    ├── validator.py     # CSV validation
    └── utils.py         # Helper functions
```

## 📊 CSV Format

Your CSV must have these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `Ad Name` | Yes | Name of the ad |
| `Target URL` | Yes | Landing page URL |
| `Creative ID` | Yes | TrafficJunky creative ID |
| `Custom CTA Text` | No | Call-to-action text |
| `Custom CTA URL` | No | CTA destination URL |
| `Banner CTA Creative ID` | No | Banner CTA creative ID |
| `Banner CTA Title` | No | Banner title |
| `Banner CTA Subtitle` | No | Banner subtitle |
| `Banner CTA URL` | No | Banner URL |
| `Tracking Pixel` | No | Tracking pixel URL |

See `Example_docs/Gay.csv` for a complete example.

## 🔒 Security

- **NEVER commit `.env` file** - It contains your credentials
- Credentials are stored locally only
- No data is sent anywhere except TrafficJunky
- Session cookies are temporary and automatically cleared

## 🐛 Troubleshooting

### Login Fails
- Check credentials in `.env`
- Try logging in manually first
- Check for reCAPTCHA (may need manual intervention)

### Upload Not Working
- Ensure `DRY_RUN=False` in `.env`
- Check CSV format matches requirements
- Verify campaign ID exists and you have access

### Browser Won't Open
```bash
# Reinstall Playwright browsers
playwright install --force chromium
```

### Element Not Found Errors
- TrafficJunky may have updated their UI
- Check logs for specific element that failed
- May need to update selectors in code

## 📝 Logs

Logs are saved in `logs/` folder with timestamps:
- All actions taken
- Errors encountered
- Success/failure status
- Screenshots (if enabled)

## 🧪 Development Mode

Set these in `.env` for development:
```env
DRY_RUN=True
HEADLESS_MODE=False
TAKE_SCREENSHOTS=True
LOG_LEVEL=DEBUG
```

## 🤝 Contributing

This is a private tool, but improvements welcome:
1. Test thoroughly before changes
2. Document new features
3. Update Plan.md for major changes

## 📚 Documentation

- [Detailed Project Plan](Setup/Plan.md)
- [Playwright Docs](https://playwright.dev/python/)
- [TrafficJunky API](https://api.trafficjunky.com/api/documentation)

## ⚠️ Important Notes

1. **Creative IDs**: The CSV references Creative IDs, meaning creatives must already be uploaded to TrafficJunky
2. **Rate Limiting**: Add delays between uploads to avoid being flagged
3. **Testing**: Always test with dry run first on non-critical campaigns
4. **Backup**: Keep backup of original CSVs before modifications

## 🚀 Next Steps

1. ✅ Review [Setup/Plan.md](Setup/Plan.md) for detailed implementation plan
2. ⬜ Set up `.env` with your credentials
3. ⬜ Test login with dry run mode
4. ⬜ Upload test CSV to one campaign
5. ⬜ Scale to multiple campaigns

## 📞 Support

For issues or questions:
- Check logs in `logs/` folder
- Review [Plan.md](Setup/Plan.md) for detailed workflow
- Test with dry run mode first

---

**Version**: 1.0.0  
**Status**: In Development  
**Last Updated**: November 2, 2025


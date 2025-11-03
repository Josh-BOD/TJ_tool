#!/bin/bash
# TrafficJunky Automation Tool - Setup Script

echo "=================================="
echo "TJ Tool Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version

if [ $? -ne 0 ]; then
    echo "❌ Python 3 not found. Please install Python 3.9 or higher."
    exit 1
fi

echo "✓ Python found"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo "❌ Failed to create virtual environment"
    exit 1
fi

echo "✓ Virtual environment created"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✓ Dependencies installed"
echo ""

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Playwright browsers"
    exit 1
fi

echo "✓ Playwright browsers installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cat > .env << 'EOF'
# TrafficJunky Credentials
TJ_USERNAME=your_username_here
TJ_PASSWORD=your_password_here

# Campaigns are configured in data/input/campaign_mapping.csv
# No need to configure campaign IDs here

# File Paths
CSV_INPUT_DIR=./data/input
CSV_OUTPUT_DIR=./data/output
LOG_DIR=./logs
CREATIVE_DIR=./data/creatives

# Browser Settings
HEADLESS_MODE=False
BROWSER_TYPE=chromium
TIMEOUT=30000
SLOW_MO=500

# Automation Behavior
DRY_RUN=True
TAKE_SCREENSHOTS=True
MAX_RETRIES=3
RETRY_DELAY=5

# Logging
LOG_LEVEL=INFO
LOG_TO_FILE=True
LOG_TO_CONSOLE=True
EOF

    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file with your TrafficJunky credentials!"
    echo ""
else
    echo "✓ .env file already exists"
    echo ""
fi

echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your credentials:"
echo "   nano .env"
echo ""
echo "2. Update campaign_mapping.csv with your campaigns:"
echo "   nano data/input/campaign_mapping.csv"
echo ""
echo "3. Run a dry-run test:"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "4. When ready, run live:"
echo "   python main.py --live"
echo ""
echo "See README.md for more information."
echo ""


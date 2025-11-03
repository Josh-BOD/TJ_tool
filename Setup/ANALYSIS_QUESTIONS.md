# Campaign Performance Analysis & Reporting Questions 📊

These questions will help us build an automated tool that pulls data from TrafficJunky, analyzes campaign performance, and generates categorized reports for Slack Canvas.

---

## ❓ Critical Questions

### 1. Data Source & API Capabilities ⚠️ **MOST IMPORTANT**

**Question**: How should we pull campaign performance data from TrafficJunky?

- [ ] **Option A**: TrafficJunky Reporting API
  - Use `/reporting/campaigns` endpoint
  - Pull structured data (spend, conversions, impressions, etc.)
  - Clean, reliable, fast
  - **Need to verify**: Does TJ API have reporting endpoints?

- [ ] **Option B**: Web Dashboard Scraping
  - Navigate to reporting section in browser
  - Extract data from tables/charts
  - More fragile, but works if API is limited
  - Can reuse existing Playwright authentication

- [ ] **Option C**: Manual CSV Export + Analysis
  - You export data from TJ manually
  - Tool analyzes the CSV and generates report
  - Simplest, no API/scraping needed
  - Less automated

**Why This Matters**:
- Option A: Fastest and most reliable if API supports it
- Option B: Fully automated but requires more maintenance
- Option C: Simple but requires manual data export step

**Please confirm**: Which option is feasible? (Check TJ API docs first)

---

### 2. Metrics to Track

**Question**: Which performance metrics do we need to pull and analyze?

**Core Metrics** (check all that apply):
- [ ] Spend (total cost)
- [ ] Conversions (total conversions)
- [ ] eCPA (cost per acquisition)
- [ ] Impressions
- [ ] Clicks
- [ ] CTR (click-through rate)
- [ ] CVR (conversion rate)
- [ ] Revenue (if tracked)
- [ ] ROAS (return on ad spend)

**Calculated Metrics**:
- [ ] eCPA = Spend / Conversions
- [ ] CTR = Clicks / Impressions
- [ ] CVR = Conversions / Clicks
- [ ] ROAS = Revenue / Spend

**Other Metrics** (specify):
```
[List any other metrics you track]




```

---

### 3. Time Period for Analysis

**Question**: What time period should the report cover?

- [ ] **Today** (last 24 hours)
  - Most recent performance
  - Daily check-in reports

- [ ] **Yesterday** (previous full day)
  - Complete day's data
  - Common for daily reports

- [ ] **Last 7 Days** (weekly view)
  - Trend analysis
  - Better for statistical significance

- [ ] **Last 30 Days** (monthly view)
  - Long-term trends
  - Campaign lifecycle analysis

- [ ] **Custom Date Range**
  - Flexible date selection
  - Specify: From _________ to _________

- [ ] **Multiple Time Periods**
  - Compare periods (e.g., today vs yesterday)
  - Show trend direction (↑ ↓)

**Default Period**: _________________

**Can user override**: [ ] Yes [ ] No

---

### 4. Campaign Categorization Rules 🎯

**Question**: How should campaigns be automatically categorized?

#### **Category: "What to do more of" 🟢**

**Rule**: Campaigns performing well that should be scaled

**Criteria** (fill in your thresholds):
- eCPA < $_________ 
- Conversions > _________
- Spend > $_________ (minimum spend to qualify)
- AND/OR: _________________________________________

**Example**: eCPA < $50 AND Conversions > 5

---

#### **Category: "To Watch" 🟡**

**Rule**: Campaigns that need monitoring (borderline performance)

**Criteria**:
- eCPA between $_________ and $_________
- Conversions between _________ and _________
- Spend > $_________
- AND/OR: _________________________________________

**Example**: eCPA between $100-$200 AND Conversions > 2

---

#### **Category: "Scaled" 📈**

**Rule**: Campaigns where budget was recently increased

**Criteria**:
- Budget increased in last _________ days
- OR: Spend increased by _________% compared to previous period
- AND: eCPA < $_________

**How to detect budget changes**:
- [ ] Track budget changes in database
- [ ] Compare spend period-over-period
- [ ] Manual tagging in campaign name
- [ ] Other: _________________________________________

---

#### **Category: "Killed" ❌**

**Rule**: Campaigns that were paused/stopped due to poor performance

**Criteria**:
- eCPA > $_________
- OR: Zero conversions after $_________ spend
- OR: Campaign status = "Paused" in TJ
- AND: Paused in last _________ days

**How to identify killed campaigns**:
- [ ] Check campaign status in TJ
- [ ] Track status changes over time
- [ ] Manual list of killed campaigns
- [ ] Other: _________________________________________

---

#### **Category: "Launched" 🚀**

**Rule**: New campaigns recently created

**Criteria**:
- Campaign created in last _________ days
- OR: First spend date within last _________ days
- Spend > $_________  (minimum to show activity)

**How to identify launch date**:
- [ ] Campaign creation date from TJ API
- [ ] First spend date in reporting data
- [ ] Manual tracking
- [ ] Other: _________________________________________

---

#### **Category: "WIP" 🔧**

**Rule**: Campaigns being actively worked on

**Criteria**:
- [ ] Manual list/tagging
- [ ] Campaign name contains "TEST", "WIP", etc.
- [ ] Recent creative uploads (last _________ days)
- [ ] Other: _________________________________________

**Please specify**: _________________________________________

---

### 5. Minimum Thresholds for Inclusion

**Question**: Should campaigns be excluded from the report if they don't meet certain minimums?

**Minimum Spend**:
- [ ] No minimum, show all campaigns
- [ ] Only show campaigns with spend > $_________

**Minimum Data**:
- [ ] Only show campaigns with at least _________ impressions
- [ ] Only show campaigns with at least _________ days of data

**Campaign Status**:
- [ ] Only active campaigns
- [ ] Active + paused campaigns
- [ ] All campaigns (including archived)

**Why This Matters**: Prevents noise from test campaigns or campaigns with insufficient data.

---

### 6. Report Output Format

**Question**: How should the report be formatted and delivered?

#### **Output Format**:
- [ ] Markdown for Slack Canvas (like the example you provided)
- [ ] CSV file
- [ ] JSON file
- [ ] HTML report
- [ ] Multiple formats (specify): _________________________________________

#### **Report Structure**:

**Do you want**:
- [ ] Campaign name only
- [ ] Campaign name + key metrics (eCPA, conversions, spend)
- [ ] Campaign name + all metrics
- [ ] Campaign name + URL to TJ dashboard

**Example Line** (specify your preference):
```
US_EN_PREROLL_CPA_PH_KEY-Blowjob_DESK_M_JB - eCPA: $45.32 | Conv: 12 | Spend: $543.84

OR

US_EN_PREROLL_CPA_PH_KEY-Blowjob_DESK_M_JB

OR

[US_EN_PREROLL_CPA_PH_KEY-Blowjob_DESK_M_JB](https://advertiser.trafficjunky.com/campaign/overview/1013022481) - eCPA: $45.32

```

**Your preference**: _________________________________________

---

#### **Sorting Within Categories**:

**How should campaigns be sorted in each section?**
- [ ] By eCPA (lowest first)
- [ ] By conversions (highest first)
- [ ] By spend (highest first)
- [ ] Alphabetically
- [ ] Other: _________________________________________

---

#### **Additional Sections**:

**Do you want these sections in the report?**
- [ ] Summary stats (total spend, total conversions, average eCPA)
- [ ] Trends vs previous period (↑↓ indicators)
- [ ] Recommendations (auto-generated suggestions)
- [ ] Budget utilization (% of budget spent)
- [ ] Other: _________________________________________

---

### 7. File Saving & Distribution

**Question**: Where should reports be saved and how should they be distributed?

#### **Save Location**:
- [ ] `data/reports/report_YYYY-MM-DD.md`
- [ ] `data/reports/daily/report_YYYY-MM-DD.md`
- [ ] `reports/` folder in project root
- [ ] Other: _________________________________________

#### **File Naming**:
- [ ] `report_2025-11-03.md`
- [ ] `performance_report_2025-11-03.md`
- [ ] `tj_analysis_2025-11-03.md`
- [ ] Other: _________________________________________

#### **Distribution**:
- [ ] **Manual**: Generate file, I copy to Slack Canvas manually
- [ ] **Clipboard**: Copy report to clipboard automatically
- [ ] **Slack Webhook**: Auto-post to Slack channel
- [ ] **Email**: Send via email
- [ ] **Multiple**: Save file + auto-post to Slack

**If Slack Integration**:
- Slack Webhook URL: _______________________________ (will store in .env)
- Channel: _________________________________________
- Notification style: [ ] Full report [ ] Summary with link

---

### 8. Automation & Scheduling

**Question**: How should the analysis tool run?

- [ ] **Manual**: Run command when I want a report
  - Example: `python analyze.py`

- [ ] **Scheduled**: Run automatically at specific times
  - Daily at _________ AM/PM
  - Multiple times: _________________________________________

- [ ] **Triggered**: Run when certain conditions are met
  - After creative upload completes
  - When spend threshold is reached
  - Other: _________________________________________

**Operating System** (for scheduling):
- [ ] macOS (use launchd or cron)
- [ ] Linux (use cron)
- [ ] Windows (use Task Scheduler)
- [ ] Cloud (use AWS Lambda, etc.)

---

### 9. Historical Data & Trend Analysis

**Question**: Should we track data over time to show trends?

- [ ] **No**: Just current period snapshot
  - Simple, report shows current state only

- [ ] **Yes**: Track historical data
  - Store data in database/CSV
  - Show trends (eCPA improving/worsening)
  - Compare to previous periods
  - Requires: Database setup (SQLite, PostgreSQL, or CSV files)

**If Yes**:
- Storage method: [ ] SQLite [ ] CSV files [ ] PostgreSQL [ ] Other: _________
- Compare to: [ ] Previous day [ ] Previous week [ ] Same day last week
- Show trend indicators: [ ] ↑↓ arrows [ ] Percentage change [ ] Both

---

### 10. Authentication & Session

**Question**: How should the tool authenticate with TrafficJunky?

- [ ] **Use existing session**: Reuse saved session from upload tool
  - Fast, no re-login needed
  - Works if both tools use same auth module

- [ ] **Separate login**: Independent authentication
  - More isolated, but requires login

- [ ] **API Key**: If TJ provides API keys
  - Store in `.env`
  - No browser automation needed

**Preferred**: _________________________________________

---

### 11. Error Handling & Alerts

**Question**: What should happen if the analysis fails?

**If data pull fails**:
- [ ] Send error notification (email/Slack)
- [ ] Log error and exit silently
- [ ] Retry _________ times with _________ second delay
- [ ] Use cached data if available

**If categorization rules have no campaigns**:
- [ ] Show empty section: "What to do more of: None"
- [ ] Hide empty sections
- [ ] Show message: "No campaigns meet criteria"

**Alert on specific conditions**:
- [ ] Alert if ANY campaign has eCPA > $_________
- [ ] Alert if total spend > $_________
- [ ] Alert if zero conversions across all campaigns
- [ ] Other: _________________________________________

---

### 12. Campaign Filtering

**Question**: Should certain campaigns be excluded from analysis?

**Exclude campaigns with**:
- [ ] Campaign name contains: _________________________________________ (e.g., "TEST", "PAUSE", "OLD")
- [ ] Campaign status = _________________________________________
- [ ] Campaign type = _________________________________________
- [ ] Zero spend
- [ ] Created before _________ (date)

**Include only campaigns with**:
- [ ] Campaign name contains: _________________________________________
- [ ] Specific campaign IDs (use campaign_mapping.csv?)
- [ ] All campaigns (no filter)

---

## 📊 Report Format Example

**Based on your sample**, the report format is:

```markdown
# Campaign Performance Report - [Date]

## What to do more of 🟢
- Campaign_Name_1
- Campaign_Name_2

## To Watch 🟡
- Campaign_Name_3

## Scaled 📈
- Campaign_Name_4

## Killed ❌
- Campaign_Name_5

## Launched 🚀
- Campaign_Name_6

## WIP 🔧
- Campaign_Name_7
```

**Is this the exact format you want?**
- [ ] Yes, exactly like this
- [ ] Similar, but add metrics per campaign
- [ ] Different format (describe below)

**Changes needed**:
```
[Describe any changes to the format]




```

---

## 🔍 Data Structure Questions

### Campaign Data Fields

**What data fields are available from TrafficJunky?**

Please review the TJ API documentation or export a sample report and list available fields:

**Available Fields**:
```
[List fields from TJ API or report export]
Example:
- campaign_id
- campaign_name
- spend
- impressions
- clicks
- conversions
- etc.




```

**Upload sample TJ report**: _________________________________________

---

### Data Accuracy

**Question**: What date/time range should "today" mean?

- [ ] Midnight to midnight (00:00 - 23:59) in timezone: _________
- [ ] Last 24 hours from now
- [ ] Current day so far (00:00 to now)

**Timezone**:
- [ ] UTC
- [ ] Local timezone (specify): _________
- [ ] TJ account timezone

---

## 🎯 Feature Priorities

**Which features are most important for the analysis tool?**

Rank 1-7 (1 = most important):

- [ ] ___ Accurate categorization (correct thresholds)
- [ ] ___ Fast execution (< 1 minute)
- [ ] ___ Slack integration (auto-post)
- [ ] ___ Historical tracking (trends over time)
- [ ] ___ Error alerts (notify on issues)
- [ ] ___ Flexible filters (include/exclude campaigns)
- [ ] ___ Custom metrics (define your own rules)

---

## 🔧 Technical Preferences

### Programming Language

- [ ] Python (same as upload tool)
- [ ] TypeScript/Node.js
- [ ] Other: _________________________________________

### Dependencies

**Are you okay with**:
- [ ] Using pandas for data analysis
- [ ] Using requests/playwright for data fetching
- [ ] Using database (SQLite) for historical tracking
- [ ] Installing additional packages

---

## 📝 Sample Data Needed

**To build and test the tool, please provide**:

- [ ] Sample TJ API response (JSON)
- [ ] Sample TJ report export (CSV/Excel)
- [ ] Sample campaign data for testing
- [ ] Screenshots of TJ reporting dashboard
- [ ] Example of "perfect" generated report

**Upload sample data**: _________________________________________

---

## 💡 Additional Requirements

**Any other requirements or features you want?**

```
[Your notes here]







```

---

## 🚦 Next Steps After Questions Answered

Once you've answered these questions, we will:

1. **Verify TJ API capabilities** for reporting data
2. **Design database schema** (if tracking historical data)
3. **Build data fetching module** (API or scraping)
4. **Implement categorization logic** with your thresholds
5. **Create report generator** with your format
6. **Add Slack integration** (if requested)
7. **Set up scheduling** (if requested)
8. **Test with real data** and refine thresholds

---

## 📋 Action Items

**Please**:
1. ⬜ Read through all questions above
2. ⬜ Check the boxes for your answers
3. ⬜ Fill in specific thresholds and values
4. ⬜ Provide sample data if possible
5. ⬜ Save this file

**Once answered**, we can build the analysis tool to match your exact workflow! 🚀

---

## 🔗 Related Documentation

- `Plan.md` - Original project plan for creative upload tool
- `QUESTIONS_TO_ANSWER.md` - Questions for upload automation
- `IMPLEMENTATION_PLAN.md` - Technical implementation for uploads
- `TECHNICAL_SPECS.md` - TrafficJunky UI selectors and patterns

---

**Thank you!** Your answers will help us build a powerful analysis tool that saves you hours of manual reporting work. 📊✨


# TrafficJunky API Analysis - Findings

Based on analysis of the [TrafficJunky API Documentation](https://api.trafficjunky.com/api/documentation), here are my findings for building the campaign performance analysis tool.

---

## ✅ API Supports Reporting!

**Primary Endpoint**: `GET /api/campaigns/bids/stats.{format}`

**Documentation**: https://api.trafficjunky.com/api/documentation#/Campaign/ad8f8be01d0748fa6d26e6a635b54ed5

---

## 📊 Available Data Fields

### Fields Provided by API:

```json
{
  "campaignId": 0,
  "campaignName": "string",
  "campaignType": "string",
  "dailyBudget": 0,
  "dailyBudgetLeft": 0,
  "status": "string",
  "clicks": 0,
  "impressions": "string",
  "CTR": 0,
  "CPM": 0,
  "cost": 0,
  "conversions": 0,
  "adsPaused": 0,
  "numberOfCreative": 0,
  "spots": [...]
}
```

### Mapping to Required Metrics:

| Your Requirement | API Field | Notes |
|---|---|---|
| ✅ Spend | `cost` | Direct from API |
| ✅ Conversions | `conversions` | Direct from API |
| ✅ Clicks | `clicks` | Direct from API |
| ✅ Impressions | `impressions` | Direct from API |
| ✅ CTR | `CTR` | Direct from API |
| ✅ Daily Budget | `dailyBudget` | **Perfect for budget velocity!** |
| ✅ Budget Remaining | `dailyBudgetLeft` | Can also use this |
| ✅ Campaign Status | `status` | For filtering active campaigns |
| ⚠️ CVR | *Not provided* | **Calculate**: `conversions / clicks` |
| ⚠️ eCPA | *Not provided* | **Calculate**: `cost / conversions` |
| ❌ Revenue | *Not provided* | Not available in API |
| ❌ ROAS | *Not provided* | Not available (requires revenue) |

---

## 🔧 API Parameters

### Authentication:
- **api_key** (query parameter) - Store in `.env`

### Date Range:
- **startDate** (DD/MM/YYYY) - Defaults to -30 days
- **endDate** (DD/MM/YYYY) - Defaults to today

### Pagination:
- **limit** (integer) - Default: 10 (we'll increase to 500+)
- **offset** (integer) - Default: 1

### Format:
- **format** (path) - Use `json`

---

## 🎯 Budget Velocity Calculation

**Your Requirement**: `Budget Velocity = (Daily Spend / Daily Budget) * 100%`

**API Provides**:
- `dailyBudget` - Total daily budget
- `cost` - Total spend in date range
- `dailyBudgetLeft` - Remaining budget

**Calculation Options**:

### Option 1: Using cost (if querying single day)
```python
budget_velocity = (cost / dailyBudget) * 100
```

### Option 2: Using dailyBudgetLeft
```python
daily_spend = dailyBudget - dailyBudgetLeft
budget_velocity = (daily_spend / dailyBudget) * 100
```

**Recommendation**: Use Option 2 (`dailyBudgetLeft`) for current day analysis.

---

## 🚨 Missing Metrics: Revenue & ROAS

**Problem**: API doesn't provide `revenue` field.

**Solutions**:

### Option A: Manual Revenue Tracking (Recommended for V1)
- Skip ROAS for now
- Focus on eCPA and conversions
- Add revenue tracking in V2

### Option B: External Revenue Data
- Pull revenue from your conversion tracking system
- Match by campaign_id
- Calculate ROAS = revenue / cost

### Option C: User Input
- Allow manual revenue input per campaign
- Store in CSV or database

**Your Decision Needed**: Which option do you prefer?

---

## 🔐 Authentication Setup

### To Get API Key:
1. Log into TrafficJunky dashboard
2. Click on your profile name
3. Scroll to "API Token" section
4. Click "Generate New Token" if needed
5. Copy token to `.env` file

```bash
# .env
TJ_API_KEY=your_api_key_here
```

---

## 📋 Implementation Plan Summary

### What We'll Build:

1. **API Client Module** (`src/api_client.py`)
   - Authenticate with API key
   - Fetch data from `/api/campaigns/bids/stats.json`
   - Handle date range conversions (EST timezone)
   - Parse JSON responses

2. **Data Processor** (`src/data_processor.py`)
   - Calculate derived metrics (eCPA, CVR)
   - Calculate budget velocity
   - Filter campaigns by your criteria

3. **Report Generator** (`src/report_generator.py`)
   - Categorize campaigns (What to do more of, To Watch, etc.)
   - Format as Markdown
   - Generate report with links to TJ dashboard

4. **Main Script** (`analyze.py`)
   - CLI interface
   - Select time period (today, yesterday, last 7 days)
   - Save to `data/reports/`

---

## 🎨 Example API Call

```bash
GET https://api.trafficjunky.com/api/campaigns/bids/stats.json?api_key=YOUR_KEY&startDate=03/11/2025&endDate=03/11/2025&limit=500
```

**Response** (per campaign):
```json
{
  "campaignId": 1013022481,
  "campaignName": "US_EN_PREROLL_CPA_PH_KEY-Blowjob_DESK_M_JB_AUTOTEST",
  "dailyBudget": 1000,
  "dailyBudgetLeft": 250,
  "cost": 750,
  "conversions": 15,
  "clicks": 450,
  "impressions": "45000",
  "CTR": 1.0,
  "CPM": 16.67,
  "status": "active"
}
```

**Calculated**:
- eCPA = 750 / 15 = **$50.00**
- CVR = 15 / 450 = **3.33%**
- Budget Velocity = (750 / 1000) * 100 = **75%**

**Categorization**: **🟡 To Watch** (eCPA = $50 is at your threshold, velocity is 75% which is in your 70-90% range)

---

## 🚀 Next Steps

1. **Add API key to `.env`**
2. **Test API call** (verify you can pull data)
3. **Build modules** (api_client, data_processor, report_generator)
4. **Test with real data**
5. **Refine thresholds** based on actual results

---

## ❓ Decisions Needed

### 1. Revenue/ROAS
How should we handle missing revenue data?
- [ ] Skip for V1, add later
- [ ] Pull from external source (specify where)
- [ ] Manual input
- [ ] Other: _______________

### 2. Campaign Creation Date
For "Launched" category, do you have access to campaign creation dates?
- [ ] Yes, will be in API response
- [ ] No, need to track manually
- [ ] Check API for me

### 3. All Active Campaigns or Filtered?
Should we pull ALL campaigns or only from `campaign_mapping.csv`?
- [ ] All active campaigns
- [ ] Only campaigns in campaign_mapping.csv
- [ ] Other: _______________

---

**Ready to start building once you answer the 3 questions above!** 🎯


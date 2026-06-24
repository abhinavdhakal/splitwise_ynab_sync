# GitHub Actions Cost Analysis

## GitHub Actions Pricing Overview

GitHub Actions is **free** for public repositories with unlimited minutes.

For **private repositories**, GitHub provides:

- **2,000 free minutes/month** for personal accounts
- **3,000 free minutes/month** for teams/organizations
- **$0.008/minute** for additional usage on Linux runners

## Sync Runtime Analysis

Based on typical API response times and processing:

- **Estimated runtime per sync**: ~30-60 seconds
- **Actual usage**: Usually 1-2 minutes including setup/teardown

## Cost Calculations

### Current Setup (Every 12 Hours)

```
Daily runs: 2 times
Monthly runs: 2 × 30 = 60 runs
Monthly minutes: 60 × 2 = 120 minutes

Cost: FREE (well within free tier)
```

### Hourly Alternative (Every Hour)

```
Daily runs: 24 times
Monthly runs: 24 × 30 = 720 runs
Monthly minutes: 720 × 2 = 1,440 minutes

For Personal Account:
- Free tier: 2,000 minutes
- Used: 1,440 minutes
- Cost: FREE (within free tier)

For Team/Organization:
- Free tier: 3,000 minutes
- Used: 1,440 minutes
- Cost: FREE (within free tier)
```

### Half-Hourly (Every 30 Minutes) - Not Recommended

```
Daily runs: 48 times
Monthly runs: 48 × 30 = 1,440 runs
Monthly minutes: 1,440 × 2 = 2,880 minutes

For Personal Account:
- Free tier: 2,000 minutes
- Overage: 880 minutes
- Cost: 880 × $0.008 = $7.04/month

For Team/Organization:
- Free tier: 3,000 minutes
- Used: 2,880 minutes
- Cost: FREE (barely within free tier)
```

## Recommendations

### ✅ **Recommended: Every 12 Hours (Current)**

- **Cost**: Always FREE
- **Frequency**: Adequate for expense tracking
- **Benefits**:
  - Zero cost
  - Reasonable sync frequency
  - Minimal API usage
  - Good for expense tracking workflow

### ⚠️ **Acceptable: Every Hour**

- **Cost**: FREE for most users
- **Frequency**: More responsive
- **Considerations**:
  - Still within free tier limits
  - Higher API usage (may approach rate limits)
  - More frequent notifications if issues occur
  - Good if you need near real-time syncing

### ❌ **Not Recommended: Every 30 Minutes or Less**

- **Cost**: May exceed free tier ($7+/month)
- **Issues**:
  - Risk of hitting API rate limits
  - Splitwise expenses don't change that frequently
  - Unnecessary overhead
  - May trigger abuse detection

## API Rate Limit Considerations

### Splitwise API Limits

- **Rate limit**: Not clearly documented, but conservative usage recommended
- **Best practice**: No more than 1 request per minute sustained

### YNAB API Limits

- **Rate limit**: 200 requests per hour per token
- **Current usage**: ~3-5 requests per sync
- **Hourly sync impact**: ~72-120 requests/day (well within limits)

## Optimal Configurations by Use Case

### 🏠 **Personal Expense Tracking** (Recommended)

```yaml
# Every 12 hours - perfect balance
schedule:
  - cron: "0 6,18 * * *" # 6 AM and 6 PM UTC
```

**Why**: Expenses don't change frequently, 12 hours is responsive enough.

### 💼 **Business/Team Usage**

```yaml
# Every 6 hours - more responsive
schedule:
  - cron: "0 */6 * * *" # Every 6 hours
```

**Why**: More frequent updates for team coordination, still free.

### 🚀 **Power User/Real-time Needs**

```yaml
# Every hour - maximum free frequency
schedule:
  - cron: "0 * * * *" # Every hour
```

**Why**: Near real-time updates, maxes out free tier but stays free.

## Cost Monitoring

### How to Check Usage

1. Go to GitHub **Settings** → **Billing and plans**
2. Click **Usage this month**
3. Check **Actions** section for minute usage

### Set Up Spending Limits

1. Go to **Billing and plans** → **Spending limits**
2. Set monthly limit (e.g., $5) to prevent overages
3. Enable email notifications for 75% usage

## Alternative Approaches

### Hybrid Approach

```yaml
# Frequent during business hours, less frequent otherwise
schedule:
  - cron: "0 8-17 * * 1-5" # Every hour, business hours, weekdays
  - cron: "0 6,18 * * 0,6" # Twice daily on weekends
```

### Event-Driven (Advanced)

- Use webhook triggers from Splitwise (if available)
- Manual triggers when needed
- Cost: Nearly zero

## Summary

**For most users, the current 12-hour schedule is optimal:**

- ✅ **Always FREE**
- ✅ **Adequate frequency** for expense tracking
- ✅ **Conservative API usage**
- ✅ **Reliable and sustainable**

**Hourly syncing is acceptable but not necessary:**

- ⚠️ **Still FREE** for most accounts
- ⚠️ **Higher resource usage**
- ⚠️ **Diminishing returns** (expenses don't change that often)

**More frequent than hourly is not recommended** due to cost and API concerns.

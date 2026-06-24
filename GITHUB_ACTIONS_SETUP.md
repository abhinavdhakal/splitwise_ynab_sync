# GitHub Actions Setup Guide

This guide helps you set up automated Splitwise-YNAB syncing using GitHub Actions.

## Required GitHub Secrets

You need to configure these secrets in your GitHub repository:

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add each of the following:

### Required Secrets

| Secret Name         | Description                            | Example                         |
| ------------------- | -------------------------------------- | ------------------------------- |
| `SPLITWISE_API_KEY` | Your Splitwise API key                 | `abc123...`                     |
| `YNAB_TOKEN`        | Your YNAB Personal Access Token        | `def456...`                     |
| `YNAB_BUDGET_NAME`  | Name of your YNAB budget               | `My Budget 2025` or `last-used` |
| `YNAB_ACCOUNT_NAME` | Name of your Splitwise account in YNAB | `Splitwise`                     |

### How to Get API Keys

#### Splitwise API Key

1. Log into [Splitwise](https://secure.splitwise.com/)
2. Go to **Account Settings** → **Apps** → **Register your application**
3. Create a new application and get your Consumer Key
4. Follow the OAuth flow or use the API key directly

#### YNAB Personal Access Token

1. Log into [YNAB](https://app.youneedabudget.com/)
2. Go to **Account Settings** → **Developer Settings**
3. Click **New Token** and generate a Personal Access Token
4. Copy the token (you won't see it again!)

## Workflow Features

### Automatic Scheduling

- Runs **every 12 hours** at 6 AM and 6 PM UTC
- Syncs the last 15 days of expenses by default

### Manual Trigger

- Go to **Actions** tab in your GitHub repository
- Select **Splitwise YNAB Sync** workflow
- Click **Run workflow**
- Optionally specify number of days to sync (default: 15)

### Error Handling

- Uploads log files if sync fails
- Logs are retained for 7 days
- Check the Actions tab for detailed error information

## Local Development vs GitHub Actions

### Local Development (Continuous Mode)

```bash
# Run continuously, checking every 15 minutes
python splitwise_ynab_sync.py

# Run continuously with custom settings
SYNC_DAYS=30 python splitwise_ynab_sync.py
```

### Single Run Mode (GitHub Actions)

```bash
# Run once and exit (CI/CD friendly)
python splitwise_ynab_sync.py --once

# Run once with custom days
python splitwise_ynab_sync.py --once --days 30
```

## Customizing the Schedule

To change the sync frequency, edit `.github/workflows/sync.yml`:

```yaml
# Every hour
- cron: "0 * * * *"

# Every 6 hours
- cron: "0 */6 * * *"

# Every 12 hours (current setting)
- cron: "0 6,18 * * *"

# Daily at 6 AM UTC
- cron: "0 6 * * *"
```

## Troubleshooting

### Check Action Logs

1. Go to **Actions** tab
2. Click on the failed run
3. Expand the **Run Splitwise YNAB Sync** step
4. Check for error messages

### Common Issues

- **Invalid API keys**: Double-check your secrets
- **Budget/Account not found**: Verify the exact names in YNAB
- **Rate limiting**: Reduce sync frequency if you hit API limits

### Download Log Files

If sync fails, log files are automatically uploaded as artifacts:

1. Go to the failed action run
2. Scroll to **Artifacts** section
3. Download **sync-logs**

## Security Notes

- Never commit API keys to your repository
- Use GitHub Secrets for all sensitive information
- Review workflow runs regularly
- Revoke and regenerate keys if compromised

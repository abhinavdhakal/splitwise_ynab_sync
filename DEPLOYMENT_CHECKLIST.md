# Deployment Checklist for GitHub Actions

This guide walks you through deploying the Splitwise-YNAB Sync to GitHub Actions for free automated syncing.

## Pre-Deployment Steps

### 1. Ensure Repository is on GitHub

- [ ] Push your code to GitHub: `git push origin main`
- [ ] Verify the repository is public or private (doesn't matter for Actions on private repos)
- [ ] Repository should be at: `https://github.com/YOUR_USERNAME/Splitwise-YNAB-Sync`

### 2. Gather Your API Credentials

Before setting up GitHub Secrets, collect these:

#### Splitwise API Key
1. Log into [Splitwise](https://secure.splitwise.com/)
2. Click your profile → **Account Settings**
3. Go to **Apps** section
4. Click **Register your application**
5. Fill in the form (you can use any name)
6. You'll get a **Consumer Key** — copy this
7. Save it in a safe place (you'll need it in step 3 below)

#### YNAB Personal Access Token
1. Log into [YNAB](https://app.youneedabudget.com/)
2. Go to **Account Settings** (click your profile icon)
3. Click **Developer** in the left sidebar
4. Click **New Token**
5. Give it a name (e.g., "GitHub Automation")
6. Copy the entire token immediately (you won't see it again!)
7. Save it in a safe place

## GitHub Actions Setup

### 3. Add Repository Secrets

GitHub Secrets securely store your credentials so they're never exposed in logs.

**Steps:**

1. Go to your GitHub repository
2. Click **Settings** (top navigation)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Add each secret with the exact names below:

| Secret Name | Value |
|---|---|
| `SPLITWISE_API_KEY` | Your Splitwise Consumer Key from step 2 |
| `YNAB_TOKEN` | Your YNAB Personal Access Token from step 2 |
| `YNAB_BUDGET_NAME` | Name of your YNAB budget (e.g., `My Budget 2025` or use `last-used`) |
| `YNAB_ACCOUNT_NAME` | The YNAB account name for Splitwise (default: `Splitwise`) |

**How to add each secret:**
- Click "New repository secret"
- Name: (from table above)
- Secret: (your value)
- Click "Add secret"
- Repeat for all 4 secrets

### 4. Verify Workflow File Exists

The workflow file should already exist at [`.github/workflows/sync.yml`](.github/workflows/sync.yml)

**Check it's properly configured:**
- [ ] File exists at `.github/workflows/sync.yml`
- [ ] Scheduled to run at **6 AM and 6 PM UTC** (every 12 hours, free tier limit)
- [ ] Has `--once` flag for single-run mode (GitHub Actions friendly)

### 5. Enable GitHub Actions (if needed)

1. Go to your repository
2. Click **Actions** tab
3. If you see a message to enable Actions, click the button to enable
4. If a workflow is already listed, Actions is enabled ✓

## Testing Your Setup

### 6. Manually Trigger the Workflow

Once secrets are configured, test it:

1. Go to your GitHub repository
2. Click **Actions** tab (top navigation)
3. Click **Splitwise YNAB Sync** in the left sidebar
4. Click **Run workflow**
5. Select **Branch: main** (or your default branch)
6. Click **Run workflow** button
7. Wait for it to complete (should take 1-2 minutes)

**Check the results:**
- ✓ Green checkmark = Success! Sync completed
- ✗ Red X = Failed. Click to view logs and troubleshoot

### 7. Check Automatic Scheduling

After manual test succeeds:

1. In GitHub, go to **Actions** → **Splitwise YNAB Sync**
2. You should see your manual run
3. The next automatic run will happen at:
   - **6 AM UTC** (or 6:00 AM Coordinated Universal Time)
   - **6 PM UTC** (or 6:00 PM Coordinated Universal Time)
4. Roughly 12 hours apart, every day ✓

## Schedule Details (Free Tier)

| Aspect | Details |
|--------|---------|
| **Frequency** | Every 12 hours (6 AM & 6 PM UTC) |
| **Free Tier Limit** | Unlimited for public repos, ~2,000 minutes/month for private repos |
| **Your Usage** | ~2 minutes per run × 60 runs/month = ~120 minutes/month ♻️ |
| **Cost** | **FREE** |

### Customizing the Schedule

If you want to change the frequency, edit [`.github/workflows/sync.yml`](.github/workflows/sync.yml):

```yaml
schedule:
  # Uncomment ONE of these patterns:
  
  # Every hour
  - cron: "0 * * * *"
  
  # Every 6 hours (current default)
  - cron: "0 */6 * * *"
  
  # Every 12 hours at 6 AM and 6 PM UTC (current setting)
  - cron: "0 6,18 * * *"
  
  # Daily at 6 AM UTC (most conservative)
  - cron: "0 6 * * *"
```

After editing, save and push to GitHub.

## Troubleshooting

### Workflow Failed

1. Go to **Actions** → **Splitwise YNAB Sync** → click the failed run
2. Scroll down and read the error message
3. Common issues:
   - **"Missing required environment variables"** → Check GitHub Secrets are set correctly
   - **API errors** → Verify API keys are correct and haven't expired
   - **Account/Budget not found** → Check category/account names match exactly in YNAB

### No Automatic Runs

1. Verify Actions is enabled (step 5 above)
2. Check workflow file is in `main` branch
3. Wait up to 5 minutes for GitHub to pick up changes
4. Manually trigger once to verify setup works

### Logs Not Visible

1. Logs only appear if the sync fails
2. On success, minimal output is shown
3. To see more details, add `LOG_LEVEL: DEBUG` to the workflow env section

## Final Verification Checklist

- [ ] All 4 GitHub Secrets added
- [ ] Workflow file exists at `.github/workflows/sync.yml`
- [ ] GitHub Actions enabled
- [ ] Manual trigger test passed
- [ ] No errors in the Actions logs
- [ ] Ready for automatic 12-hourly syncing!

## Next Steps

1. **After first manual run succeeds:** Your YNAB budget should show new Splitwise transactions (or confirmation that nothing needed syncing)
2. **Monitor the schedule:** Check GitHub Actions every few days to confirm automatic runs are happening
3. **Adjust frequency if needed:** Change the cron schedule in `.github/workflows/sync.yml` if needed

## Support

If you encounter issues:
1. Check `.github/workflows/sync.yml` is properly formatted YAML
2. Verify all GitHub Secrets exist with correct names
3. Try a manual workflow trigger to see detailed error messages
4. Check that your YNAB budget/account/category names match exactly (case-sensitive)

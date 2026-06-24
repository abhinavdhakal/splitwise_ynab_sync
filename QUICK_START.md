# Quick Start: Deploy Splitwise-YNAB Sync to GitHub Actions

## TL;DR - 5 minute setup

1. **Get API credentials:**
   - Splitwise: https://secure.splitwise.com → Account Settings → Apps → Consumer Key
   - YNAB: https://app.youneedabudget.com → Settings → Developer → New Token

2. **Add GitHub Secrets:**
   - Go to GitHub repo → Settings → Secrets and variables → Actions → New secret
   - Add 4 secrets:
     ```
     SPLITWISE_API_KEY = [your splitwise key]
     YNAB_TOKEN = [your ynab token]
     YNAB_BUDGET_NAME = last-used (or your budget name)
     YNAB_ACCOUNT_NAME = Splitwise
     ```

3. **Test it:**
   - GitHub repo → Actions → Splitwise YNAB Sync → Run workflow

4. **Done!** 
   - Runs automatically every 12 hours (6 AM & 6 PM UTC)
   - Completely free
   - Check logs in Actions tab

---

## What You Get

✅ **Automatic syncing** every 12 hours  
✅ **100% free** (GitHub's free tier)  
✅ **No server needed**  
✅ **Manual trigger anytime** via Actions tab  
✅ **Error logs stored** for 7 days  

---

## Where Things Are

| File | Purpose |
|------|---------|
| [`.github/workflows/sync.yml`](.github/workflows/sync.yml) | The automation workflow |
| [`GITHUB_ACTIONS_SETUP.md`](GITHUB_ACTIONS_SETUP.md) | Full setup guide |
| [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md) | Step-by-step checklist |

---

## How to Change the Schedule

Edit [`.github/workflows/sync.yml`](.github/workflows/sync.yml):

```yaml
schedule:
  # Change this line. Examples:
  - cron: "0 * * * *"       # Every hour
  - cron: "0 */4 * * *"     # Every 4 hours
  - cron: "0 */6 * * *"     # Every 6 hours  
  - cron: "0 6,18 * * *"    # 6 AM & 6 PM UTC (current)
  - cron: "0 6 * * *"       # Daily at 6 AM UTC
```

Then push to GitHub.

---

## Troubleshooting

**Workflow won't run?**
- Check Actions is enabled (Settings → Actions)
- Verify all 4 secrets are added
- Try manual trigger first

**Sync errors?**
- Check workflow logs in Actions tab
- Verify API keys are correct
- Ensure YNAB account and category names match exactly

**No transactions synced?**
- Sync by default looks at last 15 days
- To sync more: edit workflow to custom days
- Or use manual trigger with custom days

---

For detailed setup, see [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md).

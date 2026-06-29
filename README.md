# Splitwise → YNAB Sync

Syncs your Splitwise expenses into a YNAB tracking account automatically via GitHub Actions. No server needed.

**What it imports:**
- Expenses others paid for you (you owe them) → outflow in your Splitwise YNAB account
- Expenses you paid for others → inflow (others owe you)
- Settlements / payments → recorded as they happen

Duplicate detection is built-in — running it multiple times won't create extra transactions.

---

## GitHub Actions Setup

### 1. Fork or clone this repo to your GitHub account

### 2. Get your API keys

**Splitwise:**
1. Go to https://secure.splitwise.com/apps
2. Click "Register your application" (name it anything, e.g. "YNAB Sync")
3. Copy the **Consumer Key** — this is your `SW_API_KEY`

**YNAB:**
1. Go to https://app.youneedabudget.com/settings/developer
2. Click "New Personal Access Token"
3. Copy the token — this is your `YNAB_TOKEN`

### 3. Set up YNAB

In your YNAB budget:
- Create a **tracking account** named `Splitwise` (or whatever you'll set in `YNAB_SW_ACCOUNT`)
- Create a **category** named `Splitwise` (or whatever you'll set in `YNAB_SW_CATEGORY`)

### 4. Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

Add these secrets:

| Secret | Value |
|---|---|
| `SW_API_KEY` | Your Splitwise Consumer Key |
| `YNAB_TOKEN` | Your YNAB Personal Access Token |
| `YNAB_BUDGET` | Your budget name exactly as it appears in YNAB (e.g. `Abhinav's Plan`) |
| `YNAB_SW_ACCOUNT` | The tracking account name in YNAB (e.g. `Splitwise`) |
| `YNAB_SW_CATEGORY` | The category name in YNAB (e.g. `Splitwise`) |
| `USER_NAME` | Your first name (appears in transaction memos) |
| `LOG_LEVEL` | `INFO` — shows stats without personal data (use `DEBUG` locally, `WARNING` for silent) |

### 5. Enable Actions and run

1. Go to the **Actions** tab in your repo and enable workflows if prompted
2. Click **Splitwise YNAB Sync** → **Run workflow** to do a manual first run
3. After that, it runs automatically once a day at 6 AM UTC

To change the schedule, edit `.github/workflows/sync.yml` and update the `cron` line.

---

## GitHub Actions cost

Each sync run takes roughly 30–60 seconds. GitHub's free tier gives you **2,000 minutes/month** on public repos and **500 minutes/month** on private repos.

| | Public repo | Private repo |
|---|---|---|
| Minutes used/month | ~1 min/day × 30 = **~30 min** | same |
| Free tier limit | 2,000 min | 500 min |
| % of free tier used | ~1.5% | ~6% |

**Bottom line: essentially free.** You'd have to run it ~65× per day on a private repo before hitting the limit. At once a day you'll never come close.

---

## Running locally

```bash
pip install -r requirements.txt
```

Create a `.env` file:
```env
SW_API_KEY=your_splitwise_api_key
YNAB_TOKEN=your_ynab_token
YNAB_BUDGET=Your Budget Name
YNAB_SW_ACCOUNT=Splitwise
YNAB_SW_CATEGORY=Splitwise
USER_NAME=YourName
SYNC_DAYS=15
```

Then run:
```bash
python main.py --once            # run once
python main.py --once --days 30  # sync last 30 days
python main.py                   # run continuously (every 15 min)
```

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `SW_API_KEY` | required | Splitwise API key |
| `YNAB_TOKEN` | required | YNAB Personal Access Token |
| `YNAB_BUDGET` | `last-used` | YNAB budget name |
| `YNAB_SW_ACCOUNT` | `Splitwise` | YNAB tracking account name |
| `YNAB_SW_CATEGORY` | `Splitwise` | YNAB category for expenses |
| `USER_NAME` | `you` | Your name (used in memos) |
| `SYNC_DAYS` | `15` | Days back to look for expenses |
| `POLL_INTERVAL` | `15` | Minutes between syncs (continuous mode) |
| `LOG_LEVEL` | `INFO` | Logging verbosity: `INFO` shows counts/stats only, `DEBUG` shows full detail (names, memos), `WARNING` shows errors only |
| `ALLOW_DUPLICATES` | `false` | Set to `true` only if you've manually deleted transactions and need to re-import |

### Log level guide

| Level | What you see | Good for |
|---|---|---|
| `WARNING` | Errors only | Fully silent unless something breaks |
| `INFO` | Count/type summaries, no personal data | GitHub Actions (public repos) |
| `DEBUG` | Full detail — names, memos, amounts | Local troubleshooting |

Set `LOG_LEVEL` as a GitHub secret to `INFO` to get useful stats in your Actions logs without exposing transaction details.

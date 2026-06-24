# Splitwise-YNAB Sync Tool

A Python tool that automatically syncs money you owe or are owed from Splitwise into your YNAB budget. This helps you track shared expenses and settlements without double-counting transactions.

## How This Tool Works

### The Problem This Solves

When you use Splitwise to track shared expenses, you end up with two types of transactions:
1. **Money you spent** (already tracked in your bank/credit card)
2. **Money owed between you and friends** (tracked in Splitwise)

The challenge is getting the "money owed" part into YNAB without messing up your budget.

### Your Workflow With This Tool

#### Scenario 1: Someone Pays For You
1. **Your friend pays** for dinner and adds it to Splitwise
2. **You categorize** your share in your normal YNAB categories (Food, etc.)
3. **This tool adds** a transaction to your "Splitwise" account showing you owe your friend money
4. **When you pay them back** (via Venmo, cash, etc.), the tool records that payment and it cancels out

#### Scenario 2: You Pay For Others
1. **You pay** for dinner with your credit card
2. **You split** the credit card transaction in YNAB:
   - Your share → appropriate category (Food, etc.)
   - Others' share → "Split for Others" category
3. **You add** the expense to Splitwise
4. **This tool adds** a transaction showing others owe you money (goes to "Split for Others")
5. **The two "Split for Others" transactions cancel out** (your credit card split + Splitwise entry = $0)
6. **When friends pay you back**, that money goes from your Splitwise account to your real bank account

### Important: Virtual vs Real Money

The Splitwise account in YNAB is **virtual money** - it tracks IOUs, not real cash. Only when money actually moves between you and friends (settlements) does it affect your real accounts.

## Features

- **Smart Transaction Types**: Only tracks what you actually need to budget for
- **No Double-Counting**: Designed to work with your existing credit card splitting workflow  
- **Automatic Settlements**: Records when you pay friends back or they pay you
- **Real-time Sync**: Continuously monitors for new Splitwise activity

## Setup Options

### 🤖 Automated Setup (Recommended) - GitHub Actions

For hands-off automation that runs in the cloud:
- **No server needed** - runs on GitHub's infrastructure
- **Automatic syncing** every 12 hours
- **Manual triggers** when needed
- **Always FREE** for most users

👉 **[Follow the GitHub Actions Setup Guide](GITHUB_ACTIONS_SETUP.md)**

### 🖥️ Local Setup

For running on your own computer:

#### What You'll Need

- Python 3.7+
- A Splitwise account and API key
- YNAB account with Personal Access Token
- Two YNAB categories:
  - **"Splitwise"** - for settlements and IOUs
  - **"Split for Others"** - for money others owe you when you pay

### Step-by-Step Setup

1. **Clone and install:**
   ```bash
   git clone <repository-url>
   cd Splitwise-YNAB-Integration
   pip install -r requirements.txt
   ```

2. **Set up your YNAB accounts:**
   - Create a tracking account called "Splitwise" 
   - Create categories "Splitwise" and "Split for Others"

3. **Get your API keys:**
   - **Splitwise**: Go to https://secure.splitwise.com/apps → Register app → Copy Consumer Key
   - **YNAB**: Go to https://app.youneedabudget.com/settings/developer → Generate token

4. **Create your `.env` file:**
   ```env
   # Required API Keys  
   SW_API_KEY=your_splitwise_api_key_here
   YNAB_TOKEN=your_ynab_personal_access_token_here

   # YNAB Settings
   YNAB_BUDGET=last-used
   YNAB_SW_ACCOUNT=Splitwise  
   YNAB_SW_CATEGORY=Splitwise

   # Your Settings
   USER_NAME=Your Name
   SYNC_DAYS=7
   POLL_INTERVAL=15
   ```

### Running the Tool

```bash
python splitwise_ynab_sync.py
```

The tool runs continuously, checking Splitwise every 15 minutes for new expenses or settlements.

## Configuration Options

| Variable           | Default     | Description                                     |
| ------------------ | ----------- | ----------------------------------------------- |
| `SW_API_KEY`       | Required    | Your Splitwise API key                          |
| `YNAB_TOKEN`       | Required    | Your YNAB Personal Access Token                 |
| `YNAB_BUDGET`      | `last-used` | Name of your YNAB budget                        |
| `YNAB_SW_ACCOUNT`  | `Splitwise` | Name of your Splitwise tracking account         |
| `YNAB_SW_CATEGORY` | `Splitwise` | Category for settlements and IOUs               |
| `USER_NAME`        | `you`       | Your name (appears in transaction memos)        |
| `SYNC_DAYS`        | `7`         | How many days back to check for expenses        |
| `POLL_INTERVAL`    | `15`        | Minutes between sync checks                     |

## Troubleshooting

### Common Issues

**"My Split for Others category doesn't zero out"**
- Make sure you're splitting your credit card transactions correctly
- Check that the amounts match between your manual split and Splitwise

**"I'm seeing duplicate transactions"**  
- The tool prevents duplicates automatically
- If you see them, check your import_id settings

**"Settlements aren't showing up"**
- Make sure you're using Splitwise's "Settle up" feature
- Manual payments outside Splitwise won't be tracked

### Money Flow Example

Here's a complete example of how money flows:

1. **You pay $40 for dinner, split with friend ($20 each)**
2. **In YNAB manually split your credit card transaction:**
   - $20 → Food category  
   - $20 → Split for Others category
3. **Add expense to Splitwise** 
4. **This tool creates:** +$20 inflow to Splitwise account (uncategorized)
5. **You assign** that +$20 to "Split for Others" 
6. **Result:** Split for Others = $20 - $20 = $0 ✓
7. **When friend pays you back:** Tool records settlement, money moves from Splitwise to your real account

## Contributing

This project helps bridge the gap between Splitwise's expense tracking and YNAB's budgeting. Feel free to submit issues or improvements!

## Project Structure

```
├── splitwise_ynab_sync.py     # Main sync application
├── config.py                  # Configuration and environment handling  
├── api_client.py              # Splitwise and YNAB API clients
├── transaction_processor.py   # Logic for converting expenses to transactions
├── requirements.txt           # Python dependencies
└── .env                       # Your configuration (create this file)
```

### Transaction Types

This tool creates three types of transactions in your Splitwise YNAB account:

1. **When You Pay For Others**
   - Creates an **inflow** transaction for the amount others owe you
   - Memo: "Dinner at restaurant, paid by you ($50.00), others owe me 25.00"
   - Left uncategorized so it goes to "Split for Others" and cancels your credit card split

2. **When Others Pay For You**  
   - Creates an **inflow** transaction for the amount you owe them
   - Memo: "Groceries, paid by Sarah, you owe 15.50"
   - Left uncategorized for you to assign to appropriate categories

3. **When You Settle Up**
   - Creates an **outflow** transaction when you pay someone back
   - Memo: "Settlement to John (25.00)"
   - Automatically categorized to your Splitwise category

## API Key Setup Details

### Getting Your Splitwise API Key

1. Visit https://secure.splitwise.com/apps
2. Click "Register your application"
3. Fill out the form (name can be anything like "YNAB Sync")
4. Copy your **Consumer Key** - this is your `SW_API_KEY`

### Getting Your YNAB Token

1. Go to https://app.youneedabudget.com/settings/developer
2. Click "New Personal Access Token"
3. Give it a name like "Splitwise Sync"
4. Copy the token - this is your `YNAB_TOKEN`

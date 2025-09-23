# Splitwise-YNAB Sync Tool

A Python application that automatically synchronizes Splitwise expenses with your YNAB (You Need A Budget) account. This tool monitors your Splitwise expenses and creates corresponding transactions in YNAB, handling split payments, repayments, and regular expenses intelligently.

## Features

- **Automatic Sync**: Continuously monitors Splitwise for new expenses
- **Smart Transaction Processing**: Handles different expense types:
  - Split payments (when you pay and need to track others' shares)
  - Repayments/settlements between users
  - Regular expenses (when others pay and you owe)
- **Duplicate Prevention**: Avoids creating duplicate transactions
- **Flexible Configuration**: Customizable sync intervals, date ranges, and account mappings
- **Robust Error Handling**: Comprehensive logging and error recovery

## Setup

### Prerequisites

- Python 3.7 or higher
- Splitwise API key
- YNAB Personal Access Token
- A dedicated Splitwise account in YNAB
- A Splitwise category in YNAB (for categorizing shared expenses)

### Installation

1. Clone this repository:

   ```bash
   git clone <repository-url>
   cd Splitwise-YNAB-Integration
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your configuration:

   ```env
   # Required API Keys
   SW_API_KEY=your_splitwise_api_key_here
   YNAB_TOKEN=your_ynab_personal_access_token_here

   # YNAB Configuration
   YNAB_BUDGET=last-used
   YNAB_SW_ACCOUNT=Splitwise
   YNAB_SW_CATEGORY=Splitwise

   # Sync Settings
   USER_NAME=your_name
   SYNC_DAYS=7
   POLL_INTERVAL=15
   ALLOW_DUPLICATES=false

   # Logging
   LOG_LEVEL=INFO
   ```

### Configuration Options

| Variable           | Default     | Description                                     |
| ------------------ | ----------- | ----------------------------------------------- |
| `SW_API_KEY`       | Required    | Your Splitwise API key                          |
| `YNAB_TOKEN`       | Required    | Your YNAB Personal Access Token                 |
| `YNAB_BUDGET`      | `last-used` | Name of your YNAB budget or 'last-used'         |
| `YNAB_SW_ACCOUNT`  | `Splitwise` | Name of your Splitwise tracking account in YNAB |
| `YNAB_SW_CATEGORY` | `Splitwise` | Category for shared expenses                    |
| `USER_NAME`        | `you`       | Your name for transaction memos                 |
| `SYNC_DAYS`        | `7`         | How many days back to check for expenses        |
| `POLL_INTERVAL`    | `15`        | Minutes between sync cycles                     |
| `ALLOW_DUPLICATES` | `false`     | Whether to allow duplicate transactions         |
| `LOG_LEVEL`        | `INFO`      | Logging level (DEBUG, INFO, WARNING, ERROR)     |

## Usage

### Running the Sync Tool

```bash
python splitwise_ynab_sync.py
```

The tool will:

1. Connect to both Splitwise and YNAB APIs
2. Fetch recent expenses from Splitwise
3. Check for existing transactions in YNAB to avoid duplicates
4. Process and create new transactions as needed
5. Sleep for the configured interval and repeat

### Transaction Types

The tool creates different transaction types based on the Splitwise expense:

1. **Split Payments**: When you pay for an expense that's shared with others

   - Creates a split transaction with your share (outflow) and others' shares (inflow)
   - Others' shares are categorized to your Splitwise category

2. **Repayments**: When you pay someone back or settle up

   - Creates an outflow transaction categorized to your Splitwise category

3. **Regular Expenses**: When someone else pays and you owe money
   - Creates an inflow transaction (uncategorized for you to assign)

## API Keys Setup

### Splitwise API Key

1. Go to https://secure.splitwise.com/apps
2. Register a new application
3. Copy your Consumer Key (API Key)

### YNAB Personal Access Token

1. Go to https://app.youneedabudget.com/settings/developer
2. Generate a new Personal Access Token
3. Copy the token

## Project Structure

```
├── splitwise_ynab_sync.py     # Main application entry point
├── config.py                  # Configuration management
├── api_client.py              # API client classes for Splitwise and YNAB
├── transaction_processor.py   # Expense processing logic
├── requirements.txt           # Python dependencies
└── .env                       # Environment configuration (create this)
```

## Contributing

This project was refactored for improved maintainability and clarity. Feel free to submit issues or pull requests for enhancements.

## License

This project is open source. Please check the license file for more details.

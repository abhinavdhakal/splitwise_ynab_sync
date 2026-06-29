"""
Splitwise → YNAB Sync
Entry point. Run with: python main.py --once
"""

import datetime
import time
import sys
import argparse
from typing import List

from config import Config
from api import SplitwiseAPI, YNABAPI, APIError
from processor import TransactionProcessor


class SplitYNABSync:
    """Main synchronization application."""

    def __init__(self):
        Config.validate()
        self.logger = Config.setup_logging()

        self.splitwise = SplitwiseAPI(Config.SW_API_KEY)
        self.ynab = YNABAPI(Config.YNAB_TOKEN)

        self.logger.info("Initializing account information...")
        try:
            self.splitwise_user_id = self.splitwise.get_current_user_id()
            self.budget_id = self.ynab.get_budget_id(Config.YNAB_BUDGET)
            self.account_id = self.ynab.get_account_id(self.budget_id, Config.YNAB_SW_ACCOUNT)
            self.category_id = self.ynab.get_category_id(self.budget_id, Config.YNAB_SW_CATEGORY)
        except APIError as e:
            self.logger.error(f"Failed to initialize: {e}")
            sys.exit(1)

        self.processor = TransactionProcessor(
            self.splitwise_user_id,
            Config.USER_NAME,
            Config.ALLOW_DUPLICATES
        )
        self.logger.info("Initialized successfully")

    def run(self, single_run=False):
        """Run once or continuously on a loop."""
        if single_run:
            self.logger.info("Running single sync...")
            try:
                self.sync_once()
                self.logger.info("Sync completed successfully")
            except Exception as e:
                self.logger.error(f"Sync failed: {e}", exc_info=True)
                sys.exit(1)
        else:
            self.logger.info("Starting continuous sync loop...")
            while True:
                try:
                    self.sync_once()
                    self.logger.info(f"Sleeping for {Config.POLL_INTERVAL} minutes...")
                    time.sleep(Config.POLL_INTERVAL * 60)
                except KeyboardInterrupt:
                    self.logger.info("Sync interrupted by user")
                    break
                except Exception as e:
                    self.logger.error(f"Sync error: {e}", exc_info=True)
                    self.logger.info(f"Retrying in {Config.POLL_INTERVAL} minutes...")
                    time.sleep(Config.POLL_INTERVAL * 60)

    def sync_once(self):
        """Perform a single sync operation."""
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=Config.SYNC_DAYS)
        self.logger.info(f"Syncing last {Config.SYNC_DAYS} days (from {cutoff_date.strftime('%Y-%m-%d')})")

        splitwise_data = self.splitwise.get_recent_expenses(cutoff_date)

        # Fetch all existing transactions to check for duplicates (not just recent ones,
        # because users may have categorized/moved them)
        all_ynab_transactions = self.ynab.get_all_account_transactions(self.budget_id, self.account_id)
        existing_import_ids = [tx['import_id'] for tx in all_ynab_transactions if tx.get('import_id')]

        self.logger.debug(f"Found {len(existing_import_ids)} existing import IDs in YNAB")

        new_transactions = self.processor.process_expenses(
            splitwise_data.get('expenses', []),
            existing_import_ids
        )

        if new_transactions:
            self.logger.debug(f"New import IDs: {[tx.get('import_id') for tx in new_transactions]}")

        self._finalize_transactions(new_transactions)

        if new_transactions:
            result = self.ynab.create_transactions(self.budget_id, new_transactions)
            created_count = result["created"]
            duplicate_ids = result["duplicates"]

            if created_count > 0:
                self.logger.info(f"✓ Created {created_count} new transaction(s)")

            if duplicate_ids:
                duplicate_descriptions = []
                for dup_id in duplicate_ids:
                    expense_id = dup_id.split('_')[0]
                    for expense in splitwise_data.get('expenses', []):
                        if str(expense['id']) == expense_id:
                            duplicate_descriptions.append(expense['description'])
                            break
                self.logger.info(
                    f"⚠ Skipped {len(duplicate_ids)} duplicate(s): "
                    + ", ".join(duplicate_descriptions[:3])
                    + (f" and {len(duplicate_descriptions) - 3} more" if len(duplicate_descriptions) > 3 else "")
                )

            if created_count == 0 and not duplicate_ids:
                self.logger.info("No new transactions to create")
        else:
            self.logger.info("No new transactions to create")

    def _finalize_transactions(self, transactions: List[dict]):
        """Attach account and category IDs to each transaction."""
        for transaction in transactions:
            transaction['account_id'] = self.account_id
            if transaction['amount'] < 0:  # Outflow — categorize automatically
                transaction['category_id'] = self.category_id
            # Inflows are left uncategorized so the user can assign them


def main():
    parser = argparse.ArgumentParser(description='Sync Splitwise expenses to YNAB')
    parser.add_argument('--once', action='store_true', help='Run once and exit (used by GitHub Actions)')
    parser.add_argument('--days', type=int, help=f'Days to sync (default: {Config.SYNC_DAYS})')
    args = parser.parse_args()

    if args.days:
        Config.SYNC_DAYS = args.days

    try:
        sync_app = SplitYNABSync()
        sync_app.run(single_run=args.once)
    except Exception as e:
        logger = Config.setup_logging()
        logger.error(f"Failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

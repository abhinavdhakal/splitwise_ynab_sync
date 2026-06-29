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

        self.logger.info("Connecting to Splitwise and YNAB...")
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
        self.logger.info("Connected successfully")

    def run(self, single_run=False):
        """Run once or continuously on a loop."""
        if single_run:
            try:
                self.sync_once()
            except Exception as e:
                self.logger.error(f"Sync failed: {e}", exc_info=True)
                sys.exit(1)
        else:
            self.logger.info("Starting continuous sync loop...")
            while True:
                try:
                    self.sync_once()
                    self.logger.info(f"Sleeping {Config.POLL_INTERVAL} min until next sync...")
                    time.sleep(Config.POLL_INTERVAL * 60)
                except KeyboardInterrupt:
                    self.logger.info("Sync stopped")
                    break
                except Exception as e:
                    self.logger.error(f"Sync error: {e}", exc_info=True)
                    time.sleep(Config.POLL_INTERVAL * 60)

    def sync_once(self):
        """Perform a single sync operation."""
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=Config.SYNC_DAYS)
        self.logger.info(f"Checking Splitwise for the last {Config.SYNC_DAYS} days (since {cutoff_date.strftime('%Y-%m-%d')})")

        splitwise_data = self.splitwise.get_recent_expenses(cutoff_date)
        expenses = splitwise_data.get('expenses', [])

        all_ynab_transactions = self.ynab.get_all_account_transactions(self.budget_id, self.account_id)
        existing_import_ids = [tx['import_id'] for tx in all_ynab_transactions if tx.get('import_id')]

        new_transactions, stats = self.processor.process_expenses(expenses, existing_import_ids)

        # Log a privacy-safe summary
        active = stats["total"] - stats["deleted"]
        total_new = sum(stats["new"].values())
        total_dup = sum(stats["duplicate"].values())

        self.logger.info(
            f"Fetched {stats['total']} expenses"
            + (f" ({stats['deleted']} deleted/ignored)" if stats["deleted"] else "")
        )

        if total_dup:
            parts = [f"{v} {k}" for k, v in stats["duplicate"].items() if v]
            self.logger.info(f"Already in YNAB: {total_dup} ({', '.join(parts)})")

        if total_new:
            parts = [f"{v} {k}" for k, v in stats["new"].items() if v]
            self.logger.info(f"New to import: {total_new} ({', '.join(parts)})")
        else:
            self.logger.info("Nothing new to import")

        self._finalize_transactions(new_transactions)

        if new_transactions:
            result = self.ynab.create_transactions(self.budget_id, new_transactions)
            created = result["created"]
            ynab_dupes = result["duplicates"]

            if created:
                self.logger.info(f"✓ Created {created} transaction(s) in YNAB")
            if ynab_dupes:
                # These are caught by YNAB's own dedup as a safety net — shouldn't normally happen
                self.logger.info(f"⚠ YNAB rejected {len(ynab_dupes)} as duplicate (safety net catch)")

    def _finalize_transactions(self, transactions: List[dict]):
        """Attach account and category IDs to each transaction."""
        for transaction in transactions:
            transaction['account_id'] = self.account_id
            if transaction['amount'] < 0:  # Outflow — categorize automatically
                transaction['category_id'] = self.category_id
            # Inflows left uncategorized for the user to assign


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

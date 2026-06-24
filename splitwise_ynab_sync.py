"""
Splitwise-YNAB Integration Sync Tool
Automatically syncs Splitwise expenses to YNAB budgets.
"""

import datetime
import time
import sys
import argparse
from typing import List

from config import Config
from api_client import SplitwiseAPI, YNABAPI, APIError
from transaction_processor import TransactionProcessor


class SplitYNABSync:
    """Main synchronization application."""
    
    def __init__(self):
        """Initialize the sync application."""
        # Validate configuration
        Config.validate()
        
        # Setup logging
        self.logger = Config.setup_logging()
        
        # Initialize API clients
        self.splitwise = SplitwiseAPI(Config.SW_API_KEY)
        self.ynab = YNABAPI(Config.YNAB_TOKEN)
        
        # Get account information
        self.logger.info("Initializing account information...")
        try:
            self.splitwise_user_id = self.splitwise.get_current_user_id()
            self.budget_id = self.ynab.get_budget_id(Config.YNAB_BUDGET)
            self.account_id = self.ynab.get_account_id(self.budget_id, Config.YNAB_SW_ACCOUNT)
            self.category_id = self.ynab.get_category_id(self.budget_id, Config.YNAB_SW_CATEGORY)
        except APIError as e:
            self.logger.error(f"Failed to initialize: {e}")
            sys.exit(1)
        
        # Initialize transaction processor
        self.processor = TransactionProcessor(
            self.splitwise_user_id,
            Config.USER_NAME,
            Config.ALLOW_DUPLICATES
        )
        
        self.logger.info("Sync application initialized successfully")
    
    def run(self, single_run=False):
        """Run the sync - either once or in continuous loop.
        
        Args:
            single_run (bool): If True, run once and exit. If False, run continuously.
        """
        if single_run:
            self.logger.info("Running single sync operation...")
            try:
                self.sync_once()
                self.logger.info("Single sync completed successfully")
            except Exception as e:
                self.logger.error(f"Single sync failed: {e}", exc_info=True)
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
        self.logger.info(f"Syncing expenses from {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')} onwards (last {Config.SYNC_DAYS} days)")
        
        # Get data from both services
        self.logger.debug("Fetching data from APIs...")
        splitwise_data = self.splitwise.get_recent_expenses(cutoff_date)
        
        # Get ALL transactions from Splitwise account to check for existing import_ids
        # This prevents duplicates even if you've manually categorized transactions
        all_ynab_transactions = self.ynab.get_all_account_transactions(
            self.budget_id, 
            self.account_id
        )
        
        # Extract existing import IDs from ALL transactions (not just recent ones)
        existing_import_ids = [
            tx['import_id'] for tx in all_ynab_transactions 
            if tx.get('import_id')
        ]
        
        self.logger.debug(f"Found {len(existing_import_ids)} existing import IDs in YNAB Splitwise account")
        if existing_import_ids:
            # Show a sample of existing import IDs for debugging
            sample_ids = existing_import_ids[:5]
            self.logger.debug(f"Sample existing import IDs: {sample_ids}")
        
        # Log total transactions retrieved from YNAB
        self.logger.debug(f"Retrieved {len(all_ynab_transactions)} total transactions from YNAB Splitwise account")
        
        # Process expenses into transactions
        new_transactions = self.processor.process_expenses(
            splitwise_data.get('expenses', []),
            existing_import_ids
        )
        
        # Log the import_ids of new transactions we're about to create
        if new_transactions:
            new_import_ids = [tx.get('import_id') for tx in new_transactions]
            self.logger.debug(f"About to create {len(new_transactions)} new transactions with import_ids: {new_import_ids}")
        
        # Add account and category information to transactions
        self._finalize_transactions(new_transactions)
        
        # Create transactions in YNAB
        if new_transactions:
            result = self.ynab.create_transactions(self.budget_id, new_transactions)
            
            created_count = result["created"]
            duplicate_ids = result["duplicates"]
            
            if created_count > 0:
                self.logger.info(f"✓ Successfully created {created_count} new transaction(s)")
            
            if duplicate_ids:
                # Map duplicate import IDs back to expense descriptions for better logging
                duplicate_descriptions = []
                for dup_id in duplicate_ids:
                    # Extract expense ID from import_id (format: "expenseId_type" or "expenseId_dup_timestamp_type")
                    expense_id = dup_id.split('_')[0]
                    for expense in splitwise_data.get('expenses', []):
                        if str(expense['id']) == expense_id:
                            duplicate_descriptions.append(expense['description'])
                            break
                
                self.logger.info(f"⚠ Skipped {len(duplicate_ids)} duplicate transaction(s): " + 
                               ", ".join(duplicate_descriptions[:3]) + 
                               (f" and {len(duplicate_descriptions)-3} more" if len(duplicate_descriptions) > 3 else ""))
            
            if created_count == 0 and not duplicate_ids:
                self.logger.info("No new transactions to create")
        else:
            self.logger.info("No new transactions to create")
    
    def _finalize_transactions(self, transactions: List[dict]):
        """Add account and category IDs to transactions."""
        for transaction in transactions:
            transaction['account_id'] = self.account_id
            
            # Add category based on transaction type
            if transaction['amount'] > 0:  # Inflow - money owed to me or expenses others paid for me
                # Leave uncategorized for user to decide
                pass  
            elif transaction['amount'] < 0:  # Outflow - repayments I make
                transaction['category_id'] = self.category_id


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Sync Splitwise expenses to YNAB',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python splitwise_ynab_sync.py                 # Run continuously (default)
  python splitwise_ynab_sync.py --once          # Run once and exit
  python splitwise_ynab_sync.py --days 30       # Sync last 30 days
        """
    )
    parser.add_argument(
        '--once', 
        action='store_true', 
        help='Run sync once and exit (useful for CI/CD)'
    )
    parser.add_argument(
        '--days',
        type=int,
        help=f'Number of days to sync (default: {Config.SYNC_DAYS})'
    )
    
    args = parser.parse_args()
    
    # Override config if command line arguments provided
    if args.days:
        Config.SYNC_DAYS = args.days
    
    try:
        sync_app = SplitYNABSync()
        sync_app.run(single_run=args.once)
    except Exception as e:
        logger = Config.setup_logging()
        logger.error(f"Application failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
"""
Splitwise-YNAB Integration Sync Tool
Automatically syncs Splitwise expenses to YNAB budgets.
"""

import datetime
import time
import sys
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
    
    def run(self):
        """Run the continuous sync loop."""
        self.logger.info("Starting sync loop...")
        
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
        
        # Get data from both services
        self.logger.debug("Fetching data from APIs...")
        splitwise_data = self.splitwise.get_recent_expenses(cutoff_date)
        ynab_transactions = self.ynab.get_account_transactions(
            self.budget_id, 
            self.account_id, 
            cutoff_date
        )
        
        # Extract existing import IDs
        existing_import_ids = [
            tx['import_id'] for tx in ynab_transactions 
            if tx.get('import_id')
        ]
        
        # Process expenses into transactions
        new_transactions = self.processor.process_expenses(
            splitwise_data.get('expenses', []),
            existing_import_ids
        )
        
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
            
            # Add category to specific transaction types
            if 'subtransactions' in transaction:
                # For split transactions, categorize the "others' share" subtransaction
                for subtx in transaction['subtransactions']:
                    if subtx['amount'] > 0:  # Inflow (others' share)
                        subtx['category_id'] = self.category_id
            elif transaction['amount'] < 0:  # Outflow (repayments)
                transaction['category_id'] = self.category_id
            # Regular expenses (inflows) are left uncategorized for user to categorize


def main():
    """Main entry point."""
    try:
        sync_app = SplitYNABSync()
        sync_app.run()
    except Exception as e:
        logger = Config.setup_logging()
        logger.error(f"Application failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
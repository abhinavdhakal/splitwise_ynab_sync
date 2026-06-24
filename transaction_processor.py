"""Transaction processing logic for Splitwise expenses."""

import time
from decimal import Decimal
from typing import Dict, List, Any, Optional
import re
import logging

logger = logging.getLogger('splitwise_ynab_sync')


class TransactionProcessor:
    """Processes Splitwise expenses into YNAB transactions."""
    
    def __init__(self, user_id: int, user_name: str, allow_duplicates: bool):
        self.user_id = user_id
        self.user_name = user_name
        self.allow_duplicates = allow_duplicates
    
    def process_expenses(self, expenses: List[Dict], existing_import_ids: List[str]) -> List[Dict]:
        """Process Splitwise expenses into YNAB transaction format."""
        new_transactions = []
        skipped_duplicates = []
        
        # Sort expenses by date for better logging
        sorted_expenses = sorted(expenses, key=lambda x: x.get('date', ''), reverse=True)
        
        for expense in sorted_expenses:
            expense_date_str = expense['date'][:10]  # Extract YYYY-MM-DD
            
            # Skip deleted expenses completely
            if self._is_deleted(expense):
                logger.debug(f'Completely avoiding deleted expense ID {expense["id"]} ({expense_date_str})')
                continue
            
            # Check if this expense was edited (has updated_at different from created_at)
            is_edited = False
            if expense.get('created_at') and expense.get('updated_at'):
                created_time = expense['created_at']
                updated_time = expense['updated_at']
                if created_time != updated_time:
                    is_edited = True
                    logger.debug(f'Expense ID {expense["id"]} was edited (created: {created_time[:10]}, updated: {updated_time[:10]})')
            
            # Process different expense types - each transaction will check for its own duplicates
            transactions = self._process_expense(expense, existing_import_ids)
            new_transactions.extend(transactions)
            
            if transactions:
                edit_note = " (edited)" if is_edited else ""
                logger.info(f'Processing expense ({expense_date_str}): "{expense["description"]}"{edit_note} -> {len(transactions)} transaction(s)')
            else:
                logger.debug(f'No new transactions for expense ({expense_date_str}): "{expense["description"]}" - likely all duplicates')
        
        return new_transactions
    
    def _is_deleted(self, expense: Dict) -> bool:
        """Check if expense is deleted - be very thorough to avoid deleted expenses."""
        deleted_at = expense.get('deleted_at')
        
        # Check various ways Splitwise might indicate deletion
        if deleted_at is not None and deleted_at != '' and deleted_at != False and deleted_at != '0':
            return True
        
        # Also check if deleted_by exists (another indicator)
        if expense.get('deleted_by') is not None:
            return True
            
        # Check if expense has been marked as deleted in other ways
        if expense.get('deleted') is True:
            return True
            
        return False
    
    def _process_expense(self, expense: Dict, existing_import_ids: List[str]) -> List[Dict]:
        """Process a single expense into YNAB transactions."""
        expense_id = expense['id']
        
        # Use created_at for transaction date to keep consistent even when expense is edited
        # Fall back to expense date if created_at is not available
        if expense.get('created_at'):
            transaction_date = expense['created_at'].split('T')[0]
        else:
            transaction_date = expense['date'].split('T')[0]
            logger.debug(f"Using expense date for transaction {expense_id} (no created_at available)")
        
        description = expense['description']
        
        # Check for repayments first
        repayment_transactions = self._process_repayments(expense, expense_id, transaction_date, description, existing_import_ids)
        if repayment_transactions:
            return repayment_transactions
        
        # Process regular expense or split payment
        return self._process_regular_expense(expense, expense_id, transaction_date, description, existing_import_ids)
    
    def _process_repayments(self, expense: Dict, expense_id: int, expense_date: str, description: str, existing_import_ids: List[str]) -> List[Dict]:
        """Process repayment transactions."""
        transactions = []
        
        for repayment in expense.get('repayments', []):
            if int(repayment['from']) == self.user_id:
                # Create unique import ID for each repayment by including recipient user ID
                import_id = self._create_repayment_import_id(expense_id, int(repayment['to']))
                logger.debug(f'Checking for duplicate repayment transaction: {import_id}')
                if not self.allow_duplicates and import_id in existing_import_ids:
                    to_user_name = self._find_user_name(expense['users'], int(repayment['to']))
                    logger.info(f'Skipping duplicate repayment transaction for expense ID {expense_id} to {to_user_name} (import_id: {import_id})')
                    continue
                
                to_user_name = self._find_user_name(expense['users'], int(repayment['to']))
                
                transaction = self._create_repayment_transaction(
                    expense_id, expense_date, description, repayment['amount'], to_user_name, import_id
                )
                transactions.append(transaction)
        
        return transactions
    
    def _process_regular_expense(self, expense: Dict, expense_id: int, expense_date: str, description: str, existing_import_ids: List[str]) -> List[Dict]:
        """Process regular expense or split payment."""
        user_data = self._get_user_data(expense['users'])
        
        if user_data['paid_share'] > 0:
            # User paid for the expense - check for duplicate split transaction
            import_id = self._create_import_id(expense_id, "split")
            logger.debug(f'Checking for duplicate split transaction: {import_id}')
            if not self.allow_duplicates and import_id in existing_import_ids:
                logger.info(f'Skipping duplicate split transaction for expense ID {expense_id} (import_id: {import_id})')
                return []
            
            return [self._create_split_transaction(expense_id, expense_date, description, user_data)]
        elif user_data['owed_share'] != 0:
            # User owes money but didn't pay - check for duplicate owed transaction
            import_id = self._create_import_id(expense_id, "exp")
            logger.debug(f'Checking for duplicate owed transaction: {import_id}')
            if not self.allow_duplicates and import_id in existing_import_ids:
                logger.info(f'Skipping duplicate owed transaction for expense ID {expense_id} (import_id: {import_id})')
                return []
            
            paid_by = self._find_payer(expense['users'])
            return [self._create_owed_transaction(expense_id, expense_date, description, user_data['owed_share'], paid_by)]
        
        return []
    
    def _get_user_data(self, users: List[Dict]) -> Dict[str, float]:
        """Extract current user's payment and owed amounts."""
        for user in users:
            if int(user['user']['id']) == self.user_id:
                return {
                    'paid_share': float(user.get('paid_share', '0')),
                    'owed_share': float(user.get('owed_share', '0'))
                }
        return {'paid_share': 0, 'owed_share': 0}
    
    def _find_user_name(self, users: List[Dict], user_id: int) -> str:
        """Find user's first name by ID."""
        for user in users:
            if int(user['user']['id']) == user_id:
                return user['user']['first_name']
        return "someone"
    
    def _find_payer(self, users: List[Dict]) -> str:
        """Find who paid for the expense."""
        for user in users:
            if float(user.get('paid_share', '0')) > 0:
                return user['user']['first_name']
        return "someone"
    
    def _create_import_id(self, expense_id: int, transaction_type: str) -> str:
        """Create unique import ID for transaction (max 36 chars for YNAB)."""
        import hashlib
        
        if self.allow_duplicates:
            # Include timestamp for uniqueness when duplicates allowed
            unique_string = f"{expense_id}_{transaction_type}_{int(time.time())}"
        else:
            unique_string = f"{expense_id}_{transaction_type}"
        
        # If it's short enough, use it directly
        if len(unique_string) <= 36:
            return unique_string
        
        # Otherwise, create a hash-based ID that's always under 36 chars
        hash_suffix = hashlib.md5(unique_string.encode()).hexdigest()[:8]
        return f"{expense_id}_{transaction_type[:4]}_{hash_suffix}"
    
    def _create_repayment_import_id(self, expense_id: int, to_user_id: int) -> str:
        """Create unique import ID for repayment transaction (max 36 chars for YNAB)."""
        import hashlib
        
        if self.allow_duplicates:
            unique_string = f"{expense_id}_repay_{to_user_id}_{int(time.time())}"
        else:
            unique_string = f"{expense_id}_repay_{to_user_id}"
        
        # If it's short enough, use it directly  
        if len(unique_string) <= 36:
            return unique_string
        
        # Otherwise, create a hash-based ID that's always under 36 chars
        hash_suffix = hashlib.md5(unique_string.encode()).hexdigest()[:8]
        return f"{expense_id}_rp{to_user_id}_{hash_suffix}"
    
    def _format_amount(self, amount: Any) -> tuple[int, str]:
        """Convert amount to YNAB milliunits and formatted string."""
        if isinstance(amount, (int, float)):
            milliunits = int(Decimal(str(amount)) * 1000)
            formatted = f'{float(amount):.2f}'
        else:
            cleaned = re.sub(r'[^\d\-.]', '', str(amount))
            milliunits = int(Decimal(cleaned) * 1000)
            formatted = f'{float(cleaned):.2f}'
        
        return milliunits, formatted
    
    def _create_split_transaction(self, expense_id: int, date: str, description: str, user_data: Dict) -> Dict:
        """Create a transaction for when user paid - only track amount owed by others."""
        others_share = user_data['paid_share'] - user_data['owed_share']
        others_share_amount, formatted_others_share = self._format_amount(others_share)
        
        memo = f"{description} | Total: {user_data['paid_share']:.2f} | My: {user_data['owed_share']:.2f} | Others: {formatted_others_share}"
        
        return {
            "import_id": self._create_import_id(expense_id, "split"),
            "date": date,
            "amount": others_share_amount,  # Inflow - amount others owe me
            "memo": memo,
            "cleared": "cleared"
        }
    
    def _create_repayment_transaction(self, expense_id: int, date: str, description: str, amount: Any, paid_to: str, import_id: str) -> Dict:
        """Create a repayment/settlement transaction."""
        amount_milliunits, formatted_amount = self._format_amount(amount)
        memo = f"{description}, settlement to {paid_to} ({formatted_amount})"
        
        return {
            "import_id": import_id,
            "date": date,
            "amount": -amount_milliunits,  # Outflow
            "memo": memo,
            "cleared": "cleared"
        }
    
    def _create_owed_transaction(self, expense_id: int, date: str, description: str, amount: Any, paid_by: str) -> Dict:
        """Create a transaction for money owed to others."""
        amount_milliunits, formatted_amount = self._format_amount(amount)
        
        verb = 'owe' if self.user_name == 'you' else 'owes'
        memo = f"{description}, paid by {paid_by}, {self.user_name} {verb} {formatted_amount}"
        
        return {
            "import_id": self._create_import_id(expense_id, "exp"),
            "date": date,
            "amount": amount_milliunits,  # Inflow (you owe this)
            "memo": memo,
            "cleared": "cleared"
        }
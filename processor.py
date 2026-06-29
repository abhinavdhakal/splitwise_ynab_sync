"""Converts Splitwise expenses into YNAB transactions."""

import hashlib
import time
import re
import logging
from decimal import Decimal
from typing import Dict, List, Any, Tuple

logger = logging.getLogger('splitwise_ynab_sync')


class TransactionProcessor:
    """Processes Splitwise expenses into YNAB transaction format."""

    def __init__(self, user_id: int, user_name: str, allow_duplicates: bool):
        self.user_id = user_id
        self.user_name = user_name
        self.allow_duplicates = allow_duplicates

    # -------------------------------------------------------------------------
    # Public interface
    # -------------------------------------------------------------------------

    def process_expenses(self, expenses: List[Dict], existing_import_ids: List[str]) -> Tuple[List[Dict], Dict]:
        """Convert Splitwise expenses into new YNAB transactions.

        Returns:
            (transactions, stats) where stats contains counts by type,
            safe to log without revealing personal information.
        """
        new_transactions = []
        stats = {
            "total": len(expenses),
            "deleted": 0,
            "new":       {"repayment": 0, "split": 0, "owed": 0},
            "duplicate": {"repayment": 0, "split": 0, "owed": 0},
        }

        sorted_expenses = sorted(expenses, key=lambda x: x.get('date', ''), reverse=True)

        for expense in sorted_expenses:
            date_str = expense['date'][:10]

            if self._is_deleted(expense):
                stats["deleted"] += 1
                logger.debug(f'Skipping deleted expense {expense["id"]} ({date_str})')
                continue

            is_edited = (
                expense.get('created_at') and expense.get('updated_at')
                and expense['created_at'] != expense['updated_at']
            )

            transactions, tx_type = self._process_expense(expense, existing_import_ids)

            if transactions:
                new_transactions.extend(transactions)
                stats["new"][tx_type] += len(transactions)
                edit_note = " (edited)" if is_edited else ""
                logger.debug(f'New {tx_type}{edit_note} ({date_str}): "{expense["description"]}"')
            elif tx_type:
                stats["duplicate"][tx_type] += 1
                logger.debug(f'Duplicate {tx_type} ({date_str}): "{expense["description"]}" — already in YNAB')

        return new_transactions, stats

    # -------------------------------------------------------------------------
    # Expense routing
    # -------------------------------------------------------------------------

    def _process_expense(self, expense: Dict, existing_import_ids: List[str]) -> Tuple[List[Dict], str]:
        """Process a single expense. Returns (transactions, type_string)."""
        expense_id = expense['id']
        transaction_date = (
            expense['created_at'].split('T')[0] if expense.get('created_at')
            else expense['date'].split('T')[0]
        )
        description = expense['description']

        # If you owe someone (repayment FROM you), always take the repayment path.
        # Critical: when all repayments are already in YNAB, _process_repayments returns []
        # (falsy). Without this guard, the code falls through to _process_regular_expense
        # and creates the same debt with the opposite sign on every subsequent run.
        has_user_repayment = any(
            int(r['from']) == self.user_id
            for r in expense.get('repayments', [])
        )
        if has_user_repayment:
            txs = self._process_repayments(expense, expense_id, transaction_date, description, existing_import_ids)
            return txs, "repayment"

        txs, tx_type = self._process_regular_expense(expense, expense_id, transaction_date, description, existing_import_ids)
        return txs, tx_type

    def _process_repayments(self, expense: Dict, expense_id: int, date: str, description: str, existing_import_ids: List[str]) -> List[Dict]:
        """Handle expenses where you owe money to someone."""
        transactions = []
        for repayment in expense.get('repayments', []):
            if int(repayment['from']) != self.user_id:
                continue

            import_id = self._repayment_import_id(expense_id, int(repayment['to']))
            if not self.allow_duplicates and import_id in existing_import_ids:
                logger.debug(f'Duplicate repayment {expense_id} → already in YNAB')
                continue

            to_name = self._find_user_name(expense['users'], int(repayment['to']))
            transactions.append(self._make_repayment(expense_id, date, description, repayment['amount'], to_name, import_id))

        return transactions

    def _process_regular_expense(self, expense: Dict, expense_id: int, date: str, description: str, existing_import_ids: List[str]) -> Tuple[List[Dict], str]:
        """Handle expenses where you paid for others, or others paid for you."""
        user_data = self._get_user_data(expense['users'])

        if user_data['paid_share'] > 0:
            import_id = self._import_id(expense_id, "split")
            if not self.allow_duplicates and import_id in existing_import_ids:
                logger.debug(f'Duplicate split {expense_id} → already in YNAB')
                return [], "split"
            return [self._make_split(expense_id, date, description, user_data)], "split"

        if user_data['owed_share'] != 0:
            import_id = self._import_id(expense_id, "exp")
            if not self.allow_duplicates and import_id in existing_import_ids:
                logger.debug(f'Duplicate owed {expense_id} → already in YNAB')
                return [], "owed"
            paid_by = self._find_payer(expense['users'])
            return [self._make_owed(expense_id, date, description, user_data['owed_share'], paid_by)], "owed"

        return [], ""

    # -------------------------------------------------------------------------
    # Transaction builders
    # -------------------------------------------------------------------------

    def _make_repayment(self, expense_id: int, date: str, description: str, amount: Any, paid_to: str, import_id: str) -> Dict:
        """Outflow: you are paying someone back."""
        milliunits, formatted = self._to_milliunits(amount)
        return {
            "import_id": import_id,
            "date": date,
            "amount": -milliunits,
            "memo": f"{description}, settlement to {paid_to} ({formatted})",
            "cleared": "cleared"
        }

    def _make_split(self, expense_id: int, date: str, description: str, user_data: Dict) -> Dict:
        """Inflow: you paid, others owe you their share."""
        others_share = user_data['paid_share'] - user_data['owed_share']
        milliunits, formatted = self._to_milliunits(others_share)
        memo = f"{description} | Total: {user_data['paid_share']:.2f} | My: {user_data['owed_share']:.2f} | Others: {formatted}"
        return {
            "import_id": self._import_id(expense_id, "split"),
            "date": date,
            "amount": milliunits,
            "memo": memo,
            "cleared": "cleared"
        }

    def _make_owed(self, expense_id: int, date: str, description: str, amount: Any, paid_by: str) -> Dict:
        """Inflow: someone paid for you (debt recorded in Splitwise account)."""
        milliunits, formatted = self._to_milliunits(amount)
        verb = 'owe' if self.user_name == 'you' else 'owes'
        return {
            "import_id": self._import_id(expense_id, "exp"),
            "date": date,
            "amount": milliunits,
            "memo": f"{description}, paid by {paid_by}, {self.user_name} {verb} {formatted}",
            "cleared": "cleared"
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _is_deleted(self, expense: Dict) -> bool:
        deleted_at = expense.get('deleted_at')
        if deleted_at not in (None, '', False, '0'):
            return True
        if expense.get('deleted_by') is not None:
            return True
        if expense.get('deleted') is True:
            return True
        return False

    def _get_user_data(self, users: List[Dict]) -> Dict[str, float]:
        for user in users:
            if int(user['user']['id']) == self.user_id:
                return {
                    'paid_share': float(user.get('paid_share', '0')),
                    'owed_share': float(user.get('owed_share', '0'))
                }
        return {'paid_share': 0.0, 'owed_share': 0.0}

    def _find_user_name(self, users: List[Dict], user_id: int) -> str:
        for user in users:
            if int(user['user']['id']) == user_id:
                return user['user']['first_name']
        return "someone"

    def _find_payer(self, users: List[Dict]) -> str:
        for user in users:
            if float(user.get('paid_share', '0')) > 0:
                return user['user']['first_name']
        return "someone"

    def _to_milliunits(self, amount: Any) -> tuple[int, str]:
        if isinstance(amount, (int, float)):
            milliunits = int(Decimal(str(amount)) * 1000)
            formatted = f'{float(amount):.2f}'
        else:
            cleaned = re.sub(r'[^\d\-.]', '', str(amount))
            milliunits = int(Decimal(cleaned) * 1000)
            formatted = f'{float(cleaned):.2f}'
        return milliunits, formatted

    def _import_id(self, expense_id: int, tx_type: str) -> str:
        base = f"{expense_id}_{tx_type}" if not self.allow_duplicates else f"{expense_id}_{tx_type}_{int(time.time())}"
        if len(base) <= 36:
            return base
        suffix = hashlib.md5(base.encode()).hexdigest()[:8]
        return f"{expense_id}_{tx_type[:4]}_{suffix}"

    def _repayment_import_id(self, expense_id: int, to_user_id: int) -> str:
        base = f"{expense_id}_repay_{to_user_id}" if not self.allow_duplicates else f"{expense_id}_repay_{to_user_id}_{int(time.time())}"
        if len(base) <= 36:
            return base
        suffix = hashlib.md5(base.encode()).hexdigest()[:8]
        return f"{expense_id}_rp{to_user_id}_{suffix}"

from decimal import Decimal

import pytest

from moneywiz_api.model.transaction import (
    RefundTransaction,
    Transaction,
    TransferDepositTransaction,
    TransferWithdrawTransaction,
)
from tests.integration.conftest import category_manager, transaction_manager


def test_category():
    for category in category_manager.records().values():
        chain = category_manager.get_name_chain(category.id)
        assert chain[-1] == category.name


@pytest.mark.parametrize(
    "transaction",
    [
        x
        for _, x in transaction_manager.records().items()
        if isinstance(x, RefundTransaction)
    ],
)
def test_category_assignment_refund_transactions(transaction: Transaction):
    # Refund transaction doesn't have correct category assignments

    category_assignment = transaction_manager.category_for_transaction(transaction.id)
    original_transaction_id = (
        transaction_manager.original_transaction_for_refund_transaction(transaction.id)
    )
    assert original_transaction_id is not None
    original_transaction = transaction_manager.get(original_transaction_id)
    assert original_transaction is not None
    original_category_assignment = transaction_manager.category_for_transaction(
        original_transaction_id
    )

    if category_assignment is None and original_category_assignment is None:
        return

    assert category_assignment is not None
    assert original_category_assignment is not None

    assert len(category_assignment) == len(original_category_assignment)

    total_amount, original_total_amount = Decimal(0), Decimal(0)

    for category, amount in category_assignment:
        total_amount += amount

    for category, amount in original_category_assignment:
        original_total_amount += amount

    if len(category_assignment) == 1:
        # total_amount == transaction.amount is not necessarily
        pass
    else:
        assert total_amount == pytest.approx(transaction.amount, abs=0.001)
    assert original_total_amount == pytest.approx(
        original_transaction.amount, abs=0.001
    )


@pytest.mark.parametrize(
    "transaction",
    [
        x
        for _, x in transaction_manager.records().items()
        if not isinstance(x, RefundTransaction)
    ],
)
def test_category_assignment_non_refund_transaction(transaction: Transaction):
    category_assignment = transaction_manager.category_for_transaction(transaction.id)
    if category_assignment:
        total_amount = Decimal(0)
        for category_id, amount in category_assignment:
            total_amount += amount

        if isinstance(transaction, TransferDepositTransaction) or isinstance(
            transaction, TransferWithdrawTransaction
        ):
            # The sign of the category_assignment could be wrong for Transfer Transactions
            assert abs(transaction.amount) == pytest.approx(
                abs(total_amount), abs=0.01
            ), (transaction, category_assignment)
        else:
            assert transaction.amount == pytest.approx(total_amount, abs=0.01), (
                transaction,
                category_assignment,
            )

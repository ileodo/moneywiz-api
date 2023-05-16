import pytest

from src.moneywiz_api.model.transaction import (
    RefundTransaction,
    WithdrawTransaction,
    DepositTransaction,
    InvestmentBuyTransaction,
    InvestmentSellTransaction,
    ReconcileTransaction,
    TransferDepositTransaction,
    TransferWithdrawTransaction,
    TransferBudgetTransaction,
)


from conftest import transaction_manager, account_manager


@pytest.mark.parametrize(
    "deposit_transaction",
    [
        x
        for _, x in transaction_manager.records().items()
        if isinstance(x, DepositTransaction)
    ],
)
def test_all_deposit_transaction(deposit_transaction: DepositTransaction):
    deposit_transaction.validate()


@pytest.mark.parametrize(
    "investment_buy_transaction",
    [
        x
        for _, x in transaction_manager.records().items()
        if isinstance(x, InvestmentBuyTransaction)
    ],
)
def test_all_investment_buy_transaction(
    investment_buy_transaction: InvestmentBuyTransaction,
):
    investment_buy_transaction.validate()


@pytest.mark.parametrize(
    "investment_sell_transaction",
    [
        x
        for _, x in transaction_manager.records().items()
        if isinstance(x, InvestmentSellTransaction)
    ],
)
def test_all_investment_sell_transaction(
    investment_sell_transaction: InvestmentSellTransaction,
):
    investment_sell_transaction.validate()


@pytest.mark.parametrize(
    "reconcile_transaction",
    [
        x
        for _, x in transaction_manager.records().items()
        if isinstance(x, ReconcileTransaction)
    ],
)
def test_all_reconcile_transaction(reconcile_transaction: ReconcileTransaction):
    reconcile_transaction.validate()


@pytest.mark.parametrize(
    "refund_transaction",
    [
        x
        for _, x in transaction_manager.records().items()
        if isinstance(x, RefundTransaction)
    ],
)
def test_all_refund_transactions(refund_transaction: RefundTransaction):
    refund_transaction.validate()

    original_transaction_id = (
        transaction_manager.original_transaction_for_refund_transaction(
            refund_transaction.id
        )
    )
    original_transaction = transaction_manager.get(original_transaction_id)
    assert isinstance(original_transaction, WithdrawTransaction)
    assert original_transaction.amount < 0


@pytest.mark.parametrize(
    "transfer_budget_transaction",
    [
        x
        for _, x in transaction_manager.records().items()
        if isinstance(x, TransferBudgetTransaction)
    ],
)
def test_all_transfer_budget_transaction(
    transfer_budget_transaction: TransferBudgetTransaction,
):
    transfer_budget_transaction.validate()


@pytest.mark.parametrize(
    "transfer_deposit_transaction",
    [
        x
        for _, x in transaction_manager.records().items()
        if isinstance(x, TransferDepositTransaction)
    ],
)
def test_all_transfer_deposit_transaction(
    transfer_deposit_transaction: TransferDepositTransaction,
):
    transfer_deposit_transaction.validate()

    to_account = account_manager.get(transfer_deposit_transaction.account)
    from_account = account_manager.get(transfer_deposit_transaction.sender_account)

    withdraw_transaction = transaction_manager.get(
        transfer_deposit_transaction.sender_transaction
    )

    assert transfer_deposit_transaction.original_currency == to_account.currency
    assert transfer_deposit_transaction.sender_currency == from_account.currency

    assert transfer_deposit_transaction.sender_amount == withdraw_transaction.amount
    assert (
        transfer_deposit_transaction.sender_currency
        == withdraw_transaction.original_currency
    )


@pytest.mark.parametrize(
    "transfer_withdraw_transaction",
    [
        x
        for _, x in transaction_manager.records().items()
        if isinstance(x, TransferWithdrawTransaction)
    ],
)
def test_all_transfer_withdraw_transaction(
    transfer_withdraw_transaction: TransferWithdrawTransaction,
):
    transfer_withdraw_transaction.validate()

    from_account = account_manager.get(transfer_withdraw_transaction.account)
    to_account = account_manager.get(transfer_withdraw_transaction.recipient_account)

    deposit_transaction = transaction_manager.get(
        transfer_withdraw_transaction.recipient_transaction
    )

    assert transfer_withdraw_transaction.original_currency == from_account.currency
    assert transfer_withdraw_transaction.recipient_currency == to_account.currency

    assert (
        abs(transfer_withdraw_transaction.recipient_amount)
        == deposit_transaction.amount
    )
    assert (
        transfer_withdraw_transaction.recipient_currency
        == deposit_transaction.original_currency
    )


@pytest.mark.parametrize(
    "withdraw_transaction",
    [
        x
        for _, x in transaction_manager.records().items()
        if isinstance(x, WithdrawTransaction)
    ],
)
def test_all_withdraw_transactions(withdraw_transaction: WithdrawTransaction):
    withdraw_transaction.validate()

from datetime import datetime

TEST_DB_PATH = "/Users/<USERNAME>/Library/Containers/com.moneywiz.personalfinance/Data/Documents/.AppData/ipadMoneyWiz.sqlite"

BALANCE_AS_OF_DATE = datetime(2023, 5, 19, 0, 0, 0)
CASH_BALANCES = [
    # (ACCOUNT_PK, BALANCE)
    (1001, -100.00),
    (1002, -202.33),
]

HOLDINGS_BALANCES = [
    # (ACCOUNT_PK, {
    #     HOLDINGS_PK: HOLDINGS_BALANCE)
    # })
    (
        2001,
        {
            3001: 15,
        },
    ),
]

import pandas as pd

import data_utils as du

COLUMNS = ["InvoiceNo", "StockCode", "InvoiceDate", "Category", "City",
           "Quantity", "NetPrice", "UnitPrice"]


def raw(rows):
    return pd.DataFrame(rows, columns=COLUMNS)


def test_clean_transactions_keeps_only_valid_rows():
    data = raw([
        ("I1", 1, "2020-01-06", "A", "IST", 5, 10.0, 12.0),   # valid
        ("I2", 2, "2020-01-12", "B", "ANK", 3, 20.0, 25.0),   # valid
        ("I3", 3, "2020-01-06", "B", None, 7, 20.0, 25.0),    # missing City
        ("I4", 4, "2020-01-06", None, "IST", 7, 20.0, 25.0),  # missing Category
        ("I5", 5, "2020-01-06", "A", "IST", -2, 10.0, 12.0),  # negative Quantity
        ("I6", 6, "2020-01-06", "A", "IST", 0, 10.0, 12.0),   # zero Quantity
        ("I7", 7, "2020-01-06", "A", "IST", 4, 0.0, 12.0),    # zero NetPrice
        ("I8", 8, "2020-01-06", "A", "IST", 4, 10.0, -1.0),   # negative UnitPrice
    ])
    cleaned = du.clean_transactions(data)
    assert cleaned["InvoiceNo"].tolist() == ["I1", "I2"]
    assert cleaned["Quantity"].sum() == 8


def test_clean_transactions_adds_derived_columns():
    cleaned = du.clean_transactions(raw([
        ("I1", 1, "2020-01-06", "A", "IST", 5, 10.0, 12.0),
        ("I2", 2, "2020-03-01", "B", "ANK", 2, 7.5, 9.0),
    ]))
    assert pd.api.types.is_datetime64_any_dtype(cleaned["InvoiceDate"])
    assert cleaned["SalesAmount"].tolist() == [50.0, 15.0]
    assert cleaned["Week"].tolist() == [2, 9]  # ISO weeks
    assert cleaned["Month"].tolist() == [1, 3]


def test_clean_transactions_does_not_modify_input():
    data = raw([("I1", 1, "2020-01-06", "A", "IST", 5, 10.0, 12.0)])
    before = data.copy()
    du.clean_transactions(data)
    pd.testing.assert_frame_equal(data, before)

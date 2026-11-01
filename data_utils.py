"""Shared data preparation used by every dashboard tab (no Streamlit import)."""

import pandas as pd


def clean_transactions(data):
    """The team's Sales cleaning rules, shared by Sales and Forecast.

    Drops rows with any missing field, keeps positive Quantity, NetPrice and
    UnitPrice, parses InvoiceDate and adds SalesAmount, Week and Month.
    Exact duplicates are removed by the caller before this step.
    """
    data = data.dropna()
    data = data[
        (data["Quantity"] > 0) &
        (data["NetPrice"] > 0) &
        (data["UnitPrice"] > 0)
    ]
    data["InvoiceDate"] = pd.to_datetime(data["InvoiceDate"])
    data["SalesAmount"] = data["Quantity"] * data["NetPrice"]
    data["Week"] = data["InvoiceDate"].dt.isocalendar().week
    data["Month"] = data["InvoiceDate"].dt.month

    return data

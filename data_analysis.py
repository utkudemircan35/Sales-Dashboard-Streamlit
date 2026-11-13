"""Veri temizligi ve urun analizleri. Hesaplar arayuzden bagimsizdir."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def clean_transactions(raw):
    """Satirlari nedenlerine gore ayirir; eksik sehir satisi silmez."""
    data = raw.copy()
    steps = []

    def remove_rows(mask, reason):
        nonlocal data
        steps.append({"Reason": reason, "Rows removed": int(mask.sum())})
        data = data.loc[~mask].copy()

    remove_rows(data.duplicated(), "Exact duplicate rows")
    data["InvoiceDate"] = pd.to_datetime(data["InvoiceDate"], errors="coerce").dt.normalize()
    for column in ["Quantity", "NetPrice", "UnitPrice"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    for column in ["InvoiceNo", "CustomerID", "StockCode", "Description", "Category", "City"]:
        data[column] = data[column].astype("string").str.strip().replace("", pd.NA)

    required = ["InvoiceNo", "CustomerID", "StockCode", "InvoiceDate", "Quantity", "NetPrice"]
    invalid = data[required].isna().any(axis=1)
    invalid |= ~np.isfinite(data["Quantity"]) | ~np.isfinite(data["NetPrice"])
    remove_rows(invalid, "Missing or invalid essential fields")
    negative_units = data["Quantity"] < 0
    return_rows = int(negative_units.sum())
    return_value = float((data.loc[negative_units, "Quantity"] * data.loc[negative_units, "NetPrice"]).sum())
    remove_rows(negative_units, "Negative quantities: review as possible returns")
    remove_rows((data["Quantity"] <= 0) | (data["NetPrice"] <= 0), "Zero quantity or non-positive net price")

    missing_city = int(data["City"].isna().sum())
    missing_category = int(data["Category"].isna().sum())
    data["City"] = data["City"].fillna("Unknown")
    data["Category"] = data["Category"].fillna("Unknown")
    data["Description"] = data["Description"].fillna(data["StockCode"])
    data["SalesAmount"] = data["Quantity"] * data["NetPrice"]
    data["Week"] = data["InvoiceDate"].dt.isocalendar().week
    data["Month"] = data["InvoiceDate"].dt.month
    data = data.sort_values("InvoiceDate", kind="stable").reset_index(drop=True)
    report = {
        "raw_rows": len(raw), "clean_rows": len(data), "steps": steps,
        "unknown_city_rows": missing_city, "unknown_category_rows": missing_category,
        "possible_return_rows": return_rows, "possible_return_signed_amount": return_value,
    }
    return data, report


def source_hash(path):
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def load_data(folder):
    """Yalnizca bu temizleme surumuyle uretilmis hazir veriyi kullanir."""
    folder = Path(folder)
    source = folder / "B2B_Transaction_Data_.xlsx"
    prepared = folder / "B2B_Transaction_Data_clean.parquet"
    report_path = folder / "data_quality.json"
    signature = source_hash(source)
    if prepared.exists() and report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("source_sha256") == signature and report.get("cleaning_version") == 1:
            return pd.read_parquet(prepared), report
    data, report = clean_transactions(pd.read_excel(source))
    report.update(source_sha256=signature, cleaning_version=1)
    return data, report


def save_prepared_data(folder):
    folder = Path(folder)
    source = folder / "B2B_Transaction_Data_.xlsx"
    data, report = clean_transactions(pd.read_excel(source))
    report.update(source_sha256=source_hash(source), cleaning_version=1)
    data.to_parquet(folder / "B2B_Transaction_Data_clean.parquet", index=False)
    (folder / "data_quality.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def category_performance(data):
    categories = data.groupby("Category", observed=True).agg(
        TotalRevenue=("SalesAmount", "sum"), TotalUnits=("Quantity", "sum"),
        ProductCount=("StockCode", "nunique"), InvoiceCount=("InvoiceNo", "nunique"),
    ).sort_values("TotalRevenue", ascending=False).reset_index()
    categories["RevenueShare"] = categories["TotalRevenue"] / categories["TotalRevenue"].sum()
    return categories


def product_performance(data):
    return data.groupby("StockCode", observed=True).agg(
        Description=("Description", "first"), Category=("Category", "first"),
        TotalRevenue=("SalesAmount", "sum"), TotalUnits=("Quantity", "sum"),
    ).sort_values(["TotalRevenue", "StockCode"], ascending=[False, True]).reset_index()


def abc_xyz_analysis(data, start_date=None, end_date=None):
    products = product_performance(data).rename(columns={"TotalRevenue": "TotalSales"})
    products["CumulativeShare"] = products["TotalSales"].cumsum() / products["TotalSales"].sum()
    # Esigi asan urun onceki sinifta kalir; ilk urun her zaman A'dir.
    previous_share = products["CumulativeShare"].shift(1, fill_value=0).round(12)
    products["ABCClass"] = np.select([previous_share < 0.80, previous_share < 0.95], ["A", "B"], default="C")

    start = pd.Timestamp(start_date) if start_date is not None else data["InvoiceDate"].min()
    end = pd.Timestamp(end_date) if end_date is not None else data["InvoiceDate"].max()
    months = pd.period_range(start, end, freq="M")
    months = months[(months.start_time >= start) & (months.end_time.normalize() <= end)]
    monthly = data.groupby(["StockCode", data["InvoiceDate"].dt.to_period("M")], observed=True)["Quantity"].sum().unstack(fill_value=0)
    monthly = monthly.reindex(columns=months, fill_value=0)
    cv = monthly.std(axis=1) / monthly.mean(axis=1).replace(0, np.nan)
    products["CV"] = products["StockCode"].map(cv) if len(months) >= 3 else np.nan
    products["XYZClass"] = products["CV"].apply(
        lambda value: "N/A" if pd.isna(value) else ("X" if value <= 0.5 else "Y" if value <= 1 else "Z")
    )
    products["StockClass"] = products["ABCClass"] + products["XYZClass"]
    products["ProductRank"] = np.arange(1, len(products) + 1)
    return products


def monthly_sales(data):
    sales = data.groupby(data["InvoiceDate"].dt.to_period("M"))["SalesAmount"].sum().sort_index()
    if sales.empty:
        return sales
    return sales.reindex(pd.period_range(sales.index.min(), sales.index.max(), freq="M"), fill_value=0)

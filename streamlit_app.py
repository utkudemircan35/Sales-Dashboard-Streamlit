"""Bes temel bolum, ortak filtreler ve anlasilir aciklamalar."""
from pathlib import Path

import pandas as pd
import streamlit as st

from data_analysis import load_data, category_performance, abc_xyz_analysis, monthly_sales
from dashboard_utils import format_number, money, metric, line_chart, sales_bar
from forecast import render_forecast_page

st.set_page_config(page_title="Book sales dashboard", page_icon=":material/menu_book:", layout="wide")


@st.cache_data(max_entries=1, show_spinner="Loading sales data...")
def read_sales(folder, source_modified):
    return load_data(folder)


@st.cache_data(max_entries=3, show_spinner=False)
def product_analysis(data, start, end):
    return abc_xyz_analysis(data, start, end)


folder = Path(__file__).resolve().parent
source = folder / "B2B_Transaction_Data_.xlsx"
data, report = read_sales(folder, source.stat().st_mtime_ns)

with st.container(horizontal=True):
    st.badge("B2B BOOK DISTRIBUTION", icon=":material/menu_book:", color="red")
    st.badge("2020 · Historical edition", color="gray")
st.title("Book sales dashboard")
st.caption("A B2B book distributor • Historical data: 2020 • All amounts in Turkish lira (₺)")

with st.sidebar:
    st.header(":material/tune: Your view")
    st.caption("These filters apply to every section. Results update automatically.")
    dates = st.date_input(
        "Period", (data.InvoiceDate.min().date(), data.InvoiceDate.max().date()),
        min_value=data.InvoiceDate.min().date(), max_value=data.InvoiceDate.max().date(),
        format="DD.MM.YYYY", key="period",
        help="Choose the first and last dates to include. Forecasts start after the last complete week in this period.",
    )
    category = st.selectbox("Category", ["All categories"] + sorted(data.Category.unique()), key="category",
                            help="Choose one book category, or leave all categories included.")
    city = st.selectbox("City", ["All cities"] + sorted(data.City.unique()), key="city",
                        help="Choose the customer city. Unknown means the source did not provide a city.")

if len(dates) != 2:
    st.info("Select both a start and an end date in the sidebar.")
    st.stop()
start, end = pd.Timestamp(dates[0]), pd.Timestamp(dates[1])
filtered = data[data.InvoiceDate.between(start, end)]
if category != "All categories":
    filtered = filtered[filtered.Category == category]
if city != "All cities":
    filtered = filtered[filtered.City == city]

section = st.segmented_control(
    "Explore", ["Overview", "Customers", "Products", "Forecast", "Data notes"],
    default="Overview", key="section", selection_mode="single", required=True,
)
st.caption(f"Viewing {start:%d.%m.%Y}–{end:%d.%m.%Y} · {category} · {city}")
if filtered.empty:
    st.info("No sales match this selection. Choose a wider period or All categories / All cities.")
    st.stop()

if section == "Overview":
    st.header("How are sales performing?")
    st.write("Start with the four figures below, then check when and where sales occur. Hover over a card's help icon for its definition.")
    sales = filtered.SalesAmount.sum()
    orders = filtered.InvoiceNo.nunique()
    cards = list(st.columns(4))
    metric(cards[0], "Total sales", money(sales), "Sum of quantity × net unit price for the selected positive sales. This is sales value, not profit.")
    metric(cards[1], "Orders", format_number(orders), "Number of distinct invoices. One invoice can contain several product lines.")
    metric(cards[2], "Units sold", format_number(filtered.Quantity.sum()), "Total number of items sold in the selected period.")
    metric(cards[3], "Average order", money(sales / orders), "Total sales divided by distinct invoices in this selection.")
    monthly = monthly_sales(filtered).rename_axis("Date").reset_index(name="Sales")
    monthly["Date"] = monthly.Date.dt.to_timestamp()
    left, right = st.columns(2)
    with left:
        line_chart(monthly, "Date", "Sales", "Sales over time", "Each point is a month's total sales. First and last months may cover only part of a month.", currency=True)
    cities = filtered.groupby("City").SalesAmount.sum().sort_values(ascending=False)
    with right:
        sales_bar(cities.head(8).rename_axis("City").reset_index(name="Sales"), "City", "Sales", "Where sales come from", "The eight largest customer cities by sales value. Hover over a bar for its exact amount.")
    share = cities.iloc[0] / sales * 100
    st.info(f"{cities.index[0]} contributes {format_number(share, 1)}% of selected sales. Review regional customer coverage before concentrating more sales effort there.", title="What this means")

elif section == "Customers":
    st.header("Who buys, and who comes back?")
    st.write("Compare customer value and repeat purchasing to guide account management.")
    customers = filtered.groupby("CustomerID").agg(
        Sales=("SalesAmount", "sum"), Orders=("InvoiceNo", "nunique"), LastPurchase=("InvoiceDate", "max")
    ).sort_values("Sales", ascending=False)
    repeat = (customers.Orders > 1).sum()
    cards = list(st.columns(3))
    metric(cards[0], "Customers", format_number(len(customers)), "Customers with at least one invoice in the selected view.")
    metric(cards[1], "Repeat buyers", format_number(repeat / len(customers) * 100, 1) + "%", "Share of selected customers with more than one distinct invoice in this period. This is not a retention or churn forecast.")
    metric(cards[2], "Sales per customer", money(customers.Sales.mean()), "Total selected sales divided by the number of customers.")
    sales_bar(customers.head(10).reset_index(), "CustomerID", "Sales", "Ten largest customers", "Ranks customers by sales value in your selection. Customer IDs identify business accounts.")
    inactive = ((end - customers.LastPurchase).dt.days >= 60).sum()
    if (end - start).days >= 60:
        st.info(f"{inactive} customers in this history have no recorded purchase in the final 60 days. Check these accounts for a reactivation campaign.", title="Marketing action")
    else:
        st.info("Select at least 60 days to screen customers for a reactivation campaign.", title="Marketing action")

elif section == "Products":
    st.header("Which products deserve attention?")
    st.write("Sales value identifies the important products. Variation in units sold shows which products need closer purchasing review.")
    products = product_analysis(filtered, start, end)
    a_products = products[products.ABCClass == "A"]
    a_share = a_products.TotalSales.sum() / products.TotalSales.sum() * 100
    cards = list(st.columns(3))
    metric(cards[0], "Products sold", format_number(len(products)), "Distinct product codes sold in the selected period.")
    metric(cards[1], "Priority products (A)", format_number(len(a_products)), "Products ranked from highest sales value until roughly 80% of total sales is reached. The item crossing the threshold stays in A.")
    metric(cards[2], "A products' sales share", format_number(a_share, 1) + "%", "Actual share of selected sales generated by A products. It can be slightly above 80%.")
    categories = category_performance(filtered).head(8)
    sales_bar(categories, "Category", "TotalRevenue", "Best-selling categories", "Sales after discounts, in Turkish lira. This compares sales value, not profit.")
    st.markdown("**Ten products to review first**")
    with st.container(horizontal=True):
        st.badge("A · High sales contribution", color="red")
        st.badge("B · Medium contribution", color="orange")
        st.badge("C · Low contribution", color="gray")
    st.caption("X/Y/Z = stable/moderate/variable monthly unit sales. N/A = insufficient complete-month history.")
    table = products.head(10).rename(columns={"Description": "Product", "TotalSales": "Sales (₺)", "ABCClass": "Sales priority", "XYZClass": "Demand pattern"})
    st.dataframe(table[["Product", "Sales (₺)", "Sales priority", "Demand pattern"]], hide_index=True, width="stretch",
                 column_config={"Sales (₺)": st.column_config.NumberColumn(format="₺ %.2f", help="Quantity × net unit price.")}, alt="Ten highest-value products and their priority classes")
    variable_a = ((products.ABCClass == "A") & (products.XYZClass == "Z")).sum()
    if products.CV.notna().any():
        st.info(f"{variable_a} priority products have variable monthly unit sales (AZ). Review their demand individually before purchasing; stock and supplier lead times are not available here.", title="Purchasing action")
    else:
        st.info("Select at least 3 complete calendar months to measure demand variation. Sales priority remains available.", title="More history needed")

elif section == "Forecast":
    render_forecast_page(filtered, start, end)

elif section == "Data notes":
    st.header("What is this dashboard based on?")
    st.write("Each row is an invoice product line. Sales = quantity × net price, in Turkish lira. The view covers recorded positive sales; it does not measure profit or available inventory.")
    st.markdown("**How the data was prepared**")
    st.write(f"{report['raw_rows']:,} original rows → {report['clean_rows']:,} usable sales rows.")
    st.dataframe(pd.DataFrame(report["steps"]), hide_index=True, width="stretch", alt="Rows excluded at each cleaning step")
    st.caption("Exact duplicate rows are treated as repeated records. Invalid essential fields, negative quantities and non-positive sales are excluded. Missing city/category values are retained as Unknown. Possible returns are not included in positive-sales totals.")
    st.markdown("**Your selected records**")
    preview = filtered[["InvoiceDate", "InvoiceNo", "Description", "City", "Quantity", "NetPrice", "SalesAmount"]].head(200)
    st.dataframe(preview, hide_index=True, width="stretch", column_config={
        "NetPrice": st.column_config.NumberColumn("Net unit price (₺)", format="₺ %.2f"),
        "SalesAmount": st.column_config.NumberColumn("Sales (₺)", format="₺ %.2f"),
    }, alt="First 200 selected sales lines")
    st.caption("The preview contains at most 200 rows; charts and totals use every matching row.")

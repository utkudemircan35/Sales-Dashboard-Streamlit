import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")


st.markdown("""
<style>
.stApp {
    background-color: #FFFFFF;
}

h1, h2, h3, p, label {
    color: #171717;
}

.page-title {
    color: #171717;
    font-size: 1.35rem;
    font-weight: 600;
    margin-bottom: 1rem;
}

.section-title {
    color: #333333;
    font-size: 0.9rem;
    font-weight: 600;
    margin: 0.6rem 0;
}

[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E5E5E5;
    border-radius: 8px;
    padding: 12px;
}

.chart-placeholder {
    height: 220px;
    border: 1px dashed #D8D8D8;
    border-radius: 6px;
    color: #888888;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
}

[data-baseweb="tab-highlight"] {
    background-color: #B4232F;
}

.stButton button, [data-testid="stFormSubmitButton"] button {
    min-height: 2rem;
    padding: 0.25rem 0.65rem;
    font-size: 0.8rem;
}
[data-testid="stMetricValue"],
[data-testid="stMetricValue"] * {
    font-size: 1.35rem !important;
    line-height: 1.2 !important;
}

[data-testid="stMetricLabel"] {
    font-size: 0.78rem !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.72rem !important;
}


</style>
""", unsafe_allow_html=True)


def prepare_data(file_name):
    data = pd.read_excel(file_name)
    data = data.drop_duplicates()

    data["SalesAmount"] = data["Quantity"] * data["NetPrice"]

    return data


def reset_filters(tab_name):
    for name in ["date", "description", "category", "city"]:
        st.session_state[f"{tab_name}_{name}"] = []

    st.session_state[f"{tab_name}_applied"] = False


def show_filters(data, tab_name, options):
    applied_key = f"{tab_name}_applied"

    if applied_key not in st.session_state:
        st.session_state[applied_key] = False

    with st.form(f"{tab_name}_filter_form"):
        columns = st.columns(4)

        with columns[0]:
            st.multiselect("Invoice Date", options["dates"], key=f"{tab_name}_date")
        with columns[1]:
            st.multiselect(
                "Description", options["descriptions"],
                key=f"{tab_name}_description"
            )
        with columns[2]:
            st.multiselect(
                "Category", options["categories"],
                key=f"{tab_name}_category"
            )
        with columns[3]:
            st.multiselect("City", options["cities"], key=f"{tab_name}_city")

        apply_col, reset_col = st.columns(2)

        with apply_col:
            apply_filters = st.form_submit_button("Apply")

        with reset_col:
            st.form_submit_button(
                "Reset",
                on_click=reset_filters,
                args=(tab_name,)
            )


    if apply_filters:
        st.session_state[applied_key] = True

    filtered_data = data

    if st.session_state[applied_key]:
        selected_dates = st.session_state[f"{tab_name}_date"]
        selected_descriptions = st.session_state[f"{tab_name}_description"]
        selected_categories = st.session_state[f"{tab_name}_category"]
        selected_cities = st.session_state[f"{tab_name}_city"]

        if selected_dates:
            filtered_data = filtered_data[
                filtered_data["InvoiceDate"].astype(str).isin(selected_dates)
            ]

        if selected_descriptions:
            filtered_data = filtered_data[
                filtered_data["Description"].astype(str).isin(
                    selected_descriptions
                )
            ]

        if selected_categories:
            filtered_data = filtered_data[
                filtered_data["Category"].astype(str).isin(selected_categories)
            ]

        if selected_cities:
            filtered_data = filtered_data[
                filtered_data["City"].astype(str).isin(selected_cities)
            ]

    return filtered_data


def show_cards(labels):
    columns = st.columns(4)

    for column, label in zip(columns, labels):
        with column:
            st.metric(label, "—")


def show_chart_placeholders(titles):
    left, right = st.columns(2)

    for column, title in zip([left, right], titles):
        with column:
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.markdown(
                    '<div class="chart-placeholder">Chart placeholder</div>',
                    unsafe_allow_html=True,
                )


data = prepare_data("B2B_Transaction_Data_.xlsx")

filter_options = {
    "dates": sorted(data["InvoiceDate"].dropna().astype(str).unique()),
    "descriptions": sorted(data["Description"].dropna().astype(str).unique()),
    "categories": sorted(data["Category"].dropna().astype(str).unique()),
    "cities": sorted(data["City"].dropna().astype(str).unique()),
}

st.markdown(
    '<div class="page-title">B2B Transaction Dashboard</div>',
    unsafe_allow_html=True,
)

sales_tab, customer_tab, product_tab, forecast_tab, raw_tab = st.tabs([
    "Sales & Cities",
    "Customer & Marketing",
    "Product & Supply",
    "Forecast & Integration",
    "Filtered & Raw Data",
])

with sales_tab:
    top_cards = st.container()
    lower_cards = st.container()

    st.markdown(
        '<div class="section-title">Filters</div>',
        unsafe_allow_html=True,
    )
    sales_data = show_filters(data, "sales", filter_options)

    total_sales = sales_data["SalesAmount"].sum()
    total_orders = sales_data["InvoiceNo"].nunique()
    units_sold = sales_data["Quantity"].sum()
    average_sales = total_sales / total_orders if total_orders else 0

    city_sales = (
        sales_data.dropna(subset=["City"])
        .groupby("City")["SalesAmount"]
        .sum()
    )

    category_sales = (
        sales_data.dropna(subset=["Category"])
        .groupby("Category")["SalesAmount"]
        .sum()
    )

    top_city = city_sales.idxmax() if not city_sales.empty else "—"
    top_city_sales = city_sales.max() if not city_sales.empty else 0
    top_city_share = (
        top_city_sales / total_sales * 100 if total_sales else 0
    )

    top_category = (
        category_sales.idxmax() if not category_sales.empty else "—"
    )
    top_category_sales = (
        category_sales.max() if not category_sales.empty else 0
    )

    period_data = sales_data.copy()
    period_data["InvoiceDate"] = pd.to_datetime(
        period_data["InvoiceDate"], errors="coerce"
    )
    period_data = period_data.dropna(subset=["InvoiceDate"])

    monthly_sales = period_data.groupby(
        period_data["InvoiceDate"].dt.to_period("M")
    )["SalesAmount"].sum().sort_index()

    weekly_sales = period_data.groupby(
        period_data["InvoiceDate"].dt.to_period("W")
    )["SalesAmount"].sum().sort_index()

    month_percent = None
    month_amount = None
    if len(monthly_sales) > 1:
        previous = monthly_sales.iloc[-2]
        current = monthly_sales.iloc[-1]
        month_amount = current - previous
        if previous != 0:
            month_percent = month_amount / previous * 100

    week_percent = None
    week_amount = None
    if len(weekly_sales) > 1:
        previous = weekly_sales.iloc[-2]
        current = weekly_sales.iloc[-1]
        week_amount = current - previous
        if previous != 0:
            week_percent = week_amount / previous * 100

    with top_cards:
        st.markdown(
            '<div class="section-title">Sales Overview</div>',
            unsafe_allow_html=True,
        )
        columns = st.columns(4)
        columns[0].metric("Total Sales", f"{total_sales:,.0f}")
        columns[1].metric("Total Orders", f"{total_orders:,}")
        columns[2].metric("Units Sold", f"{units_sold:,.0f}")
        columns[3].metric("Average Sales per Invoice", f"{average_sales:,.2f}")

    with lower_cards:
        left, right = st.columns(2)

        with left:
            st.markdown(
                '<div class="section-title">Sales Leaders</div>',
                unsafe_allow_html=True,
            )
            columns = st.columns(2)
            columns[0].metric(
                "Top City Sales Amount Share",
                f"{top_city} · {top_city_share:.1f}%",
                f"Sales: {top_city_sales:,.0f}",
                delta_color="off",
            )
            columns[1].metric(
                "Top Category",
                top_category,
                f"Sales: {top_category_sales:,.0f}",
                delta_color="off",
            )

        with right:
            st.markdown(
                '<div class="section-title">Sales Momentum</div>',
                unsafe_allow_html=True,
            )
            columns = st.columns(2)
            columns[0].metric(
                "Month-to-Month Sales Change",
                f"{month_percent:+.1f}%" if month_percent is not None else "—",
                f"{month_amount:+,.0f}" if month_amount is not None else None,
            )
            columns[1].metric(
                "Week-to-Week Sales Change",
                f"{week_percent:+.1f}%" if week_percent is not None else "—",
                f"{week_amount:+,.0f}" if week_amount is not None else None,
            )

    show_chart_placeholders(["Monthly Sales Trend", "Sales by City"])

with customer_tab:
    show_cards(["Customers", "Repeat Customers", "Customer Value", "RFM Segment"])
    st.markdown('<div class="section-title">Filters</div>', unsafe_allow_html=True)
    show_filters(data, "customer", filter_options)
    show_chart_placeholders(["Customer Segments", "Customer Value"])

with product_tab:
    show_cards(["Units Sold", "Top Product", "Top Category", "Product Share"])
    st.markdown('<div class="section-title">Filters</div>', unsafe_allow_html=True)
    show_filters(data, "product", filter_options)
    show_chart_placeholders(["Sales by Category", "Top Products"])

with forecast_tab:
    show_cards(["Forecasted Demand", "Forecast Method", "Forecast Error", "Forecast Horizon"])
    st.markdown('<div class="section-title">Filters</div>', unsafe_allow_html=True)
    show_filters(data, "forecast", filter_options)
    show_chart_placeholders(["Actual vs Forecast", "Forecast Error by Method"])

with raw_tab:
    st.markdown('<div class="section-title">Filters</div>', unsafe_allow_html=True)
    raw_data = show_filters(data, "raw", filter_options)
    st.dataframe(raw_data, use_container_width=True)
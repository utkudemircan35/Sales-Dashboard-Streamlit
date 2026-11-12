import pandas as pd
import streamlit as st
import altair as alt
from pathlib import Path

st.set_page_config(
    page_title="Bookstore B2B  Dashboard",
    page_icon="chart_with_upwards_trend",
    layout="wide")

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


@st.cache_data(
    show_spinner="Loading transaction data...",
    max_entries=1,
)
def prepare_data(file_name):
    prepared_file = Path(file_name).with_name(
        "B2B_Transaction_Data_prepared.parquet"
    )

    if prepared_file.exists():
        return pd.read_parquet(prepared_file)

    data = pd.read_excel(file_name)
    data = data.drop_duplicates()
    data = data.dropna()
    data = data[
        (data["Quantity"] > 0) &
        (data["NetPrice"] > 0) &
        (data["UnitPrice"] > 0)
    ]
    data["InvoiceDate"] = pd.to_datetime(data["InvoiceDate"])
    data["Description"] = data["Description"].astype(str)
    data["SalesAmount"] = data["Quantity"] * data["NetPrice"]
    data["Week"] = data["InvoiceDate"].dt.isocalendar().week
    data["Month"] = data["InvoiceDate"].dt.month

    return data


def format_number(value, decimal_places=0):
    number = f"{value:,.{decimal_places}f}"
    return number.replace(",", "X").replace(".", ",").replace("X", ".")


def format_change(value, decimal_places=0):
    sign = "+" if value > 0 else ""
    return sign + format_number(value, decimal_places)


def reset_filters(tab_name):
    for name in ["date", "week", "month", "description", "category", "city"]:
        st.session_state[f"{tab_name}_{name}"] = []

    st.session_state[f"{tab_name}_applied"] = False


def show_filters(data, tab_name, options):
    applied_key = f"{tab_name}_applied"

    if applied_key not in st.session_state:
        st.session_state[applied_key] = False

    with st.form(f"{tab_name}_filter_form"):
        columns = st.columns(6)

        with columns[0]:
            st.multiselect("Invoice Date", options["dates"], key=f"{tab_name}_date")
        with columns[1]:
            st.multiselect("Week", options["weeks"], key=f"{tab_name}_week")
        with columns[2]:
            st.multiselect("Month", options["months"], key=f"{tab_name}_month")
        with columns[3]:
            st.multiselect(
                "Description", options["descriptions"],
                key=f"{tab_name}_description"
            )
        with columns[4]:
            st.multiselect(
                "Category", options["categories"],
                key=f"{tab_name}_category"
            )
        with columns[5]:
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
        selected_weeks = st.session_state[f"{tab_name}_week"]
        selected_months = st.session_state[f"{tab_name}_month"]
        selected_descriptions = st.session_state[f"{tab_name}_description"]
        selected_categories = st.session_state[f"{tab_name}_category"]
        selected_cities = st.session_state[f"{tab_name}_city"]

        if selected_dates:
            filtered_data = filtered_data[
                filtered_data["InvoiceDate"].astype(str).isin(selected_dates)
            ]

        if selected_weeks:
            filtered_data = filtered_data[
                filtered_data["Week"].isin(selected_weeks)
            ]

        if selected_months:
            filtered_data = filtered_data[
                filtered_data["Month"].isin(selected_months)
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


def style_chart(chart):
    return (
        chart
        .properties(height=280)
        .configure_view(strokeWidth=0)
        .configure_axis(
            gridColor="#EEEEEE",
            labelColor="#555555",
            titleColor="#333333",
        )
        .configure_legend(
            labelColor="#555555",
            titleColor="#333333",
        )
        .configure(
            locale={
                "number": {
                    "decimal": ",",
                    "thousands": ".",
                    "grouping": [3],
                    "currency": ["", ""],
                }
            }
        )
    )


def show_chart(column, title, chart, is_empty):
    with column:
        with st.container(border=True):
            st.markdown(f"**{title}**")

            if is_empty:
                st.info("No data available for the selected filters.")
            else:
                st.altair_chart(style_chart(chart), use_container_width=True)


def show_sales_charts(
    period_data,
    monthly_sales,
    weekly_sales,
    city_sales,
):
    monthly_chart = monthly_sales.rename_axis("Month").reset_index(
        name="SalesAmount"
    )
    monthly_chart["Month"] = monthly_chart["Month"].astype(str)
    monthly_chart["SalesAmount"] = monthly_chart["SalesAmount"].round().astype(int)

    weekly_chart = weekly_sales.rename_axis("Week").reset_index(
        name="SalesAmount"
    )
    weekly_chart["Week"] = [
        week.start_time.strftime("%G-W%V") for week in weekly_chart["Week"]
    ]
    weekly_chart["SalesAmount"] = weekly_chart["SalesAmount"].round().astype(int)

    monthly_change = monthly_sales.pct_change(fill_method=None) * 100
    monthly_change = monthly_change.replace(
        [float("inf"), float("-inf")], pd.NA
    ).dropna()
    monthly_change_chart = monthly_change.rename_axis("Month").reset_index(
        name="ChangePercent"
    )
    monthly_change_chart["Month"] = monthly_change_chart["Month"].astype(str)
    monthly_change_chart["ChangePercent"] = (
        monthly_change_chart["ChangePercent"].round(1)
    )
    monthly_change_chart["ChangeLabel"] = monthly_change_chart[
        "ChangePercent"
    ].apply(lambda value: f"{format_change(value, 1)}%")

    city_chart = (
        city_sales.nlargest(10)
        .rename_axis("City")
        .reset_index(name="SalesAmount")
    )
    city_chart["SalesAmount"] = city_chart["SalesAmount"].round().astype(int)

    top_5_cities = city_sales.nlargest(5).index
    top_5_sales = city_sales.nlargest(5).sum()
    other_cities_sales = city_sales.sum() - top_5_sales

    city_share = pd.DataFrame({
        "City Group": ["Top 5 Cities", "Other Cities"],
        "SalesAmount": [top_5_sales, other_cities_sales],
    })
    city_share["SalesAmount"] = city_share["SalesAmount"].round().astype(int)
    city_share["Share"] = (
        city_share["SalesAmount"] / city_share["SalesAmount"].sum()
        if city_share["SalesAmount"].sum() > 0 else 0
    )

    top_city_data = period_data[
        period_data["City"].isin(top_5_cities)
    ].copy()
    top_city_data["Month"] = (
        top_city_data["InvoiceDate"].dt.to_period("M").astype(str)
    )
    top_city_data["Week"] = top_city_data["InvoiceDate"].dt.strftime("%G-W%V")

    monthly_city = (
        top_city_data.groupby(["Month", "City"])["SalesAmount"]
        .sum()
        .round()
        .astype(int)
        .reset_index()
    )

    weekly_city = (
        top_city_data.groupby(["Week", "City"])["SalesAmount"]
        .sum()
        .round()
        .astype(int)
        .reset_index()
    )

    sales_tooltip = alt.Tooltip(
        "SalesAmount:Q",
        title="Sales Amount",
        format=",.0f",
    )

    monthly_line = (
        alt.Chart(monthly_chart)
        .mark_line(color="#B4232F", point=True, strokeWidth=2)
        .encode(
            x=alt.X("Month:O", title="Month"),
            y=alt.Y(
                "SalesAmount:Q",
                title="Sales Amount",
                axis=alt.Axis(format=",.0f"),
            ),
            tooltip=[alt.Tooltip("Month:O", title="Month"), sales_tooltip],
        )
    )

    city_bar = (
        alt.Chart(city_chart)
        .mark_bar(color="#B4232F", cornerRadiusEnd=3)
        .encode(
            x=alt.X(
                "SalesAmount:Q",
                title="Sales Amount",
                axis=alt.Axis(format=",.0f"),
            ),
            y=alt.Y("City:N", title="City", sort="-x"),
            tooltip=[alt.Tooltip("City:N", title="City"), sales_tooltip],
        )
    )

    share_donut = (
        alt.Chart(city_share)
        .mark_arc(innerRadius=65, outerRadius=100)
        .encode(
            theta=alt.Theta("SalesAmount:Q"),
            color=alt.Color(
                "City Group:N",
                scale=alt.Scale(range=["#B4232F", "#E5E5E5"]),
                legend=alt.Legend(title=None),
            ),
            tooltip=[
                alt.Tooltip("City Group:N", title="City Group"),
                sales_tooltip,
                alt.Tooltip("Share:Q", title="Share", format=".1%"),
            ],
        )
    )

    city_colors = alt.Scale(
        range=["#B4232F", "#D75B65", "#E58B92", "#6F6F6F", "#AFAFAF"]
    )

    monthly_city_line = (
        alt.Chart(monthly_city)
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=alt.X("Month:O", title="Month"),
            y=alt.Y(
                "SalesAmount:Q",
                title="Sales Amount",
                axis=alt.Axis(format=",.0f"),
            ),
            color=alt.Color("City:N", scale=city_colors, legend=alt.Legend(title=None)),
            tooltip=[
                alt.Tooltip("Month:O", title="Month"),
                alt.Tooltip("City:N", title="City"),
                sales_tooltip,
            ],
        )
    )

    weekly_line = (
        alt.Chart(weekly_chart)
        .mark_line(color="#B4232F", point=True, strokeWidth=2)
        .encode(
            x=alt.X("Week:O", title="Week"),
            y=alt.Y(
                "SalesAmount:Q",
                title="Sales Amount",
                axis=alt.Axis(format=",.0f"),
            ),
            tooltip=[alt.Tooltip("Week:O", title="Week"), sales_tooltip],
        )
    )

    weekly_city_line = (
        alt.Chart(weekly_city)
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=alt.X("Week:O", title="Week"),
            y=alt.Y(
                "SalesAmount:Q",
                title="Sales Amount",
                axis=alt.Axis(format=",.0f"),
            ),
            color=alt.Color("City:N", scale=city_colors, legend=alt.Legend(title=None)),
            tooltip=[
                alt.Tooltip("Week:O", title="Week"),
                alt.Tooltip("City:N", title="City"),
                sales_tooltip,
            ],
        )
    )

    monthly_change_bar = (
        alt.Chart(monthly_change_chart)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X("Month:O", title="Month"),
            y=alt.Y(
                "ChangePercent:Q",
                title="Change (%)",
                axis=alt.Axis(format="+.0f"),
            ),
            color=alt.condition(
                alt.datum.ChangePercent >= 0,
                alt.value("#2E8B57"),
                alt.value("#B4232F"),
            ),
            tooltip=[
                alt.Tooltip("Month:O", title="Month"),
                alt.Tooltip("ChangeLabel:N", title="Change"),
            ],
        )
    )

    left, right = st.columns(2)
    show_chart(left, "Monthly Sales Trend", monthly_line, monthly_chart.empty)
    show_chart(
        right,
        "Top 10 Cities by Total Sales Amount",
        city_bar,
        city_chart.empty,
    )

    left, right = st.columns(2)
    show_chart(
        left,
        "Top 5 Cities vs Other Cities",
        share_donut,
        city_share["SalesAmount"].sum() == 0,
    )
    show_chart(
        right,
        "Monthly Sales Trend of Top 5 Cities",
        monthly_city_line,
        monthly_city.empty,
    )

    left, right = st.columns(2)
    show_chart(left, "Weekly Sales Trend", weekly_line, weekly_chart.empty)
    show_chart(
        right,
        "Weekly Sales Trend of Top 5 Cities",
        weekly_city_line,
        weekly_city.empty,
    )

    full_width = st.container()
    show_chart(
        full_width,
        "Month-to-Month Sales Change (%)",
        monthly_change_bar,
        monthly_change_chart.empty,
    )


def category_performance(data):
    category_data = (
        data.groupby("Category", observed=True)
        .agg(
            TotalRevenue=("SalesAmount", "sum"),
            TotalUnits=("Quantity", "sum"),
            ProductCount=("StockCode", "nunique"),
            InvoiceCount=("InvoiceNo", "nunique"),
        )
        .sort_values("TotalRevenue", ascending=False)
        .reset_index()
    )
    category_data["RevenueShare"] = (
        category_data["TotalRevenue"] / category_data["TotalRevenue"].sum()
    )
    return category_data


def product_performance(data):
    products = (
        data.groupby("StockCode", observed=True)
        .agg(
            Description=("Description", "first"),
            Category=("Category", "first"),
            TotalRevenue=("SalesAmount", "sum"),
            TotalUnits=("Quantity", "sum"),
        )
        .sort_values("TotalRevenue", ascending=False)
        .reset_index()
    )
    products["Description"] = products["Description"].astype(str)
    products["Category"] = products["Category"].astype(str)
    return products


def xyz_classification(value):
    if value <= 0.5:
        return "X"
    if value <= 1:
        return "Y"
    return "Z"


def abc_classification(value):
    if value <= 0.80:
        return "A"
    if value <= 0.95:
        return "B"
    return "C"


def abc_xyz_analysis(data):
    months = sorted(data["Month"].unique())

    monthly_products = (
        data.groupby(["StockCode", "Month"], observed=True)["SalesAmount"]
        .sum()
        .reset_index()
    )
    monthly_pivot = monthly_products.pivot(
        index="StockCode",
        columns="Month",
        values="SalesAmount",
    )
    monthly_pivot = monthly_pivot.reindex(columns=months).fillna(0)

    monthly_pivot["TotalSales"] = monthly_pivot[months].sum(axis=1)
    monthly_pivot["AverageSales"] = monthly_pivot["TotalSales"] / len(months)
    monthly_pivot["StandardDeviation"] = monthly_pivot[months].std(axis=1)
    monthly_pivot["CV"] = (
        monthly_pivot["StandardDeviation"] / monthly_pivot["AverageSales"]
    ).fillna(0)
    monthly_pivot["XYZClass"] = monthly_pivot["CV"].apply(
        xyz_classification
    )
    monthly_pivot = monthly_pivot.reset_index()

    abc_data = (
        monthly_pivot[["StockCode", "TotalSales"]]
        .sort_values("TotalSales", ascending=False)
        .reset_index(drop=True)
    )
    abc_data["CumulativeSales"] = abc_data["TotalSales"].cumsum()
    abc_data["CumulativeShare"] = (
        abc_data["CumulativeSales"] / abc_data["TotalSales"].sum()
    )
    abc_data["ABCClass"] = abc_data["CumulativeShare"].apply(
        abc_classification
    )

    abc_data = abc_data.merge(
        monthly_pivot[
            [
                "StockCode",
                "AverageSales",
                "StandardDeviation",
                "CV",
                "XYZClass",
            ]
        ],
        on="StockCode",
        how="left",
    )

    product_names = data.drop_duplicates("StockCode")[
        ["StockCode", "Description", "Category"]
    ]
    abc_data = abc_data.merge(product_names, on="StockCode", how="left")
    abc_data["Description"] = abc_data["Description"].astype(str)
    abc_data["Category"] = abc_data["Category"].astype(str)
    abc_data["StockClass"] = abc_data["ABCClass"] + abc_data["XYZClass"]
    abc_data["ProductRank"] = abc_data.index + 1
    return abc_data


@st.cache_data(show_spinner="Calculating product analysis...")
def run_product_analysis(product_data):
    return category_performance(product_data), abc_xyz_analysis(product_data)


def render_product_page(product_data):
    card_area = st.container()

    st.markdown(
        '<div class="section-title">Filters</div>',
        unsafe_allow_html=True,
    )
    product_data = show_filters(product_data, "product", filter_options)

    if product_data.empty:
        with card_area:
            show_cards(["Active Products", "Best Product Revenue", "Top Category", "A-Class Products"])
        st.warning("No data available for the selected filters.")
        return

    category_data, abc_data = run_product_analysis(product_data)

    if product_data["Month"].nunique() < 3:
        st.warning(
            "Demand variability (XYZ) needs at least 3 months of data. "
            "Please widen the date filter."
        )

    a_count = int((abc_data["ABCClass"] == "A").sum())
    top_product = abc_data.iloc[0]
    top_category = category_data.iloc[0]

    with card_area:
        st.markdown(
            '<div class="section-title">Product Overview</div>',
            unsafe_allow_html=True,
        )
        columns = st.columns(4)
        columns[0].metric("Active Products", format_number(len(abc_data)))
        columns[1].metric(
            "Best Product Revenue",
            format_number(top_product["TotalSales"]),
        )
        columns[2].metric(
            "Top Category",
            top_category["Category"],
            f"{format_number(top_category['RevenueShare'] * 100, 1)}% of revenue",
            delta_color="off",
        )
        columns[3].metric(
            "A-Class Products",
            format_number(a_count),
            f"{format_number(a_count / len(abc_data) * 100, 1)}% of products",
            delta_color="off",
        )

    category_tab, abc_tab, xyz_tab, insight_tab = st.tabs([
        "Category Performance",
        "ABC Analysis",
        "Demand Variability (XYZ)",
        "Insights",
    ])

    with category_tab:
        maximum = min(30, len(category_data))
        category_count = st.slider(
            "Number of categories to show",
            1,
            maximum,
            min(15, maximum),
        )
        top_categories = category_data.head(category_count)

        category_chart = (
            alt.Chart(top_categories)
            .mark_bar(color="#B4232F", cornerRadiusEnd=3)
            .encode(
                x=alt.X(
                    "TotalRevenue:Q",
                    title="Revenue",
                    axis=alt.Axis(format=",.0f"),
                ),
                y=alt.Y("Category:N", title="Category", sort="-x"),
                tooltip=[
                    alt.Tooltip("Category:N", title="Category"),
                    alt.Tooltip(
                        "TotalRevenue:Q",
                        title="Revenue",
                        format=",.0f",
                    ),
                    alt.Tooltip("TotalUnits:Q", title="Units", format=",.0f"),
                ],
            )
        )
        show_chart(
            st.container(),
            "Revenue by Category",
            category_chart,
            top_categories.empty,
        )

        selected_category = st.selectbox(
            "Category details",
            category_data["Category"],
        )
        selected_data = product_data[
            product_data["Category"] == selected_category
        ]
        monthly_category = (
            selected_data.groupby("Month", observed=True)["SalesAmount"]
            .sum()
            .round()
            .reset_index()
        )
        monthly_chart = (
            alt.Chart(monthly_category)
            .mark_line(color="#B4232F", point=True, strokeWidth=2)
            .encode(
                x=alt.X("Month:O", title="Month"),
                y=alt.Y(
                    "SalesAmount:Q",
                    title="Revenue",
                    axis=alt.Axis(format=",.0f"),
                ),
                tooltip=[
                    alt.Tooltip("Month:O", title="Month"),
                    alt.Tooltip(
                        "SalesAmount:Q",
                        title="Revenue",
                        format=",.0f",
                    ),
                ],
            )
        )
        show_chart(
            st.container(),
            f"Monthly Revenue of {selected_category}",
            monthly_chart,
            monthly_category.empty,
        )

        st.markdown("**Best Selling Products in This Category**")
        best_products = product_performance(selected_data).head(10)
        st.dataframe(
            best_products[["Description", "TotalRevenue", "TotalUnits"]],
            hide_index=True,
            use_container_width=True,
        )

    with abc_tab:
        abc_summary = (
            abc_data.groupby("ABCClass", observed=True)
            .agg(
                ProductCount=("StockCode", "count"),
                Revenue=("TotalSales", "sum"),
            )
            .reset_index()
        )
        abc_summary["RevenueShare"] = (
            abc_summary["Revenue"] / abc_summary["Revenue"].sum()
        )
        abc_summary["ProductShare"] = (
            abc_summary["ProductCount"] / abc_summary["ProductCount"].sum()
        )
        abc_summary["RevenueShare"] = abc_summary["RevenueShare"] * 100
        abc_summary["ProductShare"] = abc_summary["ProductShare"] * 100
        st.dataframe(
            abc_summary,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Revenue": st.column_config.NumberColumn(format="%.0f"),
                "RevenueShare": st.column_config.NumberColumn(format="%.1f%%"),
                "ProductShare": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

        step = max(1, len(abc_data) // 2000)
        pareto_data = abc_data.iloc[::step]
        pareto_line = (
            alt.Chart(pareto_data)
            .mark_line(color="#B4232F", strokeWidth=2)
            .encode(
                x=alt.X("ProductRank:Q", title="Product Rank"),
                y=alt.Y(
                    "CumulativeShare:Q",
                    title="Cumulative Revenue Share",
                    axis=alt.Axis(format=".0%"),
                ),
                tooltip=[
                    alt.Tooltip("ProductRank:Q", title="Rank"),
                    alt.Tooltip(
                        "CumulativeShare:Q",
                        title="Cumulative Share",
                        format=".1%",
                    ),
                ],
            )
        )
        threshold_data = pd.DataFrame({"Threshold": [0.80, 0.95]})
        threshold_lines = (
            alt.Chart(threshold_data)
            .mark_rule(color="#777777", strokeDash=[5, 5])
            .encode(y="Threshold:Q")
        )
        show_chart(
            st.container(),
            "Pareto Curve: Cumulative Revenue Share of Products",
            pareto_line + threshold_lines,
            pareto_data.empty,
        )

        selected_abc = st.selectbox(
            "Show products of ABC class",
            ["A", "B", "C"],
        )
        st.dataframe(
            abc_data[abc_data["ABCClass"] == selected_abc][
                ["Description", "Category", "TotalSales", "CV", "StockClass"]
            ].head(100),
            hide_index=True,
            use_container_width=True,
        )

    with xyz_tab:
        matrix = (
            abc_data.groupby(["ABCClass", "XYZClass"], observed=True)
            .size()
            .reset_index(name="ProductCount")
        )
        heatmap_base = alt.Chart(matrix).encode(
            x=alt.X("XYZClass:N", title="XYZ Class", sort=["X", "Y", "Z"]),
            y=alt.Y("ABCClass:N", title="ABC Class", sort=["A", "B", "C"]),
        )
        heatmap = heatmap_base.mark_rect().encode(
            color=alt.Color(
                "ProductCount:Q",
                scale=alt.Scale(range=["#F8E8EA", "#B4232F"]),
                legend=alt.Legend(title="Products"),
            ),
            tooltip=[
                alt.Tooltip("ABCClass:N", title="ABC Class"),
                alt.Tooltip("XYZClass:N", title="XYZ Class"),
                alt.Tooltip("ProductCount:Q", title="Products"),
            ],
        ) + heatmap_base.mark_text().encode(
            text="ProductCount:Q",
            color=alt.condition(
                alt.datum.ProductCount > matrix["ProductCount"].max() / 2,
                alt.value("white"),
                alt.value("#171717"),
            ),
        )
        show_chart(
            st.container(),
            "Number of Products in Each ABC-XYZ Class",
            heatmap,
            matrix.empty,
        )
        st.caption(
            "X: CV ≤ 0,5 (stable), Y: 0,5 < CV ≤ 1 (medium), "
            "Z: CV > 1 (highly variable). CV = monthly standard deviation / average."
        )

        cv_data = abc_data[abc_data["CV"] <= 4]
        cv_histogram = (
            alt.Chart(cv_data)
            .mark_bar(color="#B4232F")
            .encode(
                x=alt.X("CV:Q", bin=alt.Bin(maxbins=40), title="CV"),
                y=alt.Y("count():Q", title="Product Count"),
                tooltip=[alt.Tooltip("count():Q", title="Products")],
            )
        )
        show_chart(
            st.container(),
            "Distribution of CV (CV ≤ 4)",
            cv_histogram,
            cv_data.empty,
        )

        class_list = sorted(abc_data["StockClass"].unique())
        default_class = class_list.index("AZ") if "AZ" in class_list else 0
        selected_class = st.selectbox(
            "Show products of class",
            class_list,
            index=default_class,
        )
        st.dataframe(
            abc_data[abc_data["StockClass"] == selected_class][
                ["Description", "Category", "TotalSales", "CV"]
            ].head(100),
            hide_index=True,
            use_container_width=True,
        )

    with insight_tab:
        a_products = abc_data[abc_data["ABCClass"] == "A"]
        c_products = abc_data[abc_data["ABCClass"] == "C"]
        a_share = a_count / len(abc_data)
        c_share = len(c_products) / len(abc_data)
        c_revenue_share = (
            c_products["TotalSales"].sum() / abc_data["TotalSales"].sum()
        )
        az_count = int((abc_data["StockClass"] == "AZ").sum())
        az_share = az_count / len(a_products) if len(a_products) else 0
        top_five_share = category_data.head(5)["RevenueShare"].sum()
        monthly_total = product_data.groupby("Month")["SalesAmount"].sum()
        month_names = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December",
        }

        st.info(
            f"**Insight 1 - Concentration:** {format_number(a_share * 100, 1)}% "
            f"of products ({format_number(a_count)} items) create approximately "
            f"80% of revenue, while {format_number(c_share * 100, 1)}% of products "
            f"create only {format_number(c_revenue_share * 100, 1)}%."
        )
        st.warning(
            f"**Insight 2 - Risky A Products:** {format_number(az_count)} of "
            f"{format_number(len(a_products))} A-class products "
            f"({format_number(az_share * 100, 1)}%) have highly variable demand."
        )
        st.success(
            f"**Category and Season:** The top 5 categories bring "
            f"{format_number(top_five_share * 100, 1)}% of revenue. "
            f"Best month is {month_names[monthly_total.idxmax()]} and weakest "
            f"month is {month_names[monthly_total.idxmin()]}."
        )


data = prepare_data("B2B_Transaction_Data_.xlsx")

filter_options = {
    "dates": sorted(data["InvoiceDate"].dropna().astype(str).unique()),
    "weeks": sorted(data["Week"].dropna().unique()),
    "months": sorted(data["Month"].dropna().unique()),
    "descriptions": sorted(data["Description"].dropna().astype(str).unique()),
    "categories": sorted(data["Category"].dropna().astype(str).unique()),
    "cities": sorted(data["City"].dropna().astype(str).unique()),
}

st.markdown(
    '<div class="page-title">B2B Transaction Dashboard</div>',
    unsafe_allow_html=True,
)

sales_tab, customer_tab, product_tab, forecast_tab, raw_tab = st.tabs(
    [
        "Sales & Cities",
        "Customer & Marketing",
        "Product & Supply",
        "Forecast & Integration",
        "Filtered & Raw Data",
    ],
    key="main_tabs",
    on_change="rerun",
)

active_tab = st.session_state.get("main_tabs", "Sales & Cities")

if active_tab == "Sales & Cities":
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

    top_city = city_sales.idxmax() if not city_sales.empty else "—"
    top_city_sales = city_sales.max() if not city_sales.empty else 0
    top_5_cities_sales = city_sales.nlargest(5).sum()
    top_5_cities_share = (
        top_5_cities_sales / total_sales * 100 if total_sales else 0
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

    if not weekly_sales.empty:
        all_weeks = pd.period_range(
            weekly_sales.index.min(),
            weekly_sales.index.max(),
            freq="W",
        )
        weekly_sales = weekly_sales.reindex(all_weeks, fill_value=0)

    weekly_change_sales = weekly_sales.copy()

    if not weekly_change_sales.empty:
        first_week = weekly_change_sales.index[0]
        last_week = weekly_change_sales.index[-1]
        first_date = period_data["InvoiceDate"].min().normalize()
        last_date = period_data["InvoiceDate"].max().normalize()

        if first_date > first_week.start_time.normalize():
            weekly_change_sales = weekly_change_sales.iloc[1:]

        last_complete_day = (
            last_week.start_time + pd.Timedelta(days=5)
        ).normalize()
        if last_date < last_complete_day:
            weekly_change_sales = weekly_change_sales.iloc[:-1]

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
    if len(weekly_change_sales) > 1:
        previous = weekly_change_sales.iloc[-2]
        current = weekly_change_sales.iloc[-1]
        week_amount = current - previous
        if previous != 0:
            week_percent = week_amount / previous * 100

    with top_cards:
        st.markdown(
            '<div class="section-title">Sales Overview</div>',
            unsafe_allow_html=True,
        )
        columns = st.columns(4)
        columns[0].metric("Total Sales", format_number(total_sales))
        columns[1].metric("Total Orders", format_number(total_orders))
        columns[2].metric("Units Sold", format_number(units_sold))
        columns[3].metric(
            "Average Sales per Order",
            format_number(average_sales, 2),
        )

    with lower_cards:
        left, right = st.columns(2)

        with left:
            st.markdown(
                '<div class="section-title">Sales Leaders</div>',
                unsafe_allow_html=True,
            )
            columns = st.columns(2)
            columns[0].metric(
                "Top City",
                top_city,
                f"Sales: {format_number(top_city_sales)}",
                delta_color="off",
            )
            columns[1].metric(
                "Top 5 Cities Share",
                f"{format_number(top_5_cities_share, 1)}%",
                f"Sales: {format_number(top_5_cities_sales)}",
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
                f"{format_change(month_percent, 1)}%" if month_percent is not None else "—",
                format_change(month_amount) if month_amount is not None else None,
            )
            columns[1].metric(
                "Week-to-Week Sales Change",
                f"{format_change(week_percent, 1)}%" if week_percent is not None else "—",
                format_change(week_amount) if week_amount is not None else None,
            )

    show_sales_charts(
        period_data,
        monthly_sales,
        weekly_sales,
        city_sales,
    )

elif active_tab == "Customer & Marketing":
    show_cards(["Customers", "Repeat Customers", "Customer Value", "RFM Segment"])
    st.markdown('<div class="section-title">Filters</div>', unsafe_allow_html=True)
    show_filters(data, "customer", filter_options)
    show_chart_placeholders(["Customer Segments", "Customer Value"])

elif active_tab == "Product & Supply":
    render_product_page(data)

elif active_tab == "Forecast & Integration":
    show_cards(["Forecasted Demand", "Forecast Method", "Forecast Error", "Forecast Horizon"])
    st.markdown('<div class="section-title">Filters</div>', unsafe_allow_html=True)
    show_filters(data, "forecast", filter_options)
    show_chart_placeholders(["Actual vs Forecast", "Forecast Error by Method"])

elif active_tab == "Filtered & Raw Data":
    st.markdown('<div class="section-title">Filters</div>', unsafe_allow_html=True)
    raw_data = show_filters(data, "raw", filter_options)
    preview = raw_data.head(5000).copy()
    preview["Description"] = preview["Description"].astype(str)
    st.caption(
        f"Showing the first {format_number(len(preview))} of "
        f"{format_number(len(raw_data))} filtered rows."
    )
    st.dataframe(preview, use_container_width=True)

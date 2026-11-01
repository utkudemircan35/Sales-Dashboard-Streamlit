import pandas as pd
import streamlit as st
import altair as alt

import data_utils as du
import forecast_utils as fu

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


@st.cache_data(show_spinner="Loading data...")
def load_dashboard_bundle(file_name):
    """Read the Excel file once; return the cleaned Sales data and small
    Forecast artifacts built from that same data (no second row table)."""
    raw = pd.read_excel(file_name)
    duplicates = du.clean_transactions(raw[raw.duplicated()])
    data = du.clean_transactions(raw.drop_duplicates())
    forecast = fu.build_forecast_artifacts(data, duplicates)
    return data, forecast


def prepare_data(file_name):
    data, _ = load_dashboard_bundle(file_name)
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


def show_method_notes(notes, duplicate_info, test_weeks):
    with st.expander("Method notes"):
        st.markdown(f"""
**Data base.** Forecast uses the same valid transactions as the Sales tab:
exact duplicates removed, rows with any missing field dropped, positive
Quantity, NetPrice and UnitPrice, and a valid InvoiceDate
({notes["input_rows"]:,} rows, {notes["input_units"]:,.0f} units). Only
InvoiceDate, Category and Quantity are used.

**Weekly demand.** Quantity is summed per Monday-start week; weeks without
sales count as 0. Weeks that do not cover seven days of data are excluded.

**Model selection and backtest.** The last {test_weeks} weeks are held out as
the test period. Naive (last week's actual) and Moving Averages over 2, 4 and 8
weeks are compared on the training weeks only, with rolling one-step-ahead
forecasts after an 8-week warm-up (validation). The method with the lowest
validation MAE is recommended (ties go to the simpler method). Every method is
then scored once on the test weeks; test results are never used for selection.

**Data sufficiency.** A series needs at least {fu.minimum_weeks(test_weeks)}
weeks (8 warm-up + {fu.MIN_VALIDATION_WEEKS} validation + {test_weeks} test) and
sales in at least {fu.MIN_ACTIVE_SHARE:.0%} of weeks. When most weeks are zero
(intermittent demand), Naive and Moving Average forecasts swing between zero
and spikes and MAE becomes misleading; such series need intermittent-demand
methods (e.g. Croston), which are out of scope.

{fu.duplicate_note(duplicate_info)}
""")


def show_forecast_tab(forecast):
    weekly_table = forecast["weekly_table"]
    notes = forecast["notes"]
    duplicate_info = forecast["duplicate_info"]
    categories = sorted(c for c in weekly_table.columns if c != fu.TOTAL)

    with st.form("forecast_form"):
        columns = st.columns([1, 2, 1])
        scope = columns[0].radio("Scope", ["Overall", "Category"])
        category = columns[1].selectbox("Category", categories)
        test_weeks = columns[2].slider(
            "Test weeks", 4, 16, fu.DEFAULT_TEST_WEEKS
        )
        st.form_submit_button("Apply")

    column = category if scope == "Category" else fu.TOTAL
    series = weekly_table[column]
    result = fu.compare_methods(series, test_weeks=test_weeks)

    if not result.ok:
        for message in result.warnings:
            st.warning(f"**{column}**: {message} No forecast is shown for this series.")
        show_method_notes(notes, duplicate_info, test_weeks)
        return

    last_week = series.index[-1]
    st.markdown(
        '<div class="section-title">Next Week Forecast</div>',
        unsafe_allow_html=True,
    )
    left, right = st.columns([1, 3])
    left.metric(
        f"Week of {result.next_week:%d %b %Y}",
        f"{result.next_week_forecast:,.0f} units",
        f"Method: {result.recommended_method}",
        delta_color="off", delta_arrow="off",
    )
    partial_note = (
        f" The week of {notes['partial_week']:%d %b %Y} has only "
        f"{notes['partial_days']} days of data (up to {notes['last_date']:%d %b %Y}); "
        "that partial week is not used for training or evaluation."
        if notes["partial_week"] is not None else ""
    )
    right.caption(
        f"One-week-ahead forecast made from the last complete week "
        f"(week of {last_week:%d %b %Y}) with the recommended method, using all "
        f"complete weeks up to that point. It is not a forecast beyond the end "
        f"of the data set.{partial_note}"
    )

    st.markdown(
        f'<div class="section-title">Backtest · last {test_weeks} weeks '
        f"(held out, scored once)</div>",
        unsafe_allow_html=True,
    )
    columns = st.columns(4)
    columns[0].metric(
        "Recommended Method", result.recommended_method,
        f"Test MAE {result.recommended_test_mae:,.1f}",
        delta_color="off", delta_arrow="off",
        help=f"Lowest validation MAE over {result.validation_weeks} training weeks.",
    )
    columns[1].metric(
        "Best Moving Average", result.best_ma_method,
        f"Test MAE {result.best_ma_test_mae:,.1f}",
        delta_color="off", delta_arrow="off",
        help="Moving Average window with the lowest validation MAE.",
    )
    label, value, caption = fu.improvement_card(result)
    columns[2].metric(label, value, caption, delta_color="off", delta_arrow="off")
    columns[3].metric(
        f"Forecast Bias · {result.recommended_method}",
        f"{result.bias_pct:+.1f}%" if result.bias_pct is not None else "—",
        f"{result.bias:+,.1f} units/week ({result.bias_label})",
        delta_color="off", delta_arrow="off",
    )

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown(f"**Actual vs Forecast · {column}**")
            next_point = pd.Series(
                [series.iloc[-1], result.next_week_forecast],
                index=[last_week, result.next_week],
                name="Next week forecast",
            )
            history = pd.concat(
                [
                    series.rename("Actual"),
                    result.forecasts.drop(columns="Actual").add_suffix(" (backtest)"),
                    next_point,
                ],
                axis=1,
            )
            st.line_chart(history, height=260)
    with right:
        with st.container(border=True):
            st.markdown(f"**Test MAE by Method · last {test_weeks} weeks**")
            st.bar_chart(result.metrics.set_index("Method")["Test MAE"], height=260)

    st.dataframe(
        result.metrics,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Validation MAE": st.column_config.NumberColumn(format="%.1f"),
            "Test MAE": st.column_config.NumberColumn(format="%.1f"),
            "Test Bias": st.column_config.NumberColumn(format="%+.1f"),
            "Test Bias %": st.column_config.NumberColumn(format="%+.1f%%"),
            "Test Improvement vs Naive %": st.column_config.NumberColumn(
                format="%+.1f%%"
            ),
        },
    )
    show_method_notes(notes, duplicate_info, test_weeks)


data, forecast_bundle = load_dashboard_bundle("B2B_Transaction_Data_.xlsx")

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
    show_forecast_tab(forecast_bundle)

with raw_tab:
    st.markdown('<div class="section-title">Filters</div>', unsafe_allow_html=True)
    raw_data = show_filters(data, "raw", filter_options)
    preview_rows = st.selectbox("Preview rows", [1000, 5000, 10000], key="raw_rows")
    st.caption(f"Showing {min(preview_rows, len(raw_data)):,} of {len(raw_data):,} filtered rows")
    preview = raw_data.head(preview_rows).copy()
    preview["Description"] = preview["Description"].astype(str)
    st.dataframe(preview, use_container_width=True)

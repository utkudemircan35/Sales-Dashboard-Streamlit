"""Ufka uygun gecmis testleriyle basit tahmin yontemi secimi."""
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.linear_model import LinearRegression

from dashboard_utils import format_number, money, metric, line_chart

TIME_MODELS = ["Last week", "Last 4 weeks average", "Weighted 4 weeks", "Linear trend"]
MIN_TRAIN_WEEKS = 12


def complete_week_index(start, end):
    start, end = pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
    weeks = pd.period_range(start, end, freq="W")
    return weeks[(weeks.start_time >= start) & (weeks.end_time.normalize() <= end)]


def prepare_weekly_data(data, weeks):
    weekly = data.groupby(data["InvoiceDate"].dt.to_period("W")).agg(
        SalesAmount=("SalesAmount", "sum"), Units=("Quantity", "sum"),
    ).reindex(weeks, fill_value=0).rename(columns={"SalesAmount": "Sales Amount"})
    weekly["Period"] = np.arange(1, len(weekly) + 1)
    weekly["Week Start"] = weeks.start_time
    return weekly.reset_index(drop=True)


def error_scores(actual, predicted):
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    error = actual - predicted
    total = np.abs(actual).sum()
    variation = ((actual - actual.mean()) ** 2).sum()
    return {
        "MAE": np.abs(error).mean(),
        "RMSE": np.sqrt((error ** 2).mean()),
        "WAPE (%)": np.abs(error).sum() / total * 100 if total else np.nan,
        "MAPE (%)": np.abs(error / actual).mean() * 100 if (actual != 0).all() else np.nan,
        "R2": 1 - (error ** 2).sum() / variation if variation else np.nan,
    }


def predict_time_model(name, train, target, periods):
    values = train[target]
    if name == "Last week":
        predicted = np.repeat(values.iloc[-1], len(periods))
    elif name == "Last 4 weeks average":
        predicted = np.repeat(values.tail(4).mean(), len(periods))
    elif name == "Weighted 4 weeks":
        recent = values.tail(4)
        # En yeni hafta en buyuk agirligi alir: 1, 2, 3, 4.
        level = np.average(recent, weights=np.arange(1, len(recent) + 1))
        predicted = np.repeat(level, len(periods))
    elif name == "Linear trend":
        model = LinearRegression().fit(train[["Period"]], values)
        predicted = model.predict(pd.DataFrame({"Period": np.asarray(periods)}))
    else:
        raise ValueError(f"Unknown forecasting method: {name}")
    return np.maximum(predicted, 0)


def required_weeks(horizon):
    # 12 egitim + en az 2 dogrulama penceresi + 1 bagimsiz test penceresi.
    return MIN_TRAIN_WEEKS + 3 * horizon


def selection_origins(week_count, horizon):
    if horizon not in [4, 8, 12]:
        raise ValueError("Forecast horizon must be 4, 8 or 12 weeks.")
    if week_count < required_weeks(horizon):
        raise ValueError(f"At least {required_weeks(horizon)} complete weeks are needed.")
    development_end = week_count - horizon
    fold_count = min(3, (development_end - MIN_TRAIN_WEEKS) // horizon)
    # Pencereler cakismadan ilerler ve son test doneminden once biter.
    return [development_end - fold * horizon for fold in range(fold_count, 0, -1)]


def select_model(weekly, target, horizon):
    """Son h hafta burada okunmaz. Her pencere kendi gecmisiyle egitilir."""
    origins = selection_origins(len(weekly), horizon)
    rows = []
    for name in TIME_MODELS:
        actual, predicted = [], []
        for origin in origins:
            train = weekly.iloc[:origin]
            validation = weekly.iloc[origin:origin + horizon]
            forecast = predict_time_model(name, train, target, validation["Period"])
            actual.extend(validation[target].tolist())
            predicted.extend(forecast.tolist())
        rows.append({"Model": name, **error_scores(actual, predicted), "Windows": len(origins)})
    # Ayni gercek degerler kullanildigi icin MAE ve WAPE ayni siralamayi verir.
    comparison = pd.DataFrame(rows).sort_values("MAE", kind="stable").reset_index(drop=True)
    return comparison, origins


def evaluate_forecast(weekly, target, horizon):
    comparison, origins = select_model(weekly, target, horizon)
    selected = comparison.iloc[0]["Model"]
    test_start = len(weekly) - horizon
    train, test = weekly.iloc[:test_start], weekly.iloc[test_start:]
    # Yontem secildikten sonra bagimsiz test sadece bir kez acilir.
    test_prediction = predict_time_model(selected, train, target, test["Period"])
    test_table = pd.DataFrame({
        "Week starting": test["Week Start"].to_numpy(),
        "Actual": test[target].to_numpy(), "Predicted": test_prediction,
    })
    future_periods = np.arange(len(weekly) + 1, len(weekly) + horizon + 1)
    # Gelecek icin ayni secili yontem, tum gozlenen haftalarla yeniden kurulur.
    future = predict_time_model(selected, weekly, target, future_periods)
    return {
        "model": selected, "comparison": comparison, "origins": origins,
        "test_start": test_start, "test_table": test_table,
        "test_scores": error_scores(test[target], test_prediction), "future": future,
    }


def render_forecast_page(data, start, end):
    st.header("What could the next weeks look like?")
    st.write("The method is selected automatically using past forecasts of the same length as your chosen horizon. A separate final period checks the selected method.")
    left, right = st.columns(2)
    target_label = left.segmented_control(
        "What to estimate", ["Units sold", "Sales (₺)"], default="Units sold",
        required=True, key="forecast_target",
        help="Units support demand planning. Sales value is expressed in Turkish lira.",
    )
    horizon = right.selectbox(
        "Weeks ahead", [4, 8, 12], key="forecast_horizon",
        help="Past validation windows, the independent final test and the future forecast all use this number of weeks.",
    )
    target = "Units" if target_label == "Units sold" else "Sales Amount"
    currency = target == "Sales Amount"
    weeks = complete_week_index(start, end)
    minimum = required_weeks(horizon)
    if len(weeks) < minimum:
        st.info(f"Select at least {minimum} complete calendar weeks for a {horizon}-week forecast. This leaves 12 initial training weeks, at least two validation windows and one independent test. Widen the sidebar period or choose a shorter horizon.")
        return
    weekly = prepare_weekly_data(data, weeks)
    if weekly.Units.sum() == 0:
        st.info("There are no sales in the complete weeks of this selection.")
        return
    result = evaluate_forecast(weekly, target, horizon)
    future = result["future"]
    selected = result["model"]
    score = result["test_scores"]
    future_dates = pd.date_range(weeks[-1].start_time + pd.Timedelta(weeks=1), periods=horizon, freq="W-MON")
    st.caption(f"Selected method: {selected} · Compared on {len(result['origins'])} past {horizon}-week windows · Lowest average absolute validation error wins.")
    columns = st.columns(3)
    total = money(future.sum()) if currency else format_number(future.sum()) + " units"
    average = money(future.mean()) if currency else format_number(future.mean()) + " units"
    error_label = format_number(score["WAPE (%)"], 1) + "%" if pd.notna(score["WAPE (%)"]) else "Not available"
    metric(columns[0], f"Next {horizon} weeks", total, "Sum of weekly estimates from the automatically selected method. Estimates are not booked orders.")
    metric(columns[1], "Average per week", average, "Total forecast divided by the selected number of weeks.")
    metric(columns[2], "Independent test error", error_label,
           f"WAPE on the final {horizon} complete weeks, excluded from model selection. Total absolute error / total actual sales. Lower is better; this is not guaranteed future accuracy.")
    st.caption(f"Forecast window: {future_dates[0]:%d.%m.%Y}–{(future_dates[-1] + pd.Timedelta(days=6)):%d.%m.%Y}. Dates follow this historical dataset, not today's date. Partial boundary weeks are excluded.")
    actual = pd.DataFrame({"Date": weekly["Week Start"], "Value": weekly[target], "Series": "Recorded"})
    estimated = pd.DataFrame({"Date": future_dates, "Value": future, "Series": "Forecast"})
    line_chart(pd.concat([actual, estimated], ignore_index=True), "Date", "Value",
               "Recorded sales and the next weeks",
               "Grey points are recorded weekly sales. The thicker red dashed line is the selected method's forecast. Hover over a point for its date and value.",
               series="Series", currency=currency)
    if np.allclose(future, future[0]):
        explanations = {
            "Last week": "The selected method repeats the latest recorded week's sales.",
            "Last 4 weeks average": "The selected method repeats the average of the latest four weeks.",
            "Weighted 4 weeks": "The selected method uses a four-week average with more weight on recent weeks.",
            "Linear trend": "The fitted trend is flat or reaches the zero-sales floor.",
        }
        st.info(f"{explanations[selected]} This produces a flat forecast by design. It was chosen by validation error, not by the shape of its line.", title="Why the forecast is flat")
    else:
        st.info("The selected trend changes over time. Its direction alone does not establish accuracy; review the independent test error above.", title="How to read the forecast")
    st.caption("Use estimates alongside current stock, supplier lead times and promotions. Error can vary between periods and may be higher in future weeks.")
    with st.expander("How was this checked?", key="forecast_details", on_change="rerun"):
        st.write(f"Each method is tested on {len(result['origins'])} successive, non-overlapping {horizon}-week windows. At each start date, only earlier weeks train the method. All methods use exactly the same actual sales; no test values are changed or removed.")
        st.dataframe(result["comparison"].round(2), hide_index=True, width="stretch", column_config={
            "MAE": st.column_config.NumberColumn("Validation MAE (₺)" if currency else "Validation MAE (units)"),
            "WAPE (%)": st.column_config.NumberColumn("Validation WAPE (%)"),
            "RMSE": st.column_config.NumberColumn("Validation RMSE (₺)" if currency else "Validation RMSE (units)"),
        }, alt="Simple methods ranked only on past validation windows")
        test = result["test_table"]
        st.write(f"The last {horizon} complete weeks ({test['Week starting'].iloc[0]:%d.%m.%Y}–{(test['Week starting'].iloc[-1] + pd.Timedelta(days=6)):%d.%m.%Y}) are held back from method selection. The error card reports this independent test. The method is then refitted on all complete weeks for the future forecast.")
        st.dataframe(test, hide_index=True, width="stretch", column_config={
            "Actual": st.column_config.NumberColumn("Actual (₺)" if currency else "Actual units", format="₺ %.2f" if currency else "%.0f"),
            "Predicted": st.column_config.NumberColumn("Predicted (₺)" if currency else "Predicted units", format="₺ %.2f" if currency else "%.0f"),
        }, alt="Unchanged actual sales and selected-method predictions in the independent test")
        st.caption("Weighted 4 weeks uses weights 1, 2, 3, 4 from oldest to newest. Weeks without transactions count as zero sales. WAPE is unavailable for an all-zero test. Model selection uses MAE, so zero-sales weeks are still included. One year does not establish reliable annual seasonality.")
        table = pd.DataFrame({"Week starting": future_dates, "Estimate": future})
        st.dataframe(table, hide_index=True, width="stretch", column_config={
            "Estimate": st.column_config.NumberColumn("Sales estimate (₺)" if currency else "Unit estimate", format="₺ %.2f" if currency else "%.0f"),
        }, alt="Weekly estimates from the automatically selected method")

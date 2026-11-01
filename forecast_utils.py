"""Pure pandas helpers for the Forecast & Integration tab (no Streamlit import)."""

from dataclasses import dataclass, field

import pandas as pd

TOTAL = "All categories"
UNKNOWN_CATEGORY = "Unknown"
NAIVE = "Naive"
DEFAULT_WINDOWS = (2, 4, 8)
DEFAULT_TEST_WEEKS = 8
MIN_VALIDATION_WEEKS = 8
MIN_ACTIVE_SHARE = 0.5
NEUTRAL_BIAS = "neutral/no bias"


def duplicate_summary(raw):
    """Count exact duplicate rows (every column identical) and their units.

    Returns a dict with row/unit counts and shares plus `rows`: the duplicate
    copies that drop_duplicates() would remove (InvoiceDate, Category, Quantity).
    """
    duplicated = raw.duplicated()
    quantity = pd.to_numeric(raw["Quantity"], errors="coerce")
    total_units = float(quantity.sum())
    units = float(quantity[duplicated].sum())
    return {
        "rows": raw.loc[duplicated, ["InvoiceDate", "Category", "Quantity"]].copy(),
        "row_count": int(duplicated.sum()),
        "total_rows": int(len(raw)),
        "row_share": float(duplicated.mean()) * 100 if len(raw) else 0.0,
        "units": units,
        "unit_share": units / total_units * 100 if total_units else 0.0,
    }


def clean_quantity(data):
    """Split rows into positive demand rows and negative (possible return) rows.

    Quantity is converted with pd.to_numeric(errors="coerce"). Rows with a
    missing/unparseable date, a non-numeric quantity, or a missing/zero quantity
    are dropped. Returns (sales, returns, notes); notes holds the row counts.
    """
    frame = data[["InvoiceDate", "Category", "Quantity"]].copy()
    frame["InvoiceDate"] = pd.to_datetime(frame["InvoiceDate"], errors="coerce")
    frame["Category"] = (
        frame["Category"].astype("object").fillna(UNKNOWN_CATEGORY).astype(str)
    )
    numeric = pd.to_numeric(frame["Quantity"], errors="coerce")
    non_numeric = numeric.isna() & frame["Quantity"].notna()
    frame["Quantity"] = numeric

    bad_date = frame["InvoiceDate"].isna()
    bad_quantity = frame["Quantity"].isna() | (frame["Quantity"] == 0)
    frame = frame[~bad_date & ~bad_quantity]

    returns = frame[frame["Quantity"] < 0]
    sales = frame[frame["Quantity"] > 0]
    notes = {
        "invalid_date_rows": int(bad_date.sum()),
        "non_numeric_quantity_rows": int((~bad_date & non_numeric).sum()),
        "missing_or_zero_quantity_rows": int(
            (~bad_date & bad_quantity & ~non_numeric).sum()
        ),
        "return_rows": int(len(returns)),
        "return_units": abs(float(returns["Quantity"].sum())),
    }
    return sales, returns, notes


def week_start(dates):
    return dates.dt.normalize() - pd.to_timedelta(dates.dt.dayofweek, unit="D")


def build_weekly_table(sales, data_start=None, data_end=None, drop_partial=True):
    """Weekly (Monday-start) Quantity per category plus a TOTAL column.

    Weeks without sales are filled with 0. When drop_partial is True the first
    week (if data_start is not a Monday) and the last week (if data_end is not a
    Sunday) are removed because they do not cover seven days.
    """
    if sales.empty:
        return pd.DataFrame(columns=[TOTAL])

    data_start = pd.Timestamp(data_start) if data_start is not None else sales["InvoiceDate"].min()
    data_end = pd.Timestamp(data_end) if data_end is not None else sales["InvoiceDate"].max()

    table = (
        sales.assign(Week=week_start(sales["InvoiceDate"]))
        .groupby(["Week", "Category"], observed=True)["Quantity"]
        .sum()
        .unstack("Category", fill_value=0)
    )
    full_index = pd.date_range(table.index.min(), table.index.max(), freq="W-MON")
    table = table.reindex(full_index, fill_value=0)
    table.insert(0, TOTAL, table.sum(axis=1))
    table.index.name = "Week"

    if drop_partial:
        if data_start.dayofweek != 0:
            table = table[table.index > data_start.normalize() - pd.Timedelta(days=data_start.dayofweek)]
        if data_end.dayofweek != 6:
            last_week = data_end.normalize() - pd.Timedelta(days=data_end.dayofweek)
            table = table[table.index < last_week]
    return table


def build_weekly_series(sales, category=None, **kwargs):
    """Weekly Quantity series for one category (None = overall total)."""
    table = build_weekly_table(sales, **kwargs)
    column = category or TOTAL
    if column not in table.columns:
        return pd.Series(dtype="float64", name=column)
    return table[column].rename(column)


def method_names(windows=DEFAULT_WINDOWS):
    return [NAIVE] + [f"MA({window})" for window in windows]


def method_window(method):
    return 1 if method == NAIVE else int(method[3:-1])


def one_step_forecasts(series, method):
    """One-step-ahead forecast for every week, using only earlier weeks.

    Naive is the previous week's actual; MA(k) is the mean of the k weeks
    before the forecast week (the week itself is never included).
    """
    return series.rolling(method_window(method)).mean().shift(1)


def naive_forecast(series, test_weeks=DEFAULT_TEST_WEEKS):
    return one_step_forecasts(series, NAIVE).iloc[-test_weeks:]


def moving_average_forecast(series, window, test_weeks=DEFAULT_TEST_WEEKS):
    return one_step_forecasts(series, f"MA({window})").iloc[-test_weeks:]


def next_week_forecast(series, method):
    """Forecast for the week after the last week in `series` (history only)."""
    window = method_window(method)
    value = float(series.iloc[-window:].mean())
    return series.index[-1] + pd.Timedelta(days=7), value


def split_train_test(series, test_weeks=DEFAULT_TEST_WEEKS):
    return series.iloc[:-test_weeks], series.iloc[-test_weeks:]


def minimum_weeks(test_weeks=DEFAULT_TEST_WEEKS, max_window=max(DEFAULT_WINDOWS)):
    return test_weeks + max_window + MIN_VALIDATION_WEEKS


def check_data_sufficiency(series, test_weeks=DEFAULT_TEST_WEEKS, max_window=max(DEFAULT_WINDOWS)):
    """Return (ok, message). The message is empty when the data are sufficient."""
    needed = minimum_weeks(test_weeks, max_window)
    if len(series) < needed:
        return False, (
            f"Not enough history: {len(series)} weeks available, at least {needed} "
            f"needed ({max_window} warm-up + {MIN_VALIDATION_WEEKS} validation "
            f"+ {test_weeks} test)."
        )
    active = (series > 0).mean()
    if active < MIN_ACTIVE_SHARE:
        return False, (
            f"Sparse demand: only {active:.0%} of weeks have sales "
            f"(minimum {MIN_ACTIVE_SHARE:.0%})."
        )
    if (series.iloc[-test_weeks:] == 0).all():
        return False, "No sales in the test period."
    return True, ""


def mae(actual, forecast):
    if len(actual) != len(forecast):
        raise ValueError("actual and forecast must have the same length")
    return float((actual - forecast).abs().mean())


def forecast_bias(actual, forecast):
    """Return (mean signed error, bias %). Positive = over-forecast.

    Bias % is sum(forecast - actual) / sum(actual) * 100, None when actuals sum to 0.
    """
    error = forecast - actual
    total = float(actual.sum())
    percent = float(error.sum()) / total * 100 if total else None
    return float(error.mean()), percent


def classify_bias(bias):
    if abs(bias) < 1e-9:
        return NEUTRAL_BIAS
    return "over-forecast" if bias > 0 else "under-forecast"


def improvement_vs_naive(naive_mae, method_mae):
    return (naive_mae - method_mae) / naive_mae * 100 if naive_mae else None


@dataclass
class ForecastResult:
    ok: bool
    warnings: list = field(default_factory=list)
    metrics: pd.DataFrame = field(default_factory=pd.DataFrame)
    forecasts: pd.DataFrame = field(default_factory=pd.DataFrame)
    validation_weeks: int = 0
    recommended_method: str = ""
    best_ma_method: str = ""
    recommended_test_mae: float = 0.0
    best_ma_test_mae: float = 0.0
    naive_test_mae: float = 0.0
    improvement_pct: float = None
    best_ma_improvement_pct: float = None
    bias: float = None
    bias_pct: float = None
    bias_label: str = ""
    next_week: pd.Timestamp = None
    next_week_forecast: float = None


def compare_methods(series, windows=DEFAULT_WINDOWS, test_weeks=DEFAULT_TEST_WEEKS):
    """Select a method on training data, then score every method once on test.

    The last `test_weeks` weeks are held out. Inside the training weeks, after a
    warm-up of max(windows) weeks, every method makes rolling one-step-ahead
    forecasts; the lowest validation MAE picks the recommended method (any
    method) and the best moving average. Ties go to the simpler method.
    """
    max_window = max(windows)
    ok, message = check_data_sufficiency(series, test_weeks, max_window)
    if not ok:
        return ForecastResult(ok=False, warnings=[message])

    methods = method_names(windows)
    predictions = pd.DataFrame({m: one_step_forecasts(series, m) for m in methods})
    train, test = split_train_test(series, test_weeks)
    validation = train.iloc[max_window:]

    rows = []
    for method in methods:
        test_forecast = predictions[method].loc[test.index]
        bias, bias_pct = forecast_bias(test, test_forecast)
        rows.append({
            "Method": method,
            "Validation MAE": mae(validation, predictions[method].loc[validation.index]),
            "Test MAE": mae(test, test_forecast),
            "Test Bias": bias,
            "Test Bias %": bias_pct,
        })
    metrics = pd.DataFrame(rows)
    naive_test_mae = float(metrics["Test MAE"].iloc[0])
    metrics["Test Improvement vs Naive %"] = [
        improvement_vs_naive(naive_test_mae, value) for value in metrics["Test MAE"]
    ]

    recommended = metrics.loc[metrics["Validation MAE"].idxmin()]
    ma_rows = metrics[metrics["Method"] != NAIVE]
    best_ma = ma_rows.loc[ma_rows["Validation MAE"].idxmin()]
    next_week, next_value = next_week_forecast(series, recommended["Method"])

    return ForecastResult(
        ok=True,
        metrics=metrics,
        forecasts=pd.concat([test.rename("Actual"), predictions.loc[test.index]], axis=1),
        validation_weeks=len(validation),
        recommended_method=recommended["Method"],
        best_ma_method=best_ma["Method"],
        recommended_test_mae=float(recommended["Test MAE"]),
        best_ma_test_mae=float(best_ma["Test MAE"]),
        naive_test_mae=naive_test_mae,
        improvement_pct=improvement_vs_naive(naive_test_mae, recommended["Test MAE"]),
        best_ma_improvement_pct=improvement_vs_naive(naive_test_mae, best_ma["Test MAE"]),
        bias=float(recommended["Test Bias"]),
        bias_pct=None if pd.isna(recommended["Test Bias %"]) else float(recommended["Test Bias %"]),
        bias_label=classify_bias(float(recommended["Test Bias"])),
        next_week=next_week,
        next_week_forecast=next_value,
    )


def method_ranking(series, windows=DEFAULT_WINDOWS, test_weeks=DEFAULT_TEST_WEEKS):
    """Methods ordered by test MAE (best first), or None if data are insufficient."""
    result = compare_methods(series, windows, test_weeks)
    if not result.ok:
        return None
    return result.metrics.sort_values("Test MAE", kind="stable")["Method"].tolist()


RANKING_UNCHANGED = "unchanged"
RANKING_CHANGED = "changed"
RANKING_NOT_COMPARABLE = "not comparable"


def compare_rankings(first, second):
    """Three-state comparison of two method rankings (None = not computed)."""
    if first is None or second is None:
        return RANKING_NOT_COMPARABLE
    return RANKING_UNCHANGED if first == second else RANKING_CHANGED


def duplicate_effect(weekly_table, duplicate_table, test_weeks=DEFAULT_TEST_WEEKS):
    """Effect of exact duplicate rows on the forecast inputs.

    `duplicate_table` holds the weekly units of the removed duplicate rows on
    the same index/columns as `weekly_table`. Returns the overall ranking status
    (with duplicates removed vs kept, on `test_weeks` test weeks) and the
    category with the largest duplicate share, or None values when there is no
    duplicate quantity to compare.
    """
    if float(duplicate_table[TOTAL].sum()) == 0:
        return {"ranking_status": None, "max_category": None, "max_category_share": None}

    ranking_status = compare_rankings(
        method_ranking(weekly_table[TOTAL], test_weeks=test_weeks),
        method_ranking((weekly_table + duplicate_table)[TOTAL], test_weeks=test_weeks),
    )
    category_units = weekly_table.drop(columns=TOTAL).sum()
    duplicate_units = duplicate_table.drop(columns=TOTAL).sum()
    share = (duplicate_units / category_units * 100)[category_units > 0]
    share = share[share > 0]
    if share.empty:
        return {"ranking_status": ranking_status, "max_category": None, "max_category_share": None}
    return {
        "ranking_status": ranking_status,
        "max_category": share.idxmax(),
        "max_category_share": float(share.max()),
    }


def improvement_card(result):
    """(label, value, caption) for the improvement card of a ForecastResult."""
    def percent(value):
        return f"{value:+.1f}%" if value is not None else "—"

    label = f"Improvement vs Naive · {result.recommended_method}"
    if result.recommended_method == NAIVE:
        caption = f"Best {result.best_ma_method} vs Naive: {percent(result.best_ma_improvement_pct)}"
    else:
        caption = f"Naive test MAE {result.naive_test_mae:,.1f}"
    return label, percent(result.improvement_pct), caption


def duplicate_note(duplicate_info):
    """Method-notes paragraph built from duplicate_summary + duplicate_effect.

    Only states results that were measured: no ranking or category sentence
    when there are no duplicates or nothing could be compared.
    """
    if duplicate_info["row_count"] == 0:
        return (
            "**Duplicate rows.** A duplicate is a row whose every column is "
            "identical to an earlier row. No such rows were found, so nothing "
            "was removed."
        )

    text = (
        "**Duplicate rows.** A duplicate is a row whose every column is identical "
        "to an earlier row. As in all other tabs, these rows are removed with "
        f"`drop_duplicates()`: {duplicate_info['row_count']:,} of "
        f"{duplicate_info['total_rows']:,} rows ({duplicate_info['row_share']:.2f}%), "
        f"{duplicate_info['units']:,.0f} units ({duplicate_info['unit_share']:.2f}% "
        "of total quantity). Rows that share an invoice and stock code but differ "
        "in any field are kept."
    )
    setting = f"the default {DEFAULT_TEST_WEEKS}-week test setting"
    status = duplicate_info["ranking_status"]
    if status == RANKING_UNCHANGED:
        text += (
            " Keeping the duplicates does not change the overall test MAE ranking "
            f"of the methods (checked with {setting})."
        )
    elif status == RANKING_CHANGED:
        text += (
            " Keeping the duplicates changes the overall test MAE ranking of the "
            f"methods (checked with {setting})."
        )
    elif status == RANKING_NOT_COMPARABLE:
        text += (
            " The effect on the overall method ranking could not be compared "
            "because at least one of the two series has insufficient data under "
            f"{setting}."
        )
    if duplicate_info["max_category"] is not None:
        text += (
            " The effect can be larger in individual categories (up to "
            f"{duplicate_info['max_category_share']:.1f}% of units in "
            f"{duplicate_info['max_category']})."
        )
    return text + (
        " The rule is applied for consistency with the existing dashboard, "
        "reproducibility (one analysis for every user) and memory use (no second "
        "copy of the raw data is cached)."
    )

import pandas as pd
import pytest

import forecast_utils as fu


def raw(rows):
    return pd.DataFrame(rows, columns=["InvoiceDate", "Category", "Quantity"])


def weekly(values, start="2020-01-06"):
    index = pd.date_range(start, periods=len(values), freq="W-MON")
    return pd.Series(values, index=index, dtype="float64")


def test_clean_quantity_splits_returns_and_drops_invalid():
    data = raw([
        ("2020-01-06", "A", 5),
        ("2020-01-07", "A", -2),
        ("2020-01-08", "A", 0),
        ("2020-01-09", None, float("nan")),
        ("not-a-date", "A", 3),
        ("2020-01-10", None, 4),
    ])
    sales, returns, notes = fu.clean_quantity(data)
    assert list(sales["Quantity"]) == [5, 4]
    assert list(returns["Quantity"]) == [-2]
    assert sales["Category"].tolist() == ["A", fu.UNKNOWN_CATEGORY]
    assert notes["return_rows"] == 1 and notes["return_units"] == 2
    assert notes["invalid_date_rows"] == 1
    assert notes["missing_or_zero_quantity_rows"] == 2


def test_negative_only_category_gives_empty_series():
    sales, returns, _ = fu.clean_quantity(raw([("2020-01-06", "A", -3)]))
    assert sales.empty and len(returns) == 1
    assert fu.build_weekly_series(sales, "A").empty


def test_weekly_totals_and_gap_filled_with_zero():
    data = raw([
        ("2020-01-06", "A", 5), ("2020-01-08", "B", 3),
        ("2020-01-20", "A", 4),
    ])
    sales, _, _ = fu.clean_quantity(data)
    table = fu.build_weekly_table(sales, "2020-01-06", "2020-01-26")
    assert list(table.index) == list(pd.date_range("2020-01-06", periods=3, freq="W-MON"))
    assert table[fu.TOTAL].tolist() == [8, 0, 4]
    assert table["A"].tolist() == [5, 0, 4]
    assert table["B"].tolist() == [3, 0, 0]


def test_partial_first_and_last_weeks_dropped():
    data = raw([("2020-01-02", "A", 1), ("2020-01-08", "A", 2), ("2020-01-16", "A", 3)])
    sales, _, _ = fu.clean_quantity(data)
    table = fu.build_weekly_table(sales, "2020-01-02", "2020-01-16")
    assert table.index.tolist() == [pd.Timestamp("2020-01-06")]
    kept = fu.build_weekly_table(sales, "2020-01-02", "2020-01-16", drop_partial=False)
    assert len(kept) == 3


def test_naive_and_moving_average_values():
    s = weekly([10, 20, 30, 40, 50, 60])
    assert fu.naive_forecast(s, 2).tolist() == [40, 50]
    assert fu.moving_average_forecast(s, 2, 2).tolist() == [35, 45]
    assert fu.moving_average_forecast(s, 4, 2).tolist() == [25, 35]


def test_no_leakage_from_test_week_actual():
    base = weekly(list(range(10, 40)))
    changed = base.copy()
    changed.iloc[-1] = 9999
    for fn in (lambda x: fu.naive_forecast(x, 8),
               lambda x: fu.moving_average_forecast(x, 4, 8)):
        assert fn(base).iloc[:-1].tolist() == fn(changed).iloc[:-1].tolist()
        assert fn(base).iloc[-1] == fn(changed).iloc[-1]


def test_mae_and_length_check():
    a, f = weekly([10, 20]), weekly([12, 17])
    assert fu.mae(a, f) == 2.5
    with pytest.raises(ValueError):
        fu.mae(a, weekly([1]))


def test_bias_sign_and_zero_actuals():
    a = weekly([10, 10])
    assert fu.forecast_bias(a, weekly([12, 14])) == (3.0, 30.0)
    assert fu.forecast_bias(a, weekly([8, 6]))[0] < 0
    assert fu.forecast_bias(weekly([0, 0]), weekly([1, 1]))[1] is None


def test_compare_methods_same_test_weeks_and_best_window():
    s = weekly([100.0] * 30)
    result = fu.compare_methods(s)
    assert result.ok
    assert len(result.forecasts) == 8
    assert result.forecasts.index.tolist() == s.index[-8:].tolist()
    assert result.naive_test_mae == 0 and result.improvement_pct is None
    assert result.bias == 0
    assert result.recommended_method == fu.NAIVE  # tie goes to the simpler method


def test_moving_average_recommended_on_alternating_series():
    s = weekly([100, 200] * 15)
    result = fu.compare_methods(s)
    assert result.recommended_method == "MA(2)"
    assert result.best_ma_method == "MA(2)"
    assert result.recommended_test_mae < result.naive_test_mae
    assert result.improvement_pct == pytest.approx(
        (result.naive_test_mae - result.recommended_test_mae)
        / result.naive_test_mae * 100)
    assert result.improvement_pct > 0


def test_naive_can_win_overall():
    s = weekly([float(i) * 10 for i in range(1, 31)])
    result = fu.compare_methods(s)
    assert result.recommended_method == fu.NAIVE
    assert result.improvement_pct == 0
    assert result.best_ma_method == "MA(2)"
    assert result.best_ma_improvement_pct < 0


def test_selection_independent_of_test_weeks():
    s = weekly([100, 200] * 15)
    base = fu.compare_methods(s)
    changed = s.copy()
    changed.iloc[-8:] = [5000, 0, 7, 9000, 1, 3000, 2, 8000]
    other = fu.compare_methods(changed)
    assert other.recommended_method == base.recommended_method
    assert other.best_ma_method == base.best_ma_method
    assert other.metrics["Validation MAE"].tolist() == base.metrics["Validation MAE"].tolist()
    assert other.metrics["Test MAE"].tolist() != base.metrics["Test MAE"].tolist()


def test_bias_belongs_to_recommended_method():
    s = weekly([float(i) * 10 for i in range(1, 31)])
    result = fu.compare_methods(s)
    row = result.metrics.set_index("Method").loc[result.recommended_method]
    assert result.bias == row["Test Bias"]
    assert result.bias_pct == row["Test Bias %"]
    assert result.bias_label == "under-forecast"


def test_classify_bias():
    assert fu.classify_bias(0.0) == fu.NEUTRAL_BIAS
    assert fu.classify_bias(1e-12) == fu.NEUTRAL_BIAS
    assert fu.classify_bias(2.5) == "over-forecast"
    assert fu.classify_bias(-0.1) == "under-forecast"
    assert fu.compare_methods(weekly([100.0] * 30)).bias_label == fu.NEUTRAL_BIAS


def test_next_week_forecast_uses_history_only():
    s = weekly([10, 20, 30, 40, 50])
    next_date = s.index[-1] + pd.Timedelta(days=7)
    assert fu.next_week_forecast(s, fu.NAIVE) == (next_date, 50.0)
    assert fu.next_week_forecast(s, "MA(2)") == (next_date, (40 + 50) / 2)
    assert fu.next_week_forecast(s, "MA(4)") == (next_date, (20 + 30 + 40 + 50) / 4)

    series = weekly([100, 200] * 15)
    result = fu.compare_methods(series)
    assert result.next_week == series.index[-1] + pd.Timedelta(days=7)
    assert result.next_week_forecast == pytest.approx(series.iloc[-2:].mean())


def test_text_quantity_is_coerced():
    data = raw([
        ("2020-01-06", "A", "5"),
        ("2020-01-06", "A", "2.5"),
        ("2020-01-07", "A", "abc"),
        ("2020-01-07", "A", None),
    ])
    sales, _, notes = fu.clean_quantity(data)
    assert sales["Quantity"].tolist() == [5.0, 2.5]
    assert notes["non_numeric_quantity_rows"] == 1
    assert notes["missing_or_zero_quantity_rows"] == 1


def test_duplicate_summary_counts_exact_rows_only():
    data = pd.DataFrame({
        "InvoiceNo": ["X1", "X1", "X1", "X2"],
        "StockCode": [1, 1, 1, 1],
        "InvoiceDate": ["2020-01-06"] * 4,
        "Category": ["A"] * 4,
        "Quantity": [2, 2, 3, 2],
    })
    summary = fu.duplicate_summary(data)
    assert summary["row_count"] == 1  # same invoice+stock with Quantity 3 is kept
    assert summary["units"] == 2
    assert summary["row_share"] == 25
    assert summary["unit_share"] == pytest.approx(2 / 9 * 100)
    assert len(summary["rows"]) == 1


def test_insufficient_data_warns():
    result = fu.compare_methods(weekly([5.0] * 10))
    assert not result.ok and "Not enough history" in result.warnings[0]


def test_sparse_series_warns():
    s = weekly([0.0, 0.0, 0.0, 5.0] * 8)
    assert "Sparse" in fu.compare_methods(s).warnings[0]


def test_no_sales_in_test_period_warns():
    s = weekly([5.0] * 25 + [0.0] * 8)
    assert "No sales in the test period" in fu.compare_methods(s).warnings[0]


def test_compare_rankings_three_states():
    order = ["Naive", "MA(2)", "MA(4)", "MA(8)"]
    assert fu.compare_rankings(order, list(order)) == fu.RANKING_UNCHANGED
    assert fu.compare_rankings(order, order[::-1]) == fu.RANKING_CHANGED
    assert fu.compare_rankings(None, None) == fu.RANKING_NOT_COMPARABLE
    assert fu.compare_rankings(order, None) == fu.RANKING_NOT_COMPARABLE


def weekly_frame(total, **categories):
    frame = pd.DataFrame({fu.TOTAL: total, **categories},
                         index=pd.date_range("2020-01-06", periods=len(total), freq="W-MON"))
    return frame.astype("float64")


def test_duplicate_effect_without_duplicates():
    base = weekly_frame([100, 200] * 15, A=[100, 200] * 15)
    effect = fu.duplicate_effect(base, base * 0)
    assert effect == {"ranking_status": None, "max_category": None, "max_category_share": None}


def test_duplicate_effect_not_comparable_on_short_series():
    base = weekly_frame([10.0] * 10, A=[10.0] * 10)
    dup = weekly_frame([1.0] * 10, A=[1.0] * 10)
    effect = fu.duplicate_effect(base, dup)
    assert effect["ranking_status"] == fu.RANKING_NOT_COMPARABLE
    assert effect["max_category"] == "A" and effect["max_category_share"] == 10


def test_duplicate_effect_ranking_and_largest_category():
    base = weekly_frame([100, 200] * 15, A=[50, 100] * 15, B=[50, 100] * 15)
    dup = weekly_frame([1] * 30, A=[0] * 30, B=[1] * 30)
    effect = fu.duplicate_effect(base, dup)
    assert effect["ranking_status"] == fu.RANKING_UNCHANGED
    assert effect["max_category"] == "B"
    assert effect["max_category_share"] == pytest.approx(30 / 2250 * 100)


def duplicate_info(row_count, ranking_status=None, max_category=None):
    return {
        "row_count": row_count, "total_rows": 1000, "row_share": row_count / 10,
        "units": row_count * 2.0, "unit_share": 0.5, "ranking_status": ranking_status,
        "max_category": max_category, "max_category_share": 12.5 if max_category else None,
    }


def test_duplicate_note_without_duplicates():
    note = fu.duplicate_note(duplicate_info(0))
    assert "No such rows were found" in note
    assert "ranking" not in note and "categories" not in note


def test_duplicate_note_states_only_measured_results():
    unchanged = fu.duplicate_note(duplicate_info(5, fu.RANKING_UNCHANGED, "Turizm"))
    assert "does not change" in unchanged
    assert "default 8-week test setting" in unchanged
    assert "12.5% of units in Turizm" in unchanged

    changed = fu.duplicate_note(duplicate_info(5, fu.RANKING_CHANGED))
    assert "changes the overall" in changed and "does not change" not in changed
    assert "categories" not in changed

    not_comparable = fu.duplicate_note(duplicate_info(5, fu.RANKING_NOT_COMPARABLE))
    assert "could not be compared" in not_comparable
    assert "does not change" not in not_comparable


def test_improvement_card_naive_and_moving_average():
    naive = fu.compare_methods(weekly([float(i) * 10 for i in range(1, 31)]))
    label, value, caption = fu.improvement_card(naive)
    assert label == "Improvement vs Naive · Naive"
    assert value == "+0.0%"
    assert caption == f"Best MA(2) vs Naive: {naive.best_ma_improvement_pct:+.1f}%"
    assert naive.best_ma_improvement_pct < 0

    ma = fu.compare_methods(weekly([100, 200] * 15))
    label, value, caption = fu.improvement_card(ma)
    assert label == "Improvement vs Naive · MA(2)"
    assert value == "+50.0%"
    assert caption == "Naive test MAE 100.0"

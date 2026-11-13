"""Kisa aciklamalar, para bicimi ve ortak grafikler."""
import altair as alt
import pandas as pd
import streamlit as st


def format_number(value, decimals=0):
    if pd.isna(value):
        return "Not available"
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def money(value):
    return "₺ " + format_number(value, 2)


def metric(column, title, value, explanation):
    column.metric(title, value, help=explanation, border=True)


def line_chart(data, x, y, title, explanation, series=None, currency=False):
    st.markdown(f"**{title}**")
    st.caption(explanation)
    unit = "Sales (₺)" if currency else "Units sold"
    encoding = {
        "x": alt.X(f"{x}:T", title="Date"),
        "y": alt.Y(f"{y}:Q", title=unit, axis=alt.Axis(format=",.0f")),
        "tooltip": [alt.Tooltip(f"{x}:T", title="Date", format="%d.%m.%Y"),
                    alt.Tooltip(f"{y}:Q", title=unit, format=",.2f" if currency else ",.0f")],
    }
    if series:
        encoding["color"] = alt.Color(f"{series}:N", title=None,
                                       scale=alt.Scale(domain=["Recorded", "Forecast"], range=["#55515B", "#C52F43"]))
        encoding["strokeWidth"] = alt.condition(
            alt.datum.Series == "Forecast", alt.value(3.5), alt.value(1.8)
        )
        encoding["strokeDash"] = alt.StrokeDash(
            f"{series}:N", legend=None,
            scale=alt.Scale(domain=["Recorded", "Forecast"], range=[[1, 0], [6, 3]]),
        )
    chart = alt.Chart(data).mark_line(point=True, color="#C52F43", strokeWidth=2.5).encode(**encoding)
    st.altair_chart(chart.properties(height=300), width="stretch", alt=title)


def sales_bar(data, label, value, title, explanation):
    st.markdown(f"**{title}**")
    st.caption(explanation)
    chart = alt.Chart(data).mark_bar(color="#C52F43", cornerRadiusEnd=4).encode(
        x=alt.X(f"{value}:Q", title="Sales (₺)", axis=alt.Axis(format=",.0f")),
        y=alt.Y(f"{label}:N", sort="-x", title=None),
        tooltip=[alt.Tooltip(f"{label}:N"), alt.Tooltip(f"{value}:Q", title="Sales (₺)", format=",.2f")],
    )
    st.altair_chart(chart.properties(height=300), width="stretch", alt=title)

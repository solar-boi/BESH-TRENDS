"""Reusable Altair chart builders and narrative renderers for the dashboard."""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st


def render_interactive_line_chart(
    df: pd.DataFrame,
    x_col: str,
    y_cols: list[str],
    time_format: str = "%b %d, %I:%M %p",
) -> None:
    """Render an Altair line chart with shared hover tooltips."""
    hover = alt.selection_point(
        fields=[x_col],
        nearest=True,
        on="mouseover",
        empty=False,
    )

    base = alt.Chart(df).encode(x=alt.X(f"{x_col}:T", title=""))

    tooltips_list = [alt.Tooltip(f"{x_col}:T", title="Time", format=time_format)]
    for y_col in y_cols:
        tooltips_list.append(alt.Tooltip(f"{y_col}:Q", title=y_col, format=".2f"))

    rule = (
        base.mark_rule(color="gray")
        .encode(
            opacity=alt.condition(hover, alt.value(0.5), alt.value(0)),
            tooltip=tooltips_list,
        )
        .add_params(hover)
    )

    melted = df.melt(
        id_vars=[x_col], value_vars=y_cols, var_name="Metric", value_name="Price"
    )

    lines = (
        alt.Chart(melted)
        .mark_line()
        .encode(
            x=alt.X(f"{x_col}:T", title=""),
            y=alt.Y("Price:Q", title="Price (¢/kWh)"),
            color=alt.Color("Metric:N", legend=alt.Legend(title="", orient="bottom")),
        )
    )

    points = lines.mark_circle().encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
    )

    chart = (lines + points + rule).interactive()
    st.altair_chart(chart, use_container_width=True)


def render_narrative_message(title: str, level: str, description: str) -> None:
    """Render a narrative callout with matching Streamlit status styling."""
    message = f"**{title}**\n\n{description}"
    renderer = {
        "success": st.success,
        "info": st.info,
        "warning": st.warning,
        "error": st.error,
    }.get(level, st.info)
    renderer(message)

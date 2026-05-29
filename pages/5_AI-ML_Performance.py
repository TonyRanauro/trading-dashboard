"""
AI-ML Performance — model prediction tracking and diagnostics.

Joins ml_predictions to ml_targets in pandas, aggregates per-model performance
metrics on demand, and displays:
  - Headline KPI cards (accuracy, rank IC, top-decile return, decile spread)
  - Decile performance bar chart
  - Rank IC over time
  - Top vs bottom decile cumulative return
  - Probability distribution histogram
  - Calibration plot
  - Confusion matrix (resolved predictions only)

Data conventions:
- predicted_value is a probability (0-1) for classification models, or a
  log-return for regression models.
- actual log_ret_10d is a log return (not pct). For display we leave it as a
  number (e.g., 0.0234 = +2.34% but rendered as 0.0234 unless multiplied).
- A prediction is "resolved" once ml_targets has a non-null log_ret_10d for
  (ticker, prediction_date) — i.e., 10 trading days after the prediction.
"""

from datetime import date, timedelta
import pandas as pd
import streamlit as st
from lib.supabase_client import get_client

st.set_page_config(page_title="ML Performance", page_icon="🤖", layout="wide")
st.title("🤖 AI-ML Performance")
st.caption("Model prediction tracking, accuracy, and diagnostics")


# ============================================================
# DATA LAYER
# ============================================================
@st.cache_data(ttl=300)
def load_models() -> pd.DataFrame:
    """Load the ml_models registry."""
    s = get_client()
    rows = (s.table("ml_models")
             .select("model_id, model_name, component, target_name, "
                     "algorithm, train_start, train_end, is_production, "
                     "created_at, notes")
             .order("model_id", desc=False)
             .execute().data)
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def load_predictions(model_id: int) -> pd.DataFrame:
    """Load all ml_predictions for a given model. Pages past 1000-row default.
    Returns a DataFrame with prediction_date typed as datetime.date."""
    s = get_client()
    rows = []
    offset = 0
    while True:
        batch = (s.table("ml_predictions")
                  .select("prediction_id, ticker, prediction_date, model_id, "
                          "predicted_value, predicted_class, probability, "
                          "rank_overall, decile, top_decile_flag")
                  .eq("model_id", model_id)
                  .order("prediction_date", desc=True)
                  .range(offset, offset + 999)
                  .execute().data)
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["prediction_date"] = pd.to_datetime(df["prediction_date"]).dt.date
    return df


@st.cache_data(ttl=300)
def load_targets() -> pd.DataFrame:
    """Load ml_targets (last 90 days are mirrored from SQL Server).
    Returns DataFrame with target_date as datetime.date."""
    s = get_client()
    rows = []
    offset = 0
    while True:
        batch = (s.table("ml_targets")
                  .select("ticker, target_date, log_ret_10d, "
                          "beat_median_10d, quintile_10d, "
                          "excess_ret_10d, universe_size")
                  .order("target_date", desc=True)
                  .range(offset, offset + 999)
                  .execute().data)
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["target_date"] = pd.to_datetime(df["target_date"]).dt.date
    return df


@st.cache_data(ttl=300)
def load_universe() -> pd.DataFrame:
    """Load universe for ticker -> sector / company_name lookup."""
    s = get_client()
    rows = (s.table("universe")
             .select("ticker, company_name, sector")
             .execute().data)
    return pd.DataFrame(rows)


def build_outcomes_frame(predictions: pd.DataFrame,
                         targets: pd.DataFrame) -> pd.DataFrame:
    """Join predictions to targets.
    Adds:
      - resolved (bool): True if log_ret_10d is not null
      - prediction_correct (Int64 0/1, NA if unresolved or no class)
    """
    if predictions.empty:
        return predictions.copy()

    df = predictions.merge(
        targets,
        left_on=["ticker", "prediction_date"],
        right_on=["ticker", "target_date"],
        how="left",
    )
    df["resolved"] = df["log_ret_10d"].notnull()

    # Classification correctness: predicted_class (0/1) vs beat_median_10d (bool)
    # Compute only where both exist; otherwise pd.NA.
    df["prediction_correct"] = pd.NA
    mask = df["predicted_class"].notnull() & df["beat_median_10d"].notnull()
    df.loc[mask, "prediction_correct"] = (
        df.loc[mask, "predicted_class"].astype(int)
        == df.loc[mask, "beat_median_10d"].astype(int)
    ).astype(int)

    return df


# ============================================================
# LOAD DATA
# ============================================================
models = load_models()

if models.empty:
    st.warning("No models found in ml_models. Run register_model.py first.")
    st.stop()


# ============================================================
# CONTROLS
# ============================================================
ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 2])

with ctrl_col1:
    # Default to production model if one exists, else most recent
    prod_mask = models["is_production"] == True
    if prod_mask.any():
        default_model_idx = int(models[prod_mask].index[0])
    else:
        default_model_idx = int(models.index[-1])

    model_options = models.apply(
        lambda r: f"{r['model_id']}: {r['model_name']} "
                  f"({'PROD' if r['is_production'] else 'archive'})",
        axis=1,
    ).tolist()

    selected_label = st.selectbox(
        "Model",
        options=model_options,
        index=default_model_idx,
    )
    selected_model_id = int(selected_label.split(":")[0])
    selected_model = models[models["model_id"] == selected_model_id].iloc[0]

predictions = load_predictions(selected_model_id)
targets = load_targets()

if predictions.empty:
    st.info(f"No predictions yet for model_id={selected_model_id}. "
            "The daily inference job will populate this once it runs.")
    st.stop()

outcomes = build_outcomes_frame(predictions, targets)

# Date range picker — bounded to the prediction date range we have data for
min_date = outcomes["prediction_date"].min()
max_date = outcomes["prediction_date"].max()

with ctrl_col2:
    date_range = st.date_input(
        "Prediction date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Filter predictions by date. Default is full available range.",
    )
    # Handle the case where user has only selected one date (in-progress)
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = (date_range if not isinstance(date_range, tuple)
                                 else date_range[0])

with ctrl_col3:
    mode = st.radio(
        "View mode",
        options=["Aggregate over range", "By prediction date"],
        index=0,
        help=("Aggregate: pool all predictions in the date range and compute "
              "summary metrics. Per-date: trends over time."),
        horizontal=False,
    )


# ============================================================
# FILTER DATA TO DATE RANGE
# ============================================================
mask = (outcomes["prediction_date"] >= start_date) & (outcomes["prediction_date"] <= end_date)
filtered = outcomes[mask].copy()

st.caption(
    f"Model: **{selected_model['model_name']}** "
    f"(id={selected_model_id}, target={selected_model['target_name']}, "
    f"trained {selected_model['train_start']} → {selected_model['train_end']}) | "
    f"Date range: **{start_date}** to **{end_date}** | "
    f"{len(filtered):,} predictions ({filtered['resolved'].sum():,} resolved, "
    f"{(~filtered['resolved']).sum():,} pending)"
)

st.divider()


# ============================================================
# METRIC HELPERS
# ============================================================
def _safe_rank_ic(group: pd.DataFrame) -> float | None:
    """Spearman rank IC between predicted_value and actual log_ret_10d
    over the resolved rows in `group`. Returns None if <2 resolved rows
    or no variance.
    """
    g = group[group["resolved"]]
    if len(g) < 2:
        return None
    pred = g["predicted_value"].rank()
    actl = g["log_ret_10d"].rank()
    if pred.nunique() < 2 or actl.nunique() < 2:
        return None
    return float(pred.corr(actl))


def compute_aggregate_metrics(df: pd.DataFrame) -> dict:
    """Compute headline metrics over the full filtered set.
    df is expected to be `outcomes` for the selected model + date range.
    Returns dict with: n_total, n_resolved, accuracy, rank_ic,
    top_decile_mean_ret, decile_spread.
    """
    resolved = df[df["resolved"]]
    metrics = {
        "n_total":   len(df),
        "n_resolved": len(resolved),
        "accuracy":  None,
        "rank_ic":   None,
        "top_decile_mean_ret":   None,
        "bottom_decile_mean_ret": None,
        "decile_spread":         None,
    }

    if len(resolved) == 0:
        return metrics

    # Accuracy: only meaningful if predicted_class is populated
    correct_series = resolved["prediction_correct"].dropna()
    if len(correct_series) > 0:
        metrics["accuracy"] = float(correct_series.mean())

    # Rank IC over all resolved rows in the period.
    # NOTE: this pools across dates, which is a slight statistical sin
    # (each day's universe is independent). For the headline number it's
    # fine; the "per-date" view in the line chart will be honest.
    metrics["rank_ic"] = _safe_rank_ic(df)

    # Top / bottom decile mean returns
    top    = resolved[resolved["decile"] == 10]["log_ret_10d"]
    bottom = resolved[resolved["decile"] == 1]["log_ret_10d"]
    if len(top) > 0:
        metrics["top_decile_mean_ret"] = float(top.mean())
    if len(bottom) > 0:
        metrics["bottom_decile_mean_ret"] = float(bottom.mean())
    if metrics["top_decile_mean_ret"] is not None \
       and metrics["bottom_decile_mean_ret"] is not None:
        metrics["decile_spread"] = (
            metrics["top_decile_mean_ret"] - metrics["bottom_decile_mean_ret"]
        )

    return metrics


def fmt_pct(v: float | None, decimals: int = 1) -> str:
    """Format a probability/percentage. None → '—'."""
    if v is None or pd.isna(v):
        return "—"
    return f"{v * 100:.{decimals}f}%"


def fmt_ret(v: float | None, decimals: int = 2) -> str:
    """Format a return (log return as %). None → '—'."""
    if v is None or pd.isna(v):
        return "—"
    return f"{v * 100:+.{decimals}f}%"


def fmt_ic(v: float | None, decimals: int = 3) -> str:
    """Format a rank IC (correlation). None → '—'."""
    if v is None or pd.isna(v):
        return "—"
    return f"{v:+.{decimals}f}"


# ============================================================
# KPI ROW
# ============================================================
metrics = compute_aggregate_metrics(filtered)

k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.metric(
        label="Predictions",
        value=f"{metrics['n_total']:,}",
        delta=f"{metrics['n_resolved']:,} resolved",
        delta_color="off",
        help="Total predictions in the selected date range. "
             "Resolved = 10-day forward window has closed; "
             "remaining are pending.",
    )

with k2:
    st.metric(
        label="Accuracy",
        value=fmt_pct(metrics["accuracy"]),
        help="Share of RESOLVED predictions where predicted_class "
             "matched actual beat_median_10d. Only meaningful once "
             "predictions have aged ~10 trading days.",
    )

with k3:
    st.metric(
        label="Rank IC",
        value=fmt_ic(metrics["rank_ic"]),
        help="Spearman correlation between predicted_value and actual "
             "10-day return over resolved predictions. > 0 = model "
             "ranks correctly; 0 = noise; < 0 = inverted.",
    )

with k4:
    st.metric(
        label="Top-decile mean return",
        value=fmt_ret(metrics["top_decile_mean_ret"]),
        help="Average realized 10-day log return for picks the model "
             "ranked in the top decile of predicted_value.",
    )

with k5:
    st.metric(
        label="Decile spread (top − bottom)",
        value=fmt_ret(metrics["decile_spread"]),
        help="Top-decile mean return minus bottom-decile mean return. "
             "Positive and growing = the model is generating economically "
             "useful ranking signal.",
    )

# Friendly hint when nothing is resolved yet
if metrics["n_resolved"] == 0:
    st.info(
        "⏳ No resolved predictions yet in the selected date range. "
        "Predictions resolve ~10 trading days after they're made. "
        "Charts and metrics will populate automatically as outcomes arrive."
    )

st.divider()


# ============================================================
# CHART 1: DECILE PERFORMANCE STAIRCASE
# ============================================================
st.subheader("Decile performance")
st.caption(
    "Mean realized 10-day return by predicted decile, over resolved predictions "
    "in the selected date range. A monotonically rising 'staircase' (decile 1 "
    "lowest, decile 10 highest) indicates the model is correctly ranking stocks."
)


def build_decile_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per-decile aggregates over the RESOLVED rows in df.
    Returns a frame with columns: decile, n, mean_ret, median_ret, std_ret.
    Always returns 10 rows (deciles 1..10), with NaN where empty.
    """
    base = pd.DataFrame({"decile": list(range(1, 11))})
    resolved = df[df["resolved"] & df["decile"].notnull()].copy()
    if resolved.empty:
        for col in ["n", "mean_ret", "median_ret", "std_ret"]:
            base[col] = pd.NA
        return base

    resolved["decile"] = resolved["decile"].astype(int)
    grp = resolved.groupby("decile")["log_ret_10d"]
    summary = pd.DataFrame({
        "n":          grp.size(),
        "mean_ret":   grp.mean(),
        "median_ret": grp.median(),
        "std_ret":    grp.std(),
    }).reset_index()
    return base.merge(summary, on="decile", how="left")


decile_df = build_decile_summary(filtered)
has_decile_data = decile_df["n"].notna().any()

if not has_decile_data:
    st.info(
        "No resolved predictions yet — the decile chart will populate "
        "automatically as forward windows close."
    )
else:
    # Build the bar chart in plotly
    import plotly.graph_objects as go

    # Red → green gradient for bars by decile (1 = red, 10 = green)
    decile_colors = [
        "#a00", "#c44", "#e77", "#f99", "#fcc",
        "#cfc", "#9f9", "#7e7", "#4c4", "#0a7a0a",
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=decile_df["decile"],
        y=decile_df["mean_ret"] * 100,            # display as %
        marker_color=decile_colors,
        text=[
            f"{(v * 100):+.2f}%" if pd.notnull(v) else ""
            for v in decile_df["mean_ret"]
        ],
        textposition="outside",
        hovertemplate=(
            "<b>Decile %{x}</b><br>"
            "Mean return: %{y:+.2f}%<br>"
            "Resolved n: %{customdata[0]}<br>"
            "Median return: %{customdata[1]:+.2f}%"
            "<extra></extra>"
        ),
        customdata=list(zip(
            decile_df["n"].fillna(0).astype(int),
            (decile_df["median_ret"] * 100).fillna(0),
        )),
        name="Mean return",
    ))

    # Zero line for reference
    fig.add_hline(y=0, line_dash="dot", line_color="#888", line_width=1)

    fig.update_layout(
        template="plotly",
        height=380,
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis=dict(
            title="Predicted decile (1 = lowest, 10 = highest)",
            tickmode="linear", tick0=1, dtick=1,
        ),
        yaxis=dict(title="Mean 10-day return (%)", zeroline=False),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Small companion table below the chart
    table_df = decile_df.copy()
    table_df["mean_ret"]   = (table_df["mean_ret"]   * 100).round(3)
    table_df["median_ret"] = (table_df["median_ret"] * 100).round(3)
    table_df["std_ret"]    = (table_df["std_ret"]    * 100).round(3)
    table_df = table_df.rename(columns={
        "n": "Resolved n",
        "mean_ret":   "Mean return (%)",
        "median_ret": "Median return (%)",
        "std_ret":    "Stdev (%)",
        "decile":     "Decile",
    })

    with st.expander("Decile details", expanded=False):
        st.dataframe(
            table_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Decile": st.column_config.NumberColumn(format="%d"),
                "Resolved n": st.column_config.NumberColumn(format="%d"),
            },
        )

st.divider()


# ============================================================
# CHART 2: PROBABILITY DISTRIBUTION HISTOGRAM
# ============================================================
st.subheader("Probability distribution")
st.caption(
    "Histogram of predicted_value (probability of beating the S&P median over "
    "10 days). The 0.50 line marks the classifier's neutral threshold. "
    "A distribution skewed left of 0.50 = model is collectively bearish; "
    "right of 0.50 = bullish."
)

import plotly.graph_objects as go  # noqa: E402  (re-import is harmless and keeps section self-contained)

if filtered.empty:
    st.info("No predictions in the selected date range.")
else:
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Histogram(
        x=filtered["predicted_value"],
        xbins=dict(start=0.0, end=1.0, size=0.02),
        marker_color="#2563eb",
        marker_line=dict(color="#1e40af", width=0.5),
        hovertemplate=(
            "Predicted value: %{x:.3f}<br>"
            "Count: %{y:,}"
            "<extra></extra>"
        ),
        name="Predictions",
    ))

    # 0.50 threshold reference line
    fig_hist.add_vline(
        x=0.50, line_dash="dash", line_color="#dc2626", line_width=2,
        annotation_text="0.50 (neutral)",
        annotation_position="top right",
        annotation_font_color="#dc2626",
    )

    # Mean line for context
    mean_p = float(filtered["predicted_value"].mean())
    fig_hist.add_vline(
        x=mean_p, line_dash="dot", line_color="#0a7a0a", line_width=2,
        annotation_text=f"Mean: {mean_p:.3f}",
        annotation_position="top left",
        annotation_font_color="#0a7a0a",
    )

    fig_hist.update_layout(
        template="plotly",
        height=340,
        margin=dict(l=40, r=20, t=30, b=40),
        xaxis=dict(title="Predicted value (probability)",
                   range=[0.0, 1.0], tick0=0.0, dtick=0.1),
        yaxis=dict(title="Count of predictions"),
        showlegend=False,
        bargap=0.02,
    )

    h1, h2, h3 = st.columns([2, 1, 1])
    with h1:
        st.plotly_chart(fig_hist, use_container_width=True)
    with h2:
        st.metric("Mean probability", f"{mean_p:.3f}")
        st.metric("Median probability",
                  f"{float(filtered['predicted_value'].median()):.3f}")
    with h3:
        pct_above_50 = (filtered["predicted_value"] > 0.50).mean() * 100
        st.metric("% above 0.50", f"{pct_above_50:.1f}%")
        st.metric("Universe", f"{len(filtered):,}")


st.divider()


# ============================================================
# CHART 3: TOP DECILE COMPOSITION BY SECTOR
# ============================================================
st.subheader("Top-decile composition by sector")
st.caption(
    "Which sectors dominate the model's top-decile picks in the selected date "
    "range? Useful for spotting concentration risk ('is it just buying tech?')."
)

universe = load_universe()

top_decile = filtered[filtered["decile"] == 10].copy()

if top_decile.empty:
    st.info("No top-decile predictions in the selected date range.")
elif universe.empty:
    st.info("Universe lookup unavailable — cannot resolve sectors.")
else:
    # Join to universe to pick up sector
    td_with_sector = top_decile.merge(
        universe[["ticker", "sector"]], on="ticker", how="left",
    )
    sector_counts = (
        td_with_sector.groupby("sector", dropna=False)
                       .size()
                       .reset_index(name="count")
                       .sort_values("count", ascending=False)
    )
    sector_counts["sector"] = sector_counts["sector"].fillna("(unknown)")
    sector_counts["pct"] = sector_counts["count"] / sector_counts["count"].sum() * 100

    s1, s2 = st.columns([2, 1])

    with s1:
        fig_sec = go.Figure()
        fig_sec.add_trace(go.Bar(
            y=sector_counts["sector"],
            x=sector_counts["count"],
            orientation="h",
            marker_color="#0a7a0a",
            text=[f"{c}  ({p:.1f}%)"
                  for c, p in zip(sector_counts["count"], sector_counts["pct"])],
            textposition="outside",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Top-decile picks: %{x}<br>"
                "Share of top decile: %{customdata:.1f}%"
                "<extra></extra>"
            ),
            customdata=sector_counts["pct"],
            name="Top-decile picks",
        ))
        fig_sec.update_layout(
            template="plotly",
            height=max(300, 32 * len(sector_counts) + 60),
            margin=dict(l=10, r=80, t=10, b=40),
            xaxis=dict(title="Top-decile picks in date range"),
            yaxis=dict(autorange="reversed"),   # biggest at top
            showlegend=False,
        )
        st.plotly_chart(fig_sec, use_container_width=True)

    with s2:
        st.markdown("**Sector counts (top-decile)**")
        display = sector_counts.copy()
        display["pct"] = display["pct"].round(1)
        display = display.rename(columns={
            "sector": "Sector", "count": "Count", "pct": "% of top decile",
        })
        st.dataframe(display, use_container_width=True, hide_index=True)


st.divider()


# ============================================================
# CHART 4: PREDICTIONS PER DAY (PIPELINE HEALTH)
# ============================================================
st.subheader("Predictions per day")
st.caption(
    "Count of predictions written by the daily inference job per prediction date. "
    "A healthy pipeline writes ~503 rows per trading day. Gaps or counts that "
    "drop sharply may indicate a broken pipeline step."
)

if filtered.empty:
    st.info("No predictions in the selected date range.")
else:
    per_day = (
        filtered.groupby("prediction_date")
                .size()
                .reset_index(name="n")
                .sort_values("prediction_date")
    )

    # Color bars green when ~full (>=400 = healthy), amber otherwise
    bar_colors = ["#0a7a0a" if n >= 400 else "#f59e0b" for n in per_day["n"]]

    fig_per_day = go.Figure()
    fig_per_day.add_trace(go.Bar(
        x=per_day["prediction_date"],
        y=per_day["n"],
        marker_color=bar_colors,
        hovertemplate=(
            "<b>%{x|%Y-%m-%d}</b><br>"
            "Predictions: %{y:,}"
            "<extra></extra>"
        ),
        name="Predictions",
    ))
    fig_per_day.update_layout(
        template="plotly",
        height=300,
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis=dict(
            title="Prediction date",
            type="date",
            tickformat="%Y-%m-%d",
        ),
        yaxis=dict(title="Predictions written"),
        showlegend=False,
    )
    st.plotly_chart(fig_per_day, use_container_width=True)


st.divider()


# ============================================================
# CHART 5: RANK IC OVER TIME
# ============================================================
st.subheader("Rank IC over time")
st.caption(
    "Per-day Spearman rank correlation between predicted_value and actual "
    "10-day return, over resolved predictions. Above zero = correct ranking; "
    "the dashed line shows a 5-day rolling average for trend."
)


def build_per_day_rank_ic(df: pd.DataFrame) -> pd.DataFrame:
    """One Spearman rank IC per prediction_date, over resolved rows only."""
    out = []
    for day, grp in df.groupby("prediction_date"):
        ic = _safe_rank_ic(grp)
        if ic is not None:
            out.append({"prediction_date": day, "rank_ic": ic, "n": int(grp["resolved"].sum())})
    return pd.DataFrame(out).sort_values("prediction_date") if out else pd.DataFrame()


per_day_ic = build_per_day_rank_ic(filtered)

if per_day_ic.empty:
    st.info(
        "No days with resolved predictions yet. This chart will populate as "
        "predictions age past their 10-day forward window."
    )
else:
    # 5-day rolling average
    per_day_ic["rolling_ic"] = per_day_ic["rank_ic"].rolling(
        window=5, min_periods=1
    ).mean()

    fig_ic = go.Figure()
    fig_ic.add_trace(go.Scatter(
        x=per_day_ic["prediction_date"],
        y=per_day_ic["rank_ic"],
        mode="lines+markers",
        line=dict(color="#2563eb", width=2),
        marker=dict(size=6),
        name="Daily Rank IC",
        hovertemplate=(
            "<b>%{x|%Y-%m-%d}</b><br>"
            "Rank IC: %{y:+.3f}<br>"
            "Resolved n: %{customdata}"
            "<extra></extra>"
        ),
        customdata=per_day_ic["n"],
    ))
    fig_ic.add_trace(go.Scatter(
        x=per_day_ic["prediction_date"],
        y=per_day_ic["rolling_ic"],
        mode="lines",
        line=dict(color="#dc2626", width=2, dash="dash"),
        name="5-day rolling avg",
        hovertemplate=(
            "<b>%{x|%Y-%m-%d}</b><br>"
            "Rolling avg: %{y:+.3f}"
            "<extra></extra>"
        ),
    ))
    fig_ic.add_hline(y=0, line_dash="dot", line_color="#888", line_width=1)
    fig_ic.update_layout(
        template="plotly",
        height=340,
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis=dict(title="Prediction date", type="date", tickformat="%Y-%m-%d"),
        yaxis=dict(title="Rank IC (Spearman)", zeroline=False),
        legend=dict(orientation="h", y=1.08, x=1, xanchor="right"),
    )
    st.plotly_chart(fig_ic, use_container_width=True)


st.divider()


# ============================================================
# CHART 6: TOP VS BOTTOM DECILE CUMULATIVE RETURN
# ============================================================
st.subheader("Top vs bottom decile cumulative return")
st.caption(
    "If you'd held an equal-weight basket of decile 10 (top) vs decile 1 "
    "(bottom) each day, here's how each would have performed in cumulative "
    "log-return terms. The spread between the lines is the model's economic "
    "value."
)


def build_per_day_decile_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Per (prediction_date, decile) mean log_ret_10d over resolved rows.
    Then build cumulative log returns for top (10) and bottom (1) deciles.
    """
    resolved = df[df["resolved"] & df["decile"].notnull()].copy()
    if resolved.empty:
        return pd.DataFrame()
    resolved["decile"] = resolved["decile"].astype(int)

    # Daily mean return per decile
    daily = (
        resolved[resolved["decile"].isin([1, 10])]
            .groupby(["prediction_date", "decile"])["log_ret_10d"]
            .mean()
            .unstack("decile")
            .sort_index()
    )
    if daily.empty:
        return pd.DataFrame()

    # Need both deciles present to compute spread; fillna 0 for missing days
    for d in (1, 10):
        if d not in daily.columns:
            daily[d] = 0.0

    daily = daily.rename(columns={1: "bottom_decile_ret", 10: "top_decile_ret"})
    daily = daily.fillna(0.0).reset_index()

    # Cumulative log returns (sum of daily log returns)
    daily["top_decile_cum"]    = daily["top_decile_ret"].cumsum()
    daily["bottom_decile_cum"] = daily["bottom_decile_ret"].cumsum()
    daily["spread_cum"]        = daily["top_decile_cum"] - daily["bottom_decile_cum"]
    return daily


cum_df = build_per_day_decile_returns(filtered)

if cum_df.empty:
    st.info(
        "No resolved predictions in either decile 1 or decile 10 yet. "
        "Chart will populate as predictions resolve."
    )
else:
    fig_cum = go.Figure()
    fig_cum.add_trace(go.Scatter(
        x=cum_df["prediction_date"],
        y=cum_df["top_decile_cum"] * 100,
        mode="lines",
        line=dict(color="#0a7a0a", width=2.5),
        name="Top decile (long)",
        hovertemplate=(
            "<b>%{x|%Y-%m-%d}</b><br>"
            "Cumulative: %{y:+.2f}%"
            "<extra></extra>"
        ),
    ))
    fig_cum.add_trace(go.Scatter(
        x=cum_df["prediction_date"],
        y=cum_df["bottom_decile_cum"] * 100,
        mode="lines",
        line=dict(color="#dc2626", width=2.5),
        name="Bottom decile (short)",
        hovertemplate=(
            "<b>%{x|%Y-%m-%d}</b><br>"
            "Cumulative: %{y:+.2f}%"
            "<extra></extra>"
        ),
    ))
    fig_cum.add_trace(go.Scatter(
        x=cum_df["prediction_date"],
        y=cum_df["spread_cum"] * 100,
        mode="lines",
        line=dict(color="#2563eb", width=2, dash="dash"),
        name="Long-short spread",
        hovertemplate=(
            "<b>%{x|%Y-%m-%d}</b><br>"
            "Spread: %{y:+.2f}%"
            "<extra></extra>"
        ),
    ))
    fig_cum.add_hline(y=0, line_dash="dot", line_color="#888", line_width=1)
    fig_cum.update_layout(
        template="plotly",
        height=380,
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis=dict(title="Prediction date", type="date", tickformat="%Y-%m-%d"),
        yaxis=dict(title="Cumulative log return (%)"),
        legend=dict(orientation="h", y=1.08, x=1, xanchor="right"),
    )
    st.plotly_chart(fig_cum, use_container_width=True)


st.divider()


# ============================================================
# CHART 7: CALIBRATION PLOT
# ============================================================
st.subheader("Calibration plot")
st.caption(
    "Bucket predictions by predicted probability (0.0-0.1, 0.1-0.2, …), then "
    "plot the actual hit rate (share that beat the S&P median) for each "
    "bucket. Perfectly calibrated = points sit on the diagonal. Above the "
    "line = model is under-confident; below = over-confident."
)


def build_calibration_data(df: pd.DataFrame, n_bins: int = 10) -> pd.DataFrame:
    """Bucket predicted_value into n_bins equal-width bins, compute mean
    predicted and mean actual beat_median_10d per bucket.
    Operates on resolved rows where beat_median_10d is not null."""
    base = df[df["resolved"] & df["beat_median_10d"].notnull()].copy()
    if base.empty:
        return pd.DataFrame()
    base["beat_median_10d"] = base["beat_median_10d"].astype(int)

    edges = [i / n_bins for i in range(n_bins + 1)]
    base["bucket"] = pd.cut(base["predicted_value"],
                             bins=edges, labels=False, include_lowest=True)
    grp = base.groupby("bucket")
    out = pd.DataFrame({
        "n":         grp.size(),
        "mean_pred": grp["predicted_value"].mean(),
        "mean_act":  grp["beat_median_10d"].mean(),
    }).reset_index()
    return out


calib_df = build_calibration_data(filtered, n_bins=10)

if calib_df.empty:
    st.info(
        "No resolved predictions with binary outcomes yet. Calibration plot "
        "will populate as predictions resolve."
    )
else:
    fig_calib = go.Figure()

    # Diagonal reference line (perfect calibration)
    fig_calib.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1],
        mode="lines",
        line=dict(color="#888", width=1, dash="dot"),
        name="Perfect calibration",
        hoverinfo="skip",
    ))

    # Actual calibration points
    fig_calib.add_trace(go.Scatter(
        x=calib_df["mean_pred"],
        y=calib_df["mean_act"],
        mode="lines+markers",
        line=dict(color="#2563eb", width=2),
        marker=dict(size=[max(6, min(30, n / 5)) for n in calib_df["n"]],
                    color="#2563eb"),
        name="Model",
        hovertemplate=(
            "<b>Bucket %{customdata[0]}</b><br>"
            "Mean predicted: %{x:.3f}<br>"
            "Actual hit rate: %{y:.3f}<br>"
            "n: %{customdata[1]:,}"
            "<extra></extra>"
        ),
        customdata=list(zip(calib_df["bucket"].astype(int), calib_df["n"].astype(int))),
    ))

    fig_calib.update_layout(
        template="plotly",
        height=420,
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis=dict(title="Mean predicted probability",
                   range=[0, 1], dtick=0.1),
        yaxis=dict(title="Actual hit rate (share beating median)",
                   range=[0, 1], dtick=0.1),
        legend=dict(orientation="h", y=1.08, x=1, xanchor="right"),
    )
    st.plotly_chart(fig_calib, use_container_width=True)


st.divider()


# ============================================================
# CHART 8: CONFUSION MATRIX
# ============================================================
st.subheader("Confusion matrix")
st.caption(
    "Predicted class (0 = below median, 1 = above) vs actual outcome over "
    "resolved predictions. Diagonal cells = correct; off-diagonal = errors. "
    "Cell sizes scaled to share of total."
)


def build_confusion_matrix(df: pd.DataFrame) -> pd.DataFrame | None:
    """Return 2x2 grid as a DataFrame, or None if no resolved data."""
    base = df[df["resolved"]
              & df["predicted_class"].notnull()
              & df["beat_median_10d"].notnull()].copy()
    if base.empty:
        return None
    base["predicted_class"] = base["predicted_class"].astype(int)
    base["beat_median_10d"] = base["beat_median_10d"].astype(int)
    cm = pd.crosstab(
        base["predicted_class"],
        base["beat_median_10d"],
        rownames=["Predicted"],
        colnames=["Actual"],
        dropna=False,
    )
    # Ensure both classes present in both axes
    for v in (0, 1):
        if v not in cm.index:
            cm.loc[v] = [0] * cm.shape[1]
        if v not in cm.columns:
            cm[v] = [0] * cm.shape[0]
    cm = cm.sort_index().sort_index(axis=1)
    return cm


cm = build_confusion_matrix(filtered)

if cm is None:
    st.info(
        "No resolved predictions with both predicted class and actual outcome. "
        "Confusion matrix will populate as predictions resolve."
    )
else:
    total = int(cm.values.sum())
    cm_pct = cm / total * 100

    cm1, cm2 = st.columns([2, 1])

    with cm1:
        # Heatmap: rows = predicted, cols = actual
        z = cm.values
        text = [[f"{cm.iloc[i, j]:,}<br>{cm_pct.iloc[i, j]:.1f}%"
                 for j in range(cm.shape[1])]
                for i in range(cm.shape[0])]

        fig_cm = go.Figure(data=go.Heatmap(
            z=z,
            x=["Actual: Below median (0)", "Actual: Above median (1)"],
            y=["Predicted: Below (0)", "Predicted: Above (1)"],
            colorscale=[[0, "#fee2e2"], [1, "#0a7a0a"]],
            text=text,
            texttemplate="%{text}",
            textfont=dict(size=14, color="#111"),
            showscale=False,
            hovertemplate="%{y} / %{x}<br>Count: %{z}<extra></extra>",
        ))
        fig_cm.update_layout(
            template="plotly",
            height=380,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis=dict(side="top"),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_cm, use_container_width=True)

    with cm2:
        st.markdown("**Metrics**")
        tn, fp = int(cm.iloc[0, 0]), int(cm.iloc[0, 1])
        fn, tp = int(cm.iloc[1, 0]), int(cm.iloc[1, 1])
        denom = tn + fp + fn + tp
        acc = (tn + tp) / denom if denom else 0
        prec = tp / (tp + fp) if (tp + fp) else 0
        rec  = tp / (tp + fn) if (tp + fn) else 0
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
        st.metric("Accuracy", f"{acc * 100:.1f}%")
        st.metric("Precision (positive class)", f"{prec * 100:.1f}%")
        st.metric("Recall (positive class)", f"{rec * 100:.1f}%")
        st.metric("F1", f"{f1:.3f}")


st.divider()


# ============================================================
# DEBUG (optional, collapsed)
# ============================================================
with st.expander("Debug: data preview", expanded=False):
    st.write("**Models loaded:**", len(models))
    st.dataframe(models, use_container_width=True, hide_index=True)
    st.write("**Predictions for selected model:**", len(predictions))
    st.write("**Targets loaded:**", len(targets))
    st.write("**Outcomes (joined):**", len(outcomes))
    st.write("**Metrics:**", metrics)
    st.dataframe(filtered.head(20), use_container_width=True, hide_index=True)
"""
Sentiment — FinBERT-derived daily sentiment aggregates per ticker.

Data source: sentiment_daily in Supabase (last 90 days, refreshed daily).
Joined to:
  - universe (for sector and company name)
  - ml_predictions (for the "sentiment vs ML predictions" cross-view)

Sections:
  1. Today's extremes (most positive / most negative tickers)
  2. Sentiment by sector heatmap
  3. Sentiment leaders & laggards over a date range
  4. Per-ticker sentiment time series
  5. Sentiment vs ML predictions scatter

Data conventions:
- avg_net_score ranges roughly [-1, +1]; > 0 = net positive, < 0 = net negative
- pct_positive, pct_negative are stored as DECIMALS (0.65 = 65%); multiply by
  100 EXACTLY ONCE just before rendering, per the project convention.
- A given (ticker, sentiment_date) row aggregates ALL articles published that
  day mentioning that ticker. n_articles is the article count for that bucket.
"""

from datetime import date, timedelta
import pandas as pd
import streamlit as st
from lib.supabase_client import get_client

st.set_page_config(page_title="Sentiment", page_icon="📰", layout="wide")
st.title("📰 Sentiment")
st.caption("FinBERT daily sentiment aggregates — what the news is saying")


# Decimal-stored percent columns (multiply by 100 right before rendering)
DECIMAL_PCT_COLS = ["pct_positive", "pct_negative"]


# ============================================================
# DATA LAYER
# ============================================================
@st.cache_data(ttl=300)
def load_sentiment() -> pd.DataFrame:
    """Load the full sentiment_daily window (~90 days). Pages past 1000-row default."""
    s = get_client()
    rows = []
    offset = 0
    while True:
        batch = (s.table("sentiment_daily")
                  .select("ticker, sentiment_date, n_articles, "
                          "avg_net_score, avg_confidence, "
                          "pct_positive, pct_negative, n_publishers")
                  .order("sentiment_date", desc=True)
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
    df["sentiment_date"] = pd.to_datetime(df["sentiment_date"]).dt.date
    return df


@st.cache_data(ttl=300)
def load_universe() -> pd.DataFrame:
    """Load universe for ticker -> sector / company_name lookup."""
    s = get_client()
    rows = (s.table("universe")
             .select("ticker, company_name, sector")
             .execute().data)
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def load_predictions_for_date(target_date: date) -> pd.DataFrame:
    """Load ml_predictions for a single date.
    Used in section 5 (sentiment vs predictions scatter)."""
    s = get_client()
    rows = []
    offset = 0
    while True:
        batch = (s.table("ml_predictions")
                  .select("ticker, prediction_date, model_id, "
                          "predicted_value, decile, top_decile_flag")
                  .eq("prediction_date", str(target_date))
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


# ============================================================
# LOAD DATA
# ============================================================
sentiment = load_sentiment()
universe = load_universe()

if sentiment.empty:
    st.warning(
        "No sentiment data in Supabase. Verify the push_to_supabase.py "
        "sync ran today, and that sentiment_daily has rows."
    )
    st.stop()

# Enrich with sector / company_name from universe
if not universe.empty:
    sentiment = sentiment.merge(
        universe[["ticker", "company_name", "sector"]],
        on="ticker",
        how="left",
    )
else:
    sentiment["company_name"] = None
    sentiment["sector"] = None


# ============================================================
# CONTROLS (page-wide; section-specific controls live inside their sections)
# ============================================================
available_dates = sorted(sentiment["sentiment_date"].unique(), reverse=True)
latest_date = available_dates[0]
earliest_date = available_dates[-1]

ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 2])

with ctrl_col1:
    # Default to most recent date with data
    snapshot_date = st.date_input(
        "Snapshot date",
        value=latest_date,
        min_value=earliest_date,
        max_value=latest_date,
        help="Date used for 'Today's extremes' and the sector heatmap. "
             "Other sections have their own date range pickers.",
    )

with ctrl_col2:
    sectors_available = sorted(
        s for s in sentiment["sector"].dropna().unique() if s
    )
    selected_sectors = st.multiselect(
        "Sector filter",
        options=sectors_available,
        default=[],   # empty = all sectors
        help="Limit to specific sectors. Empty = include all.",
    )

with ctrl_col3:
    min_articles = st.slider(
        "Min articles per ticker",
        min_value=1, max_value=20, value=3,
        help="Exclude tickers with fewer than N articles on a given date. "
             "Filters out noise from one-off mentions.",
    )


# ============================================================
# APPLY FILTERS
# ============================================================
mask = sentiment["n_articles"] >= min_articles
if selected_sectors:
    mask &= sentiment["sector"].isin(selected_sectors)

filtered_all = sentiment[mask].copy()
snapshot = filtered_all[filtered_all["sentiment_date"] == snapshot_date].copy()

# Sentiment-page-wide info caption
st.caption(
    f"Snapshot: **{snapshot_date}** | "
    f"Sectors: **{'All' if not selected_sectors else ', '.join(selected_sectors)}** | "
    f"Min articles: **{min_articles}** | "
    f"Tickers on snapshot date: **{len(snapshot):,}** "
    f"(out of {len(sentiment[sentiment['sentiment_date'] == snapshot_date]):,} total)"
)

st.divider()


# ============================================================
# SECTION 1: TODAY'S EXTREMES
# ============================================================
st.subheader("Today's extremes")
st.caption(
    f"Top 10 most positive and most negative tickers on {snapshot_date}. "
    "Score range is roughly -1 to +1 (FinBERT net score). Click a row to "
    "jump to its Ticker Detail page."
)


def fmt_score(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{float(v):+.4f}"


if snapshot.empty:
    st.info(
        "No tickers meet the current filters on the snapshot date. "
        "Try lowering the 'Min articles' slider or clearing the sector filter."
    )
else:
    ext_col1, ext_col2 = st.columns(2)

    # Common display columns + config used by both tables
    display_cols = ["ticker", "company_name", "sector",
                    "avg_net_score", "n_articles", "n_publishers"]
    col_config = {
        "ticker":        st.column_config.TextColumn("Ticker"),
        "company_name":  st.column_config.TextColumn("Company"),
        "sector":        st.column_config.TextColumn("Sector"),
        "avg_net_score": st.column_config.NumberColumn(
            "FinBERT score",
            format="%+.4f",
            help="Net sentiment score (positive_share - negative_share, "
                 "weighted by confidence). Range ~[-1, +1].",
        ),
        "n_articles":    st.column_config.NumberColumn("Articles", format="%d"),
        "n_publishers":  st.column_config.NumberColumn("Publishers", format="%d"),
    }

    # ---------- MOST POSITIVE ----------
    with ext_col1:
        st.markdown("##### :green[Most positive]")
        top_pos = (
            snapshot.sort_values("avg_net_score", ascending=False)
                    .head(10)
                    .reset_index(drop=True)
        )

        pos_event = st.dataframe(
            top_pos[display_cols],
            use_container_width=True,
            hide_index=True,
            column_config=col_config,
            on_select="rerun",
            selection_mode="single-row",
            key="extremes_positive",
        )
        # Click → jump to Ticker Detail
        sel = pos_event.selection.get("rows") if pos_event else None
        if sel:
            ticker = top_pos.iloc[sel[0]]["ticker"]
            st.session_state["selected_ticker"] = ticker
            st.switch_page("pages/2_Ticker_Detail.py")

    # ---------- MOST NEGATIVE ----------
    with ext_col2:
        st.markdown("##### :red[Most negative]")
        top_neg = (
            snapshot.sort_values("avg_net_score", ascending=True)
                    .head(10)
                    .reset_index(drop=True)
        )

        neg_event = st.dataframe(
            top_neg[display_cols],
            use_container_width=True,
            hide_index=True,
            column_config=col_config,
            on_select="rerun",
            selection_mode="single-row",
            key="extremes_negative",
        )
        sel = neg_event.selection.get("rows") if neg_event else None
        if sel:
            ticker = top_neg.iloc[sel[0]]["ticker"]
            st.session_state["selected_ticker"] = ticker
            st.switch_page("pages/2_Ticker_Detail.py")


st.divider()


# ============================================================
# SECTION 2: SENTIMENT BY SECTOR HEATMAP
# ============================================================
st.subheader("Sentiment by sector")
st.caption(
    f"Article-weighted average FinBERT score per sector on {snapshot_date}. "
    "Each ticker contributes in proportion to its article count, so heavily-"
    "covered names move the sector average more. Sorted most positive to "
    "most negative."
)

import plotly.graph_objects as go  # noqa: E402

if snapshot.empty or snapshot["sector"].isna().all():
    st.info("No sector-tagged sentiment data on the snapshot date.")
else:
    base = snapshot.dropna(subset=["sector", "avg_net_score", "n_articles"]).copy()

    # Article-weighted average per sector
    def _weighted_sector_summary(df: pd.DataFrame) -> pd.DataFrame:
        out = []
        for sector, grp in df.groupby("sector"):
            total_articles = int(grp["n_articles"].sum())
            if total_articles == 0:
                continue
            weighted = float(
                (grp["avg_net_score"] * grp["n_articles"]).sum() / total_articles
            )
            out.append({
                "sector": sector,
                "weighted_score": weighted,
                "n_tickers": int(len(grp)),
                "n_articles": total_articles,
            })
        return pd.DataFrame(out).sort_values("weighted_score", ascending=False)

    sector_df = _weighted_sector_summary(base)

    if sector_df.empty:
        st.info("No sectors meet the current filters.")
    else:
        # Red → green color scale based on weighted_score
        # Map score in [-0.5, +0.5] → 0..1 for color picking; clamp outside
        def _color_for_score(v: float) -> str:
            if v >= 0.3:   return "#0a7a0a"
            if v >= 0.15:  return "#4c4"
            if v >= 0.05:  return "#9f9"
            if v >  -0.05: return "#dcdcdc"
            if v > -0.15:  return "#fcc"
            if v > -0.3:   return "#e77"
            return "#a00"

        colors = [_color_for_score(v) for v in sector_df["weighted_score"]]

        fig_sec = go.Figure()
        fig_sec.add_trace(go.Bar(
            y=sector_df["sector"],
            x=sector_df["weighted_score"],
            orientation="h",
            marker_color=colors,
            text=[
                f"{s:+.3f}  ({a} article{'s' if a != 1 else ''}, "
                f"{t} ticker{'s' if t != 1 else ''})"
                for s, a, t in zip(sector_df["weighted_score"],
                                    sector_df["n_articles"],
                                    sector_df["n_tickers"])
            ],
            textposition="outside",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Weighted score: %{x:+.4f}<br>"
                "Articles: %{customdata[0]:,}<br>"
                "Tickers: %{customdata[1]}"
                "<extra></extra>"
            ),
            customdata=list(zip(sector_df["n_articles"], sector_df["n_tickers"])),
            name="Sentiment",
        ))
        # Zero reference line
        fig_sec.add_vline(x=0, line_dash="dot", line_color="#888", line_width=1)

        # Symmetric x-axis range with a little padding past the extremes
        max_abs = float(sector_df["weighted_score"].abs().max())
        pad = max(0.15, max_abs * 1.4)

        fig_sec.update_layout(
            template="plotly",
            height=max(320, 36 * len(sector_df) + 60),
            margin=dict(l=10, r=160, t=10, b=40),
            xaxis=dict(title="Article-weighted FinBERT score",
                       range=[-pad, pad], zeroline=False),
            yaxis=dict(autorange="reversed"),  # most positive at top
            showlegend=False,
        )
        st.plotly_chart(fig_sec, use_container_width=True)


st.divider()


# ============================================================
# SECTION 3: SENTIMENT LEADERS & LAGGARDS OVER A DATE RANGE
# ============================================================
st.subheader("Sustained sentiment — leaders & laggards")
st.caption(
    "Article-weighted avg sentiment over a multi-day window, plus consistency "
    "(how many days were positive vs negative). Filters out one-day blips. "
    "Tickers need at least N days of coverage to qualify."
)

# Section-specific controls
sec3_col1, sec3_col2, sec3_col3 = st.columns([3, 2, 2])

with sec3_col1:
    # Default: last 14 days of available data
    default_start = latest_date - timedelta(days=14)
    if default_start < earliest_date:
        default_start = earliest_date
    range_value = st.date_input(
        "Sustained-window date range",
        value=(default_start, latest_date),
        min_value=earliest_date,
        max_value=latest_date,
        key="leaders_laggards_date_range",
        help="Window to compute the article-weighted average over.",
    )
    if isinstance(range_value, tuple) and len(range_value) == 2:
        range_start, range_end = range_value
    else:
        range_start = range_end = (range_value if not isinstance(range_value, tuple)
                                   else range_value[0])

with sec3_col2:
    min_days = st.slider(
        "Min days with coverage",
        min_value=1, max_value=21, value=5,
        key="leaders_laggards_min_days",
        help="Exclude tickers with fewer than N days of sentiment data in the range.",
    )

with sec3_col3:
    sort_metric = st.radio(
        "Rank by",
        options=["Weighted avg score", "Consistency (% days positive)"],
        index=0,
        key="leaders_laggards_sort",
        help="Weighted average favors strong-tone tickers; consistency favors "
             "tickers that are positive (or negative) most days in the window.",
    )


# Filter to window
in_range = filtered_all[
    (filtered_all["sentiment_date"] >= range_start)
    & (filtered_all["sentiment_date"] <= range_end)
].copy()

if in_range.empty:
    st.info("No sentiment data in the selected window.")
else:
    def _per_ticker_window_summary(df: pd.DataFrame) -> pd.DataFrame:
        out = []
        for ticker, grp in df.groupby("ticker"):
            n_days = int(len(grp))
            total_articles = int(grp["n_articles"].sum())
            if total_articles == 0:
                continue
            weighted_score = float(
                (grp["avg_net_score"] * grp["n_articles"]).sum() / total_articles
            )
            n_days_pos = int((grp["avg_net_score"] > 0).sum())
            n_days_neg = int((grp["avg_net_score"] < 0).sum())
            pct_days_pos = (n_days_pos / n_days * 100) if n_days else 0.0
            pct_days_neg = (n_days_neg / n_days * 100) if n_days else 0.0
            out.append({
                "ticker": ticker,
                "company_name": grp["company_name"].iloc[0],
                "sector": grp["sector"].iloc[0],
                "weighted_score": weighted_score,
                "n_days": n_days,
                "n_days_pos": n_days_pos,
                "n_days_neg": n_days_neg,
                "pct_days_pos": pct_days_pos,
                "pct_days_neg": pct_days_neg,
                "total_articles": total_articles,
            })
        return pd.DataFrame(out)

    summary = _per_ticker_window_summary(in_range)
    # Apply min_days qualifier
    summary = summary[summary["n_days"] >= min_days]

    if summary.empty:
        st.info(
            f"No tickers meet the qualifier ({min_days}+ days of coverage) in this window. "
            "Try a wider date range or lower the threshold."
        )
    else:
        # Sort: leaders use the chosen metric descending; laggards reverse
        if sort_metric == "Weighted avg score":
            leaders = summary.sort_values("weighted_score", ascending=False).head(10)
            laggards = summary.sort_values("weighted_score", ascending=True).head(10)
        else:  # Consistency
            leaders = summary.sort_values(["pct_days_pos", "weighted_score"],
                                          ascending=[False, False]).head(10)
            laggards = summary.sort_values(["pct_days_neg", "weighted_score"],
                                          ascending=[False, True]).head(10)

        display_cols_ll = [
            "ticker", "company_name", "sector",
            "weighted_score", "pct_days_pos", "pct_days_neg",
            "n_days", "total_articles",
        ]
        col_config_ll = {
            "ticker":         st.column_config.TextColumn("Ticker"),
            "company_name":   st.column_config.TextColumn("Company"),
            "sector":         st.column_config.TextColumn("Sector"),
            "weighted_score": st.column_config.NumberColumn(
                "Weighted score", format="%+.4f",
                help="Article-weighted average FinBERT score over the window.",
            ),
            "pct_days_pos":   st.column_config.NumberColumn(
                "% days pos", format="%.0f%%",
                help="Share of days in the window with positive avg_net_score.",
            ),
            "pct_days_neg":   st.column_config.NumberColumn(
                "% days neg", format="%.0f%%",
                help="Share of days in the window with negative avg_net_score.",
            ),
            "n_days":         st.column_config.NumberColumn("Days covered", format="%d"),
            "total_articles": st.column_config.NumberColumn("Total articles", format="%d"),
        }

        ll_col1, ll_col2 = st.columns(2)

        with ll_col1:
            st.markdown("##### :green[Leaders]")
            lead_event = st.dataframe(
                leaders[display_cols_ll].reset_index(drop=True),
                use_container_width=True,
                hide_index=True,
                column_config=col_config_ll,
                on_select="rerun",
                selection_mode="single-row",
                key="leaders_table",
            )
            sel = lead_event.selection.get("rows") if lead_event else None
            if sel:
                ticker = leaders.iloc[sel[0]]["ticker"]
                st.session_state["selected_ticker"] = ticker
                st.switch_page("pages/2_Ticker_Detail.py")

        with ll_col2:
            st.markdown("##### :red[Laggards]")
            lag_event = st.dataframe(
                laggards[display_cols_ll].reset_index(drop=True),
                use_container_width=True,
                hide_index=True,
                column_config=col_config_ll,
                on_select="rerun",
                selection_mode="single-row",
                key="laggards_table",
            )
            sel = lag_event.selection.get("rows") if lag_event else None
            if sel:
                ticker = laggards.iloc[sel[0]]["ticker"]
                st.session_state["selected_ticker"] = ticker
                st.switch_page("pages/2_Ticker_Detail.py")


st.divider()


# ============================================================
# SECTION 4: PER-TICKER SENTIMENT TIME SERIES
# ============================================================
st.subheader("Per-ticker sentiment time series")
st.caption(
    "Daily FinBERT score for a single ticker over the available window, "
    "with a 5-day rolling average. Markers flag extreme days "
    "(≥ +0.40 = strong positive, ≤ -0.25 = strong negative — matches the "
    "thresholds used in the daily FinBERT email)."
)

# Pick the default ticker = the one with most articles on the snapshot date
# (falls back to alphabetical first if snapshot is empty)
tickers_with_sentiment = sorted(sentiment["ticker"].dropna().unique())
if not tickers_with_sentiment:
    st.info("No tickers with sentiment data available.")
else:
    if not snapshot.empty:
        default_ticker = (
            snapshot.sort_values("n_articles", ascending=False)
                    .iloc[0]["ticker"]
        )
    else:
        default_ticker = tickers_with_sentiment[0]

    try:
        default_idx = tickers_with_sentiment.index(default_ticker)
    except ValueError:
        default_idx = 0

    # Honor session_state["selected_ticker"] if the user got here via click-through
    if "selected_ticker" in st.session_state:
        st_pick = st.session_state["selected_ticker"]
        if st_pick in tickers_with_sentiment:
            default_idx = tickers_with_sentiment.index(st_pick)

    sec4_col1, sec4_col2 = st.columns([2, 5])

    with sec4_col1:
        selected_ticker = st.selectbox(
            "Ticker",
            options=tickers_with_sentiment,
            index=default_idx,
            key="sentiment_ts_ticker",
        )

    # Pull this ticker's full window (unfiltered — we want the time series
    # regardless of the snapshot-date/sector filters above)
    ts_df = (
        sentiment[sentiment["ticker"] == selected_ticker]
            .sort_values("sentiment_date")
            .copy()
    )

    if ts_df.empty:
        st.info(f"No sentiment data for {selected_ticker} in the window.")
    else:
        # Rolling average
        ts_df["rolling_5d"] = ts_df["avg_net_score"].rolling(
            window=5, min_periods=1
        ).mean()

        # Extreme-day markers
        POS_THRESHOLD = 0.40
        NEG_THRESHOLD = -0.25
        extreme_pos = ts_df[ts_df["avg_net_score"] >= POS_THRESHOLD]
        extreme_neg = ts_df[ts_df["avg_net_score"] <= NEG_THRESHOLD]

        # Stats for the side panel
        latest_row = ts_df.iloc[-1]
        avg_score = float(ts_df["avg_net_score"].mean())
        total_days = int(len(ts_df))
        total_articles = int(ts_df["n_articles"].sum())
        n_extreme_pos = int(len(extreme_pos))
        n_extreme_neg = int(len(extreme_neg))

        # Display: chart on left, stats on right
        chart_col, stats_col = st.columns([3, 1])

        with chart_col:
            from plotly.subplots import make_subplots

            fig_ts = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.06,
                row_heights=[0.7, 0.3],
            )

            # Top panel: daily score
            fig_ts.add_trace(
                go.Scatter(
                    x=ts_df["sentiment_date"], y=ts_df["avg_net_score"],
                    mode="lines+markers",
                    line=dict(color="#2563eb", width=1.5),
                    marker=dict(size=5, color="#2563eb"),
                    name="Daily score",
                    hovertemplate=(
                        "<b>%{x|%Y-%m-%d}</b><br>"
                        "Score: %{y:+.4f}<br>"
                        "Articles: %{customdata}"
                        "<extra></extra>"
                    ),
                    customdata=ts_df["n_articles"],
                ),
                row=1, col=1,
            )

            # 5-day rolling average
            fig_ts.add_trace(
                go.Scatter(
                    x=ts_df["sentiment_date"], y=ts_df["rolling_5d"],
                    mode="lines",
                    line=dict(color="#dc2626", width=2, dash="dash"),
                    name="5-day rolling avg",
                    hovertemplate=(
                        "<b>%{x|%Y-%m-%d}</b><br>"
                        "5-day avg: %{y:+.4f}"
                        "<extra></extra>"
                    ),
                ),
                row=1, col=1,
            )

            # Extreme positive markers
            if not extreme_pos.empty:
                fig_ts.add_trace(
                    go.Scatter(
                        x=extreme_pos["sentiment_date"],
                        y=extreme_pos["avg_net_score"],
                        mode="markers",
                        marker=dict(size=12, color="#0a7a0a", symbol="triangle-up",
                                    line=dict(color="#003a00", width=1)),
                        name=f"Extreme positive (≥ +{POS_THRESHOLD:.2f})",
                        hovertemplate=(
                            "<b>%{x|%Y-%m-%d}</b><br>"
                            "Extreme positive: %{y:+.4f}<br>"
                            "Articles: %{customdata}"
                            "<extra></extra>"
                        ),
                        customdata=extreme_pos["n_articles"],
                    ),
                    row=1, col=1,
                )
            # Extreme negative markers
            if not extreme_neg.empty:
                fig_ts.add_trace(
                    go.Scatter(
                        x=extreme_neg["sentiment_date"],
                        y=extreme_neg["avg_net_score"],
                        mode="markers",
                        marker=dict(size=12, color="#a00", symbol="triangle-down",
                                    line=dict(color="#400000", width=1)),
                        name=f"Extreme negative (≤ {NEG_THRESHOLD:+.2f})",
                        hovertemplate=(
                            "<b>%{x|%Y-%m-%d}</b><br>"
                            "Extreme negative: %{y:+.4f}<br>"
                            "Articles: %{customdata}"
                            "<extra></extra>"
                        ),
                        customdata=extreme_neg["n_articles"],
                    ),
                    row=1, col=1,
                )

            # Zero reference
            fig_ts.add_hline(y=0, line_dash="dot", line_color="#888",
                             line_width=1, row=1, col=1)

            # Bottom panel: article counts
            fig_ts.add_trace(
                go.Bar(
                    x=ts_df["sentiment_date"], y=ts_df["n_articles"],
                    marker_color="#6b7280",
                    hovertemplate=(
                        "<b>%{x|%Y-%m-%d}</b><br>"
                        "Articles: %{y}"
                        "<extra></extra>"
                    ),
                    name="Articles",
                    showlegend=False,
                ),
                row=2, col=1,
            )

            fig_ts.update_layout(
                template="plotly",
                height=480,
                margin=dict(l=40, r=20, t=10, b=40),
                hovermode="x unified",
                legend=dict(orientation="h", y=1.10, x=1, xanchor="right"),
            )
            fig_ts.update_yaxes(title_text="FinBERT score", zeroline=False,
                                row=1, col=1)
            fig_ts.update_yaxes(title_text="Articles", row=2, col=1)
            fig_ts.update_xaxes(type="date", tickformat="%Y-%m-%d",
                                row=2, col=1)

            st.plotly_chart(fig_ts, use_container_width=True)

        with stats_col:
            company_name = latest_row.get("company_name")
            sector = latest_row.get("sector")
            if pd.notna(company_name) and company_name:
                st.markdown(f"**{company_name}**")
            if pd.notna(sector) and sector:
                st.caption(f"_{sector}_")

            st.metric(
                "Latest score",
                f"{float(latest_row['avg_net_score']):+.4f}",
                help=f"As of {latest_row['sentiment_date']}",
            )
            st.metric("Window avg", f"{avg_score:+.4f}")
            st.metric("Days with coverage", f"{total_days}")
            st.metric("Total articles", f"{total_articles:,}")
            st.metric("Extreme + days", f"{n_extreme_pos}")
            st.metric("Extreme - days", f"{n_extreme_neg}")


st.divider()


# ============================================================
# SECTION 5: SENTIMENT vs AI-ML PREDICTIONS
# ============================================================
st.subheader("Sentiment vs AI-ML predictions")
st.caption(
    "Each dot is a ticker on the snapshot date with both sentiment data AND "
    "an AI-ML prediction. Quadrants tell different stories: top-right = model "
    "and news agree (bullish). Top-left = contrarian bull (model sees what "
    "news doesn't). Bottom-right = contrarian bear (model dismisses positive "
    "news). Bottom-left = model and news agree (bearish)."
)

# Load predictions for the snapshot date
preds_today = load_predictions_for_date(snapshot_date)

if preds_today.empty:
    st.info(
        f"No AI-ML predictions for {snapshot_date}. The daily inference job may "
        "not have run yet, or you've selected a weekend/holiday date."
    )
elif snapshot.empty:
    st.info("No sentiment data on the snapshot date to overlay.")
else:
    # Join sentiment ⋈ predictions on (ticker, date)
    cross = snapshot.merge(
        preds_today[["ticker", "predicted_value", "decile", "top_decile_flag"]],
        on="ticker",
        how="inner",
    )

    if cross.empty:
        st.info(
            "No tickers overlap between today's sentiment and AI-ML predictions. "
            "This is expected if sentiment data has different ticker coverage."
        )
    else:
        # Color by decile: top decile green, bottom decile red, middle gray
        def _quadrant_color(decile):
            if pd.isna(decile):
                return "#9ca3af"
            d = int(decile)
            if d == 10: return "#0a7a0a"
            if d == 1:  return "#a00"
            return "#9ca3af"

        cross["color"] = cross["decile"].apply(_quadrant_color)

        # Marker sizes scaled by n_articles (log-ish to avoid giant dots)
        def _scale_size(n):
            if pd.isna(n) or n <= 0:
                return 6
            return float(min(28, 6 + (n ** 0.5) * 3))

        cross["marker_size"] = cross["n_articles"].apply(_scale_size)

        # ---------- SCATTER ----------
        fig_sv = go.Figure()

        # Plot one trace per color group so the legend is meaningful
        groups = [
            ("Top decile (model bullish)",   "#0a7a0a"),
            ("Middle deciles",                "#9ca3af"),
            ("Bottom decile (model bearish)", "#a00"),
        ]
        for label, color in groups:
            sub = cross[cross["color"] == color]
            if sub.empty:
                continue
            fig_sv.add_trace(go.Scatter(
                x=sub["avg_net_score"], y=sub["predicted_value"],
                mode="markers",
                marker=dict(
                    size=sub["marker_size"],
                    color=color,
                    opacity=0.75,
                    line=dict(color="#222", width=0.5),
                ),
                name=label,
                customdata=list(zip(
                    sub["ticker"],
                    sub["company_name"].fillna(""),
                    sub["sector"].fillna(""),
                    sub["decile"].fillna(-1).astype(int),
                    sub["n_articles"].fillna(0).astype(int),
                )),
                hovertemplate=(
                    "<b>%{customdata[0]}</b> — %{customdata[1]}<br>"
                    "Sector: %{customdata[2]}<br>"
                    "Sentiment: %{x:+.4f}<br>"
                    "Predicted: %{y:.4f}<br>"
                    "Decile: %{customdata[3]}<br>"
                    "Articles: %{customdata[4]}"
                    "<extra></extra>"
                ),
            ))

        # Reference lines: model-neutral at y=0.50, sentiment-neutral at x=0
        fig_sv.add_hline(y=0.50, line_dash="dot", line_color="#888",
                          line_width=1, annotation_text="Model neutral (0.50)",
                          annotation_position="bottom right",
                          annotation_font_color="#888")
        fig_sv.add_vline(x=0, line_dash="dot", line_color="#888",
                          line_width=1, annotation_text="Sentiment neutral",
                          annotation_position="top right",
                          annotation_font_color="#888")

        # Compute axis ranges with a little padding
        x_pad = max(0.1, float(cross["avg_net_score"].abs().max()) * 1.2)
        y_min = float(cross["predicted_value"].min())
        y_max = float(cross["predicted_value"].max())
        y_pad = max(0.02, (y_max - y_min) * 0.15)

        fig_sv.update_layout(
            template="plotly",
            height=520,
            margin=dict(l=40, r=20, t=20, b=40),
            xaxis=dict(title="Sentiment (avg_net_score)",
                        range=[-x_pad, x_pad], zeroline=False),
            yaxis=dict(title="AI-ML predicted_value (probability)",
                        range=[y_min - y_pad, y_max + y_pad], zeroline=False),
            legend=dict(orientation="h", y=1.08, x=1, xanchor="right"),
        )
        st.plotly_chart(fig_sv, use_container_width=True)

        # ---------- COMPANION QUADRANT TABLES ----------
        # Contrarian bulls: negative sentiment, model bullish (decile >= 8)
        # Contrarian bears: positive sentiment, model bearish (decile <= 3)
        contrarian_bulls = cross[
            (cross["avg_net_score"] < 0)
            & (cross["decile"].notnull())
            & (cross["decile"].astype(int) >= 8)
        ].copy()
        contrarian_bulls["gap"] = (
            contrarian_bulls["predicted_value"]
            - contrarian_bulls["avg_net_score"]   # bigger = more contrarian
        )
        contrarian_bulls = contrarian_bulls.sort_values(
            "gap", ascending=False
        ).head(5)

        contrarian_bears = cross[
            (cross["avg_net_score"] > 0)
            & (cross["decile"].notnull())
            & (cross["decile"].astype(int) <= 3)
        ].copy()
        contrarian_bears["gap"] = (
            contrarian_bears["avg_net_score"]
            - contrarian_bears["predicted_value"]  # bigger = more contrarian
        )
        contrarian_bears = contrarian_bears.sort_values(
            "gap", ascending=False
        ).head(5)

        # Display
        cb_cols = ["ticker", "company_name", "sector",
                   "avg_net_score", "predicted_value", "decile", "n_articles"]
        cb_config = {
            "ticker":         st.column_config.TextColumn("Ticker"),
            "company_name":   st.column_config.TextColumn("Company"),
            "sector":         st.column_config.TextColumn("Sector"),
            "avg_net_score":  st.column_config.NumberColumn("Sentiment", format="%+.4f"),
            "predicted_value": st.column_config.NumberColumn("Predicted", format="%.4f"),
            "decile":         st.column_config.NumberColumn("Decile", format="%d"),
            "n_articles":     st.column_config.NumberColumn("Articles", format="%d"),
        }

        cq1, cq2 = st.columns(2)

        with cq1:
            st.markdown("##### :green[Contrarian bulls]")
            st.caption(
                "Negative sentiment, model still bullish (decile ≥ 8). "
                "The model sees something the news doesn't."
            )
            if contrarian_bulls.empty:
                st.info("No contrarian bulls on this date.")
            else:
                ev = st.dataframe(
                    contrarian_bulls[cb_cols].reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True,
                    column_config=cb_config,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="contrarian_bulls",
                )
                sel = ev.selection.get("rows") if ev else None
                if sel:
                    ticker = contrarian_bulls.iloc[sel[0]]["ticker"]
                    st.session_state["selected_ticker"] = ticker
                    st.switch_page("pages/2_Ticker_Detail.py")

        with cq2:
            st.markdown("##### :red[Contrarian bears]")
            st.caption(
                "Positive sentiment, model still bearish (decile ≤ 3). "
                "The model dismisses the optimism."
            )
            if contrarian_bears.empty:
                st.info("No contrarian bears on this date.")
            else:
                ev = st.dataframe(
                    contrarian_bears[cb_cols].reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True,
                    column_config=cb_config,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="contrarian_bears",
                )
                sel = ev.selection.get("rows") if ev else None
                if sel:
                    ticker = contrarian_bears.iloc[sel[0]]["ticker"]
                    st.session_state["selected_ticker"] = ticker
                    st.switch_page("pages/2_Ticker_Detail.py")


st.divider()


# ============================================================
# DEBUG (optional, collapsed)
# ============================================================
with st.expander("Debug: data preview", expanded=False):
    st.write("**Sentiment rows loaded:**", len(sentiment))
    st.write("**Universe rows loaded:**", len(universe))
    st.write("**Date range:**", earliest_date, "to", latest_date)
    st.write("**Number of distinct dates:**", len(available_dates))
    st.write("**Filtered (all dates):**", len(filtered_all))
    st.write("**Snapshot date filtered:**", len(snapshot))
    st.dataframe(snapshot.head(20), use_container_width=True, hide_index=True)
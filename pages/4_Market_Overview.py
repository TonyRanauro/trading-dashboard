"""
Market Overview — sector heatmap, breadth metrics, and confluence callouts.
"""

from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st
from lib.supabase_client import get_client

st.set_page_config(page_title="Market Overview", page_icon="🌐", layout="wide")
st.title("🌐 Market Overview")
st.caption("Sector breadth, leadership, and recent confluence")

# ============================================================
# DATA LOADERS
# ============================================================
@st.cache_data(ttl=300)
def load_sector_summary() -> pd.DataFrame:
    s = get_client()
    data = (s.table("sector_summary")
              .select("*")
              .order("sector_date", desc=True)
              .execute().data)
    df = pd.DataFrame(data)
    if not df.empty:
        df["sector_date"] = pd.to_datetime(df["sector_date"])
        for col in df.columns:
            if col not in ("sector", "sector_date"):
                df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

@st.cache_data(ttl=300)
def load_recent_signals(days: int = 5) -> pd.DataFrame:
    s = get_client()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    data = (s.table("latest_signals")
              .select("*")
              .gte("signal_date", cutoff)
              .execute().data)
    df = pd.DataFrame(data)
    if not df.empty:
        df["signal_date"] = pd.to_datetime(df["signal_date"])
    return df

@st.cache_data(ttl=300)
def load_universe() -> pd.DataFrame:
    s = get_client()
    data = s.table("universe").select("ticker, sector").execute().data
    return pd.DataFrame(data)


# ============================================================
# LOAD DATA
# ============================================================
with st.spinner("Loading market data..."):
    sector_df = load_sector_summary()
    universe = load_universe()
    signals_df = load_recent_signals(days=5)

if sector_df.empty:
    st.error("No sector data available. Check the data push job.")
    st.stop()

latest_date = sector_df["sector_date"].max()
latest_snapshot = sector_df[sector_df["sector_date"] == latest_date].copy()

st.caption(f"Data as of **{latest_date.strftime('%Y-%m-%d')}**")

# ============================================================
# TOP METRICS — MARKET BREADTH
# ============================================================
st.subheader("Market breadth")

total_constituents = latest_snapshot["constituent_count"].sum()
if total_constituents > 0:
    pct_above_sma50 = (
        (latest_snapshot["pct_above_sma50"] * latest_snapshot["constituent_count"]).sum()
        / total_constituents
    )
    pct_above_sma200 = (
        (latest_snapshot["pct_above_sma200"] * latest_snapshot["constituent_count"]).sum()
        / total_constituents
    )
else:
    pct_above_sma50 = pct_above_sma200 = 0

five_day_ago_date = sector_df[sector_df["sector_date"] < latest_date - pd.Timedelta(days=4)]
if not five_day_ago_date.empty:
    prev_date = five_day_ago_date["sector_date"].max()
    prev_snapshot = sector_df[sector_df["sector_date"] == prev_date]
    prev_total = prev_snapshot["constituent_count"].sum()
    prev_pct_sma200 = (
        (prev_snapshot["pct_above_sma200"] * prev_snapshot["constituent_count"]).sum() / prev_total
        if prev_total > 0 else 0
    )
    breadth_change = pct_above_sma200 - prev_pct_sma200
else:
    breadth_change = None

total_bullish = (signals_df["direction"] == "bullish").sum() if not signals_df.empty else 0
total_bearish = (signals_df["direction"] == "bearish").sum() if not signals_df.empty else 0
net_signals = total_bullish - total_bearish

m1, m2, m3, m4 = st.columns(4)
m1.metric("% above SMA 50", f"{pct_above_sma50*100:.1f}%")
m2.metric(
    "% above SMA 200",
    f"{pct_above_sma200*100:.1f}%",
    f"{breadth_change*100:+.1f}% vs 5d ago" if breadth_change is not None else None,
)
m3.metric("Bullish signals (5d)", f"{total_bullish:,}")
m4.metric(
    "Net bull/bear (5d)",
    f"{net_signals:+d}",
    delta_color="normal" if net_signals >= 0 else "inverse",
)

# ============================================================
# SECTOR HEATMAP (TREEMAP — display only)
# ============================================================
st.divider()
st.subheader("Sector heatmap")

tf_col1, tf_col2 = st.columns([1, 3])
with tf_col1:
    timeframe = st.selectbox(
        "Return period",
        options=["1D", "5D", "20D", "60D"],
        index=2,
    )

return_col_map = {
    "1D": "avg_return_1d",
    "5D": "avg_return_5d",
    "20D": "avg_return_20d",
    "60D": "avg_return_60d",
}
return_col = return_col_map[timeframe]

# Prepare treemap data
# Prepare treemap data
treemap_df = latest_snapshot.dropna(subset=[return_col]).copy()
# Round to clean values to avoid floating-point display artifacts
treemap_df["return_pct"] = (treemap_df[return_col] * 100).round(2)
treemap_df["breadth_pct"] = (treemap_df["pct_above_sma200"] * 100).round(0)
# Pre-formatted text strings — bypass Plotly's number formatting entirely
treemap_df["return_label"] = treemap_df["return_pct"].apply(
    lambda v: f"{v:+.1f}%"
)
treemap_df["breadth_label"] = treemap_df["breadth_pct"].apply(
    lambda v: f"{v:.0f}%"
)
treemap_df["return_hover"] = treemap_df["return_pct"].apply(
    lambda v: f"{v:+.2f}%"
)

# Build the treemap as a pure visualization
fig = px.treemap(
    treemap_df,
    path=[px.Constant("All Sectors"), "sector"],
    values="constituent_count",
    color="return_pct",
    color_continuous_scale=[
        [0.0, "#7f1d1d"],
        [0.4, "#ef4444"],
        [0.5, "#9ca3af"],
        [0.6, "#10b981"],
        [1.0, "#065f46"],
    ],
    color_continuous_midpoint=0,
    custom_data=["sector", "return_label", "breadth_label",
                 "constituent_count", "return_hover"],
)

fig.update_traces(
    texttemplate=(
        "<b>%{customdata[0]}</b><br>"
        "%{customdata[1]}<br>"
        "<span style='font-size:0.85em'>Breadth: %{customdata[2]}</span>"
    ),
    textinfo="text",
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        f"Return ({timeframe}): " + "%{customdata[4]}<br>"
        "Breadth (above SMA200): %{customdata[2]}<br>"
        "Constituents: %{customdata[3]}<extra></extra>"
    ),
    hoverinfo="text",
    textfont=dict(size=14, color="white"),
    root_color="rgba(0,0,0,0)",
)


fig.update_layout(
    height=500,
    margin=dict(l=10, r=10, t=10, b=10),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    coloraxis_colorbar=dict(
        title=f"{timeframe} Return %",
        tickformat=".1f",
        thickness=12,
    ),
)

st.plotly_chart(fig, use_container_width=True)

# Drill-into-sector dropdown — cleaner than fighting Plotly click events
st.markdown("**Drill into a sector**")
drill_col1, drill_col2 = st.columns([2, 1])
with drill_col1:
    sectors_list = sorted(treemap_df["sector"].tolist())
    drill_sector = st.selectbox(
        "Choose sector",
        options=["—"] + sectors_list,
        label_visibility="collapsed",
        key="market_drill_sector",
    )
with drill_col2:
    if st.button("Filter Screener →", type="primary",
                 disabled=(drill_sector == "—"),
                 use_container_width=True):
        st.session_state.preset_sectors = [drill_sector]
        st.switch_page("pages/1_Screener.py")

# ============================================================
# SECTOR RANKING TABLE
# ============================================================
st.divider()
st.subheader("Sector ranking")

ranking_cols = ["sector", "constituent_count",
                "avg_return_1d", "avg_return_5d", "avg_return_20d",
                "avg_return_60d", "avg_return_252d",
                "pct_above_sma50", "pct_above_sma200"]
ranking_cols = [c for c in ranking_cols if c in latest_snapshot.columns]
ranking = latest_snapshot[ranking_cols].copy()
ranking = ranking.sort_values(return_col, ascending=False, na_position="last")

st.dataframe(
    ranking,
    use_container_width=True,
    hide_index=True,
    column_config={
        "sector": st.column_config.TextColumn("Sector"),
        "constituent_count": st.column_config.NumberColumn("Stocks", format="%d"),
        "avg_return_1d": st.column_config.NumberColumn("1D", format="%.2f%%"),
        "avg_return_5d": st.column_config.NumberColumn("5D", format="%.2f%%"),
        "avg_return_20d": st.column_config.NumberColumn("20D", format="%.2f%%"),
        "avg_return_60d": st.column_config.NumberColumn("60D", format="%.2f%%"),
        "avg_return_252d": st.column_config.NumberColumn("1Y", format="%.2f%%"),
        "pct_above_sma50": st.column_config.NumberColumn("% > SMA50", format="%.0f%%"),
        "pct_above_sma200": st.column_config.NumberColumn("% > SMA200", format="%.0f%%"),
    },
)

# ============================================================
# CONFLUENCE CALLOUTS
# ============================================================
st.divider()
st.subheader("Recent confluence (last 5 days)")

if signals_df.empty:
    st.info("No recent signals to analyze.")
else:
    sigs_with_sector = signals_df.merge(universe, on="ticker", how="left")

    sector_bull = (sigs_with_sector[sigs_with_sector["direction"] == "bullish"]
                   .groupby("sector").size().rename("bullish"))
    sector_bear = (sigs_with_sector[sigs_with_sector["direction"] == "bearish"]
                   .groupby("sector").size().rename("bearish"))
    sector_breakdown = pd.concat([sector_bull, sector_bear], axis=1).fillna(0).astype(int)
    sector_breakdown["net"] = sector_breakdown["bullish"] - sector_breakdown["bearish"]
    sector_breakdown = sector_breakdown.sort_values("net", ascending=False).reset_index()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Sector signal balance**")
        st.dataframe(
            sector_breakdown,
            use_container_width=True,
            hide_index=True,
            column_config={
                "sector": st.column_config.TextColumn("Sector"),
                "bullish": st.column_config.NumberColumn("Bull", format="%d"),
                "bearish": st.column_config.NumberColumn("Bear", format="%d"),
                "net": st.column_config.NumberColumn("Net", format="%+d"),
            },
        )

    with col2:
        st.markdown("**Most active tickers**")
        ticker_counts = (sigs_with_sector.groupby(["ticker", "sector"])
                         .size().reset_index(name="signals")
                         .sort_values("signals", ascending=False)
                         .head(15))
        st.dataframe(
            ticker_counts,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ticker": st.column_config.TextColumn("Ticker", width="small"),
                "sector": st.column_config.TextColumn("Sector"),
                "signals": st.column_config.NumberColumn("Signals (5d)", format="%d"),
            },
        )

# ============================================================
# TREND-CHANGE SIGNALS THIS WEEK
# ============================================================
trend_types = [
    "golden_cross_50_200", "death_cross_50_200",
    "cross_above_sma200", "cross_below_sma200",
]
if not signals_df.empty:
    trend_changes = signals_df[signals_df["signal_type"].isin(trend_types)].copy()
    if not trend_changes.empty:
        st.divider()
        st.subheader("Trend-change signals (rare events)")
        trend_changes = trend_changes.merge(universe, on="ticker", how="left")
        trend_changes = trend_changes[["signal_date", "ticker", "sector",
                                        "signal_type", "direction", "strength"]]
        trend_changes = trend_changes.sort_values("signal_date", ascending=False)
        st.dataframe(
            trend_changes,
            use_container_width=True,
            hide_index=True,
            column_config={
                "signal_date": st.column_config.DateColumn("Date", width="small"),
                "ticker": st.column_config.TextColumn("Ticker", width="small"),
                "sector": st.column_config.TextColumn("Sector"),
                "signal_type": st.column_config.TextColumn("Signal"),
                "direction": st.column_config.TextColumn("Direction"),
                "strength": st.column_config.NumberColumn("Strength", format="%.4f"),
            },
        )
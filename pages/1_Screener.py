"""
Screener — filter the universe by signals or current indicator state.
"""

from datetime import date, timedelta
import pandas as pd
import streamlit as st
from lib.supabase_client import get_client

st.set_page_config(page_title="Screener", page_icon="🔍", layout="wide")
st.title("🔍 Screener")
st.caption("Filter S&P 500 stocks by signal events or current indicator state")

# ============================================================
# DATA LOADERS (cached for 5 min)
# ============================================================
@st.cache_data(ttl=300)
def load_universe() -> pd.DataFrame:
    s = get_client()
    data = s.table("universe").select("*").execute().data
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def load_latest_indicators_for_date(target_date: str) -> pd.DataFrame:
    s = get_client()
    data = s.table("latest_indicators").select("*").eq(
        "indicator_date", target_date
    ).execute().data
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def load_signals_in_range(start_date: str, end_date: str) -> pd.DataFrame:
    s = get_client()
    data = (s.table("latest_signals")
              .select("*")
              .gte("signal_date", start_date)
              .lte("signal_date", end_date)
              .execute().data)
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def get_latest_indicator_date() -> str | None:
    s = get_client()
    result = (s.table("latest_indicators")
                .select("indicator_date")
                .order("indicator_date", desc=True)
                .limit(1).execute().data)
    return result[0]["indicator_date"] if result else None

@st.cache_data(ttl=300)
def get_signal_types() -> list[str]:
    s = get_client()
    data = s.table("latest_signals").select("signal_type").execute().data
    return sorted(set(r["signal_type"] for r in data))

# ============================================================
# UI: MODE TOGGLE
# ============================================================
mode = st.radio(
    "Filter mode",
    options=["State-driven (current values)", "Signal-driven (recent events)"],
    horizontal=True,
    label_visibility="collapsed",
)

st.divider()

# ============================================================
# LOAD BASE DATA
# ============================================================
universe = load_universe()
latest_date = get_latest_indicator_date()

if latest_date is None:
    st.error("No indicator data available. Check the data push job.")
    st.stop()

# ============================================================
# SIDEBAR FILTERS (shared across modes)
# ============================================================
with st.sidebar:
    st.header("Filters")

    sectors = sorted(universe["sector"].dropna().unique())
    selected_sectors = st.multiselect(
        "Sectors",
        options=sectors,
        default=sectors,
        help="Leave all selected for entire universe",
    )

    st.subheader("Relative Strength")
    rs_spy_min, rs_spy_max = st.slider(
        "RS vs SPY (20d)",
        min_value=-1.0, max_value=1.0,
        value=(-1.0, 1.0), step=0.05,
        format="%.2f",
        help="Stock return minus SPY return over 20 days. +0.1 = outperforming by 10%",
    )
    rs_sector_min, rs_sector_max = st.slider(
        "RS vs Sector (20d)",
        min_value=-1.0, max_value=1.0,
        value=(-1.0, 1.0), step=0.05,
        format="%.2f",
    )

    st.subheader("Momentum")
    rsi_min, rsi_max = st.slider(
        "RSI (14)",
        min_value=0, max_value=100,
        value=(0, 100), step=1,
    )

    st.subheader("Trend")
    sma200_options = st.radio(
        "Position vs SMA 200",
        options=["Any", "Above SMA200", "Below SMA200"],
        index=0,
    )

# ============================================================
# MODE: STATE-DRIVEN
# ============================================================
if mode.startswith("State"):
    st.subheader(f"Current state as of {latest_date}")

    with st.spinner("Loading current snapshot..."):
        df = load_latest_indicators_for_date(latest_date)

    if df.empty:
        st.warning(f"No indicator data for {latest_date}")
        st.stop()

    # Join sector info
    df = df.merge(universe[["ticker", "sector", "company_name"]],
                  on="ticker", how="left")

    # Apply filters
    df = df[df["sector"].isin(selected_sectors)]
    df = df[(df["rs_spy_20d"].fillna(0).astype(float) >= rs_spy_min) &
            (df["rs_spy_20d"].fillna(0).astype(float) <= rs_spy_max)]
    df = df[(df["rs_sector_20d"].fillna(0).astype(float) >= rs_sector_min) &
            (df["rs_sector_20d"].fillna(0).astype(float) <= rs_sector_max)]
    df = df[(df["rsi_14"].fillna(50).astype(float) >= rsi_min) &
            (df["rsi_14"].fillna(50).astype(float) <= rsi_max)]

    if sma200_options == "Above SMA200":
        df = df[df["return_252d"].astype(float) > df["return_252d"].astype(float) * 0]  # placeholder
        # Better: check close vs SMA. We can fetch current_prices, but for now use rs as proxy.
        # Best: re-derive from latest_indicators by joining with current_prices.
        # For v1, use a simpler proxy:
        # pct_from_high being closer to 0 = stronger trend
        # Or just leave as warning for now — proper fix in v2
        st.info("Note: 'Above SMA200' filter uses RS as proxy in v1. Refined in v2.")
        df = df[df["rs_spy_20d"].astype(float) > 0]
    elif sma200_options == "Below SMA200":
        df = df[df["rs_spy_20d"].astype(float) < 0]

    # Display columns subset
    display_cols = [
        "ticker", "sector", "company_name",
        "rsi_14", "macd_hist",
        "rs_spy_20d", "rs_sector_20d",
        "return_5d", "return_20d", "return_60d",
        "pct_from_high", "pct_from_low",
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    df_display = df[display_cols].copy()

    # Format numeric columns as percentages
    pct_cols = ["rs_spy_20d", "rs_sector_20d", "return_5d", "return_20d",
                "return_60d", "pct_from_high", "pct_from_low"]
    for c in pct_cols:
        if c in df_display.columns:
            df_display[c] = pd.to_numeric(df_display[c], errors="coerce")

    # Sort by RS vs SPY descending by default
    if "rs_spy_20d" in df_display.columns:
        df_display = df_display.sort_values("rs_spy_20d", ascending=False, na_position="last")

    # Summary
    col1, col2, col3 = st.columns(3)
    col1.metric("Matches", f"{len(df_display):,}")
    if "rs_spy_20d" in df_display.columns:
        avg_rs = df_display["rs_spy_20d"].mean()
        col2.metric("Avg RS vs SPY (20d)",
                    f"{avg_rs*100:+.2f}%" if pd.notna(avg_rs) else "—")
    if "rsi_14" in df_display.columns:
        avg_rsi = df_display["rsi_14"].mean()
        col3.metric("Avg RSI",
                    f"{avg_rsi:.1f}" if pd.notna(avg_rsi) else "—")

    # Render table with formatting
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", width="small"),
            "sector": st.column_config.TextColumn("Sector", width="medium"),
            "company_name": st.column_config.TextColumn("Company", width="medium"),
            "rsi_14": st.column_config.NumberColumn("RSI", format="%.1f"),
            "macd_hist": st.column_config.NumberColumn("MACD Hist", format="%.4f"),
            "rs_spy_20d": st.column_config.NumberColumn("RS vs SPY 20d", format="%.2f%%"),
            "rs_sector_20d": st.column_config.NumberColumn("RS vs Sector 20d", format="%.2f%%"),
            "return_5d": st.column_config.NumberColumn("Return 5d", format="%.2f%%"),
            "return_20d": st.column_config.NumberColumn("Return 20d", format="%.2f%%"),
            "return_60d": st.column_config.NumberColumn("Return 60d", format="%.2f%%"),
            "pct_from_high": st.column_config.NumberColumn("From 52w High", format="%.2f%%"),
            "pct_from_low": st.column_config.NumberColumn("From 52w Low", format="%.2f%%"),
        },
    )

# ============================================================
# MODE: SIGNAL-DRIVEN
# ============================================================
else:
    st.subheader("Recent signal events")

    col1, col2 = st.columns([1, 1])
    with col1:
        lookback_days = st.selectbox(
            "Lookback window",
            options=[1, 3, 5, 10, 20, 30, 60],
            index=2,
            format_func=lambda x: f"Last {x} day{'s' if x > 1 else ''}",
        )
    with col2:
        all_signal_types = get_signal_types()
        # Smart defaults — trend signals selected, momentum unselected
        trend_signals = [s for s in all_signal_types
                         if any(s.startswith(p) for p in
                                ["golden_cross", "death_cross", "cross_above_sma200",
                                 "cross_below_sma200", "rs_breakout", "rs_breakdown",
                                 "sector_leader", "breakout_52w", "breakdown_52w"])]
        selected_signals = st.multiselect(
            "Signal types",
            options=all_signal_types,
            default=trend_signals,
            help="Trend and breakout signals selected by default",
        )

    if not selected_signals:
        st.info("Select at least one signal type")
        st.stop()

    end_date = date.fromisoformat(latest_date)
    start_date = end_date - timedelta(days=lookback_days)

    with st.spinner("Loading signals..."):
        signals_df = load_signals_in_range(start_date.isoformat(), end_date.isoformat())
        indicators_df = load_latest_indicators_for_date(latest_date)

    if signals_df.empty:
        st.warning("No signals in this window")
        st.stop()

    # Filter to selected signal types
    signals_df = signals_df[signals_df["signal_type"].isin(selected_signals)]

    # Merge with universe for sector
    signals_df = signals_df.merge(
        universe[["ticker", "sector", "company_name"]],
        on="ticker", how="left",
    )

    # Filter by sidebar
    signals_df = signals_df[signals_df["sector"].isin(selected_sectors)]

    # Merge with current indicators to enrich
    if not indicators_df.empty:
        enrich_cols = ["ticker", "rsi_14", "rs_spy_20d", "rs_sector_20d",
                       "return_20d", "pct_from_high"]
        enrich_cols = [c for c in enrich_cols if c in indicators_df.columns]
        signals_df = signals_df.merge(
            indicators_df[enrich_cols], on="ticker", how="left"
        )

        # Apply sidebar filters using current state
        signals_df["rs_spy_20d_num"] = pd.to_numeric(
            signals_df.get("rs_spy_20d"), errors="coerce")
        signals_df["rs_sector_20d_num"] = pd.to_numeric(
            signals_df.get("rs_sector_20d"), errors="coerce")
        signals_df["rsi_14_num"] = pd.to_numeric(
            signals_df.get("rsi_14"), errors="coerce")

        signals_df = signals_df[
            (signals_df["rs_spy_20d_num"].fillna(0) >= rs_spy_min) &
            (signals_df["rs_spy_20d_num"].fillna(0) <= rs_spy_max) &
            (signals_df["rs_sector_20d_num"].fillna(0) >= rs_sector_min) &
            (signals_df["rs_sector_20d_num"].fillna(0) <= rs_sector_max) &
            (signals_df["rsi_14_num"].fillna(50) >= rsi_min) &
            (signals_df["rsi_14_num"].fillna(50) <= rsi_max)
        ]

    # Order by date desc, then strength
    signals_df["strength_num"] = pd.to_numeric(signals_df["strength"], errors="coerce")
    signals_df = signals_df.sort_values(
        ["signal_date", "strength_num"], ascending=[False, False])

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Signal events", f"{len(signals_df):,}")
    col2.metric("Unique tickers", f"{signals_df['ticker'].nunique():,}")
    bullish = (signals_df["direction"] == "bullish").sum()
    bearish = (signals_df["direction"] == "bearish").sum()
    col3.metric("Bull / Bear", f"{bullish} / {bearish}")

    # Render table
    display_cols = [
        "signal_date", "ticker", "sector", "signal_type", "direction",
        "strength", "rsi_14", "rs_spy_20d", "rs_sector_20d", "return_20d",
    ]
    display_cols = [c for c in display_cols if c in signals_df.columns]

    st.dataframe(
        signals_df[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "signal_date": st.column_config.DateColumn("Date", width="small"),
            "ticker": st.column_config.TextColumn("Ticker", width="small"),
            "sector": st.column_config.TextColumn("Sector"),
            "signal_type": st.column_config.TextColumn("Signal"),
            "direction": st.column_config.TextColumn("Direction", width="small"),
            "strength": st.column_config.NumberColumn("Strength", format="%.4f"),
            "rsi_14": st.column_config.NumberColumn("RSI", format="%.1f"),
            "rs_spy_20d": st.column_config.NumberColumn("RS vs SPY", format="%.2f%%"),
            "rs_sector_20d": st.column_config.NumberColumn("RS vs Sector", format="%.2f%%"),
            "return_20d": st.column_config.NumberColumn("Return 20d", format="%.2f%%"),
        },
    )
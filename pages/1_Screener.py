"""
Screener — filter the universe by signals or current indicator state,
plus technical and fundamental criteria.
"""

from datetime import date, timedelta
import pandas as pd
import streamlit as st
from lib.supabase_client import get_client

st.set_page_config(page_title="Screener", page_icon="🔍", layout="wide")
st.title("🔍 Screener")
st.caption("Filter S&P 500 stocks by signal events, current state, or fundamentals")

# ============================================================
# HELPERS
# ============================================================
def render_selectable_table(df, column_config, table_key, ticker_col="ticker"):
    """Render dataframe with single-row selection that jumps to Ticker Detail."""
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        on_select="rerun",
        selection_mode="single-row",
        key=table_key,
    )
    if event.selection.rows:
        row_idx = event.selection.rows[0]
        ticker = df.iloc[row_idx][ticker_col]
        st.session_state.selected_ticker = ticker
        st.switch_page("pages/2_Ticker_Detail.py")


# ============================================================
# DATA LOADERS
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

@st.cache_data(ttl=300)
def load_fundamentals() -> pd.DataFrame:
    """Load the latest fundamentals snapshot for all tickers."""
    s = get_client()
    data = s.table("fundamentals_snapshot").select("*").execute().data
    df = pd.DataFrame(data)
    if df.empty:
        return df
    # Coerce numeric columns
    numeric_cols = [c for c in df.columns
                    if c not in ("ticker", "snapshot_date")]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ============================================================
# MODE TOGGLE
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
fundamentals = load_fundamentals()

if latest_date is None:
    st.error("No indicator data available. Check the data push job.")
    st.stop()

# ============================================================
# DEEP-LINK FROM MARKET OVERVIEW
# ============================================================
sectors_all = sorted(universe["sector"].dropna().unique())
preset = st.session_state.pop("preset_sectors", None)
if preset:
    default_sectors = [s for s in preset if s in sectors_all]
    if not default_sectors:
        default_sectors = sectors_all
else:
    default_sectors = sectors_all

# Market cap buckets — used for filter dropdown and post-filter labeling
def market_cap_bucket(mc):
    if mc is None or pd.isna(mc):
        return "Unknown"
    if mc >= 2e11:
        return "Mega ($200B+)"
    if mc >= 1e10:
        return "Large ($10B-$200B)"
    if mc >= 2e9:
        return "Mid ($2B-$10B)"
    return "Small (<$2B)"


# ============================================================
# SIDEBAR FILTERS
# ============================================================
with st.sidebar:
    st.header("Filters")

    # ---- Sector ----
    selected_sectors = st.multiselect(
        "Sectors",
        options=sectors_all,
        default=default_sectors,
        help="Leave all selected for entire universe",
    )

    # ---- Technical ----
    st.subheader("Technical")
    rs_spy_min, rs_spy_max = st.slider(
        "RS vs SPY (20d)",
        min_value=-1.0, max_value=1.0,
        value=(-1.0, 1.0), step=0.05, format="%.2f",
        help="Stock return minus SPY return over 20 days. +0.1 = outperforming by 10%",
    )
    rs_sector_min, rs_sector_max = st.slider(
        "RS vs Sector (20d)",
        min_value=-1.0, max_value=1.0,
        value=(-1.0, 1.0), step=0.05, format="%.2f",
    )
    rsi_min, rsi_max = st.slider(
        "RSI (14)",
        min_value=0, max_value=100,
        value=(0, 100), step=1,
    )
    sma200_options = st.radio(
        "Position vs SMA 200",
        options=["Any", "Above SMA200", "Below SMA200"],
        index=0,
    )

    # ---- Fundamental ----
    with st.expander("💰 Fundamental filters", expanded=False):

        # Market cap bucket
        mc_buckets = ["Mega ($200B+)", "Large ($10B-$200B)",
                       "Mid ($2B-$10B)", "Small (<$2B)", "Unknown"]
        selected_mc_buckets = st.multiselect(
            "Market cap",
            options=mc_buckets,
            default=mc_buckets,
            help='"Unknown" = ETFs and stocks with missing market cap data',
        )

    # ----- Valuation -----
        st.markdown("**Valuation**")
        pe_outliers = st.checkbox("Tighten P/E to <50 (exclude high)", value=False,
                                   help="When unchecked, slider goes 0-1500 and includes all valuations")
        pe_max_slider_max = 50.0 if pe_outliers else 1500.0
        pe_range = st.slider(
            "P/E (TTM)",
            min_value=0.0, max_value=pe_max_slider_max,
            value=(0.0, pe_max_slider_max), step=5.0, format="%.0f",
        )
        pe_include_negative = st.checkbox("Include negative / no earnings", value=True)

        pb_range = st.slider(
            "P/B",
            min_value=0.0, max_value=500.0,
            value=(0.0, 500.0), step=1.0, format="%.1f",
            help="Tech names can have P/B 20+. Distressed financials can spike to 100+",
        )
        pb_include_negative = st.checkbox("Include negative / null P/B", value=True,
                                           key="pb_neg")

        # ----- Dividends -----
        st.markdown("**Dividends**")
        div_payers_only = st.checkbox("Dividend payers only", value=False)
        if div_payers_only:
            div_yield_min = st.slider(
                "Min dividend yield",
                min_value=0.0, max_value=10.0,
                value=0.0, step=0.1, format="%.1f%%",
            ) / 100.0
        else:
            div_yield_min = None

        # ----- Profitability -----
        st.markdown("**Profitability**")
        roe_min = st.slider(
            "Min ROE",
            min_value=-50, max_value=50,
            value=-50, step=5, format="%d%%",
        ) / 100.0
        net_margin_min = st.slider(
            "Min net margin",
            min_value=-50, max_value=50,
            value=-50, step=5, format="%d%%",
        ) / 100.0

        # ----- Growth -----
        st.markdown("**Growth**")
        rev_growth_min = st.slider(
            "Min revenue growth (YoY)",
            min_value=-50, max_value=100,
            value=-50, step=5, format="%d%%",
        ) / 100.0

        # ----- Leverage -----
        st.markdown("**Leverage**")
        de_tighten = st.checkbox("Tighten D/E to <200% (exclude high leverage)", value=False)
        de_max_slider = 200.0 if de_tighten else 5000.0
        de_max = st.slider(
            "Max debt/equity",
            min_value=0.0, max_value=de_max_slider,
            value=de_max_slider, step=50.0, format="%.0f%%",
            help="yfinance returns as percentage (50 = 50%). REITs and some financials can exceed 1000%",
        )
        de_include_null = st.checkbox("Include null debt/equity", value=True)


# ============================================================
# FUNDAMENTAL FILTER FUNCTION (shared across modes)
# ============================================================
def apply_fundamental_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply sidebar fundamental filters to a dataframe containing fundamental columns.

    Expects df to have already been merged with fundamentals — if not, returns df unchanged.
    """
    if "market_cap" not in df.columns:
        return df  # No fundamentals merged in

    # Market cap bucket
    df = df.copy()
    df["_mc_bucket"] = df["market_cap"].apply(market_cap_bucket)
    df = df[df["_mc_bucket"].isin(selected_mc_buckets)]
    df = df.drop(columns=["_mc_bucket"])

    # P/E
    pe_min, pe_max = pe_range
    if pe_include_negative:
        pe_filter = (df["pe_trailing"].isna()) | (
            (df["pe_trailing"] >= pe_min) & (df["pe_trailing"] <= pe_max))
    else:
        pe_filter = (df["pe_trailing"] >= pe_min) & (df["pe_trailing"] <= pe_max)
    df = df[pe_filter]

    # P/B
    pb_min, pb_max = pb_range
    if pb_include_negative:
        pb_filter = (df["pb"].isna()) | (
            (df["pb"] >= pb_min) & (df["pb"] <= pb_max))
    else:
        pb_filter = (df["pb"] >= pb_min) & (df["pb"] <= pb_max)
    df = df[pb_filter]

    # Dividend
    if div_payers_only:
        if div_yield_min is not None:
            df = df[df["dividend_yield"].fillna(0) >= div_yield_min]
        else:
            df = df[df["dividend_yield"].fillna(0) > 0]

    # ROE — only apply if user moved the slider off the floor
    if roe_min > -0.5:
        df = df[df["roe"].fillna(-99) >= roe_min]

    # Net margin
    if net_margin_min > -0.5:
        df = df[df["net_margin"].fillna(-99) >= net_margin_min]

    # Revenue growth
    if rev_growth_min > -0.5:
        df = df[df["revenue_growth_yoy"].fillna(-99) >= rev_growth_min]

    # Debt/equity
    if de_include_null:
        de_filter = (df["debt_to_equity"].isna()) | (df["debt_to_equity"] <= de_max)
    else:
        de_filter = df["debt_to_equity"] <= de_max
    df = df[de_filter]

    return df


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

    # Join sector + company info
    df = df.merge(universe[["ticker", "sector", "company_name"]],
                  on="ticker", how="left")

    # Merge in fundamentals
    if not fundamentals.empty:
        fund_cols = ["ticker", "pe_trailing", "pe_forward", "pb", "bvps",
                     "dividend_yield", "roe", "net_margin", "gross_margin",
                     "revenue_growth_yoy", "earnings_growth_yoy",
                     "debt_to_equity", "market_cap", "beta",
                     "free_cashflow_yield"]
        fund_cols = [c for c in fund_cols if c in fundamentals.columns]
        df = df.merge(fundamentals[fund_cols], on="ticker", how="left")

    # Apply technical filters
    df = df[df["sector"].isin(selected_sectors)]
    df = df[(df["rs_spy_20d"].fillna(0).astype(float) >= rs_spy_min) &
            (df["rs_spy_20d"].fillna(0).astype(float) <= rs_spy_max)]
    df = df[(df["rs_sector_20d"].fillna(0).astype(float) >= rs_sector_min) &
            (df["rs_sector_20d"].fillna(0).astype(float) <= rs_sector_max)]
    df = df[(df["rsi_14"].fillna(50).astype(float) >= rsi_min) &
            (df["rsi_14"].fillna(50).astype(float) <= rsi_max)]

    if sma200_options == "Above SMA200":
        st.info("Note: 'Above SMA200' filter uses RS as proxy in v1. Refined in v2.")
        df = df[df["rs_spy_20d"].astype(float) > 0]
    elif sma200_options == "Below SMA200":
        df = df[df["rs_spy_20d"].astype(float) < 0]

    # Apply fundamental filters
    pre_fund_count = len(df)
    df = apply_fundamental_filters(df)
    post_fund_count = len(df)
    if post_fund_count < pre_fund_count:
        st.caption(f"Fundamental filters: narrowed from {pre_fund_count} to "
                   f"{post_fund_count} tickers")

    # Display columns
    display_cols = [
        "ticker", "sector", "company_name",
        "rsi_14", "rs_spy_20d", "rs_sector_20d",
        "return_5d", "return_20d", "return_60d",
        "pct_from_high",
        "pe_trailing", "pb", "dividend_yield", "roe",
        "revenue_growth_yoy", "market_cap",
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    df_display = df[display_cols].copy()

    # Convert numeric
# Convert numeric and multiply percent columns by 100 for display
    pct_cols = ["rs_spy_20d", "rs_sector_20d", "return_5d", "return_20d",
                "return_60d", "pct_from_high",
                "dividend_yield", "roe", "revenue_growth_yoy"]
    for c in pct_cols:
        if c in df_display.columns:
            df_display[c] = pd.to_numeric(df_display[c], errors="coerce") * 100

    # Sort
    if "rs_spy_20d" in df_display.columns:
        df_display = df_display.sort_values(
            "rs_spy_20d", ascending=False, na_position="last")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Matches", f"{len(df_display):,}")
    if "rs_spy_20d" in df_display.columns:
        avg_rs = df_display["rs_spy_20d"].mean()
        col2.metric("Avg RS vs SPY",
                    f"{avg_rs*100:+.2f}%" if pd.notna(avg_rs) else "—")
    if "pe_trailing" in df_display.columns:
        med_pe = df_display["pe_trailing"].median()
        col3.metric("Median P/E",
                    f"{med_pe:.1f}" if pd.notna(med_pe) else "—")
    if "roe" in df_display.columns:
        med_roe = df_display["roe"].median()
        col4.metric("Median ROE",
                    f"{med_roe*100:.1f}%" if pd.notna(med_roe) else "—")

    # Render
    st.caption("👆 Click any row to jump to Ticker Detail")
    render_selectable_table(
        df_display,
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", width="small"),
            "sector": st.column_config.TextColumn("Sector", width="medium"),
            "company_name": st.column_config.TextColumn("Company", width="medium"),
            "rsi_14": st.column_config.NumberColumn("RSI", format="%.1f"),
            "rs_spy_20d": st.column_config.NumberColumn("RS vs SPY", format="%.2f%%"),
            "rs_sector_20d": st.column_config.NumberColumn("RS vs Sector", format="%.2f%%"),
            "return_5d": st.column_config.NumberColumn("Ret 5d", format="%.2f%%"),
            "return_20d": st.column_config.NumberColumn("Ret 20d", format="%.2f%%"),
            "return_60d": st.column_config.NumberColumn("Ret 60d", format="%.2f%%"),
            "pct_from_high": st.column_config.NumberColumn("From 52w High", format="%.2f%%"),
            "pe_trailing": st.column_config.NumberColumn("P/E", format="%.1f"),
            "pb": st.column_config.NumberColumn("P/B", format="%.2f"),
            "dividend_yield": st.column_config.NumberColumn("Div Yield", format="%.2f%%"),
            "roe": st.column_config.NumberColumn("ROE", format="%.2f%%"),
            "revenue_growth_yoy": st.column_config.NumberColumn("Rev Growth", format="%.2f%%"),
            "market_cap": st.column_config.NumberColumn("Market Cap", format="$%d"),
        },
        table_key="screener_state_table",
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
        trend_signals = [s for s in all_signal_types
                         if any(s.startswith(p) for p in
                                ["golden_cross", "death_cross", "cross_above_sma200",
                                 "cross_below_sma200", "rs_breakout", "rs_breakdown",
                                 "sector_leader", "breakout_52w", "breakdown_52w"])]
        selected_signals = st.multiselect(
            "Signal types",
            options=all_signal_types,
            default=trend_signals,
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

    # Merge with universe
    signals_df = signals_df.merge(
        universe[["ticker", "sector", "company_name"]],
        on="ticker", how="left",
    )
    signals_df = signals_df[signals_df["sector"].isin(selected_sectors)]

    # Merge with indicators for technical enrichment
    if not indicators_df.empty:
        enrich_cols = ["ticker", "rsi_14", "rs_spy_20d", "rs_sector_20d",
                       "return_20d", "pct_from_high"]
        enrich_cols = [c for c in enrich_cols if c in indicators_df.columns]
        signals_df = signals_df.merge(
            indicators_df[enrich_cols], on="ticker", how="left"
        )

        # Technical filters
        for col, lo, hi in [("rs_spy_20d", rs_spy_min, rs_spy_max),
                             ("rs_sector_20d", rs_sector_min, rs_sector_max),
                             ("rsi_14", rsi_min, rsi_max)]:
            if col in signals_df.columns:
                vals = pd.to_numeric(signals_df[col], errors="coerce").fillna(
                    50 if col == "rsi_14" else 0)
                signals_df = signals_df[(vals >= lo) & (vals <= hi)]

    # Merge with fundamentals
    if not fundamentals.empty:
        fund_cols = ["ticker", "pe_trailing", "pb", "bvps", "dividend_yield",
                     "roe", "net_margin", "gross_margin",
                     "revenue_growth_yoy", "earnings_growth_yoy",
                     "debt_to_equity", "market_cap", "beta",
                     "free_cashflow_yield"]
        fund_cols = [c for c in fund_cols if c in fundamentals.columns]
        signals_df = signals_df.merge(fundamentals[fund_cols],
                                       on="ticker", how="left")

    # Apply fundamental filters
    pre_fund_count = len(signals_df)
    signals_df = apply_fundamental_filters(signals_df)
    post_fund_count = len(signals_df)
    if post_fund_count < pre_fund_count:
        st.caption(f"Fundamental filters: narrowed from {pre_fund_count} to "
                   f"{post_fund_count} signal events")

    # Order
    signals_df["strength_num"] = pd.to_numeric(signals_df["strength"], errors="coerce")
    signals_df = signals_df.sort_values(
        ["signal_date", "strength_num"], ascending=[False, False])

    # Summary
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Signal events", f"{len(signals_df):,}")
    col2.metric("Unique tickers", f"{signals_df['ticker'].nunique():,}")
    bullish = (signals_df["direction"] == "bullish").sum()
    bearish = (signals_df["direction"] == "bearish").sum()
    col3.metric("Bull / Bear", f"{bullish} / {bearish}")
    if "pe_trailing" in signals_df.columns:
        med_pe = signals_df["pe_trailing"].median()
        col4.metric("Median P/E",
                    f"{med_pe:.1f}" if pd.notna(med_pe) else "—")

    # Display — multiply percent columns by 100 for display
    display_cols = [
        "signal_date", "ticker", "sector", "signal_type", "direction",
        "strength", "rsi_14", "rs_spy_20d", "return_20d",
        "pe_trailing", "roe", "revenue_growth_yoy", "market_cap",
    ]
    display_cols = [c for c in display_cols if c in signals_df.columns]
    signals_display = signals_df[display_cols].reset_index(drop=True)
    pct_cols_signal = ["rs_spy_20d", "return_20d", "roe", "revenue_growth_yoy"]
    for c in pct_cols_signal:
        if c in signals_display.columns:
            signals_display[c] = pd.to_numeric(signals_display[c], errors="coerce") * 100

    st.caption("👆 Click any row to jump to Ticker Detail")
    render_selectable_table(
        signals_display,
        column_config={
            "signal_date": st.column_config.DateColumn("Date", width="small"),
            "ticker": st.column_config.TextColumn("Ticker", width="small"),
            "sector": st.column_config.TextColumn("Sector"),
            "signal_type": st.column_config.TextColumn("Signal"),
            "direction": st.column_config.TextColumn("Direction", width="small"),
            "strength": st.column_config.NumberColumn("Strength", format="%.4f"),
            "rsi_14": st.column_config.NumberColumn("RSI", format="%.1f"),
            "rs_spy_20d": st.column_config.NumberColumn("RS vs SPY", format="%.2f%%"),
            "return_20d": st.column_config.NumberColumn("Ret 20d", format="%.2f%%"),
            "pe_trailing": st.column_config.NumberColumn("P/E", format="%.1f"),
            "roe": st.column_config.NumberColumn("ROE", format="%.2f%%"),
            "revenue_growth_yoy": st.column_config.NumberColumn("Rev Growth", format="%.2f%%"),
            "market_cap": st.column_config.NumberColumn("Market Cap", format="$%d"),
        },
        table_key="screener_signal_table",
    )
    
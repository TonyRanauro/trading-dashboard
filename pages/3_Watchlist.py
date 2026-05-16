"""
Watchlist — saved tickers with current state and recent signals.
"""

from datetime import date, timedelta
import pandas as pd
import streamlit as st
from lib.supabase_client import get_client

st.set_page_config(page_title="Watchlist", page_icon="⭐", layout="wide")
st.title("⭐ Watchlist")
st.caption("Saved tickers with current state and recent signal events")

LIST_NAME = "default"  # Single watchlist for v1; multi-list support is a future enhancement

# ============================================================
# DATA LOADERS
# ============================================================
@st.cache_data(ttl=60)  # Shorter cache than other pages since user edits it
def load_watchlist() -> pd.DataFrame:
    s = get_client()
    data = (s.table("watchlist")
              .select("*")
              .eq("list_name", LIST_NAME)
              .order("ticker")
              .execute().data)
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def load_universe() -> pd.DataFrame:
    s = get_client()
    data = s.table("universe").select("ticker, company_name, sector").execute().data
    return pd.DataFrame(data).sort_values("ticker")

@st.cache_data(ttl=300)
def get_latest_indicator_date() -> str | None:
    s = get_client()
    result = (s.table("latest_indicators")
                .select("indicator_date")
                .order("indicator_date", desc=True)
                .limit(1).execute().data)
    return result[0]["indicator_date"] if result else None

@st.cache_data(ttl=300)
def load_indicators_for_tickers(tickers: list, target_date: str) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()
    s = get_client()
    data = (s.table("latest_indicators")
              .select("*")
              .in_("ticker", tickers)
              .eq("indicator_date", target_date)
              .execute().data)
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def load_recent_signals_for_tickers(tickers: list, days: int = 5) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    s = get_client()
    data = (s.table("latest_signals")
              .select("*")
              .in_("ticker", tickers)
              .gte("signal_date", cutoff)
              .order("signal_date", desc=True)
              .execute().data)
    return pd.DataFrame(data)

# ============================================================
# WATCHLIST MANAGEMENT
# ============================================================
def add_to_watchlist(ticker: str, notes: str = ""):
    s = get_client()
    try:
        s.table("watchlist").insert({
            "ticker": ticker,
            "list_name": LIST_NAME,
            "notes": notes or None,
        }).execute()
        st.cache_data.clear()  # Invalidate caches so the new ticker shows
        return True
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            st.warning(f"{ticker} is already on the watchlist.")
        else:
            st.error(f"Failed to add {ticker}: {e}")
        return False

def remove_from_watchlist(ticker: str):
    s = get_client()
    try:
        (s.table("watchlist")
           .delete()
           .eq("ticker", ticker)
           .eq("list_name", LIST_NAME)
           .execute())
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Failed to remove {ticker}: {e}")
        return False

# ============================================================
# UI: ADD TICKER
# ============================================================
universe = load_universe()
watchlist = load_watchlist()
existing_tickers = set(watchlist["ticker"].tolist()) if not watchlist.empty else set()
available = [t for t in universe["ticker"].tolist() if t not in existing_tickers]

with st.expander("➕ Add ticker to watchlist"):
    col1, col2, col3 = st.columns([2, 3, 1])
    with col1:
        new_ticker = st.selectbox(
            "Ticker",
            options=available,
            format_func=lambda t: f"{t} — {universe.loc[universe['ticker']==t, 'company_name'].iloc[0]}"
                                  if t in universe['ticker'].values else t,
            key="add_ticker_select",
        )
    with col2:
        new_notes = st.text_input("Notes (optional)", key="add_ticker_notes")
    with col3:
        st.write("")  # Spacer
        st.write("")
        if st.button("Add", type="primary", use_container_width=True):
            if new_ticker and add_to_watchlist(new_ticker, new_notes):
                st.success(f"Added {new_ticker}")
                st.rerun()

# ============================================================
# DISPLAY WATCHLIST
# ============================================================
st.divider()

if watchlist.empty:
    st.info("Your watchlist is empty. Add tickers above to get started.")
    st.stop()

tickers = watchlist["ticker"].tolist()
latest_date = get_latest_indicator_date()

if latest_date is None:
    st.error("No indicator data available.")
    st.stop()

with st.spinner("Loading current state..."):
    indicators = load_indicators_for_tickers(tickers, latest_date)
    recent_signals = load_recent_signals_for_tickers(tickers, days=7)

# Merge with universe for sector + company name
display = watchlist.merge(
    universe[["ticker", "company_name", "sector"]],
    on="ticker",
    how="left",
)

# Merge with current indicators
if not indicators.empty:
    enrich_cols = ["ticker", "rsi_14", "rs_spy_20d", "rs_sector_20d",
                   "return_1d", "return_5d", "return_20d",
                   "pct_from_high", "pct_from_low", "macd_hist"]
    enrich_cols = [c for c in enrich_cols if c in indicators.columns]
    display = display.merge(indicators[enrich_cols], on="ticker", how="left")

# Add recent signal count and "hot" flag
if not recent_signals.empty:
    signal_counts = recent_signals.groupby("ticker").size().reset_index(name="signals_7d")
    display = display.merge(signal_counts, on="ticker", how="left")
    display["signals_7d"] = display["signals_7d"].fillna(0).astype(int)
else:
    display["signals_7d"] = 0

# Convert numeric cols
for col in ["rsi_14", "rs_spy_20d", "rs_sector_20d", "return_1d",
            "return_5d", "return_20d", "pct_from_high", "pct_from_low", "macd_hist"]:
    if col in display.columns:
        display[col] = pd.to_numeric(display[col], errors="coerce")

# Summary metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Tickers", len(display))
col2.metric("With recent signals", int((display["signals_7d"] > 0).sum()))
if "rs_spy_20d" in display.columns:
    avg_rs = display["rs_spy_20d"].mean()
    col3.metric("Avg RS vs SPY", f"{avg_rs*100:+.2f}%" if pd.notna(avg_rs) else "—")
if "rsi_14" in display.columns:
    avg_rsi = display["rsi_14"].mean()
    col4.metric("Avg RSI", f"{avg_rsi:.1f}" if pd.notna(avg_rsi) else "—")

# Table columns
display_cols = [
    "ticker", "sector", "company_name", "signals_7d",
    "rsi_14", "rs_spy_20d", "rs_sector_20d",
    "return_1d", "return_5d", "return_20d",
    "pct_from_high", "notes",
]
display_cols = [c for c in display_cols if c in display.columns]
display_view = display[display_cols].sort_values(
    "rs_spy_20d", ascending=False, na_position="last")

st.caption("👆 Click any row to jump to Ticker Detail")

event = st.dataframe(
    display_view,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    key="watchlist_table",
    column_config={
        "ticker": st.column_config.TextColumn("Ticker", width="small"),
        "sector": st.column_config.TextColumn("Sector"),
        "company_name": st.column_config.TextColumn("Company"),
        "signals_7d": st.column_config.NumberColumn("Signals (7d)", format="%d"),
        "rsi_14": st.column_config.NumberColumn("RSI", format="%.1f"),
        "rs_spy_20d": st.column_config.NumberColumn("RS vs SPY", format="%.2f%%"),
        "rs_sector_20d": st.column_config.NumberColumn("RS vs Sector", format="%.2f%%"),
        "return_1d": st.column_config.NumberColumn("Return 1d", format="%.2f%%"),
        "return_5d": st.column_config.NumberColumn("Return 5d", format="%.2f%%"),
        "return_20d": st.column_config.NumberColumn("Return 20d", format="%.2f%%"),
        "pct_from_high": st.column_config.NumberColumn("From 52w High", format="%.2f%%"),
        "notes": st.column_config.TextColumn("Notes"),
    },
)

if event.selection.rows:
    row_idx = event.selection.rows[0]
    ticker = display_view.iloc[row_idx]["ticker"]
    st.session_state.selected_ticker = ticker
    st.switch_page("pages/2_Ticker_Detail.py")

# ============================================================
# REMOVE A TICKER
# ============================================================
st.divider()
with st.expander("➖ Remove ticker from watchlist"):
    remove_ticker = st.selectbox(
        "Ticker to remove",
        options=tickers,
        key="remove_ticker_select",
    )
    if st.button("Remove", type="secondary"):
        if remove_from_watchlist(remove_ticker):
            st.success(f"Removed {remove_ticker}")
            st.rerun()

# ============================================================
# RECENT SIGNALS DETAIL
# ============================================================
if not recent_signals.empty:
    st.divider()
    st.subheader("Recent signals on watchlist (last 7 days)")
    sigs_display = recent_signals.merge(
        universe[["ticker", "sector"]], on="ticker", how="left")
    sigs_display = sigs_display[["signal_date", "ticker", "sector",
                                  "signal_type", "direction", "strength"]]
    sigs_display = sigs_display.sort_values("signal_date", ascending=False)
    st.dataframe(
        sigs_display,
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
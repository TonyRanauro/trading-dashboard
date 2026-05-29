"""
S&P 500 Trading Platform Dashboard — Home page
"""

import streamlit as st
import pandas as pd
from lib.supabase_client import get_client

st.set_page_config(
    page_title="Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("S&P 500 Trading Platform")
st.caption("Educational/research use only · Not investment advice")

# --- Quick health check ---
with st.spinner("Loading pipeline status..."):
    supa = get_client()
    status_data = supa.table("pipeline_status").select("*").execute()
    df_status = pd.DataFrame(status_data.data)

if df_status.empty:
    st.error("No pipeline status data found. Has the push job run?")
else:
    st.subheader("Latest Pipeline Run")
    df_status = df_status[[
        "run_type", "status", "started_at", "duration_sec",
        "rows_out", "tickers_done", "tickers_failed"
    ]].sort_values("started_at", ascending=False)
    st.dataframe(df_status, use_container_width=True, hide_index=True)

# --- Latest data freshness ---
st.subheader("Data Freshness")

@st.cache_data(ttl=300)
def get_latest_dates():
    s = get_client()
    return {
        "prices":      s.table("current_prices").select("price_date").order(
                          "price_date", desc=True).limit(1).execute().data,
        "indicators":  s.table("latest_indicators").select("indicator_date").order(
                          "indicator_date", desc=True).limit(1).execute().data,
        "signals":     s.table("latest_signals").select("signal_date").order(
                          "signal_date", desc=True).limit(1).execute().data,
        "sector":      s.table("sector_summary").select("sector_date").order(
                          "sector_date", desc=True).limit(1).execute().data,
    }

latest = get_latest_dates()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Latest Prices",
            latest["prices"][0]["price_date"] if latest["prices"] else "—")
col2.metric("Latest Indicators",
            latest["indicators"][0]["indicator_date"] if latest["indicators"] else "—")
col3.metric("Latest Signals",
            latest["signals"][0]["signal_date"] if latest["signals"] else "—")
col4.metric("Latest Sector Data",
            latest["sector"][0]["sector_date"] if latest["sector"] else "—")

# --- Navigation hint ---
st.divider()
st.markdown("""
### Navigation
Use the sidebar to browse:
- **Screener** — Filter stocks by signal type, sector, RS, and indicators
- **Ticker Detail** — Deep dive on a single ticker
- **Watchlist** — Personal watchlist with current signals
- **Market Overview** — Sector heatmap and breadth
- **AI-ML Performance** — Detailed analysis and performance tracking of AI/ML models' predictions
- **Sentiment** — Daily extremes via FinBERT net score with click to ticker detail
- **About and Glossary** — Metric Glossary and Architecture (with roadmap and vision)

ALR 2026
""")
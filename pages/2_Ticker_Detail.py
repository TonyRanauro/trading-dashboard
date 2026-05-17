"""
Ticker Detail — price chart with indicator overlays + signal timeline + fundamentals.
"""

from datetime import date, timedelta
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from lib.supabase_client import get_client

st.set_page_config(page_title="Ticker Detail", page_icon="📊", layout="wide")
st.title("📊 Ticker Detail")

# ============================================================
# DATA LOADERS (cached for 5 min)
# ============================================================
@st.cache_data(ttl=300)
def load_universe() -> pd.DataFrame:
    s = get_client()
    data = s.table("universe").select("ticker, company_name, sector").execute().data
    df = pd.DataFrame(data)
    return df.sort_values("ticker")

@st.cache_data(ttl=300)
def load_prices(ticker: str) -> pd.DataFrame:
    s = get_client()
    data = (s.table("current_prices")
              .select("*")
              .eq("ticker", ticker)
              .order("price_date")
              .execute().data)
    df = pd.DataFrame(data)
    if not df.empty:
        df["price_date"] = pd.to_datetime(df["price_date"])
        for col in ["open", "high", "low", "close", "adj_close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

@st.cache_data(ttl=300)
def load_indicators(ticker: str) -> pd.DataFrame:
    s = get_client()
    data = (s.table("latest_indicators")
              .select("*")
              .eq("ticker", ticker)
              .order("indicator_date")
              .execute().data)
    df = pd.DataFrame(data)
    if not df.empty:
        df["indicator_date"] = pd.to_datetime(df["indicator_date"])
        for col in df.columns:
            if col not in ("ticker", "indicator_date"):
                df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

@st.cache_data(ttl=300)
def load_signals(ticker: str) -> pd.DataFrame:
    s = get_client()
    data = (s.table("latest_signals")
              .select("*")
              .eq("ticker", ticker)
              .order("signal_date", desc=True)
              .execute().data)
    df = pd.DataFrame(data)
    if not df.empty:
        df["signal_date"] = pd.to_datetime(df["signal_date"])
        df["strength"] = pd.to_numeric(df["strength"], errors="coerce")
    return df

@st.cache_data(ttl=300)
def load_fundamentals(ticker: str) -> dict | None:
    s = get_client()
    data = (s.table("fundamentals_snapshot")
              .select("*")
              .eq("ticker", ticker)
              .order("snapshot_date", desc=True)
              .limit(1)
              .execute().data)
    if not data:
        return None
    return data[0]

@st.cache_data(ttl=300)
def load_earnings(ticker: str) -> pd.DataFrame:
    s = get_client()
    data = (s.table("earnings_calendar")
              .select("*")
              .eq("ticker", ticker)
              .order("earnings_date", desc=False)
              .execute().data)
    df = pd.DataFrame(data)
    if not df.empty:
        df["earnings_date"] = pd.to_datetime(df["earnings_date"])
    return df

# ============================================================
# FORMATTING HELPERS
# ============================================================
def fmt_pct(v, decimals=2):
    """Format a decimal value as percentage. 0.123 -> '+12.30%'"""
    if v is None or pd.isna(v):
        return "—"
    try:
        return f"{float(v) * 100:+.{decimals}f}%"
    except (ValueError, TypeError):
        return "—"

def fmt_num(v, decimals=2):
    """Format a number with thousands separator."""
    if v is None or pd.isna(v):
        return "—"
    try:
        return f"{float(v):,.{decimals}f}"
    except (ValueError, TypeError):
        return "—"

def fmt_money(v):
    """Format a large number as $X.XB / $X.XM / $X,XXX."""
    if v is None or pd.isna(v):
        return "—"
    try:
        v = float(v)
        if abs(v) >= 1e12:
            return f"${v/1e12:.2f}T"
        if abs(v) >= 1e9:
            return f"${v/1e9:.2f}B"
        if abs(v) >= 1e6:
            return f"${v/1e6:.2f}M"
        return f"${v:,.0f}"
    except (ValueError, TypeError):
        return "—"

def fmt_ratio(v, decimals=2):
    """Format a ratio. None -> '—'. Avoids '0.00' for None."""
    if v is None or pd.isna(v):
        return "—"
    try:
        return f"{float(v):.{decimals}f}"
    except (ValueError, TypeError):
        return "—"

# ============================================================
# TICKER SELECTION
# ============================================================
universe = load_universe()
ticker_options = universe["ticker"].tolist()

if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = "AAPL"

col_sel, col_date = st.columns([2, 1])

with col_sel:
    selected_ticker = st.selectbox(
        "Ticker",
        options=ticker_options,
        index=ticker_options.index(st.session_state.selected_ticker)
              if st.session_state.selected_ticker in ticker_options else 0,
        format_func=lambda t: f"{t} — {universe.loc[universe['ticker']==t, 'company_name'].iloc[0]}"
                              if t in universe['ticker'].values else t,
    )
    st.session_state.selected_ticker = selected_ticker

with col_date:
    date_range = st.selectbox(
        "Date range",
        options=["1M", "3M", "6M", "1Y"],
        index=2,
    )

date_range_days = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365}[date_range]

# ============================================================
# LOAD DATA
# ============================================================
with st.spinner(f"Loading {selected_ticker}..."):
    prices = load_prices(selected_ticker)
    indicators = load_indicators(selected_ticker)
    signals = load_signals(selected_ticker)
    fundamentals = load_fundamentals(selected_ticker)
    earnings = load_earnings(selected_ticker)

if prices.empty:
    st.error(f"No price data for {selected_ticker}")
    st.stop()

cutoff = prices["price_date"].max() - pd.Timedelta(days=date_range_days)
prices_view = prices[prices["price_date"] >= cutoff].copy()

if not indicators.empty:
    indicators_view = indicators[indicators["indicator_date"] >= cutoff].copy()
else:
    indicators_view = pd.DataFrame()

if not signals.empty:
    signals_view = signals[signals["signal_date"] >= cutoff].copy()
else:
    signals_view = pd.DataFrame()

# ============================================================
# HEADER METRICS
# ============================================================
sector = universe.loc[universe["ticker"] == selected_ticker, "sector"].iloc[0]
company = universe.loc[universe["ticker"] == selected_ticker, "company_name"].iloc[0]
st.caption(f"**{company}** · {sector}")

latest = prices.iloc[-1]
prev = prices.iloc[-2] if len(prices) > 1 else latest
day_change = latest["close"] - prev["close"]
day_pct = (day_change / prev["close"]) * 100 if prev["close"] else 0

latest_ind = indicators.iloc[-1] if not indicators.empty else None

# Next earnings (if any upcoming)
next_earnings_row = None
if not earnings.empty:
    upcoming = earnings[earnings["status"] == "upcoming"]
    if not upcoming.empty:
        next_earnings_row = upcoming.iloc[0]

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric(
    "Close",
    f"${latest['close']:,.2f}",
    f"{day_change:+.2f} ({day_pct:+.2f}%)",
)
if latest_ind is not None:
    m2.metric(
        "RSI (14)",
        f"{latest_ind['rsi_14']:.1f}" if pd.notna(latest_ind['rsi_14']) else "—",
    )
    rs_spy = latest_ind.get("rs_spy_20d")
    m3.metric(
        "RS vs SPY (20d)",
        f"{rs_spy*100:+.2f}%" if pd.notna(rs_spy) else "—",
    )
    pct_high = latest_ind.get("pct_from_high")
    m4.metric(
        "From 52w High",
        f"{pct_high*100:+.2f}%" if pd.notna(pct_high) else "—",
    )

# Fundamentals quick-look in header
if fundamentals is not None:
    m5.metric(
        "P/E (TTM)",
        fmt_ratio(fundamentals.get("pe_trailing"), 1),
    )
    m6.metric(
        "Market Cap",
        fmt_money(fundamentals.get("market_cap")),
    )

if next_earnings_row is not None:
    days_to = (next_earnings_row["earnings_date"].date() - date.today()).days
    if days_to >= 0:
        st.info(
            f"📅 Next earnings: **{next_earnings_row['earnings_date'].strftime('%Y-%m-%d')}** "
            f"({days_to} days) · "
            f"EPS estimate: {fmt_ratio(next_earnings_row.get('eps_estimate'), 2)} · "
            f"Revenue estimate: {fmt_money(next_earnings_row.get('revenue_estimate'))}"
        )

# ============================================================
# INDICATOR TOGGLES
# ============================================================
st.divider()
overlay_cols = st.columns(6)
show_sma20  = overlay_cols[0].checkbox("SMA 20",  value=False)
show_sma50  = overlay_cols[1].checkbox("SMA 50",  value=True)
show_sma200 = overlay_cols[2].checkbox("SMA 200", value=True)
show_ema12  = overlay_cols[3].checkbox("EMA 12",  value=False)
show_ema26  = overlay_cols[4].checkbox("EMA 26",  value=False)
show_bbands = overlay_cols[5].checkbox("Bollinger", value=False)

show_signals = st.checkbox("Show signal markers on chart", value=True)

# ============================================================
# CHART — 4 stacked panels with shared x-axis
# ============================================================
chart_df = prices_view.merge(
    indicators_view,
    left_on="price_date",
    right_on="indicator_date",
    how="left",
)

fig = make_subplots(
    rows=4, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.55, 0.15, 0.15, 0.15],
    subplot_titles=("Price", "Volume", "RSI (14)", "MACD"),
)

# Panel 1: Candlestick + overlays
fig.add_trace(
    go.Candlestick(
        x=chart_df["price_date"],
        open=chart_df["open"],
        high=chart_df["high"],
        low=chart_df["low"],
        close=chart_df["close"],
        name="Price",
        showlegend=False,
        increasing_line_color="#10b981",
        decreasing_line_color="#ef4444",
        increasing_fillcolor="#10b981",
        decreasing_fillcolor="#ef4444",
    ),
    row=1, col=1,
)

overlays = [
    (show_sma20,  "sma_20",  "SMA 20",  "#2563eb"),
    (show_sma50,  "sma_50",  "SMA 50",  "#10b981"),
    (show_sma200, "sma_200", "SMA 200", "#ef4444"),
    (show_ema12,  "ema_12",  "EMA 12",  "#f59e0b"),
    (show_ema26,  "ema_26",  "EMA 26",  "#8b5cf6"),
]
for show, col, label, color in overlays:
    if show and col in chart_df.columns:
        fig.add_trace(
            go.Scatter(
                x=chart_df["price_date"], y=chart_df[col],
                name=label, line=dict(color=color, width=1.5), opacity=0.85,
            ),
            row=1, col=1,
        )

if show_bbands and "bb_upper_20" in chart_df.columns:
    fig.add_trace(
        go.Scatter(
            x=chart_df["price_date"], y=chart_df["bb_upper_20"],
            name="BB Upper", line=dict(color="#9ca3af", width=1, dash="dot"),
            showlegend=False,
        ), row=1, col=1)
    fig.add_trace(
        go.Scatter(
            x=chart_df["price_date"], y=chart_df["bb_lower_20"],
            name="BB Lower", line=dict(color="#9ca3af", width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(156,163,175,0.1)",
            showlegend=False,
        ), row=1, col=1)

# Signal markers on price chart
if show_signals and not signals_view.empty:
    for _, sig in signals_view.iterrows():
        price_row = chart_df[chart_df["price_date"] == sig["signal_date"]]
        if price_row.empty:
            continue
        y_pos = price_row["high"].iloc[0] * 1.01
        color = "#10b981" if sig["direction"] == "bullish" else "#ef4444"
        symbol = "triangle-up" if sig["direction"] == "bullish" else "triangle-down"
        fig.add_trace(
            go.Scatter(
                x=[sig["signal_date"]], y=[y_pos],
                mode="markers",
                marker=dict(size=10, color=color, symbol=symbol,
                            line=dict(width=1, color="white")),
                name=sig["signal_type"], showlegend=False,
                hovertext=f"{sig['signal_type']}<br>{sig['direction']}<br>strength: {sig['strength']:.4f}",
                hoverinfo="text",
            ),
            row=1, col=1,
        )

# Panel 2: Volume
volume_colors = [
    "#10b981" if c >= o else "#ef4444"
    for c, o in zip(chart_df["close"], chart_df["open"])
]
fig.add_trace(
    go.Bar(x=chart_df["price_date"], y=chart_df["volume"],
           marker_color=volume_colors, name="Volume", showlegend=False),
    row=2, col=1,
)

# Panel 3: RSI
if "rsi_14" in chart_df.columns:
    fig.add_trace(
        go.Scatter(x=chart_df["price_date"], y=chart_df["rsi_14"],
                   name="RSI", line=dict(color="#8b5cf6", width=1.5),
                   showlegend=False),
        row=3, col=1,
    )
    fig.add_hline(y=70, line_dash="dash", line_color="#ef4444",
                  line_width=1, opacity=0.5, row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#10b981",
                  line_width=1, opacity=0.5, row=3, col=1)
    fig.update_yaxes(range=[0, 100], row=3, col=1)

# Panel 4: MACD
if "macd" in chart_df.columns:
    fig.add_trace(
        go.Scatter(x=chart_df["price_date"], y=chart_df["macd"],
                   name="MACD", line=dict(color="#2563eb", width=1.5),
                   showlegend=False),
        row=4, col=1,
    )
    fig.add_trace(
        go.Scatter(x=chart_df["price_date"], y=chart_df["macd_signal"],
                   name="Signal", line=dict(color="#f59e0b", width=1.5),
                   showlegend=False),
        row=4, col=1,
    )
    if "macd_hist" in chart_df.columns:
        hist_colors = [
            "#10b981" if v >= 0 else "#ef4444"
            for v in chart_df["macd_hist"].fillna(0)
        ]
        fig.add_trace(
            go.Bar(x=chart_df["price_date"], y=chart_df["macd_hist"],
                   marker_color=hist_colors, name="Histogram",
                   showlegend=False, opacity=0.5),
            row=4, col=1,
        )

fig.update_layout(
    height=820,
    showlegend=False,
    xaxis_rangeslider_visible=False,
    margin=dict(l=40, r=40, t=40, b=40),
    template="plotly",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#9ca3af"),
)
fig.update_xaxes(
    rangebreaks=[dict(bounds=["sat", "mon"])],
    showgrid=True, gridcolor="rgba(128,128,128,0.2)",
    tickfont=dict(color="#9ca3af", size=11),
    linecolor="#6b7280",
)
fig.update_yaxes(
    showgrid=True, gridcolor="rgba(128,128,128,0.2)",
    tickfont=dict(color="#9ca3af", size=11),
    linecolor="#6b7280",
)
for annotation in fig['layout']['annotations']:
    annotation['font'] = dict(color="#9ca3af", size=13)

st.plotly_chart(fig, use_container_width=True)

# ============================================================
# RECENT SIGNALS TABLE
# ============================================================
st.divider()
st.subheader("Recent signals")

if signals_view.empty:
    st.info("No signals in this date range.")
else:
    display = signals_view[["signal_date", "signal_type", "direction", "strength"]].copy()
    display = display.sort_values("signal_date", ascending=False)
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "signal_date": st.column_config.DateColumn("Date", width="small"),
            "signal_type": st.column_config.TextColumn("Signal", width="medium"),
            "direction": st.column_config.TextColumn("Direction", width="small"),
            "strength": st.column_config.NumberColumn("Strength", format="%.4f"),
        },
    )

# ============================================================
# FUNDAMENTALS PANEL (NEW)
# ============================================================
st.divider()
st.subheader("Fundamentals")

if fundamentals is None:
    st.info(f"No fundamental data available for {selected_ticker}. ETFs (SPY) "
            "and recently-added names may not have fundamentals.")
else:
    snapshot_date = fundamentals.get("snapshot_date", "—")
    st.caption(f"Snapshot date: **{snapshot_date}**")

    # ---- Valuation ----
    st.markdown("##### Valuation")
    v1, v2, v3, v4 = st.columns(4)
    v1.metric("P/E (TTM)", fmt_ratio(fundamentals.get("pe_trailing"), 1))
    v2.metric("P/E (Forward)", fmt_ratio(fundamentals.get("pe_forward"), 1))
    v3.metric("P/B", fmt_ratio(fundamentals.get("pb"), 2))
    v4.metric("BVPS", f"${fmt_ratio(fundamentals.get('bvps'), 2)}"
              if fundamentals.get("bvps") is not None else "—")

    v5, v6, v7, v8 = st.columns(4)
    v5.metric("EV/EBITDA", fmt_ratio(fundamentals.get("ev_ebitda"), 1))
    v6.metric("P/S", fmt_ratio(fundamentals.get("ps_ratio"), 2))
    v7.metric("Dividend Yield", fmt_pct(fundamentals.get("dividend_yield"), 2))
    v8.metric("Market Cap", fmt_money(fundamentals.get("market_cap")))

    # ---- Profitability & Efficiency ----
    st.markdown("##### Profitability & Efficiency")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Gross Margin", fmt_pct(fundamentals.get("gross_margin"), 2))
    p2.metric("Operating Margin", fmt_pct(fundamentals.get("operating_margin"), 2))
    p3.metric("Net Margin", fmt_pct(fundamentals.get("net_margin"), 2))
    p4.metric("EBITDA Margin", fmt_pct(fundamentals.get("ebitda_margin"), 2))

    p5, p6 = st.columns(2)
    p5.metric("ROE", fmt_pct(fundamentals.get("roe"), 2))
    p6.metric("ROA", fmt_pct(fundamentals.get("roa"), 2))

    # ---- Growth & Momentum ----
    st.markdown("##### Growth & Momentum")
    g1, g2, g3 = st.columns(3)
    g1.metric("Revenue Growth (YoY)", fmt_pct(fundamentals.get("revenue_growth_yoy"), 2))
    g2.metric("Earnings Growth (YoY)", fmt_pct(fundamentals.get("earnings_growth_yoy"), 2))
    g3.metric("Earnings Growth (Q)", fmt_pct(fundamentals.get("earnings_quarterly_growth"), 2))

    g4, g5 = st.columns(2)
    g4.metric("EPS (TTM)", fmt_ratio(fundamentals.get("eps_trailing"), 2))
    g5.metric("EPS (Forward)", fmt_ratio(fundamentals.get("eps_forward"), 2))

    # ---- Liquidity & Solvency ----
    st.markdown("##### Liquidity & Solvency")
    l1, l2, l3, l4 = st.columns(4)
    l1.metric("Current Ratio", fmt_ratio(fundamentals.get("current_ratio"), 2))
    l2.metric("Quick Ratio", fmt_ratio(fundamentals.get("quick_ratio"), 2))
    l3.metric("Debt / Equity", fmt_ratio(fundamentals.get("debt_to_equity"), 2))
    l4.metric("FCF Yield", fmt_pct(fundamentals.get("free_cashflow_yield"), 2))

    # ---- Cash & Balance Sheet ----
    st.markdown("##### Cash & Balance Sheet")
    c1, c2 = st.columns(2)
    c1.metric("Total Cash", fmt_money(fundamentals.get("total_cash")))
    c2.metric("Cash per Share",
              f"${fmt_ratio(fundamentals.get('cash_per_share'), 2)}"
              if fundamentals.get("cash_per_share") is not None else "—")

    # ---- Size & Identity ----
    st.markdown("##### Size & Identity")
    s1, s2, s3 = st.columns(3)
    s1.metric("Shares Outstanding", fmt_money(fundamentals.get("shares_outstanding")))
    s2.metric("Beta", fmt_ratio(fundamentals.get("beta"), 2))
    s3.metric("Sector", sector)

# ============================================================
# EARNINGS HISTORY
# ============================================================
if not earnings.empty:
    st.divider()
    st.subheader("Earnings calendar")

    earn_display = earnings[["earnings_date", "status", "eps_estimate",
                              "eps_actual", "eps_surprise_pct",
                              "revenue_estimate", "revenue_actual"]].copy()
    earn_display = earn_display.sort_values("earnings_date", ascending=False)

    st.dataframe(
        earn_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "earnings_date": st.column_config.DateColumn("Date"),
            "status": st.column_config.TextColumn("Status", width="small"),
            "eps_estimate": st.column_config.NumberColumn("EPS Est", format="%.2f"),
            "eps_actual": st.column_config.NumberColumn("EPS Act", format="%.2f"),
            "eps_surprise_pct": st.column_config.NumberColumn("Surprise", format="%.2f%%"),
            "revenue_estimate": st.column_config.NumberColumn("Rev Est", format="$%d"),
            "revenue_actual": st.column_config.NumberColumn("Rev Act", format="$%d"),
        },
    )

# ============================================================
# CURRENT INDICATOR VALUES (collapsible)
# ============================================================
with st.expander("Current indicator values (technical)"):
    if latest_ind is None:
        st.info("No indicator data available.")
    else:
        groups = {
            "SMAs": ["sma_5", "sma_10", "sma_20", "sma_50", "sma_100", "sma_200"],
            "EMAs": ["ema_12", "ema_26", "ema_50", "ema_200"],
            "Momentum": ["rsi_14", "macd", "macd_signal", "macd_hist"],
            "Volatility": ["atr_14", "vol_20", "vol_60"],
            "Returns": ["return_1d", "return_5d", "return_20d", "return_60d", "return_252d"],
            "RS vs SPY": ["rs_spy_5d", "rs_spy_20d", "rs_spy_60d", "rs_spy_252d"],
            "RS vs Sector": ["rs_sector_5d", "rs_sector_20d", "rs_sector_60d", "rs_sector_252d"],
            "52w range": ["high_252", "low_252", "pct_from_high", "pct_from_low"],
        }
        for group, cols in groups.items():
            st.markdown(f"**{group}**")
            vals = {c: latest_ind.get(c) for c in cols if c in latest_ind.index}
            row = pd.DataFrame([vals])
            st.dataframe(row, hide_index=True, use_container_width=True)
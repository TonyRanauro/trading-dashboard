"""
About & Glossary — page explanations, metric definitions, and architecture reference.

Designed to grow as more domains (fundamentals, sentiment, macro) come online.
"""

from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="About & Glossary", page_icon="📖", layout="wide")
st.title("📖 About & Glossary")
st.caption("Page descriptions, metric definitions, and platform architecture")

# ============================================================
# TABS
# ============================================================
tab_pages, tab_glossary, tab_arch = st.tabs([
    "Pages", "Metric Glossary", "Architecture"
])

# ============================================================
# TAB 1: PAGES OVERVIEW
# ============================================================
with tab_pages:
    st.subheader("What each page does")

    pages_info = [
        {
            "page": "🏠 Home",
            "summary": "Platform health and freshness check",
            "details": (
                "Shows the latest pipeline run status across all six daily steps "
                "(prices, indicators, sector RS, signals, email, Supabase push). "
                "Quick way to confirm overnight data has refreshed before using the rest of the app."
            ),
            "best_for": "Morning sanity check; verifying the pipeline ran cleanly.",
        },
        {
            "page": "🔍 Screener",
            "summary": "Filter the universe by signals or current state",
            "details": (
                "Two modes:\n\n"
                "**State-driven**: filter all 504 tickers by their current indicator state — "
                "RS thresholds, RSI bands, sector, trend position. Ranks results by RS vs SPY by default.\n\n"
                "**Signal-driven**: show recent signal events (last 1-60 days) filtered by signal type, "
                "enriched with current indicator values. Useful for asking 'what fired recently that I should investigate?'\n\n"
                "Click any row to jump to Ticker Detail."
            ),
            "best_for": "Generating ideas; narrowing a 500-ticker universe to a handful worth looking at.",
        },
        {
            "page": "📊 Ticker Detail",
            "summary": "Deep dive on a single ticker",
            "details": (
                "Candlestick chart with toggleable indicator overlays (SMAs, EMAs, Bollinger Bands). "
                "Volume, RSI, and MACD panels share the same time axis. Signal events appear as colored "
                "triangles on the price chart. Adjustable lookback (1M to 1Y). Recent signal history table "
                "and full current indicator values in an expandable section."
            ),
            "best_for": "Investigating a specific name; understanding why it's showing up in screens.",
        },
        {
            "page": "⭐ Watchlist",
            "summary": "Your saved tickers, with current state",
            "details": (
                "Manage a personal list of names you're tracking. Add/remove via the dropdowns. "
                "Shows current indicator state for each ticker, count of recent signals (last 7 days), "
                "and highlights names with recent activity. Click any row to drill into Ticker Detail."
            ),
            "best_for": "Daily check on positions or candidates you're monitoring.",
        },
        {
            "page": "🌐 Market Overview",
            "summary": "Sector heatmap and breadth dashboard",
            "details": (
                "Top-level view of the market: % of stocks above SMA 50/200, recent bullish/bearish signal "
                "balance, and a sector treemap colored by return (toggleable timeframe: 1D/5D/20D/60D). "
                "Includes sector ranking table, signal balance per sector, most-active tickers, and "
                "trend-change events. Drill into any sector via the dropdown to filter the Screener."
            ),
            "best_for": "Once-a-day market snapshot; understanding where leadership and risk are concentrated.",
        },
        {
            "page": "📖 About & Glossary",
            "summary": "This page",
            "details": "Documentation for pages, every metric, and the platform architecture.",
            "best_for": "Reference whenever you forget what 'RS vs Sector 60d' precisely measures.",
        },
    ]

    for p in pages_info:
        with st.expander(f"**{p['page']}** — {p['summary']}", expanded=False):
            st.markdown(p["details"])
            st.caption(f"**Best for:** {p['best_for']}")

# ============================================================
# TAB 2: METRIC GLOSSARY
# ============================================================
with tab_glossary:
    st.subheader("Metric definitions")
    st.caption("Definitions for every metric used in screening, signals, and analysis")

    # Domain filter — useful as more domains come online
    domain_filter = st.radio(
        "Domain",
        options=["Technical (current)", "Fundamental (coming soon)",
                 "Sentiment (planned)", "Macro (planned)"],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.divider()

    if domain_filter.startswith("Technical"):
        st.markdown("### Technical metrics")
        st.caption("Derived from price and volume data. All currently computed daily.")

        # Group by category
        st.markdown("#### Trend & Moving Averages")

        with st.expander("**SMA (Simple Moving Average) — 5, 10, 20, 50, 100, 200 day**"):
            st.markdown("""
            **Definition**: The unweighted average closing price over the lookback period.

            **Formula**: `SMA(n) = sum(close, n) / n`

            **Range**: Same units as price; always positive for stocks.

            **Interpretation**:
            - Price above SMA50 → short-to-medium-term uptrend
            - Price above SMA200 → long-term uptrend (often called the "bull market" line)
            - SMA50 > SMA200 → golden cross territory (bullish regime)
            - SMA50 < SMA200 → death cross territory (bearish regime)

            **Related**: EMA (weights recent prices more heavily), Bollinger Bands (built around SMA20).
            """)

        with st.expander("**EMA (Exponential Moving Average) — 12, 26, 50, 200 day**"):
            st.markdown("""
            **Definition**: Weighted moving average where recent prices count more.

            **Formula**: `EMA_today = (close_today × α) + (EMA_yesterday × (1-α))` where `α = 2 / (n+1)`

            **Range**: Same units as price.

            **Interpretation**: Reacts faster than SMA to recent price changes. EMA12 and EMA26 are the
            inputs to MACD. EMA50 and EMA200 are used by some traders instead of SMA50/SMA200 for
            more responsive trend signals.

            **Related**: MACD (built from EMA12 and EMA26), SMA (less responsive equivalent).
            """)

        st.markdown("#### Momentum")

        with st.expander("**RSI (Relative Strength Index, 14-day)**"):
            st.markdown("""
            **Definition**: Momentum oscillator measuring the speed and magnitude of recent price changes.

            **Formula**: `RSI = 100 - (100 / (1 + RS))` where `RS = avg_gain / avg_loss` over 14 days.

            **Range**: 0 to 100 (theoretical), typically 20-80 in practice.

            **Interpretation**:
            - **RSI > 70** → traditionally "overbought" (may be due for a pullback)
            - **RSI < 30** → traditionally "oversold" (may be due for a bounce)
            - **RSI 30-70** → neutral / trending zone
            - In strong trends RSI can stay overbought/oversold for extended periods — don't fade trends blindly

            **Example**: AAPL at RSI 75 after a 20% run is normal; RSI 75 with sideways action suggests exhaustion.

            **Related**: MACD (also momentum-based but different math), pct_from_high (different angle on overextension).
            """)

        with st.expander("**MACD (Moving Average Convergence Divergence)**"):
            st.markdown("""
            **Definition**: A momentum + trend indicator built from two EMAs.

            **Components**:
            - `macd = EMA12 - EMA26`
            - `macd_signal = EMA9 of macd`
            - `macd_hist = macd - macd_signal`

            **Range**: Unbounded; centered on zero. Magnitudes scale with price.

            **Interpretation**:
            - `macd > 0` → short-term momentum above long-term (bullish)
            - `macd < 0` → momentum below trend (bearish)
            - `macd_hist > 0 and rising` → accelerating bullish momentum
            - `macd crossing above signal` → bullish trigger
            - `macd crossing below signal` → bearish trigger

            **Related**: EMA12, EMA26 (the inputs); RSI (different momentum measure).
            """)

        st.markdown("#### Volatility")

        with st.expander("**ATR (Average True Range, 14-day)**"):
            st.markdown("""
            **Definition**: Average daily price range over 14 days, accounting for gaps.

            **Formula**: True range = max(high-low, |high-prev_close|, |low-prev_close|); ATR = 14-day SMA of TR.

            **Range**: Same units as price; always positive.

            **Interpretation**: Measure of volatility. Useful for position sizing — a stock with $5 ATR
            moves much more than one with $0.50 ATR. Stop-loss distances often expressed as multiples of ATR.

            **Example**: NVDA might have ATR of $20, KO might have ATR of $0.50.

            **Related**: vol_20, vol_60 (annualized volatility); Bollinger Band width.
            """)

        with st.expander("**Bollinger Bands (20-day, 2 standard deviations)**"):
            st.markdown("""
            **Definition**: A volatility envelope around SMA20.

            **Formula**:
            - `bb_middle_20 = SMA20`
            - `bb_upper_20 = SMA20 + 2 × std_dev(close, 20)`
            - `bb_lower_20 = SMA20 - 2 × std_dev(close, 20)`

            **Interpretation**:
            - Price near upper band → high-end of typical range (may be overextended)
            - Price near lower band → low-end of typical range (may be oversold)
            - Bands narrowing ("squeeze") → low volatility, often precedes large moves
            - Bands widening → expanding volatility

            **Related**: ATR (related volatility measure), Keltner Channels (similar concept, ATR-based).
            """)

        with st.expander("**Realized Volatility (vol_20, vol_60)**"):
            st.markdown("""
            **Definition**: Annualized standard deviation of daily log returns.

            **Formula**: `vol_N = std(log_returns over N days) × sqrt(252)`

            **Range**: 0 to ~2 (200%) in extreme cases; typical equity vol is 0.15-0.45.

            **Interpretation**:
            - `vol_20 ≈ 0.20` → about 20% annualized vol, typical large-cap stock
            - `vol_20 > 0.50` → very volatile (small cap, recent crisis, or speculation)
            - Rising vol often precedes regime changes

            **Related**: ATR (similar concept, different math), beta (relative to market).
            """)

        st.markdown("#### Returns")

        with st.expander("**Return periods (1d, 5d, 20d, 60d, 252d)**"):
            st.markdown("""
            **Definition**: Percentage change in adjusted close over the lookback period.

            **Formula**: `return_Nd = (close_today / close_N_days_ago) - 1`

            **Range**: Usually -0.5 to +2.0 in practice; can exceed for individual stocks in extreme cases.

            **Interpretation**:
            - `return_1d` → today's change
            - `return_5d` → about one week
            - `return_20d` → about one month
            - `return_60d` → about three months / one quarter
            - `return_252d` → one year (252 trading days)

            **Related**: All RS metrics are derived from these by subtracting SPY or sector returns.
            """)

        st.markdown("#### Relative Strength")

        with st.expander("**RS vs SPY (5d, 20d, 60d, 252d)**"):
            st.markdown("""
            **Definition**: How much a stock outperformed or underperformed SPY (S&P 500 ETF) over the lookback.

            **Formula**: `rs_spy_Nd = stock_return_Nd - spy_return_Nd`

            **Range**: Typically -0.5 to +0.5; extremes can be ±1.0 or more for momentum names.

            **Interpretation**:
            - **Positive RS** → outperforming the market
            - **Negative RS** → underperforming the market
            - **RS > 0.2 over 20 days** → very strong outperformance, often a momentum leader
            - **RS < -0.2 over 20 days** → meaningful underperformance, often a sector laggard

            **Why it matters**: Removes market direction from the equation. A stock can be down 5% but still
            be RS positive if SPY was down 10%. Helps identify true leaders/laggards.

            **Example**: MU recently showed RS vs SPY 20d of +63%, meaning it outperformed SPY by 63
            percentage points over a month.

            **Related**: RS vs Sector (similar concept, sector-relative); raw return.
            """)

        with st.expander("**RS vs Sector (5d, 20d, 60d, 252d)**"):
            st.markdown("""
            **Definition**: How much a stock outperformed or underperformed its own sector over the lookback.

            **Formula**: `rs_sector_Nd = stock_return_Nd - avg_sector_return_Nd`

            **Range**: Typically -0.5 to +0.5.

            **Interpretation**:
            - **Positive** → leading its sector
            - **Negative** → lagging its sector
            - **High RS vs SPY AND high RS vs Sector** → emerging leader (both market and peer outperformance)
            - **High RS vs SPY but low RS vs Sector** → riding sector tailwind, not a standout name

            **Why it matters**: Helps separate "good stock" from "good sector." A semiconductor stock with
            high RS vs SPY might just be benefiting from sector rotation; high RS vs Sector means it's
            outperforming peers too.

            **Related**: RS vs SPY, sector_leader_emerging signal.
            """)

        st.markdown("#### 52-Week Range")

        with st.expander("**high_252, low_252, pct_from_high, pct_from_low**"):
            st.markdown("""
            **Definition**: The 252-day (approximate one-year) trading range and the stock's position within it.

            **Formula**:
            - `high_252 = max(adj_close over last 252 days)`
            - `low_252 = min(adj_close over last 252 days)`
            - `pct_from_high = (current - high_252) / high_252`   (always ≤ 0)
            - `pct_from_low = (current - low_252) / low_252`      (always ≥ 0)

            **Interpretation**:
            - `pct_from_high ≈ 0` → at or near 52w high (breakout territory)
            - `pct_from_high < -0.2` → 20%+ below high (consolidation or downtrend)
            - `pct_from_low ≈ 0` → at 52w low (capitulation or value)
            - High of both metrics simultaneously is impossible (mathematically)

            **Related**: breakout_52w_high signal, breakdown_52w_low signal.
            """)

        st.divider()

        st.markdown("### Signal types (13 currently)")

        st.markdown("#### Trend signals (regime changes)")

        with st.expander("**golden_cross_50_200 / death_cross_50_200**"):
            st.markdown("""
            **Trigger**: When SMA50 crosses above (golden) or below (death) SMA200.

            **Direction**: Bullish (golden) / Bearish (death).

            **Strength**: Magnitude of the gap between SMA50 and SMA200 at the crossover.

            **Interpretation**: Major regime-change indicator. Slow to trigger (often weeks after the move
            has begun), but historically reliable for separating long-term bull from bear regimes.

            **Frequency**: Rare — about 5-15 occurrences per stock over 20 years. ~6,800 total across all
            S&P 500 names in your history.

            **Related**: cross_above_sma200, cross_below_sma200 (faster, more frequent signals).
            """)

        with st.expander("**cross_above_sma200 / cross_below_sma200**"):
            st.markdown("""
            **Trigger**: When the daily close crosses above (or below) SMA200.

            **Direction**: Bullish (above) / Bearish (below).

            **Strength**: Distance between price and SMA200 at the cross.

            **Interpretation**: Faster regime signal than the golden/death cross. Many traders use SMA200
            as the "are we in a bull market for this stock?" line.

            **Frequency**: ~37k occurrences in the historical record.

            **Related**: Golden/death cross (slower version).
            """)

        st.markdown("#### Momentum signals")

        with st.expander("**macd_cross_up / macd_cross_down**"):
            st.markdown("""
            **Trigger**: When the MACD line crosses above (or below) its signal line.

            **Direction**: Bullish (up) / Bearish (down).

            **Strength**: Absolute value of MACD at the cross.

            **Interpretation**: Short-term momentum shifts. Frequent and noisy on their own, but useful
            when filtered (e.g., MACD cross up + RSI > 50 + price above SMA50).

            **Frequency**: ~93k each direction in your history.
            """)

        with st.expander("**rsi_oversold / rsi_overbought**"):
            st.markdown("""
            **Trigger**:
            - rsi_oversold: RSI crosses below 30
            - rsi_overbought: RSI crosses above 70

            **Direction**: Bullish (oversold) / Bearish (overbought).

            **Strength**: Distance from the threshold (e.g., RSI of 25 = strength 0.05 below 30).

            **Interpretation**: Classic mean-reversion signal. Reliable in range-bound markets, often
            wrong in strong trends. Combine with sector RS or trend direction for better results.

            **Frequency**: ~24k oversold, ~46k overbought — overbought happens more (market generally rises).
            """)

        st.markdown("#### Breakouts")

        with st.expander("**breakout_52w_high / breakdown_52w_low**"):
            st.markdown("""
            **Trigger**: When today's close exceeds the prior 252-day high (or falls below the prior 252-day low).

            **Direction**: Bullish (breakout) / Bearish (breakdown).

            **Strength**: Magnitude of the breakout (e.g., +2% above prior high).

            **Interpretation**: Strong momentum/regime signals. Breakouts especially valuable in stocks
            that have consolidated for weeks/months. New 52w lows often precede further declines.

            **Frequency**: ~147k breakouts, ~32k breakdowns — asymmetry reflects the market's long-run upward bias.
            """)

        st.markdown("#### Relative Strength signals")

        with st.expander("**rs_breakout_20d / rs_breakdown_20d**"):
            st.markdown("""
            **Trigger**: When `rs_spy_20d` makes a new 20-day high (or low).

            **Direction**: Bullish (breakout) / Bearish (breakdown).

            **Strength**: Value of `rs_spy_20d` at the breakout.

            **Interpretation**: Identifies stocks where the *relative* performance trajectory is shifting.
            A stock making a new RS high while its price might still be flat means it's holding up better
            than the market — early signal of relative strength emerging.

            **Frequency**: ~145k breakouts, ~148k breakdowns (symmetric — reassuring data quality check).
            """)

        with st.expander("**sector_leader_emerging**"):
            st.markdown("""
            **Trigger**: When a stock transitions to having both `rs_spy_20d > 0` AND `rs_sector_20d > 0`
            after previously not meeting both conditions.

            **Direction**: Bullish.

            **Strength**: Sum of `rs_spy_20d` and `rs_sector_20d` at the transition.

            **Interpretation**: A "double outperformer" — beating both the market and its sector peers.
            Often signals the start of a sustained leadership run.

            **Frequency**: ~115k occurrences in the historical record.
            """)

    elif domain_filter.startswith("Fundamental"):
        st.info("**Coming in Phase F1.** Fundamental metrics will be added in this section as the "
                "ingestion pipeline is built. Expected variables across four categories:")
        st.markdown("""
        - **Valuation**: P/E (trailing, forward), P/B, P/S, EV/EBITDA, dividend yield, PEG
        - **Profitability & Efficiency**: ROE, ROA, ROIC, gross/operating/net margins
        - **Growth & Momentum**: revenue growth, earnings growth, EPS surprises, estimate revisions
        - **Liquidity & Solvency**: current ratio, debt/equity, interest coverage, free cash flow
        """)

    elif domain_filter.startswith("Sentiment"):
        st.info("**Planned future component.** Metrics will include FinBERT-derived sentiment scores "
                "on news headlines and earnings call transcripts, ticker-level sentiment aggregates, "
                "news velocity, and event flags (M&A, downgrades/upgrades, guidance changes, 8-K events).")

    elif domain_filter.startswith("Macro"):
        st.info("**Planned future component.** Macroeconomic context features for the ensemble meta-learner:")
        st.markdown("""
        - **Rates & Curve**: 2y/10y Treasury yields, 2s10s spread, real rates
        - **Risk & Volatility**: VIX, VVIX, high-yield spreads, MOVE index
        - **Currency & Commodities**: DXY (dollar index), gold, crude oil, copper
        - **Economic Indicators**: ISM PMI, unemployment claims, inflation expectations
        - **Regime Classification**: Risk-on vs risk-off, growth vs value rotation
        """)

# ============================================================
# TAB 3: ARCHITECTURE
# ============================================================
with tab_arch:
    st.subheader("Platform architecture")
    st.caption("Current state of the platform with built vs. planned components")

    # Locate the embedded HTML file
    here = Path(__file__).parent.parent  # parent of pages/ → root of dashboard
    arch_html_path = here / "assets" / "architecture.html"

    if not arch_html_path.exists():
        st.warning(
            f"Architecture HTML not found at `{arch_html_path}`. "
            "Save the architecture document to `assets/architecture.html` to embed it here."
        )
    else:
        # Read and embed
        html_content = arch_html_path.read_text(encoding="utf-8")
        components.html(html_content, height=2400, scrolling=True)

    st.divider()
    st.caption(
        "Download options: right-click the architecture above → 'Save as' to save the HTML. "
        "Or view directly: `assets/architecture.html` in the repo."
    )
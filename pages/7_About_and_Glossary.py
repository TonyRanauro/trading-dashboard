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
                "Shows the latest pipeline run status across all daily steps "
                "(prices, indicators, sector RS, technical/fundamental ranks, signals, "
                "ML inference, Supabase push, earnings calendar, daily emails). "
                "Quick way to confirm overnight data has refreshed before using the rest of the app.\n\n"
                "Three automated emails fire daily after the pipeline completes: a Signal Analytics summary, "
                "a FinBERT Sentiment Alert (extremes by ticker, with hyperlinks to source articles), "
                "and a Daily ML Picks email (top 10 / bottom 10 by predicted probability)."
            ),
            "best_for": "Morning sanity check; verifying the pipeline ran cleanly.",
        },
        {
            "page": "🔍 Screener",
            "summary": "Filter the universe by signals or current state",
            "details": (
                "Two modes:\n\n"
                "**State-driven**: filter all 504 tickers by their current indicator state — "
                "RS thresholds, RSI bands, sector, trend position, and fundamental filters. "
                "Ranks results by RS vs SPY by default.\n\n"
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
                "triangles on the price chart. Adjustable lookback (1M to 1Y).\n\n"
                "**Fundamentals panel** below the chart shows 27 metrics across valuation, "
                "profitability, growth, liquidity, cash position, and size. **Earnings calendar** "
                "shows upcoming and reported earnings dates with EPS estimates and actuals.\n\n"
                "Recent signal history table and full current indicator values in an expandable section."
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
            "page": "🤖 ML Performance",
            "summary": "Meta-learner predictions, accuracy tracking, and diagnostics",
            "details": (
                "Tracks the daily output of the production meta-learner: a 4-domain stack "
                "(technical, fundamental, sentiment, macro) of XGBoost/LightGBM/CatBoost/PyTorch sub-models "
                "predicting whether each stock will beat the S&P median over the next 10 trading days.\n\n"
                "**Headline KPIs**: resolved/pending prediction counts, accuracy, mean rank IC, top-decile "
                "mean return, decile spread.\n\n"
                "**Decile performance**: bar chart of mean realized 10-day return by predicted decile — "
                "the 'staircase' is the canonical money chart for a ranking model.\n\n"
                "**Diagnostics that work today**: probability distribution histogram, top-decile sector "
                "composition, predictions-per-day pipeline health bar.\n\n"
                "**Resolved-data charts**: rank IC over time, top-vs-bottom decile cumulative return, "
                "calibration plot, and confusion matrix. These populate automatically once predictions "
                "age past their 10-day forward window.\n\n"
                "Controls: model selector, date range picker, aggregate-vs-per-date view toggle. Defaults "
                "to the production-flagged model."
            ),
            "best_for": "Validating that the model is actually adding signal vs. noise; debugging diagnostics like calibration drift.",
        },
        {
            "page": "📰 Sentiment",
            "summary": "FinBERT-derived news sentiment, by ticker and sector",
            "details": (
                "Daily aggregates from FinBERT scoring of news articles and earnings transcripts.\n\n"
                "**Today's extremes**: top 10 most-positive and most-negative tickers on the snapshot date, "
                "with sector and article counts. Click to drill into Ticker Detail.\n\n"
                "**Sentiment by sector**: article-weighted average sentiment per sector — heavily-covered "
                "tickers move their sector's number more than lightly-covered ones.\n\n"
                "**Sustained sentiment leaders & laggards**: multi-day weighted averages, with consistency "
                "metrics (% days positive / negative) to filter out one-day blips.\n\n"
                "**Per-ticker time series**: daily score + 5-day rolling average + extreme-day markers, "
                "with article-count bars underneath. Same thresholds as the daily FinBERT email "
                "(≥ +0.40 for extreme positive, ≤ -0.25 for extreme negative).\n\n"
                "**Sentiment vs ML predictions**: scatter showing where the model agrees with the news "
                "vs where it disagrees. Companion tables flag 'contrarian bulls' (negative sentiment, model "
                "still bullish) and 'contrarian bears' (positive sentiment, model still bearish)."
            ),
            "best_for": "Spotting narrative shifts; cross-checking ML picks against news tone; finding contrarian setups.",
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

    domain_filter = st.radio(
        "Domain",
        options=["Technical", "Fundamental", "AI-ML Performance",
                 "Sentiment", "Macro"],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.divider()

    if domain_filter.startswith("Technical"):
        st.markdown("### Technical metrics")
        st.caption("Derived from price and volume data. All currently computed daily.")

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
        st.markdown("### Fundamental metrics")
        st.caption("Pulled from yfinance weekly. Earnings calendar refreshed daily.")

        st.markdown("#### Valuation")

        with st.expander("**P/E Trailing (pe_trailing)**"):
            st.markdown("""
            **Definition**: Price-to-earnings ratio using trailing 12-month EPS.

            **Formula**: `pe_trailing = current_price / trailing_12m_EPS`

            **Range**: Typically 5 to 50; high-growth names can exceed 100. Negative means losing money.

            **Interpretation**:
            - **< 10** → cheap by historical standards (often value or distressed)
            - **10-20** → typical for mature, stable companies
            - **20-30** → growth-priced or premium quality
            - **> 30** → high growth expectations baked in
            - Negative → company is unprofitable; metric is meaningless

            **Limitations**: Backward-looking. Doesn't capture growth, doesn't work for unprofitable companies,
            distorted by one-time items. Always compare to sector peers, not absolutes.

            **Example**: AAPL ~30, KO ~22, NVDA ~50, JPM ~12.

            **Related**: P/E Forward (uses estimates), PEG (P/E adjusted for growth), EV/EBITDA.
            """)

        with st.expander("**P/E Forward (pe_forward)**"):
            st.markdown("""
            **Definition**: Price-to-earnings using analyst estimates for next year's EPS.

            **Formula**: `pe_forward = current_price / forward_12m_EPS_estimate`

            **Range**: Same as trailing P/E, but usually lower since EPS is expected to grow.

            **Interpretation**: More forward-looking than trailing P/E. Useful for growing companies
            where past earnings understate future earning power. Comparing P/E forward vs trailing
            tells you the implied EPS growth (`(trailing/forward - 1) × 100`).

            **Limitations**: Depends on analyst estimates, which can be biased or wrong. Less reliable
            for less-followed companies.

            **Related**: P/E Trailing, earnings_growth_yoy.
            """)

        with st.expander("**P/B (pb) — Price to Book**"):
            st.markdown("""
            **Definition**: Stock price divided by book value per share.

            **Formula**: `pb = current_price / bvps`

            **Range**: 0.5 (deep value) to 20+ (premium). Most stocks 1.0 to 5.0.

            **Interpretation**:
            - **< 1.0** → trading below book value (potential value, or impaired assets)
            - **1.0-3.0** → typical range for industrials, financials, value
            - **> 5.0** → growth, intangible-heavy, or asset-light businesses
            - Less meaningful for tech/services (most value is intangible)

            **When useful**: Especially for banks, insurers, industrials, REITs — businesses where
            tangible book value is meaningful.

            **Related**: BVPS (the denominator), P/E.
            """)

        with st.expander("**BVPS (bvps) — Book Value Per Share**"):
            st.markdown("""
            **Definition**: Shareholder equity divided by shares outstanding.

            **Formula**: `bvps = total_shareholder_equity / shares_outstanding`

            **Range**: Same units as price; usually a small fraction of current price for non-financial stocks.

            **Interpretation**: Accounting estimate of per-share net worth. Most useful when tracked over time
            — growing BVPS indicates the company is compounding shareholder equity. Buffett's preferred
            quality metric.

            **Limitations**: Doesn't capture intangibles (brand, IP, network effects). MSFT BVPS of ~$30
            while trading at $400 means the value is almost entirely in intangibles.

            **Example**: JPM BVPS ~$109; MSFT BVPS ~$30; AAPL BVPS ~$5.

            **Related**: P/B (price relative to BVPS), tangible book value (BVPS minus goodwill).
            """)

        with st.expander("**EV/EBITDA (ev_ebitda)**"):
            st.markdown("""
            **Definition**: Enterprise value divided by earnings before interest, taxes, depreciation, amortization.

            **Formula**: `ev_ebitda = (market_cap + debt - cash) / EBITDA`

            **Range**: 5 to 25 typical; 30+ is rich.

            **Interpretation**: Cleaner than P/E for cross-company comparisons because it strips out
            capital structure (debt vs equity) and accounting differences. Especially useful for
            cyclicals (industrials, energy) and acquisition analysis.

            **Why use over P/E**: Two companies with identical operations but different debt loads have
            different P/Es but similar EV/EBITDA.

            **Related**: EBITDA Margin, debt_to_equity.
            """)

        with st.expander("**P/S (ps_ratio) — Price to Sales**"):
            st.markdown("""
            **Definition**: Market cap divided by trailing 12-month revenue.

            **Formula**: `ps_ratio = market_cap / revenue_TTM`

            **Range**: 0.5 (value) to 30+ (high-growth tech). Most stocks 1.0 to 10.0.

            **Interpretation**: Useful when P/E is meaningless (unprofitable companies).
            High P/S only justified by high gross margin or high growth.

            **When most useful**: SaaS, early-stage tech, biotech, anywhere earnings are negative or volatile.

            **Related**: Revenue growth (justifies high P/S), gross margin.
            """)

        with st.expander("**Dividend Yield (dividend_yield)**"):
            st.markdown("""
            **Definition**: Annual dividend per share divided by current price.

            **Formula**: `dividend_yield = annual_dividend / current_price`

            **Range**: 0 (no dividend) to ~8% (high-yield REITs, MLPs).

            **Interpretation**:
            - **0-1%** → tech / growth (reinvesting cash)
            - **1-3%** → typical S&P 500 stock
            - **3-5%** → dividend-focused (REITs, utilities, financials)
            - **> 5%** → yield-trap risk; verify dividend is covered by earnings

            **Trap warning**: High yields sometimes indicate the market expects the dividend to be cut.
            Cross-reference with payout ratio (dividend / EPS) — should be under 80% for sustainability.

            **Related**: dividend payout ratio, free cashflow yield.
            """)

        st.markdown("#### Profitability & Efficiency")

        with st.expander("**Gross Margin (gross_margin)**"):
            st.markdown("""
            **Definition**: Gross profit as a percentage of revenue.

            **Formula**: `gross_margin = (revenue - cost_of_goods_sold) / revenue`

            **Range**: 0% to 90%+. Industry-dependent.

            **Interpretation**:
            - **< 30%** → low margin (retailers, distributors, commodities)
            - **30-50%** → typical industrial / consumer products
            - **50-80%** → software, services, branded consumer
            - **> 80%** → very strong pricing power (luxury, top-tier software)

            **Why it matters**: Indicates pricing power. Companies with rising gross margins are
            either gaining pricing power or scaling efficiently.

            **Example**: KO ~60%, COST ~12%, MSFT ~70%, NVDA ~75%.

            **Related**: Operating margin (after operating costs), net margin (after everything).
            """)

        with st.expander("**Operating Margin (operating_margin)**"):
            st.markdown("""
            **Definition**: Operating income as a percentage of revenue.

            **Formula**: `operating_margin = operating_income / revenue`

            **Range**: -20% (losses) to 50%+ (best-in-class).

            **Interpretation**: How efficient the core business is *before* taxes and interest. Better
            apples-to-apples than net margin because not distorted by capital structure or one-time items.

            **Example**: AAPL ~30%, NVDA ~55%, COST ~3%.

            **Related**: Gross margin (upstream), net margin (downstream), EBITDA margin.
            """)

        with st.expander("**Net Margin (net_margin)**"):
            st.markdown("""
            **Definition**: Net income as a percentage of revenue.

            **Formula**: `net_margin = net_income / revenue`

            **Range**: Negative to 40%+.

            **Interpretation**: Bottom-line profitability. Affected by everything — operations, interest,
            taxes, one-time items. Lower than operating margin almost always.

            **When deceiving**: One-time gains/losses, tax law changes, accounting choices can swing
            net margin without reflecting the underlying business.

            **Related**: Operating margin (less distorted), EPS, ROE.
            """)

        with st.expander("**EBITDA Margin (ebitda_margin)**"):
            st.markdown("""
            **Definition**: EBITDA (earnings before interest, taxes, depreciation, amortization) as % of revenue.

            **Formula**: `ebitda_margin = EBITDA / revenue`

            **Range**: -10% to 60%+.

            **Interpretation**: Operating cash-generation efficiency, ignoring capital structure and
            non-cash depreciation. Particularly useful for capital-intensive industries (telecom, energy)
            where depreciation distorts traditional margins.

            **Critique**: "EBITDA is not cash flow" — Warren Buffett. Doesn't account for capex which is
            often material. Use alongside FCF metrics, not as a substitute.

            **Related**: Operating margin, free cashflow yield, EV/EBITDA.
            """)

        with st.expander("**ROE (Return on Equity)**"):
            st.markdown("""
            **Definition**: Net income divided by shareholders' equity.

            **Formula**: `roe = net_income / shareholders_equity`

            **Range**: Negative to 50%+.

            **Interpretation**:
            - **< 5%** → weak; capital not earning much
            - **10-15%** → average S&P 500
            - **15-25%** → strong; quality compounder
            - **> 25%** → exceptional or driven by leverage (verify with ROIC/ROA)

            **Trap**: High ROE can be from high leverage, not high quality. Compare with ROA.

            **Example**: AAPL ~150% (huge buybacks), MSFT ~35%, JPM ~15%.

            **Related**: ROA, ROIC (cleaner), debt_to_equity.
            """)

        with st.expander("**ROA (Return on Assets)**"):
            st.markdown("""
            **Definition**: Net income divided by total assets.

            **Formula**: `roa = net_income / total_assets`

            **Range**: 0 to 25%+.

            **Interpretation**: Capital efficiency regardless of how assets are financed. Cleaner than
            ROE because not inflated by leverage.

            **Sector caveat**: Banks and financials have low ROA (1-2%) by nature (huge balance sheets).
            Tech and consumer often have high ROA (15-30%).

            **Related**: ROE (similar but leverage-distorted), ROIC.
            """)

        st.markdown("#### Growth & Momentum")

        with st.expander("**Revenue Growth YoY (revenue_growth_yoy)**"):
            st.markdown("""
            **Definition**: Year-over-year change in revenue.

            **Formula**: `revenue_growth_yoy = (revenue_TTM / revenue_previous_TTM) - 1`

            **Range**: -50% to +100%+. Most mature companies 0-15%.

            **Interpretation**:
            - **< 0%** → declining business
            - **0-5%** → mature / mostly flat
            - **5-15%** → healthy growth
            - **15-30%** → strong growth
            - **> 30%** → hypergrowth (often unsustainable long-term)

            **Most important growth signal**: Revenue is harder to fake than earnings. Companies with
            10+ years of consistent revenue growth are the rare quality compounders.

            **Related**: Earnings growth, gross profit growth.
            """)

        with st.expander("**Earnings Growth YoY (earnings_growth_yoy)**"):
            st.markdown("""
            **Definition**: Year-over-year change in net income.

            **Formula**: `earnings_growth_yoy = (earnings_TTM / earnings_previous_TTM) - 1`

            **Range**: Wider than revenue (more volatile). Can swing wildly on margin changes.

            **Interpretation**: Powerful if sustained; treacherous if one-time. Distinguish "growing
            because more revenue" from "growing because margins expanded" from "growing because
            buybacks shrank share count."

            **Trap**: A company growing earnings 30% while revenue grew 3% is doing margin expansion
            (can't continue forever) or buybacks. Verify with revenue trend.

            **Related**: Revenue growth, EPS, earnings_quarterly_growth.
            """)

        with st.expander("**Earnings Quarterly Growth (earnings_quarterly_growth)**"):
            st.markdown("""
            **Definition**: Most recent quarter's YoY earnings growth.

            **Formula**: `earnings_quarterly_growth = (this_quarter_EPS / same_quarter_last_year_EPS) - 1`

            **Range**: Most volatile of the growth metrics.

            **Interpretation**: Faster signal than annual growth. Often used by momentum-style
            investors to spot earnings acceleration. Three consecutive quarters of accelerating
            growth historically a strong signal.

            **Related**: Earnings growth YoY (smoother), EPS surprise (similar concept).
            """)

        with st.expander("**EPS Trailing / Forward (eps_trailing, eps_forward)**"):
            st.markdown("""
            **Definition**: Earnings per share, trailing 12 months or projected forward.

            **Formula**:
            - `eps_trailing = net_income_TTM / shares_outstanding`
            - `eps_forward = consensus_estimate_next_12m_EPS`

            **Range**: Negative (losses) to $50+ per share.

            **Interpretation**: Direct EPS values. Useful for computing implied growth rates
            (`(eps_forward / eps_trailing) - 1`).

            **Related**: P/E ratios use these as denominators; earnings_growth_yoy compares them.
            """)

        st.markdown("#### Liquidity & Solvency")

        with st.expander("**Current Ratio (current_ratio)**"):
            st.markdown("""
            **Definition**: Current assets divided by current liabilities.

            **Formula**: `current_ratio = current_assets / current_liabilities`

            **Range**: 0.5 to 5.0+; healthy is 1.5-3.0.

            **Interpretation**:
            - **< 1.0** → liquidity concerns (more short-term debt than short-term assets)
            - **1.0-1.5** → tight but workable
            - **1.5-3.0** → healthy
            - **> 5.0** → cash-rich, possibly under-utilizing capital

            **Sector context**: Retail (turn inventory fast) can run lower. Tech often runs much higher.

            **Related**: Quick ratio (stricter), debt_to_equity.
            """)

        with st.expander("**Quick Ratio (quick_ratio)**"):
            st.markdown("""
            **Definition**: Current ratio excluding inventory.

            **Formula**: `quick_ratio = (current_assets - inventory) / current_liabilities`

            **Range**: 0.3 to 4.0+; healthy is 1.0+.

            **Interpretation**: Stricter version of current ratio. Tests whether liabilities can be paid
            without selling inventory. Useful for retailers or manufacturers where inventory might be
            illiquid.

            **Related**: Current ratio.
            """)

        with st.expander("**Debt to Equity (debt_to_equity)**"):
            st.markdown("""
            **Definition**: Total debt divided by shareholders' equity.

            **Formula**: `debt_to_equity = total_debt / shareholders_equity`

            **Range**: 0 (no debt) to 300%+ (leveraged). yfinance returns as percentage (50 = 50%).

            **Interpretation**:
            - **< 50%** → conservative; lots of equity cushion
            - **50-100%** → moderate leverage
            - **100-200%** → meaningfully levered
            - **> 200%** → highly levered; risk of distress in downturns

            **Sector context**: Utilities and REITs naturally high (~200%+). Tech and consumer typically low.

            **Related**: Interest coverage, current ratio, ROE (inflated by leverage).
            """)

        with st.expander("**Free Cashflow Yield (free_cashflow_yield)**"):
            st.markdown("""
            **Definition**: Free cash flow divided by market cap.

            **Formula**: `fcf_yield = free_cashflow / market_cap`

            **Range**: Negative (cash-burning) to 15%+ (deep value with high cash gen).

            **Interpretation**: Like a dividend yield, but uses actual cash generated by the business
            instead of just what's paid out. Higher FCF yield = more cash returns possible (via dividends
            or buybacks) per dollar invested.

            - **< 0%** → company is burning cash
            - **0-3%** → low; either high growth (reinvesting) or weak cash gen
            - **3-7%** → typical mature business
            - **> 7%** → strong cash generator, often value territory

            **Why important**: FCF is harder to manipulate than reported earnings. Buffett-style quality check.

            **Related**: Dividend yield, EBITDA margin.
            """)

        st.markdown("#### Cash & Balance Sheet")

        with st.expander("**Total Cash (total_cash)**"):
            st.markdown("""
            **Definition**: Cash and cash equivalents on the balance sheet (most recent quarter).

            **Range**: Millions to hundreds of billions.

            **Interpretation**: Absolute cash position. Use for big-picture optionality — companies
            with huge cash piles can absorb shocks, make acquisitions, or return capital.

            **Example**: AAPL has $50-200B in cash historically. Microsoft similar. Most companies
            far less.

            **Related**: cash_per_share (normalized), net_cash (cash minus debt), enterprise value.
            """)

        with st.expander("**Cash Per Share (cash_per_share)**"):
            st.markdown("""
            **Definition**: Total cash divided by shares outstanding.

            **Formula**: `cash_per_share = total_cash / shares_outstanding`

            **Range**: Pennies to $50+.

            **Interpretation**: Cash position normalized to per-share basis. When a company's
            cash_per_share approaches its stock price, that's a strong value signal — buyers are
            paying near-zero for the operating business.

            **Example**: AAPL ~$3/share. ETFs and recently-IPO'd companies vary wildly.

            **Related**: BVPS, free_cashflow_yield.
            """)

        st.markdown("#### Size & Identity")

        with st.expander("**Market Cap (market_cap)**"):
            st.markdown("""
            **Definition**: Total dollar value of outstanding shares.

            **Formula**: `market_cap = current_price × shares_outstanding`

            **Range**: $1B (small cap) to $3T+ (mega cap).

            **Interpretation**: Standard buckets:
            - **Mega cap**: > $200B (AAPL, MSFT, NVDA, etc.)
            - **Large cap**: $10B - $200B (most S&P 500)
            - **Mid cap**: $2B - $10B
            - **Small cap**: $300M - $2B (not in S&P 500)
            - **Micro cap**: < $300M

            **Why it matters**: Size affects volatility, analyst coverage, institutional ownership,
            and statistical behavior (larger stocks have smaller average daily moves).

            **Related**: shares_outstanding, P/E, P/B.
            """)

        with st.expander("**Shares Outstanding (shares_outstanding)**"):
            st.markdown("""
            **Definition**: Total number of common shares currently issued and held by investors.

            **Range**: Millions to billions.

            **Interpretation**: Tracking dilution. A company issuing lots of new shares dilutes existing
            holders. A company buying back shares (reducing outstanding) concentrates ownership and
            boosts EPS.

            **Watch for**: Year-over-year changes. Stock-based compensation in tech can quietly dilute
            shareholders even with buybacks.

            **Related**: Market cap (uses this in calculation), buyback rate.
            """)

        with st.expander("**Beta (beta)**"):
            st.markdown("""
            **Definition**: Sensitivity of stock returns to market returns.

            **Formula**: `beta = covariance(stock_returns, market_returns) / variance(market_returns)`

            **Range**: -1 (rare, inverse) to 3+ (high-beta tech, biotech).

            **Interpretation**:
            - **β = 1** → moves with the market
            - **β > 1** → more volatile than market (cyclicals, tech, growth)
            - **β < 1** → less volatile than market (utilities, staples, healthcare)
            - **β < 0** → moves opposite to market (rare; some gold miners, inverse ETFs)

            **Use**: Portfolio construction, expected return models (CAPM), position sizing.

            **Example**: KO ~0.6, NVDA ~1.7, MSFT ~1.0.

            **Related**: Volatility (vol_20, vol_60), market correlation.
            """)

        st.divider()

        st.markdown("### Earnings Calendar")
        st.caption("Refreshed daily; tracks both upcoming and recently-reported earnings events.")

        with st.expander("**earnings_date**"):
            st.markdown("""
            **Definition**: Scheduled or actual date of earnings announcement.

            **Interpretation**: Date when the company reports quarterly results. Stocks often move
            significantly on/around earnings dates ("earnings drift" — positive surprises tend to
            be followed by continued outperformance, and vice versa).

            **Used in**: Risk management (avoid initiating positions just before earnings), signal
            filtering (technical signals often less reliable in days near earnings).
            """)

        with st.expander("**eps_estimate, eps_actual, eps_surprise, eps_surprise_pct**"):
            st.markdown("""
            **Definitions**:
            - `eps_estimate`: consensus analyst forecast (before report)
            - `eps_actual`: reported EPS (after report)
            - `eps_surprise = eps_actual - eps_estimate`
            - `eps_surprise_pct = eps_surprise / abs(eps_estimate)`

            **Interpretation**:
            - **Positive surprise** → company beat estimates; bullish
            - **Negative surprise** → missed estimates; bearish
            - **Magnitude matters**: a beat of 1% can be a yawn; a beat of 20% is a major event

            **Earnings drift research**: Stocks that beat estimates by large margins tend to continue
            outperforming for 1-3 months afterward, even at the higher post-beat price. Strategies that
            buy post-positive-surprise have historically generated alpha.

            **Related**: Earnings growth, revenue_estimate, revenue_actual.
            """)

        with st.expander("**revenue_estimate, revenue_actual**"):
            st.markdown("""
            **Definitions**: Consensus and reported quarterly revenue.

            **Range**: Millions to tens of billions per quarter.

            **Interpretation**: Top-line beats vs. misses matter even more than EPS for growth stories.
            "Beat on EPS, missed on revenue" often gets penalized harder than the opposite — markets
            interpret it as margin gains over growth, which is harder to sustain.

            **Related**: eps_surprise, revenue_growth_yoy.
            """)

    elif domain_filter.startswith("AI-ML Performance"):
        st.markdown("### AI / ML Performance metrics")
        st.caption(
            "Definitions for the ML Performance dashboard. The production model is a "
            "hierarchical meta-learner: four domain ensembles (technical, fundamental, "
            "sentiment, macro) feed a meta-ensemble that produces the final prediction."
        )

        st.markdown("#### The model")

        with st.expander("**Meta-learner — overall architecture**"):
            st.markdown("""
            **Definition**: A two-level stacked ensemble. The bottom level has four
            domain ensembles, each with multiple base learners (XGBoost, LightGBM,
            CatBoost, PyTorch MLP). The top level is a meta-ensemble that takes the
            four domain scores plus a small set of regime-context features and
            produces the final prediction.

            **Bottom level (per domain)**:
            - Each domain ensemble trains 4 sub-models on that domain's features
            - Cross-validation finds the optimal weighted combination
            - Final output: one calibrated probability per ticker per day

            **Top level (meta-ensemble)**:
            - Input: 4 domain scores + 4 regime-context features (VIX, curve, QQQ/SPY ratio, HYG/IEF ratio)
            - Models: XGBoost + PyTorch MLP, weighted by OOF rank IC
            - Output: final probability

            **Why this design**: Each domain captures different signal; the meta-learner
            adapts the mixing weights to the regime. A 'no fundamental data, high VIX'
            day will weight domains differently than a 'rich fundamental data, low VIX' day.

            **Related**: Domain ensemble, predicted_value, rank IC.
            """)

        with st.expander("**Domain ensemble — per-domain stacker**"):
            st.markdown("""
            **Definition**: For each of the 4 domains (technical, fundamental, sentiment, macro),
            an ensemble of 4 sub-models is trained on that domain's features only.
            Sub-models: XGBoost (GPU), LightGBM (CPU), CatBoost (GPU), PyTorch MLP (GPU).

            **Weight tuning**: 500-sample Dirichlet search optimizing rank IC on out-of-fold
            predictions. Best combination becomes the domain's score.

            **Auto-pruning**: Domains with >95% null features (e.g., sentiment in the first
            ~30 days of operation, before sufficient article history accumulates) are dropped
            automatically. The meta-learner fills their slot with a neutral 0.5 / 0.0.

            **Related**: Meta-learner, OOF rank IC.
            """)

        st.markdown("#### Targets — what the model is predicting")

        with st.expander("**beat_median_10d — classification target**"):
            st.markdown("""
            **Definition**: For each (ticker, date), did this stock's log return over the
            next 10 trading days beat the **median** of the S&P 500 universe's log returns
            over the same period?

            **Type**: Binary (1 = beat, 0 = didn't beat).

            **Why median, not SPY**: SPY's return is dominated by mega-caps (top 7 names
            are ~30% of SPY). The median is a fairer cross-sectional comparison. Also,
            the label is naturally balanced (~50/50 in any regime), which is good for
            classifier training. A 'beat SPY' label would be skewed in bull markets where
            mega-caps lead.

            **What the model outputs**: Probability that beat_median_10d = 1.

            **Resolution**: The target value becomes known ~10 trading days after the
            prediction was made, once forward prices are in.

            **Related**: log_ret_10d, predicted_value, prediction_correct.
            """)

        with st.expander("**log_ret_10d — regression target**"):
            st.markdown("""
            **Definition**: `log(close_at_D+10 / close_at_D)` — the 10-trading-day forward
            log return.

            **Why log return**: Symmetric (a 100% gain and a 50% loss have equal magnitude,
            since they undo each other). Additive over time. Better behaved under outliers
            than simple percent change.

            **Range**: Roughly -0.30 to +0.30 in normal markets; can be much more extreme.

            **Used for**: Regression-target models (when present) and decile-spread / decile-
            staircase calculations on the ML Performance page (we use the actual log_ret_10d
            from ml_targets, not the predicted one).

            **Related**: beat_median_10d, decile spread, top-decile mean return.
            """)

        st.markdown("#### Predictions")

        with st.expander("**predicted_value**"):
            st.markdown("""
            **Definition**: The model's output. For a classification model, this is the
            probability of beat_median_10d = 1, in [0, 1]. For a regression model, this
            is the predicted log_ret_10d.

            **Range (classification)**: ~0.20 to ~0.55 in practice — the meta-learner
            currently runs slightly bearish on absolute calibration but ranks correctly.

            **Interpretation**: For *ranking* purposes (which is what matters for the
            dashboard's decile chart), relative ordering matters, not absolute value.
            A model whose top-decile mean is 0.45 and bottom-decile mean is 0.30 still
            has rank signal even though no ticker is above 0.50.

            **Related**: predicted_class, decile, probability.
            """)

        with st.expander("**predicted_class**"):
            st.markdown("""
            **Definition**: The hard 0/1 label derived from `predicted_value`.
            Default decision threshold is 0.50 (predicted_value > 0.50 → class 1).

            **Use**: Confusion matrix, accuracy, precision, recall calculations.

            **Caution**: Because the model currently outputs probabilities skewed below
            0.50, predicted_class will often be 0 for all rows. The decile-based view
            (top decile vs bottom decile) is more informative than the 0.50 threshold.

            **Related**: predicted_value, accuracy, confusion matrix.
            """)

        with st.expander("**rank_overall**"):
            st.markdown("""
            **Definition**: Within a single (model_id, prediction_date), rank of each
            ticker by predicted_value, with 1 = highest predicted_value.

            **Range**: 1 to N (where N is the number of predictions that day, typically ~503).

            **Pre-computed**: Calculated at sync time in push_to_supabase.py and stored
            in the Supabase mirror, so the dashboard doesn't recompute on every render.

            **Related**: decile, top_decile_flag.
            """)

        with st.expander("**decile** and **top_decile_flag**"):
            st.markdown("""
            **Definition**: Within a single (model_id, prediction_date), the decile of
            each ticker by predicted_value. **1 = lowest** predicted_value (most bearish),
            **10 = highest** predicted_value (most bullish).

            **top_decile_flag**: Boolean shortcut, true iff decile = 10.

            **Why deciles matter**: With a universe of ~500 names, each decile is ~50
            tickers — large enough that the mean return of the decile is statistically
            informative. The decile staircase (mean realized return by decile) is the
            cleanest visualization of whether the model has ranking signal.

            **Related**: rank_overall, decile spread, top-decile mean return.
            """)

        st.markdown("#### Performance metrics")

        with st.expander("**Rank IC (Spearman rank correlation)**"):
            st.markdown("""
            **Definition**: Spearman rank correlation between predicted_value and actual
            10-day return, computed over resolved predictions. Equivalent to Pearson
            correlation on the ranks of the two variables.

            **Formula** (conceptually):
            `rank_IC = corr(rank(predicted_value), rank(actual_log_ret_10d))`

            **Range**: -1 to +1.
            - +1 = model ranks tickers perfectly (top predicted = highest return)
            - 0 = no relationship (noise)
            - -1 = inverted (top predicted = lowest return)

            **Industry context**: In quantitative equity, daily rank IC of +0.02 to +0.05
            is considered respectable for a single-factor signal; +0.05 to +0.10 is good;
            > +0.10 is excellent. Multi-factor ensembles can push higher. **Our model is
            in early training and will need months of out-of-sample data to evaluate properly.**

            **Why Spearman, not Pearson**: Spearman is robust to outliers in returns
            (which are heavy-tailed). The ranks compress the tails.

            **Related**: Decile spread, top-decile mean return.
            """)

        with st.expander("**Top-decile mean return / Decile spread**"):
            st.markdown("""
            **Top-decile mean return**: Mean of actual `log_ret_10d` for resolved
            predictions where `decile = 10`. Answers: "If I'd held an equal-weight
            basket of the model's top 10% picks each day, what would my average
            10-day return have been?"

            **Decile spread**: Top-decile mean return minus bottom-decile (decile = 1)
            mean return. Answers: "What's the economic value of the model's full
            ranking, top to bottom?"

            **Interpretation**: A positive top-decile mean isn't enough on its own —
            you want the spread to be positive too. A model that ranks the entire
            universe correctly will have a clearly positive spread (top decile up,
            bottom decile down).

            **Related**: Decile staircase, rank IC.
            """)

        with st.expander("**Accuracy, precision, recall, F1 (classification)**"):
            st.markdown("""
            **Accuracy**: Share of resolved predictions where predicted_class matched
            actual beat_median_10d. With a 50/50 base rate, random guessing gives 50%
            accuracy.

            **Precision (positive class)**: Of the predictions where predicted_class = 1,
            what share actually beat the median? Useful when you only act on bullish
            signals.

            **Recall (positive class)**: Of the actual beat-median outcomes, what share
            did the model predict as class 1? Useful for understanding how many winners
            the model misses.

            **F1**: Harmonic mean of precision and recall. Balances the two.

            **Caveat**: All four depend on the 0.50 decision threshold. Because the
            current model runs probabilistically bearish, the confusion matrix can look
            poor while the rank-based metrics (rank IC, decile spread) look fine.

            **Related**: Confusion matrix, calibration.
            """)

        with st.expander("**Calibration plot**"):
            st.markdown("""
            **Definition**: Bucket predictions by predicted_value (0.0-0.1, 0.1-0.2, …),
            then plot the **mean predicted_value** vs the **mean actual hit rate**
            (share of resolved predictions in that bucket that beat the median) for
            each bucket.

            **Perfect calibration**: All buckets sit on the diagonal — a 0.30 bucket
            has 30% hit rate, a 0.50 bucket has 50%, etc.

            **Above the diagonal**: Model is **under-confident** in that bucket. Buckets
            it predicts at 0.30 actually win 45% of the time. We could raise predicted
            probabilities and improve calibration without changing rank order.

            **Below the diagonal**: Model is **over-confident**. Predicted 0.70 but only
            wins 55% of the time.

            **Why it matters**: For position sizing or ensembling with other models,
            you want calibrated probabilities. For pure ranking (deciles, picks), only
            rank order matters and calibration is cosmetic.

            **Related**: Probability distribution histogram, isotonic regression (planned
            fix when calibration drift is detected).
            """)

        with st.expander("**Confusion matrix**"):
            st.markdown("""
            **Definition**: 2x2 grid of resolved predictions, organized as:

            ```
                              Actual = 0     Actual = 1
            Predicted = 0   |     TN      |      FN     |
            Predicted = 1   |     FP      |      TP     |
            ```

            - **TN** (true negative): correctly predicted below median
            - **TP** (true positive): correctly predicted above median
            - **FP** (false positive): wrongly predicted above median (model was too bullish)
            - **FN** (false negative): wrongly predicted below median (model missed a winner)

            **Use**: Visual sanity check for class imbalance and which type of error
            dominates. The companion metrics (accuracy, precision, recall, F1) summarize
            it numerically.

            **Related**: Accuracy, precision, recall, calibration.
            """)

        with st.expander("**Rank IC over time / 5-day rolling**"):
            st.markdown("""
            **Definition**: Daily rank IC plotted over prediction_date, with a 5-day
            rolling average for trend.

            **What to look for**:
            - Sustained positive level → model has steady signal
            - Rising trend → model improving (e.g., with more training data)
            - Decay over time → model is overfitting to the past, regime has shifted, or
              data quality has degraded
            - Negative spikes → bad days; not necessarily concerning if rolling avg holds

            **Caveat**: Don't read too much into the first 30 resolved days. The variance
            of daily rank IC is large; you need ~30+ days to see a stable signal.
            """)

        with st.expander("**Top vs bottom decile cumulative return**"):
            st.markdown("""
            **Definition**: Two cumulative-return lines, one for the top decile (long)
            and one for the bottom decile (short). The spread between them is the model's
            economic value over time.

            **Methodology**: Each day, take the mean realized log_ret_10d of resolved
            predictions in decile 10 (long line) and decile 1 (short line). Cumulate
            each over the date range.

            **Note on overlap**: The 10-day forward windows overlap across daily
            predictions. This isn't a tradeable backtest — it's a visualization of the
            model's signal persistence. A proper backtest would model holding periods
            explicitly.

            **Related**: Decile spread, rank IC.
            """)

        st.markdown("#### Pipeline & infrastructure")

        with st.expander("**is_production flag**"):
            st.markdown("""
            **Definition**: A boolean on ml_models indicating which model the daily
            inference job uses to write predictions, and which model the ML Picks email
            describes.

            **Convention**: At most one row per (component, target_name) is marked
            is_production = true. The register_model.py script enforces this by demoting
            existing production rows when a new one is marked production.

            **Use**: When a new model is trained and registered, it can sit in archive
            until validated. Flipping is_production = true makes it the live model
            without code changes.

            **Related**: register_model.py, run_daily_inference.py.
            """)

        with st.expander("**v_ml_prediction_outcomes / v_ml_model_performance** (SQL Server views)"):
            st.markdown("""
            **Definition**: Two live views in SQL Server that join ml_predictions to
            ml_targets and aggregate by (model_id, prediction_date).

            - **v_ml_prediction_outcomes**: one row per prediction, with the actual
              outcome joined in (NULL for unresolved predictions)
            - **v_ml_model_performance**: per-(model, date) aggregates — count,
              accuracy, top/bottom decile returns, decile spread, rank IC

            **Not yet in Supabase**: These views run only in SQL Server. The dashboard
            recomputes the equivalent aggregations in pandas from the synced
            ml_predictions + ml_targets tables. If query performance becomes an issue,
            we may add a push function for v_ml_model_performance.

            **Related**: ml_targets, ml_predictions.
            """)

    elif domain_filter.startswith("Sentiment"):
        st.markdown("### Sentiment metrics")
        st.caption(
            "Definitions for the Sentiment dashboard page. Sentiment is computed daily "
            "by FinBERT (a transformer fine-tuned on financial text) scoring news articles "
            "and earnings transcripts, then aggregated per (ticker, date)."
        )

        st.markdown("#### Methodology")

        with st.expander("**FinBERT — the underlying model**"):
            st.markdown("""
            **Model**: ProsusAI/finbert from HuggingFace — a BERT-based transformer
            fine-tuned on financial news for sentiment classification.

            **Inference**: Each article (title + summary) is passed through FinBERT,
            which outputs probabilities for three classes: positive, negative, neutral.

            **Runtime**: GPU-accelerated on a local RTX 3060. Daily news for ~500
            tickers scores in a few minutes.

            **Limitation**: Trained on financial news pre-2020; doesn't see live macro
            context. Sometimes labels strongly negative news as 'neutral' if the
            sentiment is implicit rather than overt.
            """)

        with st.expander("**Net score per article**"):
            st.markdown("""
            **Definition**: For each article, `net = p_positive - p_negative`, ignoring
            the neutral probability.

            **Range**: -1 (purely negative) to +1 (purely positive). Centered at 0 for
            neutral coverage.

            **Why net, not just positive**: A negative article and a positive article
            both have some 'positive' probability mass; the difference is what matters.
            """)

        st.markdown("#### Daily aggregates per ticker")

        with st.expander("**avg_net_score**"):
            st.markdown("""
            **Definition**: Article-confidence-weighted average of net scores across all
            articles for a given (ticker, sentiment_date).

            **Formula**:
            `avg_net_score = sum(net_i * confidence_i) / sum(confidence_i)`

            **Range**: Roughly -1 to +1; in practice usually -0.5 to +0.5.

            **Why confidence-weighted**: Articles where FinBERT is more confident (one
            class clearly dominates) count more than ambiguous articles.

            **Used as**: The headline number on the Sentiment dashboard. Also a feature
            for the ML model (`sent_avg_net_score` in the feature store).

            **Related**: avg_confidence, pct_positive, pct_negative.
            """)

        with st.expander("**avg_confidence**"):
            st.markdown("""
            **Definition**: Mean across articles of `max(p_positive, p_negative, p_neutral)` —
            essentially "how confident was FinBERT, on average".

            **Range**: ~0.33 (random) to 1.0 (perfectly confident).

            **Use**: Differentiating high-conviction news days from ambiguous ones.
            High avg_net_score with low avg_confidence is less actionable than the
            same score with high confidence.

            **Related**: avg_net_score.
            """)

        with st.expander("**pct_positive / pct_negative**"):
            st.markdown("""
            **Definition**: Share of articles in the day's bucket whose top class was
            positive (or negative).

            **Stored as decimal** (0.65 = 65%); rendered as percent in the dashboard
            (multiply by 100 right before display, per the project convention).

            **Use**: A ticker with avg_net_score = +0.20 from 100% positive articles is
            different from one with the same score from 70% positive, 30% negative —
            the second has more contested coverage.

            **Related**: avg_net_score, n_articles.
            """)

        with st.expander("**n_articles / n_publishers**"):
            st.markdown("""
            **n_articles**: Count of distinct articles mentioning the ticker on that
            sentiment_date.

            **n_publishers**: Count of distinct publishers (Bloomberg, Reuters, WSJ, etc.).

            **Use**:
            - n_articles is a coverage / newsworthiness proxy. The 'min articles' slider
              on the Sentiment page filters out tickers with thin coverage.
            - n_publishers helps distinguish a real news event (multiple outlets) from
              a single-publisher take.

            **Related**: avg_net_score, sustained sentiment leaders.
            """)

        st.markdown("#### Derived views")

        with st.expander("**Article-weighted sector sentiment**"):
            st.markdown("""
            **Definition**: For each sector on a given date,

            `sector_score = sum(ticker_avg_score * ticker_n_articles) / sum(ticker_n_articles)`

            **Why weighted**: Heavily-covered tickers (e.g., AAPL with 50 articles)
            move the sector average more than thinly-covered ones (a small-cap with 2
            articles). Matches what's actually driving sector-level news flow.

            **Used in**: Sentiment dashboard, sector heatmap.
            """)

        with st.expander("**Sustained leaders / laggards / consistency**"):
            st.markdown("""
            **Definition**: Over a multi-day window (default 14 days), per ticker:

            - **Weighted average score**: article-weighted across all days
            - **% days positive**: share of days in the window where avg_net_score > 0
            - **% days negative**: share where avg_net_score < 0

            **Why two metrics**: Weighted average favors strong-tone tickers (one big
            positive day can pull it up). Consistency favors tickers that are positive
            most days, even if mildly. Either lens is useful; the dashboard lets you
            sort by whichever.

            **Min days qualifier**: Tickers must have at least N days of coverage in
            the window (default 5) to be ranked, to filter out one-or-two-day stories.

            **Related**: avg_net_score, n_articles.
            """)

        with st.expander("**Extreme-day thresholds**"):
            st.markdown("""
            **Positive extreme**: `avg_net_score >= +0.40`.

            **Negative extreme**: `avg_net_score <= -0.25`.

            **Why asymmetric**: Distribution of avg_net_score is naturally
            slightly-positive-biased (most financial news is neutrally factual or mildly
            bullish; truly negative news is rarer but more meaningful). Using the same
            thresholds on both sides would over-flag positive and under-flag negative.

            **Used in**: Daily FinBERT email (extreme-by-sector alerts), per-ticker time
            series markers on the Sentiment page.
            """)

        st.markdown("#### Cross-domain")

        with st.expander("**Contrarian bulls / Contrarian bears**"):
            st.markdown("""
            **Definition**: Tickers where ML prediction and sentiment disagree.

            - **Contrarian bull**: avg_net_score < 0 (negative news) but ML decile >= 8
              (model still ranks the ticker bullish)
            - **Contrarian bear**: avg_net_score > 0 (positive news) but ML decile <= 3
              (model still ranks the ticker bearish)

            **Why interesting**: These are setups where the model is leaning against
            the news narrative. Sometimes that's signal (the model sees something the
            news doesn't), sometimes it's noise — but the disagreement is worth
            investigating.

            **Used in**: Sentiment vs ML predictions scatter on the Sentiment page.
            Companion tables list the top 5 of each.

            **Related**: predicted_value, decile, avg_net_score.
            """)

    elif domain_filter.startswith("Macro"):
        st.markdown("### Macro metrics")
        st.caption(
            "Macroeconomic features collected daily, used as inputs to the meta-learner's "
            "regime-context layer. Currently built and stored in feature store, with a 10-year "
            "history; not yet surfaced in a dedicated dashboard page (planned)."
        )

        st.markdown("#### Rates & curve")

        with st.expander("**macro_us_10y_yield / macro_us_13w_yield**"):
            st.markdown("""
            **Definition**: Daily yield on the 10-year US Treasury and the 13-week
            (3-month) US T-Bill, sourced via the yfinance feed (^TNX and ^IRX).

            **Range**: Percent (e.g., 4.25 = 4.25% annualized).

            **Use**: Base inputs to the curve spread; standalone signals for rate-sensitive
            sectors (REITs, utilities, financials).

            **Related**: macro_curve_10y_minus_13w.
            """)

        with st.expander("**macro_curve_10y_minus_13w**"):
            st.markdown("""
            **Definition**: 10-year yield minus 13-week yield. The 'yield curve slope'.

            **Range**: Usually -1% to +3%. Negative values mean an inverted curve.

            **Why it matters**: Yield-curve inversion has preceded most US recessions
            historically. Used as a regime-context feature for the meta-learner —
            the model can downweight bullish technicals when the curve is deeply
            inverted.

            **Used in**: Meta-learner regime features.
            """)

        st.markdown("#### Risk & volatility")

        with st.expander("**macro_vix**"):
            st.markdown("""
            **Definition**: CBOE Volatility Index (^VIX) — implied volatility of S&P 500
            options over the next 30 days, annualized.

            **Range**: Roughly 9 (extreme complacency) to 80+ (panic).

            **Interpretation**:
            - < 15 = low fear, often coincides with grinding uptrends
            - 15-25 = normal market
            - 25-35 = elevated stress
            - 35+ = crisis-level fear

            **Used in**: Meta-learner regime features. The model uses VIX to adjust how
            much it trusts technical signals (which tend to misfire in high-VIX regimes
            where correlations spike).
            """)

        with st.expander("**macro_hyg_ief_ratio**"):
            st.markdown("""
            **Definition**: Close-of-day ratio HYG (high-yield corporate bond ETF) /
            IEF (7-10y Treasury ETF). A risk-appetite gauge.

            **Interpretation**: Rising HYG/IEF = credit investors taking more risk
            (bullish risk-on). Falling = credit risk-off, often precedes equity stress.

            **Used in**: Meta-learner regime features.
            """)

        st.markdown("#### Currencies & commodities")

        with st.expander("**macro_dollar_index**"):
            st.markdown("""
            **Definition**: DXY-equivalent — value of the US dollar against a basket of
            major currencies. Sourced as UUP (the ETF) close.

            **Use**: Strong dollar (rising DXY) is usually a headwind for multinationals
            and commodities. Used as a regime-context input.
            """)

        with st.expander("**macro_gold_close / macro_oil_close**"):
            st.markdown("""
            **macro_gold_close**: Close price of GLD (SPDR Gold Shares ETF).
            **macro_oil_close**: Close price of USO (United States Oil Fund).

            **Use**: Inputs for commodity-sensitive sectors (energy, materials, miners),
            inflation regime detection.
            """)

        st.markdown("#### Sector ratios")

        with st.expander("**macro_qqq_spy_ratio / macro_iwm_spy_ratio**"):
            st.markdown("""
            **qqq_spy_ratio**: QQQ close / SPY close — tech vs broad market.
            Rising = tech leadership; falling = tech lagging.

            **iwm_spy_ratio**: IWM close / SPY close — small-caps vs broad market.
            Rising = risk-on, small-cap leadership; falling = flight to large-caps.

            **Use**: Regime-context features for the meta-learner. These rotations
            often precede broader regime shifts.
            """)

        st.info(
            "**Planned**: A dedicated Macro dashboard page with rate / curve / volatility / "
            "ratio time series, and a regime-detection panel using a Hidden Markov Model "
            "over these features. Currently the data is available in feature store and used "
            "as inputs to the meta-learner, but not yet visualized."
        )

# ============================================================
# TAB 3: ARCHITECTURE
# ============================================================
with tab_arch:
    st.subheader("Platform architecture")
    st.caption("Current state of the platform with built vs. planned components")

    here = Path(__file__).parent.parent
    arch_html_path = here / "assets" / "architecture.html"

    if not arch_html_path.exists():
        st.warning(
            f"Architecture HTML not found at `{arch_html_path}`. "
            "Save the architecture document to `assets/architecture.html` to embed it here."
        )
    else:
        html_content = arch_html_path.read_text(encoding="utf-8")
        components.html(html_content, height=2400, scrolling=True)

    st.divider()
    st.caption(
        "Download options: right-click the architecture above → 'Save as' to save the HTML. "
        "Or view directly: `assets/architecture.html` in the repo."
    )
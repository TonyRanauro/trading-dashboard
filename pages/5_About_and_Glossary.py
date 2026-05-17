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
                "(prices, indicators, sector RS, signals, email, Supabase push, earnings calendar). "
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
        options=["Technical (current)", "Fundamental (current)",
                 "Sentiment (planned)", "Macro (planned)"],
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
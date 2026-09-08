# Synthetic Exposure — Score Methodology

**Model versions**: `v1` (historical, 90-day), `pearson_intraday_v1` (live, 30-minute)

---

## What is an Exposure Score?

An Exposure Score is the **signed** Pearson correlation, in `[−1.00, +1.00]`, between a stock's and a crypto asset's log returns over a lookback window. `+1.00` means the two assets moved in near-perfect lockstep; `−1.00` means they moved in near-perfect opposition; `0.00` means no linear relationship was observed.

Scores are always displayed with an explicit sign — `+0.78`, `−0.62`, `0.00` — never as a percentage or `/100`, and never clamped to positive-only. Two flavors are shown on each stock's asset page:

- **Historical Exposure** — 90-day daily-return correlation, recomputed twice weekly.
- **Live Exposure** — rolling 30-minute-candle correlation over the last 20 trading sessions, recomputed after each completed market bucket.

**This is a historical measure, not a forecast.** Past correlation does not guarantee future correlation. Exposure Scores are not investment advice.

---

## Historical calculation (90-day)

### Inputs

- Stock daily close — prefers `adj_close` from Marketstack; falls back to `close` when `adj_close` is missing, zero or negative, and records that fallback in `data_quality: "adj_close_missing"`.
- Crypto daily close — currently a **daily UTC close**, not yet selected against the actual XNYS session close time. Stored scores mark this with `data_quality: "crypto_daily_proxy"` rather than claiming precise market-close alignment.
- Lookback window: 90 calendar days.
- Only dates where both series have a valid, positive close are used (inner join by date).

### Steps

1. Sort prices oldest → newest.
2. Inner-join stock and crypto price series by shared calendar date.
3. Compute daily log returns on the aligned slices: `return_t = ln(price_t / price_{t−1})`.
4. Require at least 45 aligned return observations; pairs below that are excluded entirely (never scored as 0).
5. Calculate signed Pearson correlation `r` over the aligned return vectors. No clamp is applied — a negative `r` is stored and returned exactly as calculated.

### Why log returns instead of raw prices?

Log returns are time-additive and approximately normally distributed, which satisfies Pearson's linearity and homoscedasticity assumptions far better than raw price levels. Correlating raw prices would produce spuriously high scores simply because both series trend upward over time.

### Why inner-join by date before computing returns?

Stock markets close on weekdays; crypto markets trade 24/7. A Monday stock return covers the Friday → Monday interval (3 calendar days); a Monday crypto return computed independently covers only Sunday → Monday (1 day). Computing returns independently and then aligning would pair different time intervals under the same date label. Inner-joining price series first ensures both return vectors represent identical calendar intervals.

### Toward true session alignment

The target design selects, for each stock trading session, the crypto price sample nearest the actual XNYS session close (accounting for holidays and early closes via the maintained exchange calendar), using hourly/5-minute crypto observations rather than a single daily UTC value. That data pipeline exists for live 30-minute scoring (see below) but has not yet been backfilled across the full 90-day historical window — CoinGecko's Demo plan does not reliably provide 90 days of hourly history. Until it does, historical scores are honestly marked `crypto_daily_proxy` rather than claiming exact alignment.

---

## Live calculation (30-minute, intraday)

### Inputs

- Completed 30-minute stock candles from Marketstack's `/intraday` endpoint (one batched request for every stock symbol).
- Completed 30-minute crypto candles built server-side from 5-minute price observations collected via one CoinGecko `/coins/markets` batch call every 5 minutes — never a separate provider call per candle or per asset.
- Up to the last 20 US trading sessions; a minimum of 65 aligned 30-minute intervals is required before a pair produces a score (`collecting_data` otherwise, with the current/required count and an estimated ready date).

### Steps

1. Build each 30-minute candle as `open` = first sample, `high` = max, `low` = min, `close` = last sample within the bucket. A candle needs at least 3 samples to be marked `data_quality: "ok"`; candles with fewer are marked `"reduced"` and excluded from scoring entirely.
2. Never use the current, still-forming bucket — only buckets whose 30-minute interval has fully elapsed are persisted or scored.
3. Candle return is `log(close/open)` — computed within each bucket, never close-to-close across buckets, so there is no overnight or weekend return leakage.
4. Match stock and crypto candles on identical completed UTC bucket timestamps within the same NYSE session.
5. Calculate signed Pearson `r` over the matched candle returns.
6. The full result set for a stock is computed in memory first, then written atomically (bulk upsert); if computation fails partway, the previous valid scores are left untouched — nothing is deleted before a full replacement set is ready.

The live score is frozen (not recalculated) while the US market is closed, except to finalize the last bucket right after close — the frontend shows a blue "US market closed" pill with the real last-calculated timestamp, never the theoretical close time.

`GET /api/v1/intraday/{symbol}` only ever reads these stored scores — it never computes a score inside the request handler.

---

## Data sources

| Provider | Data | Notes |
|----------|------|-------|
| Marketstack | Stock daily EOD + 30-minute intraday candles | Batched across all configured symbols per request where the plan supports it |
| CoinGecko | Crypto daily OHLCV + batch quotes + 5-minute observations for candle-building | Attribution required on the Demo plan |

When `USE_DEMO_DATA=true`, deterministic fixture data is used and no external provider calls are made. Fixture-derived rows are labelled `demo: true` (or `is_demo: true`) in every API response, and the frontend shows a demo-data badge wherever they're displayed.

---

## Update schedule

| Data | Frequency | Cloudflare job |
|------|-----------|----------------|
| Crypto current price + 5-min observation | Every 5 minutes | Quote scheduler |
| 30-minute stock + crypto candles, live Exposure Scores | After each completed 30-min market bucket (market hours only, plus the final closing bucket) | Intraday scheduler |
| Stock EOD, crypto daily history, historical Exposure Scores, retention cleanup | Tuesday and Friday after market close | Historical scheduler |

Both historical and live scores are pre-computed and stored. Neither is ever calculated during a user page request.

---

## Freshness

- **Historical scores** are stale only if computed before the most recent Tuesday/Friday recalculation deadline — an ordinary weekend or a market holiday between recalculations never makes an up-to-date score look stale.
- **Live scores** are `fresh` while within one completed bucket (plus a short processing grace) of the market's current bucket, `stale` if a bucket was missed, `collecting_data` before the minimum observation count is reached, and `market_closed` (never stale) whenever the market itself is closed.
- **Crypto quotes** are stale after ~15 minutes during market hours, ~45 minutes outside market hours.

---

## Asset universe

**Guest / non-holder — 8 stocks, 30 crypto:**

NVDA, TSLA, COIN, MSTR, AMD, MSFT, META, PLTR

| Category | Assets |
|----------|--------|
| Layer 1 | BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, NEAR, ICP, APT, SUI, HBAR |
| Layer 2 | ARB, OP, POL |
| DeFi | UNI, AAVE, INJ |
| Oracle/Data | LINK, GRT |
| AI/Compute | TAO, RENDER, FET, AKT, AIOZ |
| Storage | FIL, AR |
| Memecoin | DOGE, PEPE |

**Verified `$SynthEx` holder — 20 stocks, 100 crypto** (adds AMZN, GOOGL, AAPL, INTC, QCOM, MU, SMCI, HOOD, RIOT, MARA, CLSK, WULF, plus 70 additional crypto assets across Layer 1/2, DeFi, Oracle/Data, AI/Compute, Storage, GameFi, RWA, Privacy, Memecoin, Exchange and Liquid Staking categories). Access is enforced server-side on every endpoint that serves asset data — never by hiding links on the frontend.

---

## Limitations

- The 90-day historical window may not capture long-term structural relationships.
- Correlation can change rapidly with market regime shifts.
- The asset universe is curated and does not represent the full market.
- Historical crypto prices are currently a daily UTC proxy, not precisely session-aligned to the XNYS close — see "Toward true session alignment" above.
- Stock market holidays reduce the observation count for that stock.
- Scores reflect price-movement similarity, not ownership, market-cap exposure, or any guarantee of equivalent performance.

---

## Disclaimer

Synthetic Exposure Scores are for informational and analytical purposes only. They do not constitute investment advice, a recommendation to buy or sell any asset, or a prediction of future performance. Always do your own research.

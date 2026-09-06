# DELTA — Synthetic Exposure Score Methodology

**Model version**: `pearson_v1`

---

## What is an Exposure Score?

An Exposure Score measures the historical tendency of a crypto asset to move similarly to a given stock over a 90-day window. A score of 1.0 means the two assets moved in near-perfect lockstep over that period; 0.0 means no positive historical co-movement.

**This is a historical measure, not a forecast.** Past correlation does not guarantee future correlation. Exposure Scores are not investment advice.

---

## Calculation

### Inputs

- Daily closing prices for the selected stock — sourced from Marketstack EOD
- Daily crypto prices at a consistent UTC timestamp — sourced from CoinGecko OHLCV
- Lookback window: 90 calendar days
- Only dates where both the stock and crypto have a valid close are used (inner join by date)

### Steps

1. Sort prices oldest → newest
2. Inner-join stock and crypto price series by shared calendar date
3. Compute daily log returns on the aligned slices:

   `return_t = ln(price_t / price_{t−1})`

4. Calculate Pearson correlation `r` over the aligned return vectors
5. Clamp to the unit interval:

   `exposure_score = max(0, min(1, r))`

Negative or zero correlation is clamped to 0 — the score represents positive exposure only. The raw `r` value is preserved in every API response.

### Why log returns instead of raw prices?

Log returns are time-additive and approximately normally distributed, which satisfies Pearson's linearity and homoscedasticity assumptions better than raw price levels. Computing correlation on raw prices would introduce spurious results simply because both series trend upward over time.

### Why inner-join by date before computing returns?

Stock markets close on weekdays; crypto markets trade 24/7. A Monday stock return covers the Friday → Monday interval (3 calendar days); a Monday crypto return covers only Sunday → Monday (1 day). Computing returns independently and then aligning would pair different time intervals under the same date label. Inner-joining price series first ensures both return vectors represent the same calendar interval.

---

## Data sources

| Provider | Data | Notes |
|----------|------|-------|
| Marketstack | Stock daily OHLCV (EOD) | Attribution required per provider terms |
| CoinGecko | Crypto daily OHLCV + batch quote prices | Attribution required on Demo plan |

When `USE_DEMO_DATA=true`, deterministic fixture data is used and no external provider calls are made. Fixture data is clearly labelled `demo: true` in all API responses.

---

## Update schedule

| Data | Frequency | Command |
|------|-----------|---------|
| Crypto current prices (quote) | Every 5 minutes | `refresh-crypto-quotes` |
| Stock EOD prices | Tuesday and Friday | `refresh-stock-eod` |
| Exposure Scores | Tuesday and Friday (after EOD) | `recompute-scores` |

Scores are pre-computed and stored in `stored_exposure_scores`. They are never recalculated during a user page request.

---

## Asset universe

**8 stocks**: NVDA, TSLA, COIN, MSTR, AMD, MSFT, META, PLTR

**30 crypto assets** across 7 categories:

| Category | Assets |
|----------|--------|
| Layer 1 | BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, NEAR, ICP, APT, SUI, HBAR |
| Layer 2 | ARB, OP, POL |
| DeFi | UNI, AAVE, INJ |
| Oracle/Data | LINK, GRT |
| AI/Compute | TAO, RENDER, FET, AKT, AIOZ |
| Storage | FIL, AR |
| Memecoin | DOGE, PEPE |

---

## Limitations

- The 90-day window may not capture long-term structural relationships
- Correlation can change rapidly with market regime shifts
- The crypto universe is curated (30 assets) and does not represent the full market
- Stock market holidays reduce the observation count for that stock
- Scores reflect price-movement similarity, not ownership, market-cap exposure, or any guarantee of equivalent performance

---

## Disclaimer

DELTA Exposure Scores are for informational and analytical purposes only. They do not constitute investment advice, a recommendation to buy or sell any asset, or a prediction of future performance. Always do your own research.

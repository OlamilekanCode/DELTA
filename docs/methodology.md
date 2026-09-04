# DELTA Exposure Score Methodology

> Version: pearson_v1 | Updated: Milestone 0 — Placeholder. Expand in Milestone 3.

## What is an Exposure Score?

An Exposure Score measures the historical tendency of a crypto asset to move similarly to a given stock over a defined lookback window. A score closer to 1.0 indicates a strong positive historical relationship; 0.0 indicates no positive relationship.

**This is a historical measure, not a forecast.** Past correlation does not guarantee future correlation. DELTA scores are not investment advice.

## Calculation: pearson_v1

### Inputs

- Adjusted daily closing prices for the selected stock (from Marketstack)
- Daily crypto prices sampled at a consistent UTC timestamp (from CoinGecko)
- Default lookback: 90 calendar days
- Only dates on which the stock has a valid close are used
- Minimum 45 aligned observations required

### Steps

1. Sort prices oldest → newest
2. Convert each price series to daily log returns:
   `return_t = ln(price_t / price_(t-1))`
3. Align stock and crypto returns by date
4. Calculate Pearson correlation `r`
5. Apply floor and ceiling:
   `exposure_score = max(0, min(1, r))`

Negative or zero correlation is treated as 0 positive exposure. The raw correlation value is preserved in the API response for transparency.

### Stored result fields

| Field | Description |
|-------|-------------|
| `base_asset` | Stock symbol (e.g. NVDA) |
| `related_asset` | Crypto symbol (e.g. BTC) |
| `window_days` | Lookback window (e.g. 90) |
| `score` | Exposure Score 0–1 |
| `raw_correlation` | Pearson r (can be negative) |
| `observation_count` | Aligned daily observations used |
| `model_version` | `pearson_v1` |
| `period_start` | Start date of the window |
| `period_end` | End date of the window |
| `calculated_at` | UTC timestamp of calculation |

## Data sources (Milestone 2+)

| Provider | Data | Attribution |
|----------|------|-------------|
| Marketstack | Stock daily OHLCV | Required per provider terms |
| CoinGecko | Crypto daily prices | Attribution required on Demo plan |
| DEX Screener | On-chain supplemental (optional) | — |

## Update schedule

Phase 1: after the relevant stock market closes, and optionally every 6 hours during extended trading. Scores are pre-computed and cached; they are not recalculated during a user page request.

## Limitations

- 90-day window may not capture structural long-term relationships
- Correlation can change suddenly with market regime shifts
- The crypto universe is limited in Phase 1 (20–50 curated assets)
- Stock market holidays reduce the observation count
- Scores reflect price movement similarity, not ownership, exposure by market cap, or any guarantee of equivalent performance

## Disclaimer

DELTA Exposure Scores are for informational and analytical purposes only. They do not constitute investment advice, a recommendation to buy or sell any asset, or a prediction of future performance. Always do your own research.

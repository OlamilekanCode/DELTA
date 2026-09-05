import math
from dataclasses import dataclass

import numpy as np

MIN_OBSERVATIONS = 45


@dataclass
class PricePoint:
    date: str
    close: float


def log_returns(prices: list[float]) -> list[float]:
    if len(prices) < 2:
        return []
    return [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]


def align_series(
    a: list[PricePoint], b: list[PricePoint]
) -> tuple[list[float], list[float], list[str]]:
    b_map = {p.date: p.close for p in b}
    aligned_a: list[float] = []
    aligned_b: list[float] = []
    dates: list[str] = []
    for p in a:
        if p.date in b_map:
            aligned_a.append(p.close)
            aligned_b.append(b_map[p.date])
            dates.append(p.date)
    return aligned_a, aligned_b, dates


def pearson_r(xs: list[float], ys: list[float]) -> tuple[float, int]:
    n = len(xs)
    if n < MIN_OBSERVATIONS:
        return 0.0, n
    arr = np.corrcoef(np.array(xs, dtype=float), np.array(ys, dtype=float))
    r = float(arr[0, 1])
    if math.isnan(r):
        return 0.0, n
    return r, n


def normalize_base100(prices: list[float]) -> list[float]:
    if not prices:
        return []
    base = prices[0]
    if base == 0:
        return [0.0] * len(prices)
    return [round(p / base * 100, 2) for p in prices]


@dataclass
class ExposureScore:
    symbol: str
    name: str
    category: str
    score: float          # max(0, raw_correlation)
    raw_correlation: float
    observations: int


def compute_exposure_scores(
    stock_prices: list[PricePoint],
    crypto_map: dict[str, tuple[str, str, list[PricePoint]]],  # symbol -> (name, category, prices)
) -> list[ExposureScore]:
    stock_by_date = {p.date: p.close for p in stock_prices}

    results: list[ExposureScore] = []
    for symbol, (name, category, crypto_prices) in crypto_map.items():
        crypto_by_date = {p.date: p.close for p in crypto_prices}
        # Inner-join by date first, then compute log returns on aligned prices.
        # This ensures stock and crypto returns span identical date intervals
        # (e.g. Monday's return uses Friday's close for both, not Sunday's for crypto).
        common_dates = sorted(set(stock_by_date) & set(crypto_by_date))
        if len(common_dates) < 2:
            continue
        s_rets = log_returns([stock_by_date[d] for d in common_dates])
        c_rets = log_returns([crypto_by_date[d] for d in common_dates])
        if len(s_rets) < MIN_OBSERVATIONS:
            continue
        r, n = pearson_r(s_rets, c_rets)
        results.append(ExposureScore(
            symbol=symbol,
            name=name,
            category=category,
            score=round(max(0.0, r), 4),
            raw_correlation=round(r, 4),
            observations=n,
        ))

    results.sort(key=lambda e: e.score, reverse=True)
    return results

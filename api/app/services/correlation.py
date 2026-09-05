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
    stock_rets = log_returns([p.close for p in stock_prices])
    if not stock_rets:
        return []

    results: list[ExposureScore] = []
    for symbol, (name, category, crypto_prices) in crypto_map.items():
        aligned_s, aligned_c, _ = align_series(
            [PricePoint(date=stock_prices[i + 1].date, close=stock_rets[i]) for i in range(len(stock_rets))],
            [PricePoint(date=p.date, close=math.log(crypto_prices[j + 1].close / crypto_prices[j].close))
             for j, p in enumerate(crypto_prices[1:])],
        )
        if len(aligned_s) < MIN_OBSERVATIONS:
            continue
        r, n = pearson_r(aligned_s, aligned_c)
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

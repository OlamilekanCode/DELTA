from datetime import date, timedelta

from app.providers.base import PriceRow

_RAW_NVDA = [403, 408, 412, 418, 425, 421, 430, 438, 445, 440, 452, 458, 462, 470, 465, 472, 480,
             488, 482, 491, 498, 505, 512, 508, 520, 528, 535, 530, 542, 548, 555, 562, 558, 570,
             578, 584, 590, 585, 592, 600, 608, 615, 610, 622, 630, 638, 645, 640, 652, 660, 668,
             675, 670, 682, 690, 698, 704, 710, 716, 722, 718, 728, 736]

_RAW_BTC = [62000, 62800, 63500, 64200, 63800, 64800, 65500, 66200, 65800, 66500, 67200, 66800,
            67500, 68200, 67800, 68500, 69200, 68800, 69500, 70000, 70800, 71500, 72000, 71500,
            72200, 73000, 73800, 73200, 74000, 74800, 75500, 76000, 75500, 76200, 77000, 77800,
            78500, 78000, 79000, 79800, 80500, 81000, 80500, 81200, 82000, 82800, 83500, 83000,
            84000, 84800, 85500, 86000, 85500, 86200, 87000, 87800, 88500, 89000, 88500, 89200,
            90000, 90800, 91500]

_RAW_ETH = [3200, 3240, 3270, 3310, 3280, 3320, 3360, 3400, 3370, 3410, 3450, 3420, 3460, 3500,
            3470, 3510, 3550, 3520, 3560, 3600, 3640, 3670, 3700, 3670, 3710, 3750, 3790, 3760,
            3800, 3840, 3880, 3910, 3880, 3920, 3960, 4000, 4040, 4010, 4060, 4100, 4140, 4170,
            4140, 4180, 4220, 4260, 4300, 4270, 4320, 4360, 4400, 4440, 4410, 4450, 4490, 4530,
            4570, 4610, 4580, 4620, 4660, 4700, 4740]

_START_DATE = date(2026, 6, 3)


def _noise(seed: int, i: int, amp: float) -> float:
    state = (seed * 1664525 + i * 1013904223 + 22695477) & 0xFFFFFFFF
    return 1.0 + ((state / 0xFFFFFFFF) - 0.5) * amp


def _derived(base: list[float], scale: float, seed: int, noise_amp: float = 0.02) -> list[float]:
    b0 = base[0]
    return [round(scale * (p / b0) * _noise(seed, i, noise_amp), 4) for i, p in enumerate(base)]


_RAW_SOL = _derived(_RAW_BTC, 150.0, seed=1)
_RAW_AVAX = _derived(_RAW_ETH, 35.0, seed=2)
_RAW_LINK = _derived(_RAW_ETH, 15.0, seed=3, noise_amp=0.025)
_RAW_ARB = _derived(_RAW_BTC, 1.20, seed=4, noise_amp=0.03)
_RAW_FET = _derived(_RAW_ETH, 2.50, seed=5, noise_amp=0.03)
_RAW_RNDR = _derived(_RAW_BTC, 8.00, seed=6, noise_amp=0.025)

_SYMBOL_DATA: dict[str, list[float]] = {
    "NVDA": _RAW_NVDA,
    "BTC": _RAW_BTC,
    "ETH": _RAW_ETH,
    "SOL": _RAW_SOL,
    "AVAX": _RAW_AVAX,
    "LINK": _RAW_LINK,
    "ARB": _RAW_ARB,
    "FET": _RAW_FET,
    "RNDR": _RAW_RNDR,
}

FIXTURE_ASSETS = [
    {"symbol": "NVDA", "name": "NVIDIA Corporation", "asset_type": "stock", "category": "Technology", "coingecko_id": None},
    {"symbol": "BTC", "name": "Bitcoin", "asset_type": "crypto", "category": "BTC Ecosystem", "coingecko_id": "bitcoin"},
    {"symbol": "ETH", "name": "Ethereum", "asset_type": "crypto", "category": "DeFi", "coingecko_id": "ethereum"},
    {"symbol": "SOL", "name": "Solana", "asset_type": "crypto", "category": "AI", "coingecko_id": "solana"},
    {"symbol": "AVAX", "name": "Avalanche", "asset_type": "crypto", "category": "DeFi", "coingecko_id": "avalanche-2"},
    {"symbol": "LINK", "name": "Chainlink", "asset_type": "crypto", "category": "AI", "coingecko_id": "chainlink"},
    {"symbol": "ARB", "name": "Arbitrum", "asset_type": "crypto", "category": "DeFi", "coingecko_id": "arbitrum"},
    {"symbol": "FET", "name": "Fetch.ai", "asset_type": "crypto", "category": "AI", "coingecko_id": "fetch-ai"},
    {"symbol": "RNDR", "name": "Render", "asset_type": "crypto", "category": "AI", "coingecko_id": "render-token"},
]


class FixtureProvider:
    async def fetch_ohlcv(self, symbol: str, days: int) -> list[PriceRow]:
        prices = _SYMBOL_DATA.get(symbol.upper(), [])
        rows: list[PriceRow] = []
        for i, close in enumerate(prices[-days:]):
            offset = max(0, len(prices) - days)
            d = _START_DATE + timedelta(days=offset + i)
            rows.append(PriceRow(date=d.isoformat(), close=float(close)))
        return rows

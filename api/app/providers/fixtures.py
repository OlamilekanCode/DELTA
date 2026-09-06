from datetime import UTC, date, datetime, timedelta

from app.providers.base import PriceRow, QuoteRow

_RAW_NVDA: list[float] = [
    403, 408, 412, 418, 425, 421, 430, 438, 445, 440, 452, 458, 462, 470, 465, 472, 480,
    488, 482, 491, 498, 505, 512, 508, 520, 528, 535, 530, 542, 548, 555, 562, 558, 570,
    578, 584, 590, 585, 592, 600, 608, 615, 610, 622, 630, 638, 645, 640, 652, 660, 668,
    675, 670, 682, 690, 698, 704, 710, 716, 722, 718, 728, 736,
]

_RAW_BTC: list[float] = [
    62000, 62800, 63500, 64200, 63800, 64800, 65500, 66200, 65800, 66500, 67200, 66800,
    67500, 68200, 67800, 68500, 69200, 68800, 69500, 70000, 70800, 71500, 72000, 71500,
    72200, 73000, 73800, 73200, 74000, 74800, 75500, 76000, 75500, 76200, 77000, 77800,
    78500, 78000, 79000, 79800, 80500, 81000, 80500, 81200, 82000, 82800, 83500, 83000,
    84000, 84800, 85500, 86000, 85500, 86200, 87000, 87800, 88500, 89000, 88500, 89200,
    90000, 90800, 91500,
]

_RAW_ETH: list[float] = [
    3200, 3240, 3270, 3310, 3280, 3320, 3360, 3400, 3370, 3410, 3450, 3420, 3460, 3500,
    3470, 3510, 3550, 3520, 3560, 3600, 3640, 3670, 3700, 3670, 3710, 3750, 3790, 3760,
    3800, 3840, 3880, 3910, 3880, 3920, 3960, 4000, 4040, 4010, 4060, 4100, 4140, 4170,
    4140, 4180, 4220, 4260, 4300, 4270, 4320, 4360, 4400, 4440, 4410, 4450, 4490, 4530,
    4570, 4610, 4580, 4620, 4660, 4700, 4740,
]


def _noise(seed: int, i: int, amp: float) -> float:
    state = (seed * 1664525 + i * 1013904223 + 22695477) & 0xFFFFFFFF
    return 1.0 + ((state / 0xFFFFFFFF) - 0.5) * amp


def _derived(base: list[float], scale: float, seed: int, noise_amp: float = 0.02) -> list[float]:
    b0 = base[0]
    return [round(scale * (p / b0) * _noise(seed, i, noise_amp), 8) for i, p in enumerate(base)]


# Stocks
_RAW_TSLA = _derived(_RAW_NVDA, 250.0, seed=10, noise_amp=0.04)
_RAW_COIN = _derived(_RAW_BTC, 248.0, seed=11, noise_amp=0.055)
_RAW_MSTR = _derived(_RAW_BTC, 378.0, seed=12, noise_amp=0.03)
_RAW_AMD = _derived(_RAW_NVDA, 162.0, seed=13, noise_amp=0.025)
_RAW_MSFT = _derived(_RAW_NVDA, 426.0, seed=14, noise_amp=0.012)
_RAW_META = _derived(_RAW_NVDA, 548.0, seed=15, noise_amp=0.022)
_RAW_PLTR = _derived(_RAW_NVDA, 34.0, seed=16, noise_amp=0.055)

# Crypto — Layer 1
_RAW_SOL = _derived(_RAW_BTC, 150.0, seed=1)
_RAW_BNB = _derived(_RAW_BTC, 598.0, seed=20, noise_amp=0.018)
_RAW_XRP = _derived(_RAW_BTC, 0.54, seed=21, noise_amp=0.03)
_RAW_ADA = _derived(_RAW_ETH, 0.44, seed=22, noise_amp=0.03)
_RAW_AVAX = _derived(_RAW_ETH, 35.0, seed=2)
_RAW_DOT = _derived(_RAW_ETH, 7.0, seed=24)
_RAW_NEAR = _derived(_RAW_ETH, 5.5, seed=25)
_RAW_ICP = _derived(_RAW_BTC, 10.0, seed=26)
_RAW_APT = _derived(_RAW_ETH, 8.0, seed=28)
_RAW_SUI = _derived(_RAW_ETH, 2.0, seed=29)
_RAW_HBAR = _derived(_RAW_ETH, 0.085, seed=40)

# Crypto — Layer 2
_RAW_ARB = _derived(_RAW_BTC, 1.20, seed=4, noise_amp=0.03)
_RAW_OP = _derived(_RAW_ETH, 1.80, seed=30)
_RAW_POL = _derived(_RAW_ETH, 0.55, seed=31)

# Crypto — DeFi
_RAW_UNI = _derived(_RAW_ETH, 8.0, seed=33)
_RAW_AAVE = _derived(_RAW_ETH, 180.0, seed=34)
_RAW_INJ = _derived(_RAW_ETH, 25.0, seed=32)

# Crypto — Oracle/Data
_RAW_LINK = _derived(_RAW_ETH, 15.0, seed=3, noise_amp=0.025)
_RAW_GRT = _derived(_RAW_ETH, 0.22, seed=37)

# Crypto — AI/Compute
_RAW_TAO = _derived(_RAW_BTC, 400.0, seed=35, noise_amp=0.045)
_RAW_RENDER = _derived(_RAW_BTC, 8.00, seed=6, noise_amp=0.025)
_RAW_FET = _derived(_RAW_ETH, 2.50, seed=5, noise_amp=0.03)
_RAW_AKT = _derived(_RAW_BTC, 4.5, seed=36, noise_amp=0.04)
_RAW_AIOZ = _derived(_RAW_ETH, 0.85, seed=39)

# Crypto — Storage
_RAW_FIL = _derived(_RAW_BTC, 5.0, seed=27, noise_amp=0.04)
_RAW_AR = _derived(_RAW_BTC, 25.0, seed=38, noise_amp=0.04)

# Crypto — Memecoin
_RAW_DOGE = _derived(_RAW_BTC, 0.115, seed=23, noise_amp=0.07)
_RAW_PEPE = _derived(_RAW_BTC, 0.0000125, seed=41, noise_amp=0.09)

_SYMBOL_DATA: dict[str, list[float]] = {
    "NVDA": _RAW_NVDA,
    "TSLA": _RAW_TSLA,
    "COIN": _RAW_COIN,
    "MSTR": _RAW_MSTR,
    "AMD": _RAW_AMD,
    "MSFT": _RAW_MSFT,
    "META": _RAW_META,
    "PLTR": _RAW_PLTR,
    "BTC": _RAW_BTC,
    "ETH": _RAW_ETH,
    "SOL": _RAW_SOL,
    "BNB": _RAW_BNB,
    "XRP": _RAW_XRP,
    "ADA": _RAW_ADA,
    "AVAX": _RAW_AVAX,
    "DOT": _RAW_DOT,
    "NEAR": _RAW_NEAR,
    "ICP": _RAW_ICP,
    "APT": _RAW_APT,
    "SUI": _RAW_SUI,
    "HBAR": _RAW_HBAR,
    "ARB": _RAW_ARB,
    "OP": _RAW_OP,
    "POL": _RAW_POL,
    "UNI": _RAW_UNI,
    "AAVE": _RAW_AAVE,
    "INJ": _RAW_INJ,
    "LINK": _RAW_LINK,
    "GRT": _RAW_GRT,
    "TAO": _RAW_TAO,
    "RENDER": _RAW_RENDER,
    "FET": _RAW_FET,
    "AKT": _RAW_AKT,
    "AIOZ": _RAW_AIOZ,
    "FIL": _RAW_FIL,
    "AR": _RAW_AR,
    "DOGE": _RAW_DOGE,
    "PEPE": _RAW_PEPE,
}

FIXTURE_ASSETS: list[dict] = [
    # Stocks
    {"symbol": "NVDA", "name": "NVIDIA Corporation",    "asset_type": "stock",  "category": "Technology",   "coingecko_id": None},
    {"symbol": "TSLA", "name": "Tesla Inc.",             "asset_type": "stock",  "category": "Technology",   "coingecko_id": None},
    {"symbol": "COIN", "name": "Coinbase Global Inc.",   "asset_type": "stock",  "category": "Finance",      "coingecko_id": None},
    {"symbol": "MSTR", "name": "MicroStrategy Inc.",     "asset_type": "stock",  "category": "Finance",      "coingecko_id": None},
    {"symbol": "AMD",  "name": "Advanced Micro Devices", "asset_type": "stock",  "category": "Technology",   "coingecko_id": None},
    {"symbol": "MSFT", "name": "Microsoft Corporation",  "asset_type": "stock",  "category": "Technology",   "coingecko_id": None},
    {"symbol": "META", "name": "Meta Platforms Inc.",    "asset_type": "stock",  "category": "Technology",   "coingecko_id": None},
    {"symbol": "PLTR", "name": "Palantir Technologies",  "asset_type": "stock",  "category": "Technology",   "coingecko_id": None},
    # Crypto — Layer 1
    {"symbol": "BTC",  "name": "Bitcoin",                "asset_type": "crypto", "category": "Layer 1",      "coingecko_id": "bitcoin"},
    {"symbol": "ETH",  "name": "Ethereum",               "asset_type": "crypto", "category": "Layer 1",      "coingecko_id": "ethereum"},
    {"symbol": "SOL",  "name": "Solana",                 "asset_type": "crypto", "category": "Layer 1",      "coingecko_id": "solana"},
    {"symbol": "BNB",  "name": "BNB",                    "asset_type": "crypto", "category": "Layer 1",      "coingecko_id": "binancecoin"},
    {"symbol": "XRP",  "name": "XRP",                    "asset_type": "crypto", "category": "Layer 1",      "coingecko_id": "ripple"},
    {"symbol": "ADA",  "name": "Cardano",                "asset_type": "crypto", "category": "Layer 1",      "coingecko_id": "cardano"},
    {"symbol": "AVAX", "name": "Avalanche",              "asset_type": "crypto", "category": "Layer 1",      "coingecko_id": "avalanche-2"},
    {"symbol": "DOT",  "name": "Polkadot",               "asset_type": "crypto", "category": "Layer 1",      "coingecko_id": "polkadot"},
    {"symbol": "NEAR", "name": "NEAR Protocol",          "asset_type": "crypto", "category": "Layer 1",      "coingecko_id": "near"},
    {"symbol": "ICP",  "name": "Internet Computer",      "asset_type": "crypto", "category": "Layer 1",      "coingecko_id": "internet-computer"},
    {"symbol": "APT",  "name": "Aptos",                  "asset_type": "crypto", "category": "Layer 1",      "coingecko_id": "aptos"},
    {"symbol": "SUI",  "name": "Sui",                    "asset_type": "crypto", "category": "Layer 1",      "coingecko_id": "sui"},
    {"symbol": "HBAR", "name": "Hedera",                 "asset_type": "crypto", "category": "Layer 1",      "coingecko_id": "hedera-hashgraph"},
    # Crypto — Layer 2
    {"symbol": "ARB",  "name": "Arbitrum",               "asset_type": "crypto", "category": "Layer 2",      "coingecko_id": "arbitrum"},
    {"symbol": "OP",   "name": "Optimism",               "asset_type": "crypto", "category": "Layer 2",      "coingecko_id": "optimism"},
    {"symbol": "POL",  "name": "Polygon",                "asset_type": "crypto", "category": "Layer 2",      "coingecko_id": "matic-network"},
    # Crypto — DeFi
    {"symbol": "UNI",  "name": "Uniswap",                "asset_type": "crypto", "category": "DeFi",         "coingecko_id": "uniswap"},
    {"symbol": "AAVE", "name": "Aave",                   "asset_type": "crypto", "category": "DeFi",         "coingecko_id": "aave"},
    {"symbol": "INJ",  "name": "Injective",              "asset_type": "crypto", "category": "DeFi",         "coingecko_id": "injective-protocol"},
    # Crypto — Oracle/Data
    {"symbol": "LINK", "name": "Chainlink",              "asset_type": "crypto", "category": "Oracle/Data",  "coingecko_id": "chainlink"},
    {"symbol": "GRT",  "name": "The Graph",              "asset_type": "crypto", "category": "Oracle/Data",  "coingecko_id": "the-graph"},
    # Crypto — AI/Compute
    {"symbol": "TAO",    "name": "Bittensor",            "asset_type": "crypto", "category": "AI/Compute",   "coingecko_id": "bittensor"},
    {"symbol": "RENDER", "name": "Render",               "asset_type": "crypto", "category": "AI/Compute",   "coingecko_id": "render-token"},
    {"symbol": "FET",    "name": "Fetch.ai",             "asset_type": "crypto", "category": "AI/Compute",   "coingecko_id": "fetch-ai"},
    {"symbol": "AKT",    "name": "Akash Network",        "asset_type": "crypto", "category": "AI/Compute",   "coingecko_id": "akash-network"},
    {"symbol": "AIOZ",   "name": "AIOZ Network",         "asset_type": "crypto", "category": "AI/Compute",   "coingecko_id": "aioz-network"},
    # Crypto — Storage
    {"symbol": "FIL",  "name": "Filecoin",               "asset_type": "crypto", "category": "Storage",      "coingecko_id": "filecoin"},
    {"symbol": "AR",   "name": "Arweave",                "asset_type": "crypto", "category": "Storage",      "coingecko_id": "arweave"},
    # Crypto — Memecoin
    {"symbol": "DOGE", "name": "Dogecoin",               "asset_type": "crypto", "category": "Memecoin",     "coingecko_id": "dogecoin"},
    {"symbol": "PEPE", "name": "Pepe",                   "asset_type": "crypto", "category": "Memecoin",     "coingecko_id": "pepe"},
]


def _fixture_change_pct(symbol: str) -> float:
    """Deterministic fake 24h change in range [-5%, +5%]."""
    seed = sum(ord(c) for c in symbol)
    return round(((seed % 21) - 10) * 0.5, 2)


class FixtureProvider:
    async def fetch_ohlcv(self, symbol: str, days: int) -> list[PriceRow]:
        prices = _SYMBOL_DATA.get(symbol.upper(), [])
        n = min(len(prices), days)
        today = date.today()
        return [
            PriceRow(
                date=(today - timedelta(days=n - 1 - i)).isoformat(),
                close=float(close),
            )
            for i, close in enumerate(prices[-n:])
        ]

    async def fetch_quotes(self, symbols: list[str]) -> list[QuoteRow]:
        """Return deterministic fake current quotes for the given symbols."""
        now = datetime.now(UTC)
        result = []
        for sym in symbols:
            prices = _SYMBOL_DATA.get(sym.upper(), [])
            if not prices:
                continue
            price = float(prices[-1])
            result.append(
                QuoteRow(
                    symbol=sym.upper(),
                    price_usd=price,
                    market_cap_usd=round(price * 18_000_000, 2),
                    volume_24h_usd=round(price * 1_500_000, 2),
                    change_24h_pct=_fixture_change_pct(sym),
                    ts=now,
                )
            )
        return result

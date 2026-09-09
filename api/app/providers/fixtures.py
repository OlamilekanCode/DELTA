from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

from app.providers.base import PriceRow, QuoteRow

if TYPE_CHECKING:
    from app.services.intraday import IntradayObservation

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

# Holder-tier stocks
_RAW_AMZN = _derived(_RAW_NVDA, 220.0, seed=50, noise_amp=0.02)
_RAW_GOOGL = _derived(_RAW_NVDA, 195.0, seed=51, noise_amp=0.02)
_RAW_AAPL = _derived(_RAW_NVDA, 235.0, seed=52, noise_amp=0.015)
_RAW_INTC = _derived(_RAW_NVDA, 32.0, seed=53, noise_amp=0.035)
_RAW_QCOM = _derived(_RAW_NVDA, 165.0, seed=54, noise_amp=0.025)
_RAW_MU = _derived(_RAW_NVDA, 115.0, seed=55, noise_amp=0.035)
_RAW_SMCI = _derived(_RAW_NVDA, 45.0, seed=56, noise_amp=0.06)
_RAW_HOOD = _derived(_RAW_BTC, 38.0, seed=57, noise_amp=0.05)
_RAW_RIOT = _derived(_RAW_BTC, 12.0, seed=58, noise_amp=0.07)
_RAW_MARA = _derived(_RAW_BTC, 18.0, seed=59, noise_amp=0.07)
_RAW_CLSK = _derived(_RAW_BTC, 14.0, seed=60, noise_amp=0.075)
_RAW_WULF = _derived(_RAW_BTC, 6.0, seed=61, noise_amp=0.08)

# Holder-tier crypto — Layer 1 (additional)
_RAW_TON = _derived(_RAW_BTC, 5.5, seed=62)
_RAW_ATOM = _derived(_RAW_ETH, 7.0, seed=63)
_RAW_ALGO = _derived(_RAW_ETH, 0.18, seed=64)
_RAW_XLM = _derived(_RAW_BTC, 0.13, seed=65)
_RAW_XTZ = _derived(_RAW_ETH, 0.9, seed=66)
_RAW_EOS = _derived(_RAW_BTC, 0.7, seed=67)
_RAW_FLOW = _derived(_RAW_ETH, 0.6, seed=68)
_RAW_KAS = _derived(_RAW_BTC, 0.14, seed=69)
_RAW_SEI = _derived(_RAW_ETH, 0.35, seed=70)
_RAW_TIA = _derived(_RAW_BTC, 5.0, seed=71)
_RAW_EGLD = _derived(_RAW_ETH, 28.0, seed=72)
_RAW_KAVA = _derived(_RAW_ETH, 0.45, seed=73)

# Holder-tier crypto — Layer 2 / Scaling
_RAW_STRK = _derived(_RAW_ETH, 0.5, seed=74)
_RAW_ZK = _derived(_RAW_ETH, 0.1, seed=75)
_RAW_MNT = _derived(_RAW_ETH, 0.9, seed=76)
_RAW_METIS = _derived(_RAW_ETH, 35.0, seed=77)
_RAW_MANTA = _derived(_RAW_ETH, 0.4, seed=78)
_RAW_BOBA = _derived(_RAW_ETH, 0.15, seed=79)

# Holder-tier crypto — Interoperability
_RAW_AXL = _derived(_RAW_ETH, 0.7, seed=80)
_RAW_ZRO = _derived(_RAW_ETH, 3.5, seed=81)
_RAW_W = _derived(_RAW_ETH, 0.25, seed=82)
_RAW_QNT = _derived(_RAW_ETH, 110.0, seed=83)
_RAW_REN = _derived(_RAW_ETH, 0.05, seed=84)
_RAW_SYN = _derived(_RAW_ETH, 0.3, seed=85)

# Holder-tier crypto — DeFi (additional)
_RAW_MKR = _derived(_RAW_ETH, 1500.0, seed=86, noise_amp=0.03)
_RAW_CRV = _derived(_RAW_ETH, 0.6, seed=87)
_RAW_LDO = _derived(_RAW_ETH, 1.1, seed=88)
_RAW_SNX = _derived(_RAW_ETH, 2.0, seed=89)
_RAW_COMP = _derived(_RAW_ETH, 55.0, seed=90)
_RAW_SUSHI = _derived(_RAW_ETH, 0.9, seed=91)
_RAW_CAKE = _derived(_RAW_ETH, 2.2, seed=92)
_RAW_1INCH = _derived(_RAW_ETH, 0.3, seed=93)
_RAW_DYDX = _derived(_RAW_ETH, 1.2, seed=94)
_RAW_PENDLE = _derived(_RAW_ETH, 4.5, seed=95)

# Holder-tier crypto — GameFi
_RAW_AXS = _derived(_RAW_ETH, 5.5, seed=96, noise_amp=0.06)
_RAW_SAND = _derived(_RAW_ETH, 0.35, seed=97)
_RAW_MANA = _derived(_RAW_ETH, 0.35, seed=98)
_RAW_GALA = _derived(_RAW_ETH, 0.03, seed=99)
_RAW_IMX = _derived(_RAW_ETH, 1.3, seed=100)
_RAW_ENJ = _derived(_RAW_ETH, 0.2, seed=101)
_RAW_ILV = _derived(_RAW_ETH, 45.0, seed=102, noise_amp=0.06)
_RAW_BEAM = _derived(_RAW_ETH, 0.015, seed=103)

# Holder-tier crypto — RWA
_RAW_ONDO = _derived(_RAW_ETH, 1.1, seed=104)
_RAW_POLYX = _derived(_RAW_ETH, 0.25, seed=105)
_RAW_CFG = _derived(_RAW_ETH, 0.4, seed=106)
_RAW_RSR = _derived(_RAW_BTC, 0.008, seed=107)
_RAW_TRU = _derived(_RAW_ETH, 0.1, seed=108)
_RAW_OM = _derived(_RAW_ETH, 0.8, seed=109)

# Holder-tier crypto — Oracle/Data (additional)
_RAW_PYTH = _derived(_RAW_ETH, 0.3, seed=110)
_RAW_BAND = _derived(_RAW_ETH, 1.3, seed=111)
_RAW_API3 = _derived(_RAW_ETH, 1.8, seed=112)

# Holder-tier crypto — AI/Compute (additional)
_RAW_WLD = _derived(_RAW_BTC, 1.8, seed=113, noise_amp=0.05)
_RAW_OCEAN = _derived(_RAW_ETH, 0.5, seed=114)
_RAW_NMR = _derived(_RAW_ETH, 18.0, seed=115)
_RAW_ARKM = _derived(_RAW_ETH, 1.5, seed=116)
_RAW_IO = _derived(_RAW_BTC, 2.5, seed=117, noise_amp=0.05)

# Holder-tier crypto — Storage (additional)
_RAW_STORJ = _derived(_RAW_ETH, 0.4, seed=118)

# Holder-tier crypto — Privacy
_RAW_ZEC = _derived(_RAW_BTC, 45.0, seed=119)
_RAW_XMR = _derived(_RAW_BTC, 160.0, seed=120)
_RAW_SCRT = _derived(_RAW_ETH, 0.25, seed=121)

# Holder-tier crypto — Memecoin (additional)
_RAW_SHIB = _derived(_RAW_BTC, 0.000018, seed=122, noise_amp=0.08)
_RAW_FLOKI = _derived(_RAW_BTC, 0.00015, seed=123, noise_amp=0.08)
_RAW_BONK = _derived(_RAW_BTC, 0.000022, seed=124, noise_amp=0.09)
_RAW_WIF = _derived(_RAW_BTC, 1.8, seed=125, noise_amp=0.08)

# Holder-tier crypto — Exchange tokens
_RAW_CRO = _derived(_RAW_BTC, 0.12, seed=126)
_RAW_LEO = _derived(_RAW_BTC, 5.8, seed=127, noise_amp=0.015)

# Holder-tier crypto — Legacy Layer 1
_RAW_LTC = _derived(_RAW_BTC, 95.0, seed=128)
_RAW_BCH = _derived(_RAW_BTC, 380.0, seed=129)

# Holder-tier crypto — Liquid staking
_RAW_RPL = _derived(_RAW_ETH, 15.0, seed=130)
_RAW_ETHFI = _derived(_RAW_ETH, 1.6, seed=131)

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
    "AMZN": _RAW_AMZN,
    "GOOGL": _RAW_GOOGL,
    "AAPL": _RAW_AAPL,
    "INTC": _RAW_INTC,
    "QCOM": _RAW_QCOM,
    "MU": _RAW_MU,
    "SMCI": _RAW_SMCI,
    "HOOD": _RAW_HOOD,
    "RIOT": _RAW_RIOT,
    "MARA": _RAW_MARA,
    "CLSK": _RAW_CLSK,
    "WULF": _RAW_WULF,
    "TON": _RAW_TON,
    "ATOM": _RAW_ATOM,
    "ALGO": _RAW_ALGO,
    "XLM": _RAW_XLM,
    "XTZ": _RAW_XTZ,
    "EOS": _RAW_EOS,
    "FLOW": _RAW_FLOW,
    "KAS": _RAW_KAS,
    "SEI": _RAW_SEI,
    "TIA": _RAW_TIA,
    "EGLD": _RAW_EGLD,
    "KAVA": _RAW_KAVA,
    "STRK": _RAW_STRK,
    "ZK": _RAW_ZK,
    "MNT": _RAW_MNT,
    "METIS": _RAW_METIS,
    "MANTA": _RAW_MANTA,
    "BOBA": _RAW_BOBA,
    "AXL": _RAW_AXL,
    "ZRO": _RAW_ZRO,
    "W": _RAW_W,
    "QNT": _RAW_QNT,
    "REN": _RAW_REN,
    "SYN": _RAW_SYN,
    "MKR": _RAW_MKR,
    "CRV": _RAW_CRV,
    "LDO": _RAW_LDO,
    "SNX": _RAW_SNX,
    "COMP": _RAW_COMP,
    "SUSHI": _RAW_SUSHI,
    "CAKE": _RAW_CAKE,
    "1INCH": _RAW_1INCH,
    "DYDX": _RAW_DYDX,
    "PENDLE": _RAW_PENDLE,
    "AXS": _RAW_AXS,
    "SAND": _RAW_SAND,
    "MANA": _RAW_MANA,
    "GALA": _RAW_GALA,
    "IMX": _RAW_IMX,
    "ENJ": _RAW_ENJ,
    "ILV": _RAW_ILV,
    "BEAM": _RAW_BEAM,
    "ONDO": _RAW_ONDO,
    "POLYX": _RAW_POLYX,
    "CFG": _RAW_CFG,
    "RSR": _RAW_RSR,
    "TRU": _RAW_TRU,
    "OM": _RAW_OM,
    "PYTH": _RAW_PYTH,
    "BAND": _RAW_BAND,
    "API3": _RAW_API3,
    "WLD": _RAW_WLD,
    "OCEAN": _RAW_OCEAN,
    "NMR": _RAW_NMR,
    "ARKM": _RAW_ARKM,
    "IO": _RAW_IO,
    "STORJ": _RAW_STORJ,
    "ZEC": _RAW_ZEC,
    "XMR": _RAW_XMR,
    "SCRT": _RAW_SCRT,
    "SHIB": _RAW_SHIB,
    "FLOKI": _RAW_FLOKI,
    "BONK": _RAW_BONK,
    "WIF": _RAW_WIF,
    "CRO": _RAW_CRO,
    "LEO": _RAW_LEO,
    "LTC": _RAW_LTC,
    "BCH": _RAW_BCH,
    "RPL": _RAW_RPL,
    "ETHFI": _RAW_ETHFI,
}

FIXTURE_ASSETS: list[dict] = [
    # Stocks — free tier
    {"symbol": "NVDA", "name": "NVIDIA Corporation",    "asset_type": "stock",  "category": "Technology",   "access": "free",   "coingecko_id": None},
    {"symbol": "TSLA", "name": "Tesla Inc.",             "asset_type": "stock",  "category": "Technology",   "access": "free",   "coingecko_id": None},
    {"symbol": "COIN", "name": "Coinbase Global Inc.",   "asset_type": "stock",  "category": "Finance",      "access": "free",   "coingecko_id": None},
    {"symbol": "MSTR", "name": "MicroStrategy Inc.",     "asset_type": "stock",  "category": "Finance",      "access": "free",   "coingecko_id": None},
    {"symbol": "AMD",  "name": "Advanced Micro Devices", "asset_type": "stock",  "category": "Technology",   "access": "free",   "coingecko_id": None},
    {"symbol": "MSFT", "name": "Microsoft Corporation",  "asset_type": "stock",  "category": "Technology",   "access": "free",   "coingecko_id": None},
    {"symbol": "META", "name": "Meta Platforms Inc.",    "asset_type": "stock",  "category": "Technology",   "access": "free",   "coingecko_id": None},
    {"symbol": "PLTR", "name": "Palantir Technologies",  "asset_type": "stock",  "category": "Technology",   "access": "free",   "coingecko_id": None},
    # Crypto — Layer 1 — free tier
    {"symbol": "BTC",  "name": "Bitcoin",                "asset_type": "crypto", "category": "Layer 1",      "access": "free",   "coingecko_id": "bitcoin"},
    {"symbol": "ETH",  "name": "Ethereum",               "asset_type": "crypto", "category": "Layer 1",      "access": "free",   "coingecko_id": "ethereum"},
    {"symbol": "SOL",  "name": "Solana",                 "asset_type": "crypto", "category": "Layer 1",      "access": "free",   "coingecko_id": "solana"},
    {"symbol": "BNB",  "name": "BNB",                    "asset_type": "crypto", "category": "Layer 1",      "access": "free",   "coingecko_id": "binancecoin"},
    {"symbol": "XRP",  "name": "XRP",                    "asset_type": "crypto", "category": "Layer 1",      "access": "free",   "coingecko_id": "ripple"},
    {"symbol": "ADA",  "name": "Cardano",                "asset_type": "crypto", "category": "Layer 1",      "access": "free",   "coingecko_id": "cardano"},
    {"symbol": "AVAX", "name": "Avalanche",              "asset_type": "crypto", "category": "Layer 1",      "access": "free",   "coingecko_id": "avalanche-2"},
    {"symbol": "DOT",  "name": "Polkadot",               "asset_type": "crypto", "category": "Layer 1",      "access": "free",   "coingecko_id": "polkadot"},
    {"symbol": "NEAR", "name": "NEAR Protocol",          "asset_type": "crypto", "category": "Layer 1",      "access": "free",   "coingecko_id": "near"},
    {"symbol": "ICP",  "name": "Internet Computer",      "asset_type": "crypto", "category": "Layer 1",      "access": "free",   "coingecko_id": "internet-computer"},
    {"symbol": "APT",  "name": "Aptos",                  "asset_type": "crypto", "category": "Layer 1",      "access": "free",   "coingecko_id": "aptos"},
    {"symbol": "SUI",  "name": "Sui",                    "asset_type": "crypto", "category": "Layer 1",      "access": "free",   "coingecko_id": "sui"},
    {"symbol": "HBAR", "name": "Hedera",                 "asset_type": "crypto", "category": "Layer 1",      "access": "free",   "coingecko_id": "hedera-hashgraph"},
    # Crypto — Layer 2 — free tier
    {"symbol": "ARB",  "name": "Arbitrum",               "asset_type": "crypto", "category": "Layer 2",      "access": "free",   "coingecko_id": "arbitrum"},
    {"symbol": "OP",   "name": "Optimism",               "asset_type": "crypto", "category": "Layer 2",      "access": "free",   "coingecko_id": "optimism"},
    {"symbol": "POL",  "name": "Polygon",                "asset_type": "crypto", "category": "Layer 2",      "access": "free",   "coingecko_id": "polygon-ecosystem-token"},
    # Crypto — DeFi — free tier
    {"symbol": "UNI",  "name": "Uniswap",                "asset_type": "crypto", "category": "DeFi",         "access": "free",   "coingecko_id": "uniswap"},
    {"symbol": "AAVE", "name": "Aave",                   "asset_type": "crypto", "category": "DeFi",         "access": "free",   "coingecko_id": "aave"},
    {"symbol": "INJ",  "name": "Injective",              "asset_type": "crypto", "category": "DeFi",         "access": "free",   "coingecko_id": "injective-protocol"},
    # Crypto — Oracle/Data — free tier
    {"symbol": "LINK", "name": "Chainlink",              "asset_type": "crypto", "category": "Oracle/Data",  "access": "free",   "coingecko_id": "chainlink"},
    {"symbol": "GRT",  "name": "The Graph",              "asset_type": "crypto", "category": "Oracle/Data",  "access": "free",   "coingecko_id": "the-graph"},
    # Crypto — AI/Compute — free tier
    {"symbol": "TAO",    "name": "Bittensor",            "asset_type": "crypto", "category": "AI/Compute",   "access": "free",   "coingecko_id": "bittensor"},
    {"symbol": "RENDER", "name": "Render",               "asset_type": "crypto", "category": "AI/Compute",   "access": "free",   "coingecko_id": "render-token"},
    {"symbol": "FET",    "name": "Fetch.ai",             "asset_type": "crypto", "category": "AI/Compute",   "access": "free",   "coingecko_id": "fetch-ai"},
    {"symbol": "AKT",    "name": "Akash Network",        "asset_type": "crypto", "category": "AI/Compute",   "access": "free",   "coingecko_id": "akash-network"},
    {"symbol": "AIOZ",   "name": "AIOZ Network",         "asset_type": "crypto", "category": "AI/Compute",   "access": "free",   "coingecko_id": "aioz-network"},
    # Crypto — Storage — free tier
    {"symbol": "FIL",  "name": "Filecoin",               "asset_type": "crypto", "category": "Storage",      "access": "free",   "coingecko_id": "filecoin"},
    {"symbol": "AR",   "name": "Arweave",                "asset_type": "crypto", "category": "Storage",      "access": "free",   "coingecko_id": "arweave"},
    # Crypto — Memecoin — free tier
    {"symbol": "DOGE", "name": "Dogecoin",               "asset_type": "crypto", "category": "Memecoin",     "access": "free",   "coingecko_id": "dogecoin"},
    {"symbol": "PEPE", "name": "Pepe",                   "asset_type": "crypto", "category": "Memecoin",     "access": "free",   "coingecko_id": "pepe"},
    # Stocks — holder tier
    {"symbol": "AMZN", "name": "Amazon.com Inc.",        "asset_type": "stock",  "category": "Technology",     "access": "holder", "coingecko_id": None},
    {"symbol": "GOOGL","name": "Alphabet Inc.",          "asset_type": "stock",  "category": "Technology",     "access": "holder", "coingecko_id": None},
    {"symbol": "AAPL", "name": "Apple Inc.",             "asset_type": "stock",  "category": "Technology",     "access": "holder", "coingecko_id": None},
    {"symbol": "INTC", "name": "Intel Corporation",      "asset_type": "stock",  "category": "Technology",     "access": "holder", "coingecko_id": None},
    {"symbol": "QCOM", "name": "Qualcomm Inc.",          "asset_type": "stock",  "category": "Technology",     "access": "holder", "coingecko_id": None},
    {"symbol": "MU",   "name": "Micron Technology",      "asset_type": "stock",  "category": "Technology",     "access": "holder", "coingecko_id": None},
    {"symbol": "SMCI", "name": "Super Micro Computer",   "asset_type": "stock",  "category": "Technology",     "access": "holder", "coingecko_id": None},
    {"symbol": "HOOD", "name": "Robinhood Markets Inc.", "asset_type": "stock",  "category": "Finance",        "access": "holder", "coingecko_id": None},
    {"symbol": "RIOT", "name": "Riot Platforms Inc.",    "asset_type": "stock",  "category": "Crypto Mining",  "access": "holder", "coingecko_id": None},
    {"symbol": "MARA", "name": "MARA Holdings Inc.",     "asset_type": "stock",  "category": "Crypto Mining",  "access": "holder", "coingecko_id": None},
    {"symbol": "CLSK", "name": "CleanSpark Inc.",        "asset_type": "stock",  "category": "Crypto Mining",  "access": "holder", "coingecko_id": None},
    {"symbol": "WULF", "name": "TeraWulf Inc.",          "asset_type": "stock",  "category": "Crypto Mining",  "access": "holder", "coingecko_id": None},
    # Crypto — Layer 1 (additional) — holder tier
    {"symbol": "TON",  "name": "Toncoin",                "asset_type": "crypto", "category": "Layer 1",      "access": "holder", "coingecko_id": "the-open-network"},
    {"symbol": "ATOM", "name": "Cosmos Hub",             "asset_type": "crypto", "category": "Layer 1",      "access": "holder", "coingecko_id": "cosmos"},
    {"symbol": "ALGO", "name": "Algorand",               "asset_type": "crypto", "category": "Layer 1",      "access": "holder", "coingecko_id": "algorand"},
    {"symbol": "XLM",  "name": "Stellar",                "asset_type": "crypto", "category": "Layer 1",      "access": "holder", "coingecko_id": "stellar"},
    {"symbol": "XTZ",  "name": "Tezos",                  "asset_type": "crypto", "category": "Layer 1",      "access": "holder", "coingecko_id": "tezos"},
    {"symbol": "EOS",  "name": "EOS",                    "asset_type": "crypto", "category": "Layer 1",      "access": "holder", "coingecko_id": "eos"},
    {"symbol": "FLOW", "name": "Flow",                   "asset_type": "crypto", "category": "Layer 1",      "access": "holder", "coingecko_id": "flow"},
    {"symbol": "KAS",  "name": "Kaspa",                  "asset_type": "crypto", "category": "Layer 1",      "access": "holder", "coingecko_id": "kaspa"},
    {"symbol": "SEI",  "name": "Sei",                    "asset_type": "crypto", "category": "Layer 1",      "access": "holder", "coingecko_id": "sei-network"},
    {"symbol": "TIA",  "name": "Celestia",               "asset_type": "crypto", "category": "Layer 1",      "access": "holder", "coingecko_id": "celestia"},
    {"symbol": "EGLD", "name": "MultiversX",             "asset_type": "crypto", "category": "Layer 1",      "access": "holder", "coingecko_id": "elrond-erd-2"},
    {"symbol": "KAVA", "name": "Kava",                   "asset_type": "crypto", "category": "Layer 1",      "access": "holder", "coingecko_id": "kava"},
    # Crypto — Layer 2 / Scaling — holder tier
    {"symbol": "STRK", "name": "Starknet",               "asset_type": "crypto", "category": "Layer 2",      "access": "holder", "coingecko_id": "starknet"},
    {"symbol": "ZK",   "name": "ZKsync",                 "asset_type": "crypto", "category": "Layer 2",      "access": "holder", "coingecko_id": "zksync"},
    {"symbol": "MNT",  "name": "Mantle",                 "asset_type": "crypto", "category": "Layer 2",      "access": "holder", "coingecko_id": "mantle"},
    {"symbol": "METIS","name": "Metis",                  "asset_type": "crypto", "category": "Layer 2",      "access": "holder", "coingecko_id": "metis-token"},
    {"symbol": "MANTA","name": "Manta Network",          "asset_type": "crypto", "category": "Layer 2",      "access": "holder", "coingecko_id": "manta-network"},
    {"symbol": "BOBA", "name": "Boba Network",           "asset_type": "crypto", "category": "Layer 2",      "access": "holder", "coingecko_id": "boba-network"},
    # Crypto — Interoperability — holder tier
    {"symbol": "AXL",  "name": "Axelar",                 "asset_type": "crypto", "category": "Interoperability", "access": "holder", "coingecko_id": "axelar"},
    {"symbol": "ZRO",  "name": "LayerZero",              "asset_type": "crypto", "category": "Interoperability", "access": "holder", "coingecko_id": "layerzero"},
    {"symbol": "W",    "name": "Wormhole",                "asset_type": "crypto", "category": "Interoperability", "access": "holder", "coingecko_id": "wormhole"},
    {"symbol": "QNT",  "name": "Quant",                  "asset_type": "crypto", "category": "Interoperability", "access": "holder", "coingecko_id": "quant-network"},
    {"symbol": "REN",  "name": "Ren",                    "asset_type": "crypto", "category": "Interoperability", "access": "holder", "coingecko_id": "republic-protocol"},
    {"symbol": "SYN",  "name": "Synapse",                "asset_type": "crypto", "category": "Interoperability", "access": "holder", "coingecko_id": "synapse-2"},
    # Crypto — DeFi (additional) — holder tier
    {"symbol": "MKR",    "name": "Maker",                "asset_type": "crypto", "category": "DeFi",         "access": "holder", "coingecko_id": "maker"},
    {"symbol": "CRV",    "name": "Curve DAO Token",      "asset_type": "crypto", "category": "DeFi",         "access": "holder", "coingecko_id": "curve-dao-token"},
    {"symbol": "LDO",    "name": "Lido DAO",             "asset_type": "crypto", "category": "DeFi",         "access": "holder", "coingecko_id": "lido-dao"},
    {"symbol": "SNX",    "name": "Synthetix",            "asset_type": "crypto", "category": "DeFi",         "access": "holder", "coingecko_id": "havven"},
    {"symbol": "COMP",   "name": "Compound",             "asset_type": "crypto", "category": "DeFi",         "access": "holder", "coingecko_id": "compound-governance-token"},
    {"symbol": "SUSHI",  "name": "Sushi",                "asset_type": "crypto", "category": "DeFi",         "access": "holder", "coingecko_id": "sushi"},
    {"symbol": "CAKE",   "name": "PancakeSwap",          "asset_type": "crypto", "category": "DeFi",         "access": "holder", "coingecko_id": "pancakeswap-token"},
    {"symbol": "1INCH",  "name": "1inch",                "asset_type": "crypto", "category": "DeFi",         "access": "holder", "coingecko_id": "1inch"},
    {"symbol": "DYDX",   "name": "dYdX",                 "asset_type": "crypto", "category": "DeFi",         "access": "holder", "coingecko_id": "dydx-chain"},
    {"symbol": "PENDLE", "name": "Pendle",               "asset_type": "crypto", "category": "DeFi",         "access": "holder", "coingecko_id": "pendle"},
    # Crypto — GameFi — holder tier
    {"symbol": "AXS",  "name": "Axie Infinity",          "asset_type": "crypto", "category": "GameFi",       "access": "holder", "coingecko_id": "axie-infinity"},
    {"symbol": "SAND", "name": "The Sandbox",            "asset_type": "crypto", "category": "GameFi",       "access": "holder", "coingecko_id": "the-sandbox"},
    {"symbol": "MANA", "name": "Decentraland",           "asset_type": "crypto", "category": "GameFi",       "access": "holder", "coingecko_id": "decentraland"},
    {"symbol": "GALA", "name": "Gala",                   "asset_type": "crypto", "category": "GameFi",       "access": "holder", "coingecko_id": "gala"},
    {"symbol": "IMX",  "name": "Immutable",              "asset_type": "crypto", "category": "GameFi",       "access": "holder", "coingecko_id": "immutable-x"},
    {"symbol": "ENJ",  "name": "Enjin Coin",             "asset_type": "crypto", "category": "GameFi",       "access": "holder", "coingecko_id": "enjincoin"},
    {"symbol": "ILV",  "name": "Illuvium",               "asset_type": "crypto", "category": "GameFi",       "access": "holder", "coingecko_id": "illuvium"},
    {"symbol": "BEAM", "name": "Beam",                   "asset_type": "crypto", "category": "GameFi",       "access": "holder", "coingecko_id": "beam-2"},
    # Crypto — RWA — holder tier
    {"symbol": "ONDO",  "name": "Ondo",                  "asset_type": "crypto", "category": "RWA",          "access": "holder", "coingecko_id": "ondo-finance"},
    {"symbol": "POLYX", "name": "Polymesh",               "asset_type": "crypto", "category": "RWA",          "access": "holder", "coingecko_id": "polymesh"},
    {"symbol": "CFG",   "name": "Centrifuge",             "asset_type": "crypto", "category": "RWA",          "access": "holder", "coingecko_id": "centrifuge"},
    {"symbol": "RSR",   "name": "Reserve Rights",         "asset_type": "crypto", "category": "RWA",          "access": "holder", "coingecko_id": "reserve-rights-token"},
    {"symbol": "TRU",   "name": "TrueFi",                 "asset_type": "crypto", "category": "RWA",          "access": "holder", "coingecko_id": "truefi"},
    {"symbol": "OM",    "name": "MANTRA",                 "asset_type": "crypto", "category": "RWA",          "access": "holder", "coingecko_id": "mantra-dao"},
    # Crypto — Oracle/Data (additional) — holder tier
    {"symbol": "PYTH", "name": "Pyth Network",           "asset_type": "crypto", "category": "Oracle/Data",  "access": "holder", "coingecko_id": "pyth-network"},
    {"symbol": "BAND", "name": "Band Protocol",          "asset_type": "crypto", "category": "Oracle/Data",  "access": "holder", "coingecko_id": "band-protocol"},
    {"symbol": "API3", "name": "API3",                   "asset_type": "crypto", "category": "Oracle/Data",  "access": "holder", "coingecko_id": "api3"},
    # Crypto — AI/Compute (additional) — holder tier
    {"symbol": "WLD",   "name": "Worldcoin",             "asset_type": "crypto", "category": "AI/Compute",   "access": "holder", "coingecko_id": "worldcoin-wld"},
    {"symbol": "OCEAN", "name": "Ocean Protocol",        "asset_type": "crypto", "category": "AI/Compute",   "access": "holder", "coingecko_id": "ocean-protocol"},
    {"symbol": "NMR",   "name": "Numeraire",             "asset_type": "crypto", "category": "AI/Compute",   "access": "holder", "coingecko_id": "numeraire"},
    {"symbol": "ARKM",  "name": "Arkham",                "asset_type": "crypto", "category": "AI/Compute",   "access": "holder", "coingecko_id": "arkham"},
    {"symbol": "IO",    "name": "io.net",                "asset_type": "crypto", "category": "AI/Compute",   "access": "holder", "coingecko_id": "io-net"},
    # Crypto — Storage (additional) — holder tier
    {"symbol": "STORJ", "name": "Storj",                 "asset_type": "crypto", "category": "Storage",      "access": "holder", "coingecko_id": "storj"},
    # Crypto — Privacy — holder tier
    {"symbol": "ZEC",  "name": "Zcash",                  "asset_type": "crypto", "category": "Privacy",      "access": "holder", "coingecko_id": "zcash"},
    {"symbol": "XMR",  "name": "Monero",                 "asset_type": "crypto", "category": "Privacy",      "access": "holder", "coingecko_id": "monero"},
    {"symbol": "SCRT", "name": "Secret",                 "asset_type": "crypto", "category": "Privacy",      "access": "holder", "coingecko_id": "secret"},
    # Crypto — Memecoin (additional) — holder tier
    {"symbol": "SHIB",  "name": "Shiba Inu",             "asset_type": "crypto", "category": "Memecoin",     "access": "holder", "coingecko_id": "shiba-inu"},
    {"symbol": "FLOKI", "name": "FLOKI",                 "asset_type": "crypto", "category": "Memecoin",     "access": "holder", "coingecko_id": "floki"},
    {"symbol": "BONK",  "name": "Bonk",                  "asset_type": "crypto", "category": "Memecoin",     "access": "holder", "coingecko_id": "bonk"},
    {"symbol": "WIF",   "name": "dogwifhat",             "asset_type": "crypto", "category": "Memecoin",     "access": "holder", "coingecko_id": "dogwifcoin"},
    # Crypto — Exchange tokens — holder tier
    {"symbol": "CRO", "name": "Cronos",                  "asset_type": "crypto", "category": "Exchange",     "access": "holder", "coingecko_id": "crypto-com-chain"},
    {"symbol": "LEO", "name": "UNUS SED LEO",            "asset_type": "crypto", "category": "Exchange",     "access": "holder", "coingecko_id": "leo-token"},
    # Crypto — Legacy Layer 1 — holder tier
    {"symbol": "LTC", "name": "Litecoin",                "asset_type": "crypto", "category": "Layer 1",      "access": "holder", "coingecko_id": "litecoin"},
    {"symbol": "BCH", "name": "Bitcoin Cash",            "asset_type": "crypto", "category": "Layer 1",      "access": "holder", "coingecko_id": "bitcoin-cash"},
    # Crypto — Liquid staking — holder tier
    {"symbol": "RPL",   "name": "Rocket Pool",           "asset_type": "crypto", "category": "Liquid Staking", "access": "holder", "coingecko_id": "rocket-pool"},
    {"symbol": "ETHFI", "name": "Ether.fi",              "asset_type": "crypto", "category": "Liquid Staking", "access": "holder", "coingecko_id": "ether-fi"},

    # Stablecoins — asset_type "stablecoin" (never "crypto"), so they are
    # structurally excluded from every crypto-specific pipeline (correlation
    # scoring, the public asset explorer, catalogue-sync coingecko matching)
    # without needing scattered special-case symbol checks. Portfolio
    # holdings of these are valued at a flat $1.00/unit and reported as cash
    # (see services/portfolio.py) — they never need daily price history.
    {"symbol": "USDC", "name": "USD Coin",   "asset_type": "stablecoin", "category": "Stablecoin", "access": "holder", "coingecko_id": None},
    {"symbol": "USDT", "name": "Tether",     "asset_type": "stablecoin", "category": "Stablecoin", "access": "holder", "coingecko_id": None},
    {"symbol": "USDG", "name": "Global Dollar", "asset_type": "stablecoin", "category": "Stablecoin", "access": "holder", "coingecko_id": None},
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
                adj_close=float(close),
            )
            for i, close in enumerate(prices[-n:])
        ]

    # Crypto demo candles span this many trailing calendar days of
    # continuous 24/7 buckets — comparable calendar coverage to the stock
    # side's MAX_SESSIONS trading sessions (~28 calendar days for 20
    # sessions), but continuous rather than session-bounded.
    _CRYPTO_DEMO_DAYS = 30

    async def fetch_intraday(self, symbol: str, asset_type: str = "stock") -> list["IntradayObservation"]:
        """Synthesize a full window of 30-min buckets deterministically so demo
        mode is immediately ready (collecting_data=False) instead of requiring
        real-time accumulation.

        Stocks use XNYS trading sessions (matches how real Marketstack candles
        are bounded). Crypto trades continuously, so it uses a rolling window
        of calendar days instead — using session bounds here would silently
        leave demo crypto data with the same nights/weekends gaps real crypto
        candles never have.
        """
        from app.services.intraday import (
            MAX_SESSIONS,
            MIN_SAMPLE_COUNT,
            IntradayObservation,
            floor_to_bucket,
        )
        from app.services.market_calendar import recent_session_dates, session_open_close

        prices = _SYMBOL_DATA.get(symbol.upper(), [])
        if not prices:
            return []
        base_price = float(prices[-1])
        seed_base = sum(ord(c) for c in symbol.upper())

        observations: list[IntradayObservation] = []

        if asset_type == "crypto":
            now = datetime.now(UTC)
            window_end = floor_to_bucket(now)
            bucket_start = window_end - timedelta(days=self._CRYPTO_DEMO_DAYS)
            bucket_idx = 0
            while bucket_start < window_end:
                for sample_idx in range(MIN_SAMPLE_COUNT):
                    sample_ts = bucket_start + timedelta(minutes=10 * sample_idx)
                    noise = _noise(seed_base, bucket_idx * MIN_SAMPLE_COUNT + sample_idx, 0.01)
                    observations.append(
                        IntradayObservation(ts=sample_ts, price=round(base_price * noise, 8))
                    )
                bucket_start += timedelta(minutes=30)
                bucket_idx += 1
            return observations

        for day_idx, session_date in enumerate(recent_session_dates(count=MAX_SESSIONS)):
            session_open, session_close = session_open_close(session_date)
            bucket_start = session_open
            bucket_idx = 0
            while bucket_start < session_close:
                for sample_idx in range(MIN_SAMPLE_COUNT):
                    sample_ts = bucket_start + timedelta(minutes=10 * sample_idx)
                    noise = _noise(seed_base + day_idx, bucket_idx * MIN_SAMPLE_COUNT + sample_idx, 0.01)
                    observations.append(
                        IntradayObservation(ts=sample_ts, price=round(base_price * noise, 8))
                    )
                bucket_start += timedelta(minutes=30)
                bucket_idx += 1
        return observations

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

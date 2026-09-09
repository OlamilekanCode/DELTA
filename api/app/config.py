from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite+aiosqlite:///./dev.db"
    cors_origins: str = "http://localhost:3000"
    session_secret: str = "change-me-to-a-random-64-char-string"

    # SIWE identity policy — deliberately separate from CORS. CORS controls
    # which browser origins may call the API at all; these control which
    # domain/URI values a SIWE message is allowed to assert. Left unset,
    # they default to the CORS origins for developer convenience — set them
    # explicitly in production to avoid any coupling between the two.
    siwe_allowed_domains: str = ""
    siwe_allowed_uris: str = ""

    marketstack_api_key: str = ""
    coingecko_api_key: str = ""
    coingecko_api_type: str = "demo"  # "demo" | "pro"
    use_demo_data: bool = True

    synthex_chain_id: int = 0
    synthex_token_address: str = ""
    synthex_token_decimals: int = 18
    synthex_holder_min_balance_raw: str = ""

    # Server-only RPC for Robinhood Chain on-chain reads.
    # Never expose this URL to the frontend.
    robinhood_rpc_url: str = ""

    # $SynthEx/ETH purchase verification — all fail-closed until supplied.
    synthex_dex_router_addresses: str = ""  # comma-separated
    synthex_dex_pool_addresses: str = ""  # comma-separated
    synthex_weth_address: str = ""
    synthex_min_confirmations: int = 12
    synthex_token_start_block: int = 0
    eth_usd_max_price_age_minutes: int = 60

    # Portfolio — Robinhood Chain is the primary gate; Ethereum/Base reads
    # stay disabled (their RPCs unconfigured) until explicitly enabled.
    portfolio_chain_ids: str = ""  # comma-separated, e.g. "8453,1"
    ethereum_rpc_url: str = ""
    base_rpc_url: str = ""

    # Multicall3 is deployed at the same well-known address on Ethereum and
    # Base by default (see services/multicall.py) — this only needs setting
    # to add/override a chain, e.g. Robinhood Chain once its Multicall3
    # deployment (if any) is confirmed: "4663:0x...".
    multicall3_address_overrides: str = ""  # comma-separated "chain_id:address" pairs

    cron_secret: str = ""

    # Shared secret between the Next.js BFF and this backend — lets the
    # rate limiter trust an X-Forwarded-Client-IP header (the real
    # browser IP, extracted by the BFF from its own incoming request) only
    # when it actually came from our own BFF, instead of using the raw TCP
    # peer address, which for every BFF-proxied request is Vercel's shared
    # egress IP, not the end user's. Without this secret configured, the
    # header is never trusted and rate limiting falls back to the raw
    # peer address (current behavior) — never a regression, just unfixed.
    bff_shared_secret: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def has_strong_session_secret(self) -> bool:
        weak_defaults = {"change-me-to-a-random-64-char-string", ""}
        return self.session_secret not in weak_defaults and len(self.session_secret) >= 32

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def parsed_siwe_domains(self) -> set[str]:
        from urllib.parse import urlparse

        if self.siwe_allowed_domains:
            return {d.strip() for d in self.siwe_allowed_domains.split(",") if d.strip()}
        return {urlparse(o).netloc or o for o in self.parsed_cors_origins}

    @property
    def parsed_siwe_uris(self) -> set[str]:
        if self.siwe_allowed_uris:
            return {u.strip().rstrip("/") for u in self.siwe_allowed_uris.split(",") if u.strip()}
        return {o.rstrip("/") for o in self.parsed_cors_origins}

    @property
    def parsed_dex_router_addresses(self) -> set[str]:
        return {a.strip().lower() for a in self.synthex_dex_router_addresses.split(",") if a.strip()}

    @property
    def parsed_dex_pool_addresses(self) -> set[str]:
        return {a.strip().lower() for a in self.synthex_dex_pool_addresses.split(",") if a.strip()}

    @property
    def parsed_portfolio_chain_ids(self) -> set[int]:
        return {int(c.strip()) for c in self.portfolio_chain_ids.split(",") if c.strip()}

    @property
    def parsed_multicall3_address_overrides(self) -> dict[int, str]:
        overrides: dict[int, str] = {}
        for entry in self.multicall3_address_overrides.split(","):
            entry = entry.strip()
            if not entry or ":" not in entry:
                continue
            chain_id_str, address = entry.split(":", 1)
            try:
                overrides[int(chain_id_str.strip())] = address.strip().lower()
            except ValueError:
                continue
        return overrides


@lru_cache
def get_settings() -> Settings:
    return Settings()

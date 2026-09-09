"""Shared portfolio constants.

The contract catalogue itself moved to the database — see
models/portfolio_contract.py and services/portfolio_catalog.py — replacing
the static PORTFOLIO_ASSET_CONTRACTS list this module used to hold.
"""

NATIVE = "native"  # sentinel contract_address for a chain's gas token

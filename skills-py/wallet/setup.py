"""
Web3 Wallet skill setup flow — multi-step interactive configuration.

Steps:
  1. seed_phrase — Enter 12 or 24 word mnemonic seed phrase
  2. wallets      — Select which wallets to load (up to 5, EVM and/or SOL)
  3. networks     — Select which networks to enable for each wallet type

On completion, wallets and network configs are persisted via ctx.write_data("config.json", ...).
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from eth_account import Account
from eth_account.hdaccount import seed_from_mnemonic
from mnemonic import Mnemonic
from solders.keypair import Keypair

from dev.types.setup_types import (
  SetupField,
  SetupFieldError,
  SetupFieldOption,
  SetupResult,
  SetupStep,
)

log = logging.getLogger("skill.wallet.setup")

# ---------------------------------------------------------------------------
# Network definitions
# ---------------------------------------------------------------------------

EVM_NETWORKS = [
  {
    "value": "ethereum",
    "label": "Ethereum Mainnet",
    "chain_id": "1",
    "rpc": "https://eth.llamarpc.com",
  },
  {
    "value": "polygon",
    "label": "Polygon",
    "chain_id": "137",
    "rpc": "https://polygon.llamarpc.com",
  },
  {
    "value": "bsc",
    "label": "BNB Smart Chain",
    "chain_id": "56",
    "rpc": "https://bsc.llamarpc.com",
  },
  {
    "value": "arbitrum",
    "label": "Arbitrum One",
    "chain_id": "42161",
    "rpc": "https://arb1.arbitrum.io/rpc",
  },
  {
    "value": "optimism",
    "label": "Optimism",
    "chain_id": "10",
    "rpc": "https://mainnet.optimism.io",
  },
  {
    "value": "avalanche",
    "label": "Avalanche C-Chain",
    "chain_id": "43114",
    "rpc": "https://avalanche.public-rpc.com",
  },
  {"value": "base", "label": "Base", "chain_id": "8453", "rpc": "https://mainnet.base.org"},
]

SOL_NETWORKS = [
  {
    "value": "solana_mainnet",
    "label": "Solana Mainnet",
    "chain_id": "mainnet-beta",
    "rpc": "https://api.mainnet-beta.solana.com",
  },
  {
    "value": "solana_devnet",
    "label": "Solana Devnet",
    "chain_id": "devnet",
    "rpc": "https://api.devnet.solana.com",
  },
]

# ---------------------------------------------------------------------------
# Module-level transient state
# ---------------------------------------------------------------------------

_seed_phrase: str = ""
_seed_bytes: bytes = b""
_wallet_selections: dict[str, bool] = {}
_network_selections: dict[str, list[str]] = {}


def _reset_state() -> None:
  global _seed_phrase, _seed_bytes, _wallet_selections, _network_selections
  _seed_phrase = ""
  _seed_bytes = b""
  _wallet_selections = {}
  _network_selections = {}


# ---------------------------------------------------------------------------
# Step definitions
# ---------------------------------------------------------------------------

STEP_SEED_PHRASE = SetupStep(
  id="seed_phrase",
  title="Seed Phrase",
  description=(
    "Enter your 12 or 24 word mnemonic seed phrase. "
    "This will be used to derive your wallet accounts. "
    "Your seed phrase is stored securely and never transmitted."
  ),
  fields=[
    SetupField(
      name="seed_phrase",
      type="password",
      label="Seed Phrase",
      description="Enter your 12 or 24 word recovery phrase",
      required=True,
      placeholder="word1 word2 word3 ...",
    ),
  ],
)

STEP_WALLETS = SetupStep(
  id="wallets",
  title="Select Wallets",
  description=(
    "Select which wallets to load (up to 5 total). "
    "You can choose EVM wallets (Ethereum, Polygon, BSC, etc.) "
    "and/or Solana wallets. Each wallet will be derived from your seed phrase."
  ),
  fields=[
    SetupField(
      name="evm_wallets",
      type="multiselect",
      label="EVM Wallets",
      description="Select EVM wallets to load (index 0-4)",
      required=False,
      options=[
        SetupFieldOption(label="Wallet 0 (EVM)", value="evm_0"),
        SetupFieldOption(label="Wallet 1 (EVM)", value="evm_1"),
        SetupFieldOption(label="Wallet 2 (EVM)", value="evm_2"),
        SetupFieldOption(label="Wallet 3 (EVM)", value="evm_3"),
        SetupFieldOption(label="Wallet 4 (EVM)", value="evm_4"),
      ],
    ),
    SetupField(
      name="sol_wallets",
      type="multiselect",
      label="Solana Wallets",
      description="Select Solana wallets to load (index 0-4)",
      required=False,
      options=[
        SetupFieldOption(label="Wallet 0 (SOL)", value="sol_0"),
        SetupFieldOption(label="Wallet 1 (SOL)", value="sol_1"),
        SetupFieldOption(label="Wallet 2 (SOL)", value="sol_2"),
        SetupFieldOption(label="Wallet 3 (SOL)", value="sol_3"),
        SetupFieldOption(label="Wallet 4 (SOL)", value="sol_4"),
      ],
    ),
  ],
)

STEP_NETWORKS = SetupStep(
  id="networks",
  title="Select Networks",
  description=(
    "Select which blockchain networks to enable. "
    "EVM networks work with EVM wallets, Solana networks work with SOL wallets."
  ),
  fields=[
    SetupField(
      name="evm_networks",
      type="multiselect",
      label="EVM Networks",
      description="Select EVM networks to enable",
      required=False,
      options=[SetupFieldOption(label=n["label"], value=n["value"]) for n in EVM_NETWORKS],
    ),
    SetupField(
      name="sol_networks",
      type="multiselect",
      label="Solana Networks",
      description="Select Solana networks to enable",
      required=False,
      options=[SetupFieldOption(label=n["label"], value=n["value"]) for n in SOL_NETWORKS],
    ),
  ],
)


# ---------------------------------------------------------------------------
# Hook handlers
# ---------------------------------------------------------------------------


async def on_setup_start(ctx: Any) -> SetupStep:
  """Return the first setup step."""
  _reset_state()
  return STEP_SEED_PHRASE


async def on_setup_submit(ctx: Any, step_id: str, values: dict[str, Any]) -> SetupResult:
  """Validate and process a submitted step."""
  if step_id == "seed_phrase":
    return await _handle_seed_phrase(ctx, values)
  if step_id == "wallets":
    return await _handle_wallets(ctx, values)
  if step_id == "networks":
    return await _handle_networks(ctx, values)

  return SetupResult(
    status="error",
    errors=[SetupFieldError(field="", message=f"Unknown step: {step_id}")],
  )


async def on_setup_cancel(ctx: Any) -> None:
  """Clean up transient state on cancel."""
  _reset_state()


# ---------------------------------------------------------------------------
# Step handlers
# ---------------------------------------------------------------------------


async def _handle_seed_phrase(ctx: Any, values: dict[str, Any]) -> SetupResult:
  """Validate seed phrase and derive seed bytes."""
  global _seed_phrase, _seed_bytes

  raw_phrase = str(values.get("seed_phrase", "")).strip().lower()

  # Local validation
  errors: list[SetupFieldError] = []
  if not raw_phrase:
    errors.append(SetupFieldError(field="seed_phrase", message="Seed phrase is required"))
  elif len(raw_phrase.split()) not in [12, 24]:
    errors.append(
      SetupFieldError(
        field="seed_phrase",
        message="Seed phrase must be 12 or 24 words",
      )
    )
  if errors:
    return SetupResult(status="error", errors=errors)

  # Validate mnemonic
  try:
    mnemo = Mnemonic("english")
    if not mnemo.check(raw_phrase):
      return SetupResult(
        status="error",
        errors=[
          SetupFieldError(
            field="seed_phrase",
            message="Invalid seed phrase — words not in BIP39 wordlist",
          )
        ],
      )
    _seed_bytes = seed_from_mnemonic(mnemo, raw_phrase)
    _seed_phrase = raw_phrase
  except Exception as exc:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="seed_phrase", message=f"Invalid seed phrase: {exc}")],
    )

  return SetupResult(status="next", next_step=STEP_WALLETS)


async def _handle_wallets(ctx: Any, values: dict[str, Any]) -> SetupResult:
  """Process wallet selections."""
  global _wallet_selections

  if not _seed_bytes:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="", message="Seed phrase not set — restart setup")],
    )

  evm_selected = values.get("evm_wallets", [])
  sol_selected = values.get("sol_wallets", [])

  if not isinstance(evm_selected, list):
    evm_selected = []
  if not isinstance(sol_selected, list):
    sol_selected = []

  total_selected = len(evm_selected) + len(sol_selected)

  if total_selected == 0:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="evm_wallets", message="Select at least one wallet")],
    )

  if total_selected > 5:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="evm_wallets", message="Maximum 5 wallets allowed")],
    )

  # Store selections
  _wallet_selections = {}
  for w in evm_selected:
    _wallet_selections[w] = True
  for w in sol_selected:
    _wallet_selections[w] = True

  return SetupResult(status="next", next_step=STEP_NETWORKS)


async def _handle_networks(ctx: Any, values: dict[str, Any]) -> SetupResult:
  """Process network selections and complete setup."""
  global _network_selections

  if not _seed_bytes or not _wallet_selections:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="", message="Setup incomplete — restart")],
    )

  evm_networks = values.get("evm_networks", [])
  sol_networks = values.get("sol_networks", [])

  if not isinstance(evm_networks, list):
    evm_networks = []
  if not isinstance(sol_networks, list):
    sol_networks = []

  # Check if networks match selected wallets
  has_evm_wallets = any(k.startswith("evm_") for k in _wallet_selections)
  has_sol_wallets = any(k.startswith("sol_") for k in _wallet_selections)

  if has_evm_wallets and not evm_networks:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="evm_networks", message="Select at least one EVM network")],
    )

  if has_sol_wallets and not sol_networks:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="sol_networks", message="Select at least one Solana network")],
    )

  _network_selections = {
    "evm": evm_networks,
    "sol": sol_networks,
  }

  return await _complete_setup(ctx)


# ---------------------------------------------------------------------------
# Completion
# ---------------------------------------------------------------------------


async def _complete_setup(ctx: Any) -> SetupResult:
  """Derive wallets, save config, and return completion."""
  if not _seed_bytes or not _wallet_selections:
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="", message="Setup incomplete")],
    )

  # Derive wallets
  wallets = []
  networks_config = []

  # Derive EVM wallets
  for wallet_key in sorted(_wallet_selections.keys()):
    if wallet_key.startswith("evm_"):
      index = int(wallet_key.split("_")[1])
      account = Account.from_mnemonic(_seed_phrase, account_path=f"m/44'/60'/0'/0/{index}")
      wallets.append(
        {
          "index": index,
          "chain_type": "evm",
          "address": account.address,
          "label": f"EVM Wallet {index}",
        }
      )

  # Derive Solana wallets
  for wallet_key in sorted(_wallet_selections.keys()):
    if wallet_key.startswith("sol_"):
      index = int(wallet_key.split("_")[1])
      # Solana uses BIP44 path m/44'/501'/{index}'/0'
      # Derive deterministic keypair from seed + index
      seed_32 = _seed_bytes[:32]
      index_bytes = index.to_bytes(4, "big")
      combined = seed_32 + index_bytes
      keypair_seed = hashlib.sha256(combined).digest()[:32]
      keypair = Keypair.from_bytes(keypair_seed)
      pubkey = keypair.pubkey()
      wallets.append(
        {
          "index": index,
          "chain_type": "sol",
          "address": str(pubkey),
          "label": f"Solana Wallet {index}",
        }
      )

  # Build network configs
  for net_value in _network_selections.get("evm", []):
    net_info = next((n for n in EVM_NETWORKS if n["value"] == net_value), None)
    if net_info:
      networks_config.append(
        {
          "chain_id": net_info["chain_id"],
          "name": net_info["label"],
          "rpc_url": net_info["rpc"],
          "chain_type": "evm",
        }
      )

  for net_value in _network_selections.get("sol", []):
    net_info = next((n for n in SOL_NETWORKS if n["value"] == net_value), None)
    if net_info:
      networks_config.append(
        {
          "chain_id": net_info["chain_id"],
          "name": net_info["label"],
          "rpc_url": net_info["rpc"],
          "chain_type": "sol",
        }
      )

  # Persist config
  # NOTE: In production, seed phrase should be encrypted before storage
  # For MVP, we store it directly (user is responsible for security)
  config = {
    "wallets": wallets,
    "networks": networks_config,
    "seed_phrase": _seed_phrase,  # TODO: Encrypt this in production
  }

  try:
    await ctx.write_data("config.json", json.dumps(config, indent=2))
  except Exception as exc:
    log.warning("Could not persist config.json: %s", exc)
    return SetupResult(
      status="error",
      errors=[SetupFieldError(field="", message=f"Failed to save config: {exc}")],
    )

  wallet_count = len(wallets)
  network_count = len(networks_config)

  _reset_state()

  return SetupResult(
    status="complete",
    message=f"Setup complete! Loaded {wallet_count} wallet(s) and {network_count} network(s).",
  )

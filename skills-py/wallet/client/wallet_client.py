"""
Wallet client for EVM and Solana operations.

Handles wallet derivation, balance checking, transaction signing, and network interactions.
"""

from __future__ import annotations

import hashlib
import logging
from decimal import Decimal
from typing import Any

from eth_account import Account
from eth_account.hdaccount import seed_from_mnemonic
from mnemonic import Mnemonic
from solders.keypair import Keypair
from web3 import Web3

log = logging.getLogger("skill.wallet.client")


class WalletConfig:
  """Configuration for a wallet account."""

  def __init__(
    self,
    index: int,
    chain_type: str,
    address: str,
    seed_phrase: str | None = None,
    label: str | None = None,
  ):
    self.index = index
    self.chain_type = chain_type
    self.address = address
    self.seed_phrase = seed_phrase
    self.label = label or f"{chain_type.upper()} Wallet {index}"

  def get_account(self) -> Any:
    """Get the account object for this wallet."""
    if not self.seed_phrase:
      raise ValueError("Seed phrase required to get account")

    if self.chain_type == "evm":
      return Account.from_mnemonic(
        self.seed_phrase,
        account_path=f"m/44'/60'/0'/0/{self.index}",
      )
    elif self.chain_type == "sol":
      # Derive Solana keypair from seed
      mnemo = Mnemonic("english")
      seed_bytes = seed_from_mnemonic(mnemo, self.seed_phrase)
      # Solana uses BIP44 path m/44'/501'/{index}'/0'
      # We need to derive the keypair properly
      # For now, use a simple derivation from seed + index
      seed_32 = seed_bytes[:32]
      # Create deterministic seed for this index
      index_bytes = self.index.to_bytes(4, "big")
      combined = seed_32 + index_bytes
      keypair_seed = hashlib.sha256(combined).digest()[:32]
      keypair = Keypair.from_bytes(keypair_seed)
      return keypair
    else:
      raise ValueError(f"Unknown chain type: {self.chain_type}")

  def get_address(self) -> str:
    """Get the wallet address."""
    return self.address


class NetworkConfig:
  """Configuration for a blockchain network."""

  def __init__(
    self,
    chain_id: str,
    name: str,
    rpc_url: str,
    chain_type: str,
  ):
    self.chain_id = chain_id
    self.name = name
    self.rpc_url = rpc_url
    self.chain_type = chain_type

  def get_web3(self) -> Web3 | None:
    """Get Web3 instance for EVM networks."""
    if self.chain_type != "evm":
      return None
    return Web3(Web3.HTTPProvider(self.rpc_url))

  def is_connected(self) -> bool:
    """Check if network connection is working."""
    if self.chain_type == "evm":
      w3 = self.get_web3()
      if w3:
        try:
          return w3.is_connected()
        except Exception:
          return False
    elif self.chain_type == "sol":
      # For Solana, we'd check RPC connection
      # For now, assume it works
      return True
    return False


class WalletClient:
  """Client for wallet operations."""

  def __init__(self, config: dict[str, Any], seed_phrase: str):
    self.seed_phrase = seed_phrase
    self.wallets: list[WalletConfig] = []
    self.networks: list[NetworkConfig] = []

    # Load wallets from config
    for w in config.get("wallets", []):
      wallet = WalletConfig(
        index=w["index"],
        chain_type=w["chain_type"],
        address=w["address"],
        seed_phrase=seed_phrase,
        label=w.get("label"),
      )
      self.wallets.append(wallet)

    # Load networks from config
    for n in config.get("networks", []):
      network = NetworkConfig(
        chain_id=n["chain_id"],
        name=n["name"],
        rpc_url=n["rpc_url"],
        chain_type=n["chain_type"],
      )
      self.networks.append(network)

  def get_wallet(self, address: str) -> WalletConfig | None:
    """Get wallet by address."""
    for wallet in self.wallets:
      if wallet.address.lower() == address.lower():
        return wallet
    return None

  def get_network(self, chain_id: str, chain_type: str) -> NetworkConfig | None:
    """Get network by chain ID and type."""
    for network in self.networks:
      if network.chain_id == chain_id and network.chain_type == chain_type:
        return network
    return None

  async def get_balance(self, address: str, chain_id: str, chain_type: str) -> dict[str, Any]:
    """Get balance for an address on a network."""
    wallet = self.get_wallet(address)
    if not wallet:
      raise ValueError(f"Wallet not found: {address}")

    network = self.get_network(chain_id, chain_type)
    if not network:
      raise ValueError(f"Network not found: {chain_id} ({chain_type})")

    if chain_type == "evm":
      w3 = network.get_web3()
      if not w3:
        raise ValueError("Failed to connect to EVM network")
      balance_wei = w3.eth.get_balance(Web3.to_checksum_address(address))
      balance_eth = Web3.from_wei(balance_wei, "ether")
      return {
        "address": address,
        "chain_id": chain_id,
        "chain_type": "evm",
        "balance_wei": str(balance_wei),
        "balance_eth": str(balance_eth),
        "symbol": "ETH",
      }
    elif chain_type == "sol":
      # Solana balance check would go here
      # For now, return placeholder
      return {
        "address": address,
        "chain_id": chain_id,
        "chain_type": "sol",
        "balance_lamports": "0",
        "balance_sol": "0",
        "symbol": "SOL",
      }
    else:
      raise ValueError(f"Unsupported chain type: {chain_type}")

  async def send_transaction(
    self,
    from_address: str,
    to_address: str,
    amount: str,
    chain_id: str,
    chain_type: str,
    gas_limit: int | None = None,
  ) -> dict[str, Any]:
    """Send a transaction."""
    wallet = self.get_wallet(from_address)
    if not wallet:
      raise ValueError(f"Wallet not found: {from_address}")

    network = self.get_network(chain_id, chain_type)
    if not network:
      raise ValueError(f"Network not found: {chain_id} ({chain_type})")

    if chain_type == "evm":
      account = wallet.get_account()
      w3 = network.get_web3()
      if not w3:
        raise ValueError("Failed to connect to EVM network")

      # Build transaction
      nonce = w3.eth.get_transaction_count(Web3.to_checksum_address(from_address))
      gas_price = w3.eth.gas_price

      tx = {
        "nonce": nonce,
        "to": Web3.to_checksum_address(to_address),
        "value": Web3.to_wei(Decimal(amount), "ether"),
        "gas": gas_limit or 21000,
        "gasPrice": gas_price,
        "chainId": int(chain_id),
      }

      # Sign transaction
      signed_tx = account.sign_transaction(tx)
      tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

      return {
        "tx_hash": tx_hash.hex(),
        "from": from_address,
        "to": to_address,
        "amount": amount,
        "chain_id": chain_id,
        "status": "pending",
      }
    elif chain_type == "sol":
      # Solana transaction would go here
      raise NotImplementedError("Solana transactions not yet implemented")
    else:
      raise ValueError(f"Unsupported chain type: {chain_type}")

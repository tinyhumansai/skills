# Web3 Wallet Skill

A skill connector for managing EVM and Solana wallets from seed phrases.

## Features

- **Seed Phrase Management**: Enter and securely store 12 or 24 word BIP39 mnemonic seed phrases
- **Multi-Wallet Support**: Derive and manage up to 5 wallets (EVM and/or Solana)
- **Network Selection**: Choose from popular EVM networks (Ethereum, Polygon, BSC, Arbitrum, Optimism, Avalanche, Base) and Solana networks (Mainnet, Devnet)
- **Balance Checking**: Query balances across all configured networks
- **Transaction Sending**: Send transactions on EVM networks
- **Message Signing**: Sign messages with wallet private keys

## Setup Flow

1. **Seed Phrase**: Enter your 12 or 24 word recovery phrase
2. **Wallet Selection**: Choose which wallets to load (up to 5 total, mix of EVM and Solana)
3. **Network Selection**: Select which blockchain networks to enable

## Tools

- `list_wallets` - List all configured wallet accounts
- `list_networks` - List all configured networks with connection status
- `get_balance` - Get balance for a wallet address on a specific network
- `send_transaction` - Send a transaction from one address to another
- `sign_message` - Sign a message with a wallet's private key

## Security Notes

⚠️ **IMPORTANT**: The seed phrase is currently stored in plaintext in the skill's data directory. In production, this should be encrypted using platform-provided secure storage.

## Dependencies

- `web3>=6.0.0` - Ethereum/EVM blockchain interaction
- `eth-account>=0.10.0` - Ethereum account management
- `mnemonic>=0.20` - BIP39 mnemonic handling
- `solana>=0.30.0` - Solana blockchain interaction
- `solders>=0.18.0` - Solana keypair management

## Architecture

- `setup.py` - Multi-step setup flow for seed phrase, wallets, and networks
- `skill.py` - Main skill definition with lifecycle hooks
- `client/wallet_client.py` - Wallet and network client implementations
- `handlers/wallet_handlers.py` - Tool execution handlers
- `tools.py` - Tool definitions for AI agent

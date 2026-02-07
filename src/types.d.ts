/**
 * Central type definitions for skills under src/.
 * Used by all skills: example-skill, wallet, server-ping, gmail, notion, telegram, etc.
 *
 * Skill package layout:
 *   <skill-id>/
 *     manifest.json   - SkillManifest
 *     index.ts        - Skill entry (init, start, stop, onLoad?, setup, tools)
 *     skill-state.ts - State + getState/getSkillState on globalThis
 *     types.ts        - Skill-specific config/domain types
 *     tools/*.ts      - Tool definitions (name, description, parameters, execute)
 */

// ---------------------------------------------------------------------------
// Manifest (manifest.json)
// ---------------------------------------------------------------------------

export interface SkillManifestSetupOAuth {
  provider: string;
  scopes: string[];
  apiBaseUrl: string;
}

export interface SkillManifestSetup {
  required: boolean;
  label: string;
  oauth?: SkillManifestSetupOAuth;
}

export interface EntityTypeProperty {
  name: string;
  type: string;
  description: string;
  optional?: boolean;
}

export interface EntityTypeDef {
  type: string;
  label: string;
  description: string;
  properties: EntityTypeProperty[];
}

export interface RelationshipTypeDef {
  type: string;
  source_type: string;
  target_type: string;
  description: string;
  cardinality: 'one_to_one' | 'one_to_many' | 'many_to_one' | 'many_to_many';
}

export interface SkillManifestEntitySchema {
  entity_types: EntityTypeDef[];
  relationship_types: RelationshipTypeDef[];
}

export interface SkillManifest {
  id: string;
  name: string;
  runtime: string;
  entry: string;
  version: string;
  description?: string;
  auto_start?: boolean;
  setup?: SkillManifestSetup;
  platforms?: string[];
  ignoreInProduction?: boolean;
  entity_schema?: SkillManifestEntitySchema;
}

// ---------------------------------------------------------------------------
// Load params (passed from host to skill on load)
// ---------------------------------------------------------------------------

export interface SkillLoadParams {
  /** EVM/Solana address derived from app mnemonic (e.g. wallet skill) */
  walletAddress?: string;
  /** Multiple addresses when supported */
  walletAddresses?: string[];
  [key: string]: unknown;
}

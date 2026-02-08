// Shared type for Notion helper functions exposed on globalThis
import type { NotionApi } from './api/index';

export interface NotionGlobals {
  notionFetch(endpoint: string, options?: { method?: string; body?: unknown }): unknown;
  formatApiError(error: unknown): string;
  formatRichText(richText: unknown[]): string;
  formatPageTitle(page: Record<string, unknown>): string;
  formatPageSummary(page: Record<string, unknown>): Record<string, unknown>;
  formatDatabaseSummary(db: Record<string, unknown>): Record<string, unknown>;
  formatBlockSummary(block: Record<string, unknown>): Record<string, unknown>;
  formatBlockContent(block: Record<string, unknown>): string;
  formatUserSummary(user: Record<string, unknown>): Record<string, unknown>;
  buildRichText(text: string): unknown[];
  buildParagraphBlock(text: string): Record<string, unknown>;
  fetchBlockTreeText(blockId: string, maxDepth?: number): string;
  getLocalPages(options?: { query?: string; limit?: number; includeArchived?: boolean }): unknown[];
  getLocalDatabases(options?: { query?: string; limit?: number }): unknown[];
  getLocalUsers(): unknown[];
  getPageById(pageId: string): unknown | null;
  getNotionSyncState(key: string): string | null;
  setNotionSyncState(key: string, value: string): void;
  getEntityCounts(): {
    pages: number;
    databases: number;
    users: number;
    pagesWithContent: number;
    pagesWithSummary: number;
    summariesTotal: number;
    summariesPending: number;
  };
  getPagesNeedingSummary(limit: number): unknown[];
  insertSummary(opts: {
    pageId: string;
    summary: string;
    category?: string;
    sentiment?: string;
    entities?: unknown[];
    topics?: string[];
    metadata?: Record<string, unknown>;
    sourceCreatedAt: string;
    sourceUpdatedAt: string;
  }): void;
  getUnsyncedSummaries(limit: number): unknown[];
  markSummariesSynced(ids: number[]): void;
  performSync(): void;
}

// Access helpers at runtime (call inside execute(), not at module scope).
// In the production QuickJS runtime, helpers are on globalThis.
// In esbuild IIFE bundles, helpers end up on the shared `exports` object
// due to CommonJS interop (__esm wrappers write to the outer exports shim).
// This function checks both locations.
export function n(): NotionGlobals {
  const g = globalThis as unknown as Record<string, unknown>;
  // When bundled with esbuild, helpers are on the 'exports' shim object
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
}

// Access the typed Notion API layer at runtime.
// Same dual-location resolution as n().
export function getApi(): NotionApi {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionApi === 'object') {
    return (g.exports as Record<string, unknown>).notionApi as NotionApi;
  }
  return (g as Record<string, unknown>).notionApi as NotionApi;
}

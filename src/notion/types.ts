// Shared type for Notion helper functions exposed on globalThis

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

// Tool: notion-sync-now
// Triggers an immediate sync and returns the result
import '../skill-state';
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const syncNowTool: ToolDefinition = {
  name: 'notion-sync-now',
  description:
    'Trigger an immediate Notion sync to refresh local data. ' +
    'Returns sync results including counts of synced pages, databases, and users.',
  input_schema: { type: 'object', properties: {} },
  execute(): string {
    try {
      const s = globalThis.getNotionSkillState();

      if (!oauth.getCredential()) {
        return JSON.stringify({
          success: false,
          error: 'Notion not connected. Complete OAuth setup first.',
        });
      }

      if (s.syncStatus.syncInProgress) {
        return JSON.stringify({
          success: false,
          message: 'Sync already in progress',
          sync_in_progress: true,
          last_sync_time: s.syncStatus.lastSyncTime
            ? new Date(s.syncStatus.lastSyncTime).toISOString()
            : null,
        });
      }

      // Trigger sync
      const { performSync } = n();
      performSync();

      // Return results after sync completes
      return JSON.stringify({
        success: !s.syncStatus.lastSyncError,
        duration_ms: s.syncStatus.lastSyncDurationMs,
        last_sync_time: new Date(s.syncStatus.lastSyncTime).toISOString(),
        error: s.syncStatus.lastSyncError,
        totals: {
          pages: s.syncStatus.totalPages,
          databases: s.syncStatus.totalDatabases,
          users: s.syncStatus.totalUsers,
          pages_with_content: s.syncStatus.pagesWithContent,
        },
      });
    } catch (e) {
      return JSON.stringify({ success: false, error: e instanceof Error ? e.message : String(e) });
    }
  },
};

// Tool: notion-sync-status
// Returns current sync status and statistics
import '../skill-state';

export const syncStatusTool: ToolDefinition = {
  name: 'notion-sync-status',
  description:
    'Get the current Notion sync status including last sync time, ' +
    'total synced pages/databases/users, sync progress, and any errors.',
  input_schema: { type: 'object', properties: {} },
  execute(): string {
    try {
      const s = globalThis.getNotionSkillState();

      return JSON.stringify({
        connected: !!oauth.getCredential(),
        workspace_name: s.config.workspaceName || null,
        sync_in_progress: s.syncStatus.syncInProgress,
        last_sync_time: s.syncStatus.lastSyncTime
          ? new Date(s.syncStatus.lastSyncTime).toISOString()
          : null,
        next_sync_time: s.syncStatus.nextSyncTime
          ? new Date(s.syncStatus.nextSyncTime).toISOString()
          : null,
        last_sync_duration_ms: s.syncStatus.lastSyncDurationMs,
        last_sync_error: s.syncStatus.lastSyncError,
        totals: {
          pages: s.syncStatus.totalPages,
          databases: s.syncStatus.totalDatabases,
          users: s.syncStatus.totalUsers,
          pages_with_content: s.syncStatus.pagesWithContent,
        },
        config: {
          sync_interval_minutes: s.config.syncIntervalMinutes,
          content_sync_enabled: s.config.contentSyncEnabled,
          max_pages_per_content_sync: s.config.maxPagesPerContentSync,
        },
      });
    } catch (e) {
      return JSON.stringify({ error: e instanceof Error ? e.message : String(e) });
    }
  },
};

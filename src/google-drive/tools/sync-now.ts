// Tool: google-drive-sync-now
// Triggers an immediate sync and returns the result
import { getGoogleDriveSkillState } from '../state';
import { performSync } from '../sync';

export const syncNowTool: ToolDefinition = {
  name: 'google-drive-sync-now',
  description:
    'Trigger an immediate Google Drive sync to refresh local file cache. ' +
    'Returns sync results including count of synced files.',
  input_schema: { type: 'object', properties: {} },
  async execute(): Promise<string> {
    try {
      const s = getGoogleDriveSkillState();

      if (!oauth.getCredential()) {
        return Promise.resolve(
          JSON.stringify({
            success: false,
            error: 'Google Drive not connected. Complete OAuth setup first.',
          })
        );
      }

      if (s.syncStatus.syncInProgress) {
        return Promise.resolve(
          JSON.stringify({
            success: false,
            message: 'Sync already in progress',
            sync_in_progress: true,
            last_sync_time: s.syncStatus.lastSyncTime
              ? new Date(s.syncStatus.lastSyncTime).toISOString()
              : null,
          })
        );
      }

      await performSync();

      return Promise.resolve(
        JSON.stringify({
          success: !s.syncStatus.lastSyncError,
          message: 'Sync completed',
          last_sync_time: s.syncStatus.lastSyncTime
            ? new Date(s.syncStatus.lastSyncTime).toISOString()
            : null,
          totals: {
            files: s.syncStatus.totalFiles,
            spreadsheets: s.syncStatus.totalSpreadsheets,
            documents: s.syncStatus.totalDocuments,
          },
        })
      );
    } catch (e) {
      return Promise.resolve(
        JSON.stringify({ success: false, error: e instanceof Error ? e.message : String(e) })
      );
    }
  },
};

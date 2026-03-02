// Google Drive sync engine
// Fetches file list, spreadsheet metadata/values, and doc content; stores all in SQLite (idempotent).
import { driveFetch } from './api/index';
import {
  getEntityCounts,
  getFileById,
  getLocalFiles,
  setSyncState,
  upsertDocument,
  upsertFile,
  upsertSheetValues,
  upsertSpreadsheet,
} from './db/helpers';
import { getGoogleDriveSkillState } from './state';
import { DOCS_BASE, DOCS_MIMETYPE, SHEETS_BASE, SHEETS_MIMETYPE } from './types';

const DEFAULT_PAGE_SIZE = 100;
const MAX_PAGES_PER_SYNC = 50;
/** Keep low so content phase finishes before typical socket/host timeout (~30s). Each sheet = 2 calls, each doc = 1 call. */
const MAX_SPREADSHEETS_PER_SYNC = 3;
const MAX_DOCUMENTS_PER_SYNC = 5;
/** Stop content sync (Phase 2+3) after this ms to avoid connection timeout. Next cron run continues. */
const CONTENT_SYNC_TIME_BUDGET_MS = 18_000;
const DEFAULT_SHEET_RANGE = 'A1:Z500';

function publishSyncState(): void {
  const s = getGoogleDriveSkillState();
  const isConnected = !!oauth.getCredential();

  state.setPartial({
    connection_status: isConnected ? 'connected' : 'disconnected',
    auth_status: isConnected ? 'authenticated' : 'not_authenticated',
    connection_error: s.syncStatus.lastSyncError ?? null,
    auth_error: null,
    is_initialized: isConnected,
    syncInProgress: s.syncStatus.syncInProgress,
    lastSyncTime: s.syncStatus.lastSyncTime
      ? new Date(s.syncStatus.lastSyncTime).toISOString()
      : null,
    nextSyncTime: s.syncStatus.nextSyncTime
      ? new Date(s.syncStatus.nextSyncTime).toISOString()
      : null,
    totalFiles: s.syncStatus.totalFiles,
    totalSpreadsheets: s.syncStatus.totalSpreadsheets,
    totalDocuments: s.syncStatus.totalDocuments,
    lastSyncError: s.syncStatus.lastSyncError,
    lastSyncDurationMs: s.syncStatus.lastSyncDurationMs,
  });
}

/**
 * Perform full sync: fetch files from Drive API (paginated), normalize, upsert into DB.
 * Idempotent and safe to re-run. Updates sync status on globalThis and state.
 */
export async function performSync(): Promise<void> {
  const s = getGoogleDriveSkillState();

  if (s.syncStatus.syncInProgress) {
    console.log('[google-drive] Sync already in progress, skipping');
    return;
  }

  if (!oauth.getCredential()) {
    console.log('[google-drive] No credential, skipping sync');
    return;
  }

  const startTime = Date.now();
  s.syncStatus.syncInProgress = true;
  s.syncStatus.lastSyncError = null;
  publishSyncState();

  try {
    const lastSyncTime = s.syncStatus.lastSyncTime;
    const isFirstSync = lastSyncTime === 0;

    let pageToken: string | undefined;
    let totalUpserted = 0;
    let totalSkipped = 0;
    let pageCount = 0;

    while (pageCount < MAX_PAGES_PER_SYNC) {
      const qParts = ['trashed = false'];
      const params: string[] = [
        'q=' + encodeURIComponent(qParts.join(' and ')),
        'pageSize=' + String(DEFAULT_PAGE_SIZE),
        'fields=' +
          encodeURIComponent(
            'nextPageToken, files(id, name, mimeType, size, modifiedTime, webViewLink, parents)'
          ),
        'orderBy=' + encodeURIComponent('modifiedTime desc'),
      ];
      if (pageToken) {
        params.push('pageToken=' + encodeURIComponent(pageToken));
      }
      const path = '/drive/v3/files?' + params.join('&');
      const result = await driveFetch(path);

      if (!result.success) {
        throw new Error(result.error?.message ?? 'Drive API request failed');
      }

      const data = result.data as {
        files?: Array<Record<string, unknown>>;
        nextPageToken?: string;
      };
      const files = data.files ?? [];

      for (const f of files) {
        const id = f.id as string;
        const modifiedTime = (f.modifiedTime as string) || null;
        if (!id) continue;

        if (!isFirstSync && modifiedTime) {
          const modifiedMs = new Date(modifiedTime).getTime();
          if (modifiedMs <= lastSyncTime) {
            totalSkipped++;
            continue;
          }
        }

        const existing = getFileById(id);
        if (existing && modifiedTime && existing.modified_time === modifiedTime) {
          totalSkipped++;
          continue;
        }

        upsertFile({
          id,
          name: (f.name as string) ?? '',
          mimeType: f.mimeType as string | undefined,
          size: f.size as string | undefined,
          modifiedTime: modifiedTime ?? undefined,
          webViewLink: f.webViewLink as string | undefined,
          parents: Array.isArray(f.parents) ? (f.parents as string[]) : undefined,
        });
        totalUpserted++;
      }

      pageToken = (data.nextPageToken as string) ?? undefined;
      pageCount++;
      if (!pageToken || files.length === 0) break;
    }

    // Phase 2: Sync spreadsheet metadata + first sheet values (respect time budget to avoid socket timeout)
    const sheetFiles = getLocalFiles({
      mimeType: SHEETS_MIMETYPE,
      limit: MAX_SPREADSHEETS_PER_SYNC,
    });
    let spreadsheetsSynced = 0;
    for (const file of sheetFiles) {
      if (Date.now() - startTime > CONTENT_SYNC_TIME_BUDGET_MS) {
        console.log('[google-drive] Content sync time budget reached, stopping spreadsheets');
        break;
      }
      try {
        const metaRes = await driveFetch(`/v4/spreadsheets/${encodeURIComponent(file.id)}`, {
          baseUrl: SHEETS_BASE,
        });
        if (!metaRes.success) continue;
        const meta = metaRes.data as {
          spreadsheetId?: string;
          properties?: { title?: string };
          sheets?: Array<{
            properties?: {
              title?: string;
              sheetId?: number;
              gridProperties?: { rowCount?: number; columnCount?: number };
            };
          }>;
        };
        const title = meta.properties?.title ?? file.name;
        const sheets = (meta.sheets ?? []).map(sh => ({
          sheetId: sh.properties?.sheetId,
          title: sh.properties?.title ?? '',
        }));
        upsertSpreadsheet(file.id, title, sheets);
        const firstSheet = meta.sheets?.[0]?.properties;
        const sheetTitle = firstSheet?.title ?? 'Sheet1';
        const rangeA1 = `${sheetTitle}!${DEFAULT_SHEET_RANGE}`;
        const valRes = await driveFetch(
          `/v4/spreadsheets/${encodeURIComponent(file.id)}/values/${encodeURIComponent(rangeA1)}`,
          { baseUrl: SHEETS_BASE }
        );
        if (valRes.success) {
          const valData = valRes.data as { values?: unknown[][] };
          upsertSheetValues(file.id, rangeA1, valData.values ?? []);
        }
        spreadsheetsSynced++;
      } catch (e) {
        console.error(`[google-drive] Failed to sync spreadsheet ${file.id}: ${e}`);
      }
    }

    // Phase 3: Sync document content (respect time budget to avoid socket timeout)
    const docFiles = getLocalFiles({ mimeType: DOCS_MIMETYPE, limit: MAX_DOCUMENTS_PER_SYNC });
    let documentsSynced = 0;
    for (const file of docFiles) {
      if (Date.now() - startTime > CONTENT_SYNC_TIME_BUDGET_MS) {
        console.log('[google-drive] Content sync time budget reached, stopping documents');
        break;
      }
      try {
        const docRes = await driveFetch(`/v1/documents/${encodeURIComponent(file.id)}`, {
          baseUrl: DOCS_BASE,
        });
        if (!docRes.success) continue;
        const doc = docRes.data as {
          documentId?: string;
          title?: string;
          body?: {
            content?: Array<{
              paragraph?: { elements?: Array<{ textRun?: { content?: string } }> };
            }>;
          };
        };
        const parts: string[] = [];
        (doc.body?.content ?? []).forEach(c => {
          (c.paragraph?.elements ?? []).forEach(el => {
            if (el.textRun?.content) parts.push(el.textRun.content);
          });
        });
        const contentText = parts.join('').replace(/\n$/, '') || '';
        upsertDocument(file.id, doc.title ?? file.name, contentText);
        documentsSynced++;
      } catch (e) {
        console.error(`[google-drive] Failed to sync document ${file.id}: ${e}`);
      }
    }

    const durationMs = Date.now() - startTime;
    const nowMs = Date.now();
    s.syncStatus.lastSyncTime = nowMs;
    s.syncStatus.nextSyncTime = nowMs + s.config.syncIntervalMinutes * 60 * 1000;
    s.syncStatus.lastSyncDurationMs = durationMs;
    setSyncState('last_sync', String(nowMs));

    const counts = getEntityCounts();
    s.syncStatus.totalFiles = counts.totalFiles;
    s.syncStatus.totalSpreadsheets = counts.totalSpreadsheets;
    s.syncStatus.totalDocuments = counts.totalDocuments;

    console.log(
      `[google-drive] Sync complete in ${durationMs}ms — files: ${totalUpserted} updated, ${totalSkipped} skipped; ` +
        `spreadsheets: ${spreadsheetsSynced}, documents: ${documentsSynced}; ` +
        `totals: ${counts.totalFiles} files, ${counts.totalSpreadsheets} spreadsheets, ${counts.totalDocuments} documents`
    );
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    s.syncStatus.lastSyncError = errorMsg;
    s.syncStatus.lastSyncDurationMs = Date.now() - startTime;
    console.error(`[google-drive] Sync failed: ${errorMsg}`);
  } finally {
    s.syncStatus.syncInProgress = false;
    publishSyncState();
  }
}

// Gmail email sync: initial + incremental sync with 30-day window.
// Fetches messages via Gmail API and upserts into local SQLite database.
// Skips emails already in the local DB to avoid redundant API calls.
import { gmailFetch } from './api';
import {
  getEmailById,
  getUnsubmittedEmails,
  markEmailsSubmitted,
  markSensitiveAsSubmitted,
  upsertEmail,
} from './db/helpers';
import { getGmailSkillState, publishSkillState } from './state';
import type { DatabaseEmail, GmailMessage } from './types';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/** Number of days to look back for emails. */
const SYNC_WINDOW_DAYS = 30;

/** Max emails to fetch per API page. */
const PAGE_SIZE = 100;

/** Max pages to fetch per sync (100 emails/page × 10 pages = 1000 emails). */
const MAX_PAGES = 10;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Progress callback: receives a human-readable message and a 0-100 percentage. */
type SyncProgressCallback = (message: string, progress: number) => void;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Emit sync progress to the frontend via state. */
function emitSyncProgress(message: string, progress: number): void {
  const s = getGmailSkillState();
  s.syncStatus.syncProgress = progress;
  s.syncStatus.syncProgressMessage = message;
  state.setPartial({ syncProgress: progress, syncProgressMessage: message });
}

/** Parse labels from DB JSON string into an array. */
function parseLabels(labels: string): string[] {
  try {
    const parsed = JSON.parse(labels);
    return Array.isArray(parsed) ? parsed.map((l: string) => l.toLowerCase()) : [];
  } catch {
    return [];
  }
}

/** Build a Gmail `after:` date string (YYYY/MM/DD) for N days ago. */
function getDateNDaysAgo(days: number): string {
  const date = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}/${m}/${d}`;
}

/** Format a timestamp as YYYY/MM/DD for Gmail query syntax. */
function formatDateForQuery(timestamp: number): string {
  const date = new Date(timestamp);
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}/${m}/${d}`;
}

/**
 * Fetch a page of message IDs from the Gmail API.
 * Returns the message references and optional next page token.
 */
async function fetchMessagePage(
  query: string,
  pageToken?: string
): Promise<{ messages: Array<{ id: string; threadId: string }>; nextPageToken?: string }> {
  const params: string[] = [`maxResults=${PAGE_SIZE}`, `q=${encodeURIComponent(query)}`];
  if (pageToken) params.push(`pageToken=${encodeURIComponent(pageToken)}`);

  const response = await gmailFetch(`/users/me/messages?${params.join('&')}`);

  if (!response.success || !response.data?.messages) {
    if (response.error) {
      console.error(`[gmail-sync] List error: ${response.error.message}`);
    }
    return { messages: [] };
  }

  return {
    messages: response.data.messages as Array<{ id: string; threadId: string }>,
    nextPageToken: response.data.nextPageToken,
  };
}

/**
 * Fetch full message details and upsert into DB.
 * Sensitive emails have their body redacted when `showSensitiveMessages` is off.
 * Returns true if a new email was synced, false if skipped (already exists).
 */
async function syncMessage(msgId: string): Promise<boolean> {
  // Skip if already in local DB
  if (getEmailById(msgId)) return false;

  const msgResponse = await gmailFetch(`/users/me/messages/${msgId}`);
  if (msgResponse.success && msgResponse.data) {
    const s = getGmailSkillState();
    const redact = !s.config.showSensitiveMessages;
    upsertEmail(msgResponse.data as GmailMessage, redact);
    return true;
  }
  return false;
}

// ---------------------------------------------------------------------------
// Initial Sync
// ---------------------------------------------------------------------------

/**
 * Perform initial sync: loads all emails from the last 30 days.
 * Paginates through results and skips emails already in the local database.
 * Called on first connect or when initial sync hasn't been completed.
 */
export async function performInitialSync(onProgress?: SyncProgressCallback): Promise<void> {
  const s = getGmailSkillState();

  if (!oauth.getCredential()) {
    console.log('[gmail-sync] No OAuth credential, skipping initial sync');
    return;
  }

  if (s.syncStatus.syncInProgress) {
    console.log('[gmail-sync] Sync already in progress, skipping');
    return;
  }

  const log = (msg: string, pct: number) => {
    console.log(`[gmail-sync] [${pct}%] ${msg}`);
    emitSyncProgress(msg, pct);
    onProgress?.(msg, pct);
  };

  s.syncStatus.syncInProgress = true;
  s.syncStatus.newEmailsCount = 0;
  publishSkillState();

  try {
    const afterDate = getDateNDaysAgo(SYNC_WINDOW_DAYS);
    const query = `after:${afterDate}`;
    log(`Starting initial sync (emails after ${afterDate})...`, 0);

    let pageToken: string | undefined;
    let newEmails = 0;
    let skipped = 0;
    let page = 0;

    do {
      page++;
      log(`Fetching page ${page}...`, Math.min(5 + page * 8, 80));

      const result = await fetchMessagePage(query, pageToken);
      if (result.messages.length === 0) break;

      pageToken = result.nextPageToken;

      for (const msgRef of result.messages) {
        const isNew = await syncMessage(msgRef.id);
        if (isNew) newEmails++;
        else skipped++;
      }

      log(`Page ${page}: ${newEmails} new, ${skipped} skipped`, Math.min(10 + page * 10, 90));
    } while (pageToken && page < MAX_PAGES);

    // Mark initial sync as complete
    const now = Date.now();
    state.set('initialSyncCompleted', true);
    state.set('lastSyncTime', now);

    s.syncStatus.lastSyncTime = now;
    s.syncStatus.newEmailsCount = newEmails;
    s.syncStatus.nextSyncTime = now + s.config.syncIntervalMinutes * 60 * 1000;

    log(`Initial sync complete: ${newEmails} new emails, ${skipped} skipped`, 100);

    // Submit newly synced emails to backend for processing
    submitNewEmails();

    if (newEmails > 0 && s.config.notifyOnNewEmails) {
      platform.notify('Gmail Sync Complete', `Synchronized ${newEmails} new emails`);
    }
  } catch (error) {
    console.error(`[gmail-sync] Initial sync failed: ${error}`);
    s.lastApiError = error instanceof Error ? error.message : String(error);
    emitSyncProgress(`Sync failed: ${s.lastApiError}`, 0);
  } finally {
    s.syncStatus.syncInProgress = false;
    s.syncStatus.syncProgress = 0;
    s.syncStatus.syncProgressMessage = '';
    publishSkillState();
  }
}

// ---------------------------------------------------------------------------
// Incremental Sync
// ---------------------------------------------------------------------------

/**
 * Incremental sync: fetches only emails newer than the last sync time,
 * within the 30-day window. Skips emails already in the database.
 * Falls back to initial sync if it hasn't been completed yet.
 */
export async function onSync(): Promise<void> {
  const s = getGmailSkillState();

  if (!oauth.getCredential() || s.syncStatus.syncInProgress) return;

  // If initial sync hasn't completed, run it instead
  if (!isSyncCompleted()) {
    return performInitialSync();
  }

  s.syncStatus.syncInProgress = true;
  s.syncStatus.newEmailsCount = 0;
  emitSyncProgress('Starting incremental sync...', 0);
  publishSkillState();

  try {
    // Use last sync time to narrow the query window, but never go beyond 30 days
    const thirtyDaysAgo = getDateNDaysAgo(SYNC_WINDOW_DAYS);
    const lastSyncTime = getLastSyncTime();

    let query: string;
    if (lastSyncTime) {
      // Use the later of: last sync time or 30 days ago
      const thirtyDaysAgoMs = Date.now() - SYNC_WINDOW_DAYS * 24 * 60 * 60 * 1000;
      const effectiveDate = Math.max(lastSyncTime, thirtyDaysAgoMs);
      query = `after:${formatDateForQuery(effectiveDate)}`;
    } else {
      query = `after:${thirtyDaysAgo}`;
    }

    let pageToken: string | undefined;
    let newEmails = 0;
    let skipped = 0;
    let page = 0;

    do {
      page++;
      emitSyncProgress(`Fetching page ${page}...`, Math.min(10 + page * 25, 80));

      const result = await fetchMessagePage(query, pageToken);
      if (result.messages.length === 0) break;

      pageToken = result.nextPageToken;

      for (const msgRef of result.messages) {
        const isNew = await syncMessage(msgRef.id);
        if (isNew) newEmails++;
        else skipped++;
      }

      emitSyncProgress(
        `Page ${page}: ${newEmails} new, ${skipped} skipped`,
        Math.min(20 + page * 25, 90)
      );
    } while (pageToken && page < MAX_PAGES);

    // Update sync state
    const now = Date.now();
    state.set('lastSyncTime', now);
    s.syncStatus.lastSyncTime = now;
    s.syncStatus.newEmailsCount = newEmails;
    s.syncStatus.nextSyncTime = now + s.config.syncIntervalMinutes * 60 * 1000;

    emitSyncProgress(`Sync complete: ${newEmails} new, ${skipped} skipped`, 100);
    console.log(`[gmail-sync] Incremental sync done: ${newEmails} new, ${skipped} skipped`);

    // Submit newly synced emails to backend for processing
    submitNewEmails();

    if (newEmails > 0 && s.config.notifyOnNewEmails) {
      platform.notify('New Gmail Emails', `${newEmails} new emails synced`);
    }
  } catch (error) {
    console.error(`[gmail-sync] Incremental sync failed: ${error}`);
    s.lastApiError = error instanceof Error ? error.message : String(error);
    emitSyncProgress(`Sync failed: ${s.lastApiError}`, 0);
  } finally {
    s.syncStatus.syncInProgress = false;
    s.syncStatus.syncProgress = 0;
    s.syncStatus.syncProgressMessage = '';
    publishSkillState();
  }
}

// ---------------------------------------------------------------------------
// Backend data submission
// ---------------------------------------------------------------------------

/** Approximate max payload size per socket message (~100 KB). */
const MAX_BATCH_BYTES = 100 * 1024;

/** Max emails to pull from DB per submission round. */
const SUBMIT_QUERY_LIMIT = 500;

/**
 * Build a DataSubmissionChunk from a database email row.
 * Prefers body_text, falls back to snippet. Includes key metadata,
 * raw HTML content, structured labels, and person entities.
 */
function emailToChunk(email: DatabaseEmail): DataSubmissionChunk {
  const content = email.body_text || email.snippet || '';

  // Build entities from sender + recipients
  const entities: Array<{ name: string; identifier: string; kind: string }> = [];

  if (email.sender_email) {
    entities.push({
      name: email.sender_name || email.sender_email,
      identifier: email.sender_email,
      kind: 'sender',
    });
  }

  if (email.recipient_emails) {
    for (const raw of email.recipient_emails.split(',')) {
      const trimmed = raw.trim();
      if (!trimmed) continue;
      // Parse "Name <email>" or bare email
      const match = trimmed.match(/(.+?)\s*<([^>]+)>/);
      const addr = match ? match[2].trim() : trimmed;
      const name = match ? match[1].trim().replace(/^["']|["']$/g, '') : trimmed;
      // Avoid duplicating the sender
      if (addr !== email.sender_email) {
        entities.push({ name, identifier: addr, kind: 'recipient' });
      }
    }
  }

  if (email.cc_emails) {
    for (const raw of email.cc_emails.split(',')) {
      const trimmed = raw.trim();
      if (!trimmed) continue;
      const match = trimmed.match(/(.+?)\s*<([^>]+)>/);
      const addr = match ? match[2].trim() : trimmed;
      const name = match ? match[1].trim().replace(/^["']|["']$/g, '') : trimmed;
      if (!entities.some(e => e.identifier === addr)) {
        entities.push({ name, identifier: addr, kind: 'recipient_cc' });
      }
    }
  }

  return {
    title: email.subject || undefined,
    content,
    rawContent: email.body_html || undefined,
    labels: parseLabels(email.labels),
    entities: entities.length > 0 ? entities : undefined,
    metadata: { emailId: email.id, threadId: email.thread_id, date: email.date },
  };
}

/** Rough byte size of a chunk (title + content + rawContent + overhead). */
function estimateChunkSize(chunk: DataSubmissionChunk): number {
  return (chunk.title?.length || 0) + chunk.content.length + (chunk.rawContent?.length || 0) + 256;
}

/**
 * Submit un-submitted emails to the backend for processing.
 * Batches chunks so each socket message stays under ~100 KB.
 * Sensitive emails are marked as submitted so they don't accumulate.
 */
function submitNewEmails(): void {
  // Mark sensitive emails as "submitted" so they don't pile up.
  markSensitiveAsSubmitted();

  const emails = getUnsubmittedEmails(SUBMIT_QUERY_LIMIT);
  if (emails.length === 0) return;

  // Build chunks, keeping track of which email ID produced each one
  const prepared: Array<{ id: string; chunk: DataSubmissionChunk }> = [];
  const emptyIds: string[] = [];

  for (const email of emails) {
    const chunk = emailToChunk(email);
    if (chunk.content.length > 0) prepared.push({ id: email.id, chunk });
    else emptyIds.push(email.id);
  }

  // Mark empty-content emails as submitted so they aren't re-processed
  if (emptyIds.length > 0) markEmailsSubmitted(emptyIds);
  if (prepared.length === 0) return;

  // Split into size-limited batches
  let batch: DataSubmissionChunk[] = [];
  let batchIds: string[] = [];
  let batchBytes = 0;
  let totalSubmitted = 0;

  for (const { id, chunk } of prepared) {
    const size = estimateChunkSize(chunk);

    // If adding this chunk would exceed the limit, flush the current batch first
    if (batch.length > 0 && batchBytes + size > MAX_BATCH_BYTES) {
      try {
        backend.submitData(batch, { dataSource: 'gmail' });
        markEmailsSubmitted(batchIds);
        totalSubmitted += batch.length;
      } catch (error) {
        console.error(`[gmail-sync] Failed to submit batch to backend: ${error}`);
        return; // Stop on failure; remaining emails will be retried next sync
      }
      batch = [];
      batchIds = [];
      batchBytes = 0;
    }

    batch.push(chunk);
    batchIds.push(id);
    batchBytes += size;
  }

  // Flush remaining batch
  if (batch.length > 0) {
    try {
      backend.submitData(batch, { dataSource: 'gmail' });
      markEmailsSubmitted(batchIds);
      totalSubmitted += batch.length;
    } catch (error) {
      console.error(`[gmail-sync] Failed to submit final batch to backend: ${error}`);
      return;
    }
  }

  if (totalSubmitted > 0) {
    console.log(`[gmail-sync] Submitted ${totalSubmitted} email(s) to backend`);
  }
}

// ---------------------------------------------------------------------------
// Sync state helpers
// ---------------------------------------------------------------------------

/** Check if initial sync has been completed. */
export function isSyncCompleted(): boolean {
  return state.get('initialSyncCompleted') === true;
}

/** Get last sync timestamp (ms since epoch), or null if never synced. */
export function getLastSyncTime(): number | null {
  const value = state.get('lastSyncTime');
  return typeof value === 'number' ? value : null;
}

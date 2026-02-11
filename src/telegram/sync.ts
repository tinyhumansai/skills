// Initial sync logic for loading Telegram data on authentication.
// Fetches chats, messages, and user info via TDLib and stores in SQLite.
// Import db-helpers to initialize globalThis.telegramDb
import * as api from './api';
import './db/helpers';
import type { TdLibClient } from './tdlib-client';
import type { TdChat } from './types';

// Extend globalThis for sync functions
declare global {
  var telegramSync: {
    performInitialSync: typeof performInitialSyncImpl;
    isSyncCompleted: typeof isSyncCompletedImpl;
    getLastSyncTime: typeof getLastSyncTimeImpl;
  };
}

/** Progress callback: receives a human-readable message and a 0-100 percentage. */
type SyncProgressCallback = (message: string, progress: number) => void;

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/** Number of chats to load in initial sync. */
const CHAT_LIMIT = 100;

/** Number of top chats to load full message history for. */
const TOP_CHATS_FOR_MESSAGES = 20;

/** Number of messages to load per chat. */
const MESSAGES_PER_CHAT = 100;

// ---------------------------------------------------------------------------
// Sync Functions
// ---------------------------------------------------------------------------

/**
 * Perform initial sync of Telegram data.
 * Called when authentication completes.
 *
 * @param client - TDLib client instance
 * @param onProgress - Optional callback for progress updates (message, percentage 0-100)
 */
async function performInitialSyncImpl(
  client: TdLibClient,
  onProgress?: SyncProgressCallback
): Promise<void> {
  const log = (msg: string, pct: number) => {
    console.log(`[telegram-sync] [${pct}%] ${msg}`);
    onProgress?.(msg, pct);
  };

  log('Starting initial sync...', 0);

  try {
    // 1. Load chat list
    log('Loading chat list...', 5);
    const chats = await loadChats(client, CHAT_LIMIT);
    log(`Loaded ${chats.length} chats`, 10);

    // 2. Store chats
    for (const chat of chats) globalThis.telegramDb.upsertChat(chat);
    log('Stored all chats', 15);

    // 3. Load messages for top chats
    const topChats = chats.slice(0, TOP_CHATS_FOR_MESSAGES);
    const msgRangeStart = 15;
    const msgRangeEnd = 75;

    for (let i = 0; i < topChats.length; i++) {
      const chat = topChats[i];
      const pct = Math.round(
        msgRangeStart + ((i + 1) / topChats.length) * (msgRangeEnd - msgRangeStart)
      );
      log(`Loading messages for chat ${i + 1}/${topChats.length}: ${chat.title}`, pct);

      try {
        const messages = await api.getChatHistory(client, chat.id, MESSAGES_PER_CHAT);
        for (const msg of messages) {
          globalThis.telegramDb.upsertMessage(msg);

          // Also load sender info if it's a user
          if (msg.sender_id?.['@type'] === 'messageSenderUser' && msg.sender_id.user_id) {
            try {
              const user = await api.getUser(client, msg.sender_id.user_id);
              if (user) globalThis.telegramDb.upsertContact(user);
            } catch {
              // User may not be accessible, ignore
            }
          }
        }
      } catch (err) {
        console.log(`[telegram-sync]   Error loading messages: ${err}`);
      }
    }

    // 4. Load contacts
    log('Loading contacts...', 80);
    try {
      const contacts = await api.getContacts(client);
      for (const user of contacts) {
        globalThis.telegramDb.upsertContact(user);
      }
      log(`Loaded ${contacts.length} contacts`, 85);
    } catch (err) {
      console.log(`[telegram-sync] Error loading contacts: ${err}`);
    }

    // 5. Load chat folders
    log('Loading chat folders...', 90);
    try {
      const s = globalThis.getTelegramSkillState();
      const folderInfos = s.chatFolderInfos || [];
      if (folderInfos.length > 0) {
        for (const info of folderInfos) {
          try {
            await api.getChatFolder(client, info.id);
          } catch {
            // Folder may not be accessible, ignore
          }
        }
        log(`Loaded ${folderInfos.length} chat folders`, 95);
      } else {
        log('No chat folders found', 95);
      }
    } catch (err) {
      console.log(`[telegram-sync] Error loading chat folders: ${err}`);
    }

    // 6. Mark sync as complete
    globalThis.telegramDb.setSyncState('initial_sync_completed', 'true');
    globalThis.telegramDb.setSyncState('last_sync_time', String(Date.now()));
    log('Initial sync completed!', 100);
  } catch (err) {
    console.error('[telegram-sync] Sync error:', err);
    throw err;
  }
}

/**
 * Check if initial sync has been completed.
 */
function isSyncCompletedImpl(): boolean {
  return globalThis.telegramDb.getSyncState('initial_sync_completed') === 'true';
}

/**
 * Get last sync timestamp.
 */
function getLastSyncTimeImpl(): number | null {
  const value = globalThis.telegramDb.getSyncState('last_sync_time');
  return value ? parseInt(value, 10) : null;
}

// Expose on globalThis for reliable access across bundled modules
globalThis.telegramSync = {
  performInitialSync: performInitialSyncImpl,
  isSyncCompleted: isSyncCompletedImpl,
  getLastSyncTime: getLastSyncTimeImpl,
};

// Export wrappers for backward compatibility
export async function performInitialSync(
  client: TdLibClient,
  onProgress?: SyncProgressCallback
): Promise<void> {
  return performInitialSyncImpl(client, onProgress);
}

export function isSyncCompleted(): boolean {
  return isSyncCompletedImpl();
}

export function getLastSyncTime(): number | null {
  return getLastSyncTimeImpl();
}

// ---------------------------------------------------------------------------
// TDLib API Helpers
// ---------------------------------------------------------------------------

/**
 * Load chats from TDLib.
 */
async function loadChats(client: TdLibClient, limit: number): Promise<TdChat[]> {
  // First, load the chat list (this triggers updateNewChat for each chat)
  await api.loadChats(client, limit);

  // The chats are sent via updateNewChat updates, not in the response.
  // We need to call getChats to get the ordered list.
  const chatsResponse = await api.getChats(client);

  const chatIds = chatsResponse.chat_ids || [];
  const chats: TdChat[] = [];

  // Get each chat's full info
  for (const chatId of chatIds) {
    try {
      const chat = await api.getChat(client, chatId);
      chats.push(chat);
    } catch (err) {
      console.warn(`[telegram-sync] Failed to get chat ${chatId}:`, err);
    }
  }

  return chats;
}

/**
 * Incremental sync - load recent messages for active chats.
 * Can be called periodically or on demand.
 */
export async function incrementalSync(
  client: TdLibClient,
  chatIds: number[],
  messagesPerChat = 50
): Promise<{ chatId: number; messageCount: number }[]> {
  const results: { chatId: number; messageCount: number }[] = [];

  for (const chatId of chatIds) {
    try {
      const messages = await api.getChatHistory(client, chatId, messagesPerChat);
      for (const msg of messages) {
        globalThis.telegramDb.upsertMessage(msg);
      }
      results.push({ chatId, messageCount: messages.length });
    } catch (err) {
      console.warn(`[telegram-sync] Incremental sync failed for chat ${chatId}:`, err);
      results.push({ chatId, messageCount: 0 });
    }
  }

  globalThis.telegramDb.setSyncState('last_sync_time', String(Date.now()));
  return results;
}

// Initial sync logic for loading Telegram data on authentication.
// Fetches chats, messages, and user info via TDLib and stores in SQLite.
// Import db-helpers to initialize globalThis.telegramDb
import './db-helpers';
import type { TdLibClient } from './tdlib-client';
import type { TdChat, TdMessage, TdUserFull } from './types';

// Extend globalThis for sync functions
declare global {
  var telegramSync: {
    performInitialSync: typeof performInitialSyncImpl;
    isSyncCompleted: typeof isSyncCompletedImpl;
    getLastSyncTime: typeof getLastSyncTimeImpl;
  };
}

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
 * @param onProgress - Optional callback for progress updates
 */
async function performInitialSyncImpl(
  client: TdLibClient,
  onProgress?: (message: string) => void
): Promise<void> {
  const log = (msg: string) => {
    console.log(`[telegram-sync] ${msg}`);
    onProgress?.(msg);
  };

  log('Starting initial sync...');

  try {
    // 1. Load chat list
    log('Loading chat list...');
    const chats = await loadChats(client, CHAT_LIMIT);
    log(`Loaded ${chats.length} chats`);

    // 2. Store chats
    for (const chat of chats) globalThis.telegramDb.upsertChat(chat);
    log('Stored all chats');

    // 3. Load messages for top chats
    const topChats = chats.slice(0, TOP_CHATS_FOR_MESSAGES);
    log(`Loading messages for top ${topChats.length} chats...`);

    for (let i = 0; i < topChats.length; i++) {
      const chat = topChats[i];
      log(`Loading messages for chat ${i + 1}/${topChats.length}: ${chat.title}`);

      try {
        const messages = await loadChatHistory(client, chat.id, MESSAGES_PER_CHAT);
        for (const msg of messages) {
          globalThis.telegramDb.upsertMessage(msg);

          // Also load sender info if it's a user
          if (msg.sender_id?.['@type'] === 'messageSenderUser' && msg.sender_id.user_id) {
            try {
              const user = await getUser(client, msg.sender_id.user_id);
              if (user) globalThis.telegramDb.upsertContact(user);
            } catch {
              // User may not be accessible, ignore
            }
          }
        }
        log(`  Loaded ${messages.length} messages`);
      } catch (err) {
        log(`  Error loading messages: ${err}`);
      }
    }

    // 4. Load contacts
    log('Loading contacts...');
    try {
      const contacts = await loadContacts(client);
      for (const user of contacts) {
        globalThis.telegramDb.upsertContact(user);
      }
      log(`Loaded ${contacts.length} contacts`);
    } catch (err) {
      log(`Error loading contacts: ${err}`);
    }

    // 5. Mark sync as complete
    globalThis.telegramDb.setSyncState('initial_sync_completed', 'true');
    globalThis.telegramDb.setSyncState('last_sync_time', String(Date.now()));
    log('Initial sync completed!');
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
  onProgress?: (message: string) => void
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
  await client.send({ '@type': 'loadChats', chat_list: { '@type': 'chatListMain' }, limit });

  // The chats are sent via updateNewChat updates, not in the response.
  // We need to call getChats to get the ordered list.
  const chatsResponse = await client.send({
    '@type': 'getChats',
    chat_list: { '@type': 'chatListMain' },
    limit,
  });

  const chatIds = (chatsResponse as { chat_ids?: number[] }).chat_ids || [];
  const chats: TdChat[] = [];

  // Get each chat's full info
  for (const chatId of chatIds) {
    try {
      const chat = await client.send({ '@type': 'getChat', chat_id: chatId });
      chats.push(chat as unknown as TdChat);
    } catch (err) {
      console.warn(`[telegram-sync] Failed to get chat ${chatId}:`, err);
    }
  }

  return chats;
}

/**
 * Load chat history from TDLib.
 */
async function loadChatHistory(
  client: TdLibClient,
  chatId: number,
  limit: number
): Promise<TdMessage[]> {
  const response = await client.send({
    '@type': 'getChatHistory',
    chat_id: chatId,
    from_message_id: 0, // Start from the latest
    offset: 0,
    limit,
    only_local: false,
  });

  return (response as { messages?: TdMessage[] }).messages || [];
}

/**
 * Get user info from TDLib.
 */
async function getUser(client: TdLibClient, userId: number): Promise<TdUserFull | null> {
  try {
    const response = await client.send({ '@type': 'getUser', user_id: userId });
    return response as unknown as TdUserFull;
  } catch {
    return null;
  }
}

/**
 * Load contacts from TDLib.
 */
async function loadContacts(client: TdLibClient): Promise<TdUserFull[]> {
  const response = await client.send({ '@type': 'getContacts' });

  const userIds = (response as { user_ids?: number[] }).user_ids || [];
  const users: TdUserFull[] = [];

  for (const userId of userIds) {
    const user = await getUser(client, userId);
    if (user) {
      users.push(user);
    }
  }

  return users;
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
      const messages = await loadChatHistory(client, chatId, messagesPerChat);
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

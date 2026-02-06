// TDLib update handlers for persisting data to SQLite.
// Each handler processes a specific update type and writes to the database.
// Import db-helpers to initialize globalThis.telegramDb
import './db-helpers';
import type { TdUpdate } from './tdlib-client';
import type {
  TdUpdateChatLastMessage,
  TdUpdateChatPosition,
  TdUpdateChatReadInbox,
  TdUpdateChatTitle,
  TdUpdateChatUnreadMentionCount,
  TdUpdateDeleteMessages,
  TdUpdateMessageContent,
  TdUpdateMessageEdited,
  TdUpdateNewChat,
  TdUpdateNewMessage,
  TdUpdateUser,
  TdUpdateUserStatus,
} from './types';

// ---------------------------------------------------------------------------
// Update Handler Registry
// ---------------------------------------------------------------------------

/**
 * Map of update types to their handlers.
 */
const updateHandlers: Record<string, (update: TdUpdate) => void> = {
  updateNewChat: handleUpdateNewChat,
  updateChatTitle: handleUpdateChatTitle,
  updateChatPosition: handleUpdateChatPosition,
  updateChatLastMessage: handleUpdateChatLastMessage,
  updateChatReadInbox: handleUpdateChatReadInbox,
  updateChatUnreadMentionCount: handleUpdateChatUnreadMentionCount,
  updateNewMessage: handleUpdateNewMessage,
  updateMessageContent: handleUpdateMessageContent,
  updateMessageEdited: handleUpdateMessageEdited,
  updateDeleteMessages: handleUpdateDeleteMessages,
  updateUser: handleUpdateUser,
  updateUserStatus: handleUpdateUserStatus,
};

/**
 * Main dispatch function for update handling.
 * Returns true if the update was handled, false otherwise.
 */
export function dispatchUpdate(update: TdUpdate): boolean {
  const handler = updateHandlers[update['@type']];
  if (handler) {
    try {
      handler(update);
      return true;
    } catch (err) {
      console.error(`[telegram] Error handling ${update['@type']}:`, err);
      return false;
    }
  }
  return false;
}

// ---------------------------------------------------------------------------
// Chat Update Handlers
// ---------------------------------------------------------------------------

/**
 * Handle new chat discovery.
 */
function handleUpdateNewChat(update: TdUpdate): void {
  const data = update as unknown as TdUpdateNewChat;
  if (!data.chat) return;

  console.log(`[telegram] New chat: ${data.chat.id} - ${data.chat.title}`);
  globalThis.telegramDb.upsertChat(data.chat);
}

/**
 * Handle chat title change.
 */
function handleUpdateChatTitle(update: TdUpdate): void {
  const data = update as unknown as TdUpdateChatTitle;
  if (!data.chat_id) return;

  console.log(`[telegram] Chat ${data.chat_id} title updated: ${data.title}`);
  globalThis.telegramDb.updateChatTitle(data.chat_id, data.title);
}

/**
 * Handle chat position change (ordering, pinned status).
 */
function handleUpdateChatPosition(update: TdUpdate): void {
  const data = update as unknown as TdUpdateChatPosition;
  if (!data.chat_id || !data.position) return;

  globalThis.telegramDb.updateChatPosition(data.chat_id, data.position);
}

/**
 * Handle chat last message update.
 */
function handleUpdateChatLastMessage(update: TdUpdate): void {
  const data = update as unknown as TdUpdateChatLastMessage;
  if (!data.chat_id) return;

  globalThis.telegramDb.updateChatLastMessage(data.chat_id, data.last_message, data.positions);
}

/**
 * Handle chat read inbox update (unread count change).
 */
function handleUpdateChatReadInbox(update: TdUpdate): void {
  const data = update as unknown as TdUpdateChatReadInbox;
  if (!data.chat_id) return;

  globalThis.telegramDb.updateChatUnreadCount(data.chat_id, data.unread_count);
}

/**
 * Handle chat unread mention count update.
 */
function handleUpdateChatUnreadMentionCount(update: TdUpdate): void {
  const data = update as unknown as TdUpdateChatUnreadMentionCount;
  if (!data.chat_id) return;

  globalThis.telegramDb.updateChatUnreadMentionCount(data.chat_id, data.unread_mention_count);
}

// ---------------------------------------------------------------------------
// Message Update Handlers
// ---------------------------------------------------------------------------

/**
 * Handle new message.
 */
function handleUpdateNewMessage(update: TdUpdate): void {
  const data = update as unknown as TdUpdateNewMessage;
  if (!data.message) return;

  globalThis.telegramDb.upsertMessage(data.message);
}

/**
 * Handle message content update.
 */
function handleUpdateMessageContent(update: TdUpdate): void {
  const data = update as unknown as TdUpdateMessageContent;
  if (!data.chat_id || !data.message_id || !data.new_content) return;

  globalThis.telegramDb.updateMessageContent(data.chat_id, data.message_id, data.new_content);
}

/**
 * Handle message edit.
 */
function handleUpdateMessageEdited(update: TdUpdate): void {
  const data = update as unknown as TdUpdateMessageEdited;
  if (!data.chat_id || !data.message_id) return;

  globalThis.telegramDb.markMessageEdited(data.chat_id, data.message_id, data.edit_date);
}

/**
 * Handle message deletion.
 */
function handleUpdateDeleteMessages(update: TdUpdate): void {
  const data = update as unknown as TdUpdateDeleteMessages;
  if (!data.chat_id || !data.message_ids || data.message_ids.length === 0) return;

  // Only soft delete if not from cache
  if (!data.from_cache) {
    globalThis.telegramDb.deleteMessages(data.chat_id, data.message_ids);
  }
}

// ---------------------------------------------------------------------------
// User Update Handlers
// ---------------------------------------------------------------------------

/**
 * Handle user update.
 */
function handleUpdateUser(update: TdUpdate): void {
  const data = update as unknown as TdUpdateUser;
  if (!data.user) return;

  globalThis.telegramDb.upsertContact(data.user);
}

/**
 * Handle user status update.
 */
function handleUpdateUserStatus(update: TdUpdate): void {
  const data = update as unknown as TdUpdateUserStatus;
  if (!data.user_id || !data.status) return;

  globalThis.telegramDb.updateUserStatus(data.user_id, data.status);
}

// ---------------------------------------------------------------------------
// GlobalThis Export (workaround for esbuild bundler issue)
// ---------------------------------------------------------------------------

declare global {
  var telegramDispatchUpdate: typeof dispatchUpdate;
}

globalThis.telegramDispatchUpdate = dispatchUpdate;

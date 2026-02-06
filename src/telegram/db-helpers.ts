// Database helper functions for upserting and querying Telegram data.
// All functions use the global `db` bridge API.
import type {
  ChatRow,
  ChatStats,
  ChatType,
  ContactRow,
  MessageRow,
  StorageStats,
  TdChat,
  TdChatPosition,
  TdMessage,
  TdMessageContent,
  TdUserFull,
  TdUserStatus,
} from './types';

// ---------------------------------------------------------------------------
// Utility Functions
// ---------------------------------------------------------------------------

/**
 * Convert TDLib chat type to simplified storage type.
 */
export function parseChatType(tdType: TdChat['type']): ChatType {
  switch (tdType['@type']) {
    case 'chatTypePrivate':
      return 'private';
    case 'chatTypeBasicGroup':
      return 'group';
    case 'chatTypeSupergroup':
      return tdType.is_channel ? 'channel' : 'supergroup';
    case 'chatTypeSecret':
      return 'secret';
    default:
      return 'private';
  }
}

/**
 * Extract text preview from message content.
 */
export function extractMessagePreview(content: TdMessageContent, maxLength = 100): string {
  const contentType = content['@type'];
  const c = content as Record<string, unknown>;

  switch (contentType) {
    case 'messageText': {
      const text = c.text as { text?: string } | undefined;
      return text?.text?.slice(0, maxLength) || '';
    }
    case 'messagePhoto': {
      const caption = c.caption as { text?: string } | undefined;
      return caption?.text?.slice(0, maxLength) || '📷 Photo';
    }
    case 'messageVideo': {
      const caption = c.caption as { text?: string } | undefined;
      return caption?.text?.slice(0, maxLength) || '🎬 Video';
    }
    case 'messageDocument': {
      const caption = c.caption as { text?: string } | undefined;
      return caption?.text?.slice(0, maxLength) || '📎 Document';
    }
    case 'messageAudio': {
      const caption = c.caption as { text?: string } | undefined;
      return caption?.text?.slice(0, maxLength) || '🎵 Audio';
    }
    case 'messageVoiceNote': {
      const caption = c.caption as { text?: string } | undefined;
      return caption?.text?.slice(0, maxLength) || '🎤 Voice message';
    }
    case 'messageVideoNote':
      return '📹 Video message';
    case 'messageSticker': {
      const sticker = c.sticker as { emoji?: string } | undefined;
      return sticker?.emoji ? `${sticker.emoji} Sticker` : '🎭 Sticker';
    }
    case 'messageAnimation': {
      const caption = c.caption as { text?: string } | undefined;
      return caption?.text?.slice(0, maxLength) || '🎞️ GIF';
    }
    case 'messageLocation':
      return '📍 Location';
    case 'messageContact': {
      const contact = c.contact as { first_name?: string } | undefined;
      return `👤 Contact: ${contact?.first_name || 'Unknown'}`;
    }
    case 'messagePoll': {
      const poll = c.poll as { question?: { text?: string } } | undefined;
      return `📊 Poll: ${poll?.question?.text || 'Poll'}`;
    }
    case 'messageCall':
      return '📞 Call';
    case 'messagePinMessage':
      return '📌 Pinned message';
    case 'messageChatAddMembers':
      return '👥 Members added';
    case 'messageChatJoinByLink':
      return '🔗 Joined via link';
    case 'messageChatDeleteMember':
      return '👋 Member left';
    default:
      return `[${contentType.replace('message', '')}]`;
  }
}

/**
 * Extract content type from message content.
 */
export function extractContentType(content: TdMessageContent): string {
  return content['@type'].replace('message', '').toLowerCase();
}

/**
 * Extract text content from message for full-text search.
 */
export function extractContentText(content: TdMessageContent): string | null {
  const contentType = content['@type'];
  const c = content as Record<string, unknown>;

  switch (contentType) {
    case 'messageText': {
      const text = c.text as { text?: string } | undefined;
      return text?.text || null;
    }
    case 'messagePhoto':
    case 'messageVideo':
    case 'messageDocument':
    case 'messageAudio':
    case 'messageVoiceNote':
    case 'messageAnimation': {
      const caption = c.caption as { text?: string } | undefined;
      return caption?.text || null;
    }
    default:
      return null;
  }
}

/**
 * Parse user status to string.
 */
export function parseUserStatus(status?: TdUserStatus): string {
  if (!status) return 'unknown';
  switch (status['@type']) {
    case 'userStatusOnline':
      return 'online';
    case 'userStatusOffline':
      return 'offline';
    case 'userStatusRecently':
      return 'recently';
    case 'userStatusLastWeek':
      return 'last_week';
    case 'userStatusLastMonth':
      return 'last_month';
    default:
      return 'unknown';
  }
}

/**
 * Get main chat position (from main chat list).
 */
export function getMainPosition(positions?: TdChatPosition[]): TdChatPosition | undefined {
  if (!positions || positions.length === 0) return undefined;
  return positions.find(p => p.list?.['@type'] === 'chatListMain') || positions[0];
}

// ---------------------------------------------------------------------------
// Upsert Functions
// ---------------------------------------------------------------------------

/**
 * Upsert a chat into the database.
 */
export function upsertChat(chat: TdChat): void {
  const now = Date.now();
  const id = String(chat.id);
  const type = parseChatType(chat.type);
  const position = getMainPosition(chat.positions);

  // Extract last message info
  let lastMessageId: string | null = null;
  let lastMessageDate: number | null = null;
  let lastMessagePreview: string | null = null;

  if (chat.last_message) {
    lastMessageId = String(chat.last_message.id);
    lastMessageDate = chat.last_message.date;
    lastMessagePreview = extractMessagePreview(chat.last_message.content);
  }

  // Check if chat exists
  const existing = db.get('SELECT id, created_at FROM chats WHERE id = ?', [id]);

  if (existing) {
    // Update existing chat
    db.exec(
      `UPDATE chats SET
        type = ?, title = ?, unread_count = ?, unread_mention_count = ?,
        last_message_id = COALESCE(?, last_message_id),
        last_message_date = COALESCE(?, last_message_date),
        last_message_preview = COALESCE(?, last_message_preview),
        order_position = COALESCE(?, order_position),
        is_pinned = COALESCE(?, is_pinned),
        is_muted = ?,
        photo_small = ?,
        updated_at = ?
      WHERE id = ?`,
      [
        type,
        chat.title || null,
        chat.unread_count ?? 0,
        chat.unread_mention_count ?? 0,
        lastMessageId,
        lastMessageDate,
        lastMessagePreview,
        position?.order || null,
        position?.is_pinned ? 1 : 0,
        chat.notification_settings?.mute_for ? 1 : 0,
        chat.photo?.small?.remote?.id || null,
        now,
        id,
      ]
    );
  } else {
    // Insert new chat
    db.exec(
      `INSERT INTO chats (
        id, type, title, username, unread_count, unread_mention_count,
        last_message_id, last_message_date, last_message_preview,
        order_position, is_pinned, is_muted, photo_small,
        created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        id,
        type,
        chat.title || null,
        null, // Username not in chat object, need to resolve from user
        chat.unread_count ?? 0,
        chat.unread_mention_count ?? 0,
        lastMessageId,
        lastMessageDate,
        lastMessagePreview,
        position?.order || null,
        position?.is_pinned ? 1 : 0,
        chat.notification_settings?.mute_for ? 1 : 0,
        chat.photo?.small?.remote?.id || null,
        now,
        now,
      ]
    );
  }
}

/**
 * Update chat title.
 */
export function updateChatTitle(chatId: number, title: string): void {
  const now = Date.now();
  db.exec('UPDATE chats SET title = ?, updated_at = ? WHERE id = ?', [title, now, String(chatId)]);
}

/**
 * Update chat position.
 */
export function updateChatPosition(chatId: number, position: TdChatPosition): void {
  const now = Date.now();
  db.exec('UPDATE chats SET order_position = ?, is_pinned = ?, updated_at = ? WHERE id = ?', [
    position.order || null,
    position.is_pinned ? 1 : 0,
    now,
    String(chatId),
  ]);
}

/**
 * Update chat last message.
 */
export function updateChatLastMessage(
  chatId: number,
  message: TdMessage | undefined,
  positions?: TdChatPosition[]
): void {
  const now = Date.now();
  const position = getMainPosition(positions);

  if (message) {
    db.exec(
      `UPDATE chats SET
        last_message_id = ?, last_message_date = ?, last_message_preview = ?,
        order_position = COALESCE(?, order_position),
        is_pinned = COALESCE(?, is_pinned),
        updated_at = ?
      WHERE id = ?`,
      [
        String(message.id),
        message.date,
        extractMessagePreview(message.content),
        position?.order || null,
        position?.is_pinned ? 1 : null,
        now,
        String(chatId),
      ]
    );
  } else if (position) {
    db.exec('UPDATE chats SET order_position = ?, is_pinned = ?, updated_at = ? WHERE id = ?', [
      position.order || null,
      position.is_pinned ? 1 : 0,
      now,
      String(chatId),
    ]);
  }
}

/**
 * Update chat unread count.
 */
export function updateChatUnreadCount(chatId: number, unreadCount: number): void {
  const now = Date.now();
  db.exec('UPDATE chats SET unread_count = ?, updated_at = ? WHERE id = ?', [
    unreadCount,
    now,
    String(chatId),
  ]);
}

/**
 * Update chat unread mention count.
 */
export function updateChatUnreadMentionCount(chatId: number, unreadMentionCount: number): void {
  const now = Date.now();
  db.exec('UPDATE chats SET unread_mention_count = ?, updated_at = ? WHERE id = ?', [
    unreadMentionCount,
    now,
    String(chatId),
  ]);
}

/**
 * Upsert a message into the database.
 */
export function upsertMessage(message: TdMessage): void {
  const now = Date.now();
  const id = String(message.id);
  const chatId = String(message.chat_id);

  // Extract sender info
  let senderId: string | null = null;
  let senderType: 'user' | 'chat' | null = null;

  if (message.sender_id) {
    if (message.sender_id['@type'] === 'messageSenderUser' && message.sender_id.user_id) {
      senderId = String(message.sender_id.user_id);
      senderType = 'user';
    } else if (message.sender_id['@type'] === 'messageSenderChat' && message.sender_id.chat_id) {
      senderId = String(message.sender_id.chat_id);
      senderType = 'chat';
    }
  }

  // Extract content
  const contentType = extractContentType(message.content);
  const contentText = extractContentText(message.content);

  // Extract content data (media metadata as JSON)
  let contentData: string | null = null;
  if (contentType !== 'text' && message.content) {
    try {
      // Store non-text content metadata
      const { '@type': _, ...data } = message.content as Record<string, unknown>;
      contentData = JSON.stringify(data);
    } catch {
      // Ignore serialization errors
    }
  }

  // Extract reply info
  let replyToMessageId: string | null = null;
  if (message.reply_to?.['@type'] === 'messageReplyToMessage' && message.reply_to.message_id) {
    replyToMessageId = String(message.reply_to.message_id);
  }

  // Extract forward info
  let forwardInfo: string | null = null;
  if (message.forward_info) {
    try {
      forwardInfo = JSON.stringify(message.forward_info);
    } catch {
      // Ignore serialization errors
    }
  }

  // Check if message exists
  const existing = db.get('SELECT id FROM messages WHERE chat_id = ? AND id = ?', [chatId, id]);

  if (existing) {
    // Update existing message
    db.exec(
      `UPDATE messages SET
        content_type = ?, content_text = ?, content_data = ?,
        edit_date = ?, is_pinned = ?, views = ?, updated_at = ?
      WHERE chat_id = ? AND id = ?`,
      [
        contentType,
        contentText,
        contentData,
        message.edit_date || null,
        message.is_pinned ? 1 : 0,
        message.interaction_info?.view_count || null,
        now,
        chatId,
        id,
      ]
    );
  } else {
    // Insert new message
    db.exec(
      `INSERT INTO messages (
        id, chat_id, sender_id, sender_type, content_type, content_text, content_data,
        date, edit_date, reply_to_message_id, forward_info, is_outgoing, is_pinned,
        is_deleted, views, created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        id,
        chatId,
        senderId,
        senderType,
        contentType,
        contentText,
        contentData,
        message.date,
        message.edit_date || null,
        replyToMessageId,
        forwardInfo,
        message.is_outgoing ? 1 : 0,
        message.is_pinned ? 1 : 0,
        0, // is_deleted
        message.interaction_info?.view_count || null,
        now,
        now,
      ]
    );
  }
}

/**
 * Update message content.
 */
export function updateMessageContent(
  chatId: number,
  messageId: number,
  content: TdMessageContent
): void {
  const now = Date.now();
  const contentType = extractContentType(content);
  const contentText = extractContentText(content);

  let contentData: string | null = null;
  if (contentType !== 'text') {
    try {
      const { '@type': _, ...data } = content as Record<string, unknown>;
      contentData = JSON.stringify(data);
    } catch {
      // Ignore
    }
  }

  db.exec(
    'UPDATE messages SET content_type = ?, content_text = ?, content_data = ?, updated_at = ? WHERE chat_id = ? AND id = ?',
    [contentType, contentText, contentData, now, String(chatId), String(messageId)]
  );
}

/**
 * Mark message as edited.
 */
export function markMessageEdited(chatId: number, messageId: number, editDate: number): void {
  const now = Date.now();
  db.exec('UPDATE messages SET edit_date = ?, updated_at = ? WHERE chat_id = ? AND id = ?', [
    editDate,
    now,
    String(chatId),
    String(messageId),
  ]);
}

/**
 * Soft delete messages.
 */
export function deleteMessages(chatId: number, messageIds: number[]): void {
  const now = Date.now();
  const chatIdStr = String(chatId);
  for (const msgId of messageIds) {
    db.exec('UPDATE messages SET is_deleted = 1, updated_at = ? WHERE chat_id = ? AND id = ?', [
      now,
      chatIdStr,
      String(msgId),
    ]);
  }
}

/**
 * Upsert a contact/user into the database.
 */
export function upsertContact(user: TdUserFull): void {
  const now = Date.now();
  const id = String(user.id);

  // Extract username
  const username =
    user.usernames?.active_usernames?.[0] || user.usernames?.editable_username || null;

  // Check if contact exists
  const existing = db.get('SELECT id, created_at FROM contacts WHERE id = ?', [id]);

  const isBot = user.type?.['@type'] === 'userTypeBot' ? 1 : 0;
  const status = parseUserStatus(user.status);

  if (existing) {
    // Update existing contact
    db.exec(
      `UPDATE contacts SET
        first_name = ?, last_name = ?, username = ?, phone_number = ?,
        is_bot = ?, is_premium = ?, is_contact = ?, status = ?,
        profile_photo_small = ?, updated_at = ?
      WHERE id = ?`,
      [
        user.first_name || null,
        user.last_name || null,
        username,
        user.phone_number || null,
        isBot,
        user.is_premium ? 1 : 0,
        user.is_contact ? 1 : 0,
        status,
        user.profile_photo?.small?.remote?.id || null,
        now,
        id,
      ]
    );
  } else {
    // Insert new contact
    db.exec(
      `INSERT INTO contacts (
        id, first_name, last_name, username, phone_number,
        is_bot, is_premium, is_contact, status, profile_photo_small,
        created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        id,
        user.first_name || null,
        user.last_name || null,
        username,
        user.phone_number || null,
        isBot,
        user.is_premium ? 1 : 0,
        user.is_contact ? 1 : 0,
        status,
        user.profile_photo?.small?.remote?.id || null,
        now,
        now,
      ]
    );
  }
}

/**
 * Update user status.
 */
export function updateUserStatus(userId: number, status: TdUserStatus): void {
  const now = Date.now();
  const statusStr = parseUserStatus(status);
  db.exec('UPDATE contacts SET status = ?, updated_at = ? WHERE id = ?', [
    statusStr,
    now,
    String(userId),
  ]);
}

// ---------------------------------------------------------------------------
// Sync State Functions
// ---------------------------------------------------------------------------

/**
 * Get a sync state value.
 */
export function getSyncState(key: string): string | null {
  const row = db.get('SELECT value FROM sync_state WHERE key = ?', [key]) as {
    value: string | null;
  } | null;
  return row?.value || null;
}

/**
 * Set a sync state value.
 */
export function setSyncState(key: string, value: string): void {
  const now = Date.now();
  const existing = db.get('SELECT key FROM sync_state WHERE key = ?', [key]);
  if (existing) {
    db.exec('UPDATE sync_state SET value = ?, updated_at = ? WHERE key = ?', [value, now, key]);
  } else {
    db.exec('INSERT INTO sync_state (key, value, updated_at) VALUES (?, ?, ?)', [key, value, now]);
  }
}

// ---------------------------------------------------------------------------
// Query Functions
// ---------------------------------------------------------------------------

/**
 * Get chats with optional filtering.
 */
export function getChats(options?: {
  type?: ChatType;
  unreadOnly?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}): ChatRow[] {
  const conditions: string[] = [];
  const params: unknown[] = [];

  if (options?.type) {
    conditions.push('type = ?');
    params.push(options.type);
  }

  if (options?.unreadOnly) {
    conditions.push('unread_count > 0');
  }

  if (options?.search) {
    conditions.push('(title LIKE ? OR username LIKE ?)');
    const searchTerm = `%${options.search}%`;
    params.push(searchTerm, searchTerm);
  }

  const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
  const limit = options?.limit || 50;
  const offset = options?.offset || 0;

  const sql = `
    SELECT * FROM chats
    ${whereClause}
    ORDER BY is_pinned DESC, order_position DESC, updated_at DESC
    LIMIT ? OFFSET ?
  `;

  params.push(limit, offset);

  return db.all(sql, params) as unknown as ChatRow[];
}

/**
 * Get messages from a chat with optional filtering.
 */
export function getMessages(
  chatId: string,
  options?: { contentType?: string; search?: string; beforeId?: string; limit?: number }
): MessageRow[] {
  const conditions: string[] = ['chat_id = ?', 'is_deleted = 0'];
  const params: unknown[] = [chatId];

  if (options?.contentType) {
    conditions.push('content_type = ?');
    params.push(options.contentType);
  }

  if (options?.search) {
    conditions.push('content_text LIKE ?');
    params.push(`%${options.search}%`);
  }

  if (options?.beforeId) {
    conditions.push('id < ?');
    params.push(options.beforeId);
  }

  const limit = options?.limit || 50;
  params.push(limit);

  const sql = `
    SELECT * FROM messages
    WHERE ${conditions.join(' AND ')}
    ORDER BY date DESC
    LIMIT ?
  `;

  return db.all(sql, params) as unknown as MessageRow[];
}

/**
 * Get contacts with optional filtering.
 */
export function getContacts(options?: {
  contactsOnly?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}): ContactRow[] {
  const conditions: string[] = [];
  const params: unknown[] = [];

  if (options?.contactsOnly) {
    conditions.push('is_contact = 1');
  }

  if (options?.search) {
    conditions.push('(first_name LIKE ? OR last_name LIKE ? OR username LIKE ?)');
    const searchTerm = `%${options.search}%`;
    params.push(searchTerm, searchTerm, searchTerm);
  }

  const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
  const limit = options?.limit || 50;
  const offset = options?.offset || 0;

  const sql = `
    SELECT * FROM contacts
    ${whereClause}
    ORDER BY is_contact DESC, first_name ASC
    LIMIT ? OFFSET ?
  `;

  params.push(limit, offset);

  return db.all(sql, params) as unknown as ContactRow[];
}

/**
 * Get chat statistics.
 */
export function getChatStats(chatId: string): ChatStats {
  const messageCount =
    (
      db.get('SELECT COUNT(*) as count FROM messages WHERE chat_id = ? AND is_deleted = 0', [
        chatId,
      ]) as { count: number }
    )?.count || 0;

  const textCount =
    (
      db.get(
        "SELECT COUNT(*) as count FROM messages WHERE chat_id = ? AND content_type = 'text' AND is_deleted = 0",
        [chatId]
      ) as { count: number }
    )?.count || 0;

  const dateRange = db.get(
    'SELECT MIN(date) as first_date, MAX(date) as last_date FROM messages WHERE chat_id = ? AND is_deleted = 0',
    [chatId]
  ) as { first_date: number | null; last_date: number | null } | null;

  const topSenders = db.all(
    `SELECT sender_id, COUNT(*) as count FROM messages
     WHERE chat_id = ? AND sender_id IS NOT NULL AND is_deleted = 0
     GROUP BY sender_id ORDER BY count DESC LIMIT 10`,
    [chatId]
  ) as Array<{ sender_id: string; count: number }>;

  const messageTypes = db.all(
    `SELECT content_type as type, COUNT(*) as count FROM messages
     WHERE chat_id = ? AND is_deleted = 0
     GROUP BY content_type ORDER BY count DESC`,
    [chatId]
  ) as Array<{ type: string; count: number }>;

  return {
    chat_id: chatId,
    message_count: messageCount,
    text_message_count: textCount,
    media_message_count: messageCount - textCount,
    first_message_date: dateRange?.first_date || null,
    last_message_date: dateRange?.last_date || null,
    top_senders: topSenders,
    message_types: messageTypes,
  };
}

/**
 * Get storage statistics for state publishing.
 */
export function getStorageStats(): StorageStats {
  const chatCount =
    (db.get('SELECT COUNT(*) as count FROM chats', []) as { count: number })?.count || 0;
  const messageCount =
    (db.get('SELECT COUNT(*) as count FROM messages WHERE is_deleted = 0', []) as { count: number })
      ?.count || 0;
  const contactCount =
    (db.get('SELECT COUNT(*) as count FROM contacts', []) as { count: number })?.count || 0;
  const unreadCount =
    (db.get('SELECT SUM(unread_count) as total FROM chats', []) as { total: number })?.total || 0;

  const syncCompleted = getSyncState('initial_sync_completed') === 'true';
  const lastSyncStr = getSyncState('last_sync_time');
  const lastSync = lastSyncStr ? parseInt(lastSyncStr, 10) : null;

  return { chatCount, messageCount, contactCount, unreadCount, syncCompleted, lastSync };
}

// ---------------------------------------------------------------------------
// GlobalThis Export (workaround for esbuild bundler issue)
// ---------------------------------------------------------------------------

// Extend globalThis type
declare global {
  var telegramDb: {
    parseChatType: typeof parseChatType;
    extractMessagePreview: typeof extractMessagePreview;
    extractContentType: typeof extractContentType;
    extractContentText: typeof extractContentText;
    parseUserStatus: typeof parseUserStatus;
    getMainPosition: typeof getMainPosition;
    upsertChat: typeof upsertChat;
    updateChatTitle: typeof updateChatTitle;
    updateChatPosition: typeof updateChatPosition;
    updateChatLastMessage: typeof updateChatLastMessage;
    updateChatUnreadCount: typeof updateChatUnreadCount;
    updateChatUnreadMentionCount: typeof updateChatUnreadMentionCount;
    upsertMessage: typeof upsertMessage;
    updateMessageContent: typeof updateMessageContent;
    markMessageEdited: typeof markMessageEdited;
    deleteMessages: typeof deleteMessages;
    upsertContact: typeof upsertContact;
    updateUserStatus: typeof updateUserStatus;
    getSyncState: typeof getSyncState;
    setSyncState: typeof setSyncState;
    getChats: typeof getChats;
    getMessages: typeof getMessages;
    getContacts: typeof getContacts;
    getChatStats: typeof getChatStats;
    getStorageStats: typeof getStorageStats;
  };
}

// Expose on globalThis for reliable access across bundled modules
globalThis.telegramDb = {
  parseChatType,
  extractMessagePreview,
  extractContentType,
  extractContentText,
  parseUserStatus,
  getMainPosition,
  upsertChat,
  updateChatTitle,
  updateChatPosition,
  updateChatLastMessage,
  updateChatUnreadCount,
  updateChatUnreadMentionCount,
  upsertMessage,
  updateMessageContent,
  markMessageEdited,
  deleteMessages,
  upsertContact,
  updateUserStatus,
  getSyncState,
  setSyncState,
  getChats,
  getMessages,
  getContacts,
  getChatStats,
  getStorageStats,
};

// Type definitions for TDLib objects and database rows.
// All Telegram IDs are represented as strings (int64 exceeds JS number precision).

// ---------------------------------------------------------------------------
// TDLib Object Types
// ---------------------------------------------------------------------------

/**
 * TDLib chat type enum values.
 */
export type TdChatType =
  | 'chatTypePrivate'
  | 'chatTypeBasicGroup'
  | 'chatTypeSupergroup'
  | 'chatTypeSecret';

/**
 * Simplified chat type for storage.
 */
export type ChatType = 'private' | 'group' | 'supergroup' | 'channel' | 'secret';

/**
 * TDLib chat object from updateNewChat, getChat, etc.
 */
export interface TdChat {
  '@type': 'chat';
  id: number;
  type: {
    '@type': TdChatType;
    user_id?: number;
    basic_group_id?: number;
    supergroup_id?: number;
    is_channel?: boolean;
    secret_chat_id?: number;
  };
  title: string;
  photo?: {
    small?: { local?: { path?: string }; remote?: { id?: string } };
    big?: { local?: { path?: string }; remote?: { id?: string } };
  };
  permissions?: Record<string, boolean>;
  last_message?: TdMessage;
  positions?: TdChatPosition[];
  unread_count?: number;
  unread_mention_count?: number;
  notification_settings?: { mute_for?: number };
}

/**
 * TDLib chat position for ordering.
 */
export interface TdChatPosition {
  '@type': 'chatPosition';
  list?: { '@type': string };
  order?: string;
  is_pinned?: boolean;
}

/**
 * TDLib message object from updateNewMessage, getMessage, etc.
 */
export interface TdMessage {
  '@type': 'message';
  id: number;
  chat_id: number;
  sender_id?: {
    '@type': 'messageSenderUser' | 'messageSenderChat';
    user_id?: number;
    chat_id?: number;
  };
  date: number;
  edit_date?: number;
  is_outgoing: boolean;
  is_pinned?: boolean;
  can_be_edited?: boolean;
  can_be_deleted_for_all_users?: boolean;
  reply_to?: { '@type': 'messageReplyToMessage'; chat_id?: number; message_id?: number };
  forward_info?: TdMessageForwardInfo;
  content: TdMessageContent;
  interaction_info?: { view_count?: number; forward_count?: number };
}

/**
 * TDLib message forward info.
 */
export interface TdMessageForwardInfo {
  '@type': 'messageForwardInfo';
  origin?: {
    '@type': string;
    sender_user_id?: number;
    sender_chat_id?: number;
    sender_name?: string;
  };
  date?: number;
  from_chat_id?: number;
  from_message_id?: number;
}

/**
 * TDLib message content types.
 */
export type TdMessageContent =
  | { '@type': 'messageText'; text: { '@type': 'formattedText'; text: string } }
  | { '@type': 'messagePhoto'; photo?: unknown; caption?: { text: string } }
  | { '@type': 'messageVideo'; video?: unknown; caption?: { text: string } }
  | { '@type': 'messageDocument'; document?: unknown; caption?: { text: string } }
  | { '@type': 'messageAudio'; audio?: unknown; caption?: { text: string } }
  | { '@type': 'messageVoiceNote'; voice_note?: unknown; caption?: { text: string } }
  | { '@type': 'messageVideoNote'; video_note?: unknown }
  | { '@type': 'messageSticker'; sticker?: { emoji?: string } }
  | { '@type': 'messageAnimation'; animation?: unknown; caption?: { text: string } }
  | { '@type': 'messageLocation'; location?: { latitude: number; longitude: number } }
  | { '@type': 'messageContact'; contact?: { first_name?: string; phone_number?: string } }
  | { '@type': 'messagePoll'; poll?: { question?: { text: string } } }
  | { '@type': 'messageCall'; duration?: number; discard_reason?: { '@type': string } }
  | { '@type': 'messagePinMessage'; message_id?: number }
  | { '@type': 'messageChatAddMembers'; member_user_ids?: number[] }
  | { '@type': 'messageChatJoinByLink' }
  | { '@type': 'messageChatDeleteMember'; user_id?: number }
  | { '@type': 'messageUnsupported' }
  | { '@type': string }; // Catch-all for other content types

/**
 * TDLib user object.
 */
export interface TdUserFull {
  '@type': 'user';
  id: number;
  first_name: string;
  last_name?: string;
  usernames?: { active_usernames?: string[]; editable_username?: string };
  phone_number?: string;
  status?: TdUserStatus;
  profile_photo?: {
    small?: { local?: { path?: string }; remote?: { id?: string } };
    big?: { local?: { path?: string }; remote?: { id?: string } };
  };
  is_contact?: boolean;
  is_mutual_contact?: boolean;
  is_verified?: boolean;
  is_premium?: boolean;
  is_support?: boolean;
  is_scam?: boolean;
  is_fake?: boolean;
  type?: { '@type': 'userTypeRegular' | 'userTypeBot' | 'userTypeDeleted' | 'userTypeUnknown' };
}

/**
 * TDLib user status types.
 */
export type TdUserStatus =
  | { '@type': 'userStatusOnline'; expires?: number }
  | { '@type': 'userStatusOffline'; was_online?: number }
  | { '@type': 'userStatusRecently' }
  | { '@type': 'userStatusLastWeek' }
  | { '@type': 'userStatusLastMonth' }
  | { '@type': 'userStatusEmpty' };

/**
 * TDLib update types we handle.
 */
export interface TdUpdateNewChat {
  '@type': 'updateNewChat';
  chat: TdChat;
}

export interface TdUpdateChatTitle {
  '@type': 'updateChatTitle';
  chat_id: number;
  title: string;
}

export interface TdUpdateChatPosition {
  '@type': 'updateChatPosition';
  chat_id: number;
  position: TdChatPosition;
}

export interface TdUpdateChatLastMessage {
  '@type': 'updateChatLastMessage';
  chat_id: number;
  last_message?: TdMessage;
  positions?: TdChatPosition[];
}

export interface TdUpdateChatReadInbox {
  '@type': 'updateChatReadInbox';
  chat_id: number;
  last_read_inbox_message_id: number;
  unread_count: number;
}

export interface TdUpdateChatUnreadMentionCount {
  '@type': 'updateChatUnreadMentionCount';
  chat_id: number;
  unread_mention_count: number;
}

export interface TdUpdateNewMessage {
  '@type': 'updateNewMessage';
  message: TdMessage;
}

export interface TdUpdateMessageContent {
  '@type': 'updateMessageContent';
  chat_id: number;
  message_id: number;
  new_content: TdMessageContent;
}

export interface TdUpdateMessageEdited {
  '@type': 'updateMessageEdited';
  chat_id: number;
  message_id: number;
  edit_date: number;
}

export interface TdUpdateDeleteMessages {
  '@type': 'updateDeleteMessages';
  chat_id: number;
  message_ids: number[];
  is_permanent: boolean;
  from_cache: boolean;
}

export interface TdUpdateUser {
  '@type': 'updateUser';
  user: TdUserFull;
}

export interface TdUpdateUserStatus {
  '@type': 'updateUserStatus';
  user_id: number;
  status: TdUserStatus;
}

// ---------------------------------------------------------------------------
// Database Row Types
// ---------------------------------------------------------------------------

/**
 * Chat row in the database.
 */
export interface ChatRow {
  id: string;
  type: ChatType;
  title: string | null;
  username: string | null;
  unread_count: number;
  unread_mention_count: number;
  last_message_id: string | null;
  last_message_date: number | null;
  last_message_preview: string | null;
  order_position: string | null;
  is_pinned: number;
  is_muted: number;
  photo_small: string | null;
  member_count: number | null;
  created_at: number;
  updated_at: number;
}

/**
 * Message row in the database.
 */
export interface MessageRow {
  id: string;
  chat_id: string;
  sender_id: string | null;
  sender_type: 'user' | 'chat' | null;
  content_type: string;
  content_text: string | null;
  content_data: string | null;
  date: number;
  edit_date: number | null;
  reply_to_message_id: string | null;
  forward_info: string | null;
  is_outgoing: number;
  is_pinned: number;
  is_deleted: number;
  views: number | null;
  created_at: number;
  updated_at: number;
}

/**
 * Contact row in the database.
 */
export interface ContactRow {
  id: string;
  first_name: string | null;
  last_name: string | null;
  username: string | null;
  phone_number: string | null;
  is_bot: number;
  is_premium: number;
  is_contact: number;
  status: string | null;
  profile_photo_small: string | null;
  created_at: number;
  updated_at: number;
}

/**
 * Chat summary row in the database.
 */
export interface ChatSummaryRow {
  chat_id: string;
  summary_text: string | null;
  key_topics: string | null;
  message_count_analyzed: number | null;
  last_message_id: string | null;
  created_at: number;
  updated_at: number;
}

/**
 * Sync state row in the database.
 */
export interface SyncStateRow {
  key: string;
  value: string | null;
  updated_at: number;
}

// ---------------------------------------------------------------------------
// Query Result Types
// ---------------------------------------------------------------------------

/**
 * Chat with optional last message preview for listings.
 */
export interface ChatWithPreview extends ChatRow {
  unread_total?: number;
}

/**
 * Message with sender info for display.
 */
export interface MessageWithSender extends MessageRow {
  sender_name?: string;
  sender_username?: string;
}

/**
 * Chat statistics for AI tools.
 */
export interface ChatStats {
  chat_id: string;
  message_count: number;
  text_message_count: number;
  media_message_count: number;
  first_message_date: number | null;
  last_message_date: number | null;
  top_senders: Array<{ sender_id: string; count: number }>;
  message_types: Array<{ type: string; count: number }>;
}

/**
 * Storage statistics for state publishing.
 */
export interface StorageStats {
  chatCount: number;
  messageCount: number;
  contactCount: number;
  unreadCount: number;
  syncCompleted: boolean;
  lastSync: number | null;
}

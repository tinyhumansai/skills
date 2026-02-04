// Export all Telegram tool definitions.

export { getChatsToolDefinition } from './get-chats';
export { getMessagesToolDefinition } from './get-messages';
export { getContactsToolDefinition } from './get-contacts';
export { getChatStatsToolDefinition } from './get-chat-stats';

/**
 * Get all storage-related tool definitions.
 */
export function getStorageToolDefinitions(): ToolDefinition[] {
  // Import lazily to avoid circular dependencies
  const { getChatsToolDefinition } = require('./get-chats');
  const { getMessagesToolDefinition } = require('./get-messages');
  const { getContactsToolDefinition } = require('./get-contacts');
  const { getChatStatsToolDefinition } = require('./get-chat-stats');

  return [
    getChatsToolDefinition,
    getMessagesToolDefinition,
    getContactsToolDefinition,
    getChatStatsToolDefinition,
  ];
}

// Tool: telegram-get-chats
// Get chat list with optional filtering.
import { getChats } from '../db-helpers';
import type { ChatType } from '../types';

/**
 * Get chats tool definition.
 */
export const getChatsToolDefinition: ToolDefinition = {
  name: 'telegram-get-chats',
  description:
    'Get Telegram chat list with optional filtering. Returns chats sorted by pinned status and recent activity. ' +
    'Use this to browse conversations, find specific chats, or filter by type (private, group, channel).',
  input_schema: {
    type: 'object',
    properties: {
      type: {
        type: 'string',
        description: 'Filter by chat type',
        enum: ['private', 'group', 'supergroup', 'channel'],
      },
      unread_only: {
        type: 'string',
        description: 'Only return chats with unread messages (true/false)',
        enum: ['true', 'false'],
      },
      search: { type: 'string', description: 'Search term to filter chats by title or username' },
      limit: {
        type: 'string',
        description: 'Maximum number of chats to return (default: 50, max: 100)',
      },
      offset: { type: 'string', description: 'Number of chats to skip for pagination' },
    },
    required: [],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const type = args.type as ChatType | undefined;
      const unreadOnly = args.unread_only === 'true';
      const search = args.search as string | undefined;
      const limit = Math.min(parseInt((args.limit as string) || '50', 10), 100);
      const offset = parseInt((args.offset as string) || '0', 10);

      const chats = getChats({ type, unreadOnly, search, limit, offset });

      // Format for readability
      const formattedChats = chats.map(chat => ({
        id: chat.id,
        type: chat.type,
        title: chat.title,
        username: chat.username,
        unread_count: chat.unread_count,
        is_pinned: chat.is_pinned === 1,
        is_muted: chat.is_muted === 1,
        last_message: chat.last_message_preview,
        last_message_date: chat.last_message_date
          ? new Date(chat.last_message_date * 1000).toISOString()
          : null,
      }));

      return JSON.stringify({
        success: true,
        count: formattedChats.length,
        chats: formattedChats,
        has_more: formattedChats.length === limit,
      });
    } catch (err) {
      return JSON.stringify({
        success: false,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  },
};

// Tool: telegram-get-messages
// Get messages from a chat with optional filtering.
import { getMessages } from '../db-helpers';

/**
 * Get messages tool definition.
 */
export const getMessagesToolDefinition: ToolDefinition = {
  name: 'telegram-get-messages',
  description:
    'Get messages from a specific Telegram chat. Supports filtering by content type, text search, and pagination. ' +
    'Returns messages in reverse chronological order (newest first).',
  input_schema: {
    type: 'object',
    properties: {
      chat_id: { type: 'string', description: 'The chat ID to get messages from (required)' },
      content_type: {
        type: 'string',
        description: 'Filter by message content type',
        enum: ['text', 'photo', 'video', 'document', 'audio', 'voicenote', 'sticker', 'animation'],
      },
      search: { type: 'string', description: 'Search term to filter messages by text content' },
      before_id: {
        type: 'string',
        description: 'Get messages before this message ID (for pagination)',
      },
      limit: {
        type: 'string',
        description: 'Maximum number of messages to return (default: 50, max: 100)',
      },
    },
    required: ['chat_id'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const chatId = args.chat_id as string;
      if (!chatId) {
        return JSON.stringify({ success: false, error: 'chat_id is required' });
      }

      const contentType = args.content_type as string | undefined;
      const search = args.search as string | undefined;
      const beforeId = args.before_id as string | undefined;
      const limit = Math.min(parseInt((args.limit as string) || '50', 10), 100);

      const messages = getMessages(chatId, { contentType, search, beforeId, limit });

      // Format for readability
      const formattedMessages = messages.map(msg => {
        const formatted: Record<string, unknown> = {
          id: msg.id,
          chat_id: msg.chat_id,
          sender_id: msg.sender_id,
          sender_type: msg.sender_type,
          content_type: msg.content_type,
          date: new Date(msg.date * 1000).toISOString(),
          is_outgoing: msg.is_outgoing === 1,
        };

        // Include text content if present
        if (msg.content_text) {
          formatted.text = msg.content_text;
        }

        // Include edit date if edited
        if (msg.edit_date) {
          formatted.edit_date = new Date(msg.edit_date * 1000).toISOString();
        }

        // Include reply info
        if (msg.reply_to_message_id) {
          formatted.reply_to_message_id = msg.reply_to_message_id;
        }

        // Include view count if present
        if (msg.views) {
          formatted.views = msg.views;
        }

        return formatted;
      });

      return JSON.stringify({
        success: true,
        chat_id: chatId,
        count: formattedMessages.length,
        messages: formattedMessages,
        has_more: formattedMessages.length === limit,
        oldest_id:
          formattedMessages.length > 0 ? formattedMessages[formattedMessages.length - 1].id : null,
      });
    } catch (err) {
      return JSON.stringify({
        success: false,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  },
};

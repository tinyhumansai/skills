// Tool: telegram-get-chat-stats
// Get statistics for a specific chat.
import { getChatStats, getContacts } from '../db-helpers';

/**
 * Get chat stats tool definition.
 */
export const getChatStatsToolDefinition: ToolDefinition = {
  name: 'telegram-get-chat-stats',
  description:
    'Get detailed statistics for a Telegram chat. Returns message counts, content type breakdown, ' +
    'top senders, and activity date range. Useful for understanding chat activity and composition.',
  input_schema: {
    type: 'object',
    properties: {
      chat_id: { type: 'string', description: 'The chat ID to get statistics for (required)' },
    },
    required: ['chat_id'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const chatId = args.chat_id as string;
      if (!chatId) {
        return JSON.stringify({ success: false, error: 'chat_id is required' });
      }

      const stats = getChatStats(chatId);

      // Enrich top senders with names
      const enrichedSenders = stats.top_senders.map(sender => {
        // Try to find the contact
        const contacts = getContacts({ search: sender.sender_id, limit: 1 });
        const contact = contacts.find(c => c.id === sender.sender_id);

        let name = 'Unknown';
        if (contact) {
          name = [contact.first_name, contact.last_name].filter(Boolean).join(' ') || 'Unknown';
        }

        return { sender_id: sender.sender_id, name, message_count: sender.count };
      });

      // Format message types
      const formattedTypes = stats.message_types.map(t => ({
        type: t.type,
        count: t.count,
        percentage: stats.message_count > 0 ? Math.round((t.count / stats.message_count) * 100) : 0,
      }));

      return JSON.stringify({
        success: true,
        chat_id: stats.chat_id,
        statistics: {
          total_messages: stats.message_count,
          text_messages: stats.text_message_count,
          media_messages: stats.media_message_count,
          text_percentage:
            stats.message_count > 0
              ? Math.round((stats.text_message_count / stats.message_count) * 100)
              : 0,
          first_message_date: stats.first_message_date
            ? new Date(stats.first_message_date * 1000).toISOString()
            : null,
          last_message_date: stats.last_message_date
            ? new Date(stats.last_message_date * 1000).toISOString()
            : null,
          days_active:
            stats.first_message_date && stats.last_message_date
              ? Math.ceil((stats.last_message_date - stats.first_message_date) / 86400)
              : 0,
        },
        top_senders: enrichedSenders,
        message_types: formattedTypes,
      });
    } catch (err) {
      return JSON.stringify({
        success: false,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  },
};

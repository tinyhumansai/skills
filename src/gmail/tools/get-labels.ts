// Tool: gmail-get-labels
// Get all Gmail labels with counts and details
import '../skill-state';

export const getLabelsTool: ToolDefinition = {
  name: 'gmail-get-labels',
  description:
    'Get all Gmail labels including system and user-created labels with message counts and details.',
  input_schema: {
    type: 'object',
    properties: {
      type: {
        type: 'string',
        enum: ['system', 'user', 'all'],
        description: 'Filter labels by type (default: all)',
      },
      include_hidden: { type: 'boolean', description: 'Include hidden labels (default: false)' },
    },
    required: [],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const gmailFetch = (globalThis as { gmailFetch?: (endpoint: string, options?: any) => any })
        .gmailFetch;
      if (!gmailFetch) {
        return JSON.stringify({ success: false, error: 'Gmail API helper not available' });
      }

      if (!oauth.getCredential()) {
        return JSON.stringify({
          success: false,
          error: 'Gmail not connected. Complete OAuth setup first.',
        });
      }

      const typeFilter = (args.type as string) || 'all';
      const includeHidden = args.include_hidden === true;

      // Get labels from Gmail API
      const response = gmailFetch('/users/me/labels');

      if (!response.success) {
        return JSON.stringify({
          success: false,
          error: response.error?.message || 'Failed to fetch labels',
        });
      }

      const labelsData = response.data as { labels: any[] };
      let labels = labelsData.labels || [];

      // Filter by type if specified
      if (typeFilter !== 'all') {
        labels = labels.filter(label => label.type === typeFilter);
      }

      // Filter hidden labels if not requested
      if (!includeHidden) {
        labels = labels.filter(
          label =>
            label.labelListVisibility === 'labelShow' ||
            label.labelListVisibility === 'labelShowIfUnread'
        );
      }

      // Format labels for response
      const formattedLabels = labels.map(label => ({
        id: label.id,
        name: label.name,
        type: label.type,
        visibility: {
          message_list: label.messageListVisibility,
          label_list: label.labelListVisibility,
        },
        counts: {
          messages_total: label.messagesTotal || 0,
          messages_unread: label.messagesUnread || 0,
          threads_total: label.threadsTotal || 0,
          threads_unread: label.threadsUnread || 0,
        },
        color: label.color
          ? { text: label.color.textColor, background: label.color.backgroundColor }
          : null,
      }));

      // Update local database
      const upsertLabel = (globalThis as { upsertLabel?: (label: any) => void }).upsertLabel;
      if (upsertLabel) {
        labels.forEach(label => upsertLabel(label));
      }

      // Categorize labels for easier use
      const categorized = {
        system: formattedLabels.filter(l => l.type === 'system'),
        user: formattedLabels.filter(l => l.type === 'user'),
      };

      return JSON.stringify({
        success: true,
        labels: formattedLabels,
        categorized,
        total_count: formattedLabels.length,
        system_count: categorized.system.length,
        user_count: categorized.user.length,
      });
    } catch (error) {
      return JSON.stringify({
        success: false,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  },
};

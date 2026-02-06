// Tool: gmail-get-emails
// Get emails with filtering and search capabilities
import '../skill-state';

export const getEmailsTool: ToolDefinition = {
  name: 'gmail-get-emails',
  description:
    'Get emails from Gmail with optional filtering by query, labels, read status, and pagination. Supports Gmail search syntax.',
  input_schema: {
    type: 'object',
    properties: {
      query: {
        type: 'string',
        description:
          'Search query using Gmail search syntax (e.g., "from:example@gmail.com", "subject:meeting", "is:unread")',
      },
      label_ids: {
        type: 'array',
        items: { type: 'string' },
        description: 'Filter by specific label IDs (e.g., ["INBOX", "IMPORTANT"])',
      },
      max_results: {
        type: 'number',
        description: 'Maximum number of emails to return (default: 20, max: 100)',
        minimum: 1,
        maximum: 100,
      },
      include_spam_trash: {
        type: 'boolean',
        description: 'Include emails from spam and trash (default: false)',
      },
      page_token: {
        type: 'string',
        description: 'Token for pagination (returned from previous request)',
      },
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

      // Build API parameters
      const params: string[] = [];

      if (args.query) {
        params.push(`q=${encodeURIComponent(args.query as string)}`);
      }

      if (args.label_ids && Array.isArray(args.label_ids)) {
        (args.label_ids as string[]).forEach(labelId => {
          params.push(`labelIds=${encodeURIComponent(labelId)}`);
        });
      }

      const maxResults = Math.min(parseInt((args.max_results as string) || '20', 10), 100);
      params.push(`maxResults=${maxResults}`);

      if (args.include_spam_trash) {
        params.push('includeSpamTrash=true');
      }

      if (args.page_token) {
        params.push(`pageToken=${encodeURIComponent(args.page_token as string)}`);
      }

      // Get email list
      const listResponse = gmailFetch(`/users/me/messages?${params.join('&')}`);

      if (!listResponse.success) {
        return JSON.stringify({
          success: false,
          error: listResponse.error?.message || 'Failed to fetch email list',
        });
      }

      const messageList = listResponse.data as {
        messages?: Array<{ id: string; threadId: string }>;
        nextPageToken?: string;
        resultSizeEstimate: number;
      };

      if (!messageList.messages || messageList.messages.length === 0) {
        return JSON.stringify({ success: true, emails: [], total_count: 0, next_page_token: null });
      }

      // Get detailed email data
      const emails = [];
      for (const msgRef of messageList.messages) {
        const msgResponse = gmailFetch(`/users/me/messages/${msgRef.id}`);
        if (msgResponse.success) {
          const message = msgResponse.data;
          const headers = message.payload?.headers || [];

          // Extract common headers
          const subject = headers.find((h: any) => h.name.toLowerCase() === 'subject')?.value || '';
          const from = headers.find((h: any) => h.name.toLowerCase() === 'from')?.value || '';
          const to = headers.find((h: any) => h.name.toLowerCase() === 'to')?.value || '';
          const date = headers.find((h: any) => h.name.toLowerCase() === 'date')?.value || '';

          // Parse sender info
          const fromMatch = from.match(/(.+?)\s*<([^>]+)>/) || [null, from, from];
          const senderName = fromMatch[1]?.trim().replace(/^["']|["']$/g, '') || null;
          const senderEmail = fromMatch[2]?.trim() || from;

          emails.push({
            id: message.id,
            thread_id: message.threadId,
            subject,
            sender: { email: senderEmail, name: senderName },
            recipients: to,
            date: date
              ? new Date(date).toISOString()
              : new Date(parseInt(message.internalDate)).toISOString(),
            snippet: message.snippet,
            label_ids: message.labelIds || [],
            is_read: !message.labelIds?.includes('UNREAD'),
            is_important: message.labelIds?.includes('IMPORTANT'),
            is_starred: message.labelIds?.includes('STARRED'),
            has_attachments: hasAttachments(message),
            size_estimate: message.sizeEstimate || 0,
          });

          // Store in local database for caching
          const upsertEmail = (globalThis as { upsertEmail?: (msg: any) => void }).upsertEmail;
          if (upsertEmail) {
            upsertEmail(message);
          }
        }
      }

      return JSON.stringify({
        success: true,
        emails,
        total_count: messageList.resultSizeEstimate,
        next_page_token: messageList.nextPageToken || null,
        query: args.query || null,
        label_ids: args.label_ids || null,
      });
    } catch (error) {
      return JSON.stringify({
        success: false,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  },
};

/**
 * Helper: Check if message has attachments
 */
function hasAttachments(message: any): boolean {
  if (message.payload?.body?.attachmentId) return true;
  if (message.payload?.parts) {
    return message.payload.parts.some(
      (part: any) => part.body?.attachmentId || (part.filename && part.filename.length > 0)
    );
  }
  return false;
}

// Tool: gmail-get-emails
// Get emails with filtering and search. Works with either OAuth credential (skill) or a provided accessToken (frontend after OAuth).
import { isSensitiveText } from '../../helpers';
import { getGmailSkillState } from '../state';

const GMAIL_API_BASE = 'https://gmail.googleapis.com/gmail/v1';

type GmailFetchResult = { success: boolean; data?: any; error?: { code: number; message: string } };

function buildListParams(args: Record<string, unknown>): string[] {
  const params: string[] = [];
  if (args.query) {
    params.push(`q=${encodeURIComponent(args.query as string)}`);
  }
  if (args.label_ids && Array.isArray(args.label_ids)) {
    (args.label_ids as string[]).forEach((labelId: string) => {
      params.push(`labelIds=${encodeURIComponent(labelId)}`);
    });
  }
  const maxResults = Math.min(
    parseInt(String(args.max_results ?? args.maxResults ?? 20), 10) || 20,
    100
  );
  params.push(`maxResults=${maxResults}`);
  if (args.include_spam_trash) {
    params.push('includeSpamTrash=true');
  }
  if (args.page_token) {
    params.push(`pageToken=${encodeURIComponent(args.page_token as string)}`);
  }
  return params;
}

/** Per-request timeout in seconds so a slow/hanging Gmail API call doesn't cause "Tool async execution timed out". */
const FETCH_TIMEOUT_SEC = 20;

async function fetchWithToken(
  accessToken: string,
  endpoint: string,
  _options?: { method?: string; body?: string }
): Promise<GmailFetchResult> {
  const url = endpoint.startsWith('/')
    ? `${GMAIL_API_BASE}${endpoint}`
    : `${GMAIL_API_BASE}/${endpoint}`;
  const headers: Record<string, string> = {
    Authorization: `Bearer ${accessToken}`,
    'Content-Type': 'application/json',
  };
  try {
    const res = await net.fetch(url, { method: 'GET', headers, timeout: FETCH_TIMEOUT_SEC });
    if (res.status < 200 || res.status >= 300) {
      const body = typeof res.body === 'string' ? res.body : JSON.stringify(res.body);
      return { success: false, error: { code: res.status, message: body } };
    }
    const data = typeof res.body === 'string' ? JSON.parse(res.body) : res.body;
    return { success: true, data };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { success: false, error: { code: 500, message } };
  }
}

function hasAttachments(message: any): boolean {
  if (message.payload?.body?.attachmentId) return true;
  if (message.payload?.parts) {
    return message.payload.parts.some(
      (part: any) => part.body?.attachmentId || (part.filename && part.filename.length > 0)
    );
  }
  return false;
}

function messageToEmailRow(message: any): Record<string, unknown> {
  const headers = message.payload?.headers || [];
  const getHeader = (name: string) =>
    headers.find((h: { name: string }) => h.name.toLowerCase() === name.toLowerCase())?.value || '';
  const subject = getHeader('Subject');
  const from = getHeader('From');
  const to = getHeader('To');
  const date = getHeader('Date');
  const fromMatch = from.match(/(.+?)\s*<([^>]+)>/) || [null, from, from];
  const senderName = (fromMatch[1]?.trim()?.replace(/^["']|["']$/g, '') as string) || null;
  const senderEmail = (fromMatch[2]?.trim() as string) || from;

  return {
    id: message.id,
    thread_id: message.threadId,
    subject,
    sender: { email: senderEmail, name: senderName },
    recipients: to,
    date: date
      ? new Date(date).toISOString()
      : new Date(parseInt(message.internalDate, 10)).toISOString(),
    snippet: message.snippet,
    label_ids: message.labelIds || [],
    is_read: !message.labelIds?.includes('UNREAD'),
    is_important: message.labelIds?.includes('IMPORTANT'),
    is_starred: message.labelIds?.includes('STARRED'),
    has_attachments: hasAttachments(message),
    size_estimate: message.sizeEstimate || 0,
  };
}

export const getEmailsTool: ToolDefinition = {
  name: 'get-emails',
  description:
    'Get emails from Gmail with optional filtering by query, labels, and pagination. Supports Gmail search syntax. When accessToken is provided (e.g. from frontend after OAuth), uses it directly; otherwise uses the skill OAuth credential.',
  input_schema: {
    type: 'object',
    properties: {
      accessToken: {
        type: 'string',
        description:
          'Optional OAuth access token. When provided (e.g. by frontend after OAuth), Gmail API is called directly with this token instead of the skill credential.',
      },
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
      maxResults: {
        type: 'number',
        description: 'Alias for max_results (e.g. for frontend calls)',
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
  async execute(args: Record<string, unknown>): Promise<string> {
    const accessToken = args.accessToken as string | undefined;
    const useToken = !!accessToken;

    if (!useToken) {
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
    }

    const params = buildListParams(args);
    const listEndpoint = `/users/me/messages?${params.join('&')}`;

    let listResponse: GmailFetchResult;
    if (useToken) {
      listResponse = await fetchWithToken(accessToken!, listEndpoint);
    } else {
      const gmailFetch = (
        globalThis as {
          gmailFetch?: (endpoint: string, options?: any) => Promise<GmailFetchResult>;
        }
      ).gmailFetch!;
      listResponse = await gmailFetch(listEndpoint);
    }

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
      return JSON.stringify({
        success: true,
        emails: [],
        total_count: messageList.resultSizeEstimate ?? 0,
        next_page_token: messageList.nextPageToken || null,
        query: args.query || null,
        label_ids: args.label_ids || null,
      });
    }

    const emails: Record<string, unknown>[] = [];

    for (const msgRef of messageList.messages) {
      // When using token, request metadata only to reduce payload and avoid timeout
      const msgEndpoint = useToken
        ? `/users/me/messages/${msgRef.id}?format=metadata&metadataHeaders=Subject&metadataHeaders=From&metadataHeaders=Date`
        : `/users/me/messages/${msgRef.id}`;
      let msgResponse: GmailFetchResult;

      if (useToken) {
        msgResponse = await fetchWithToken(accessToken!, msgEndpoint);
      } else {
        const gmailFetch = (
          globalThis as {
            gmailFetch?: (endpoint: string, options?: any) => Promise<GmailFetchResult>;
          }
        ).gmailFetch!;
        msgResponse = await gmailFetch(msgEndpoint);
      }

      if (msgResponse.success && msgResponse.data) {
        const message = msgResponse.data;
        emails.push(messageToEmailRow(message));

        if (!useToken) {
          const upsertEmail = (globalThis as { upsertEmail?: (msg: any) => void }).upsertEmail;
          if (upsertEmail) {
            upsertEmail(message);
          }
        }
      }
    }

    const s = getGmailSkillState();
    const showSensitive = s.config.showSensitiveMessages ?? false;
    const filteredEmails = showSensitive
      ? emails
      : emails.filter(
          (e: Record<string, unknown>) =>
            !isSensitiveText(((e.subject as string) || '') + ' ' + ((e.snippet as string) || ''))
        );

    return JSON.stringify({
      success: true,
      emails: filteredEmails,
      total_count: messageList.resultSizeEstimate ?? 0,
      next_page_token: messageList.nextPageToken || null,
      query: args.query || null,
      label_ids: args.label_ids || null,
    });
  },
};

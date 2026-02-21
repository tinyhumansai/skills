// Tool: gmail-get-profile
// Get Gmail user profile information. Supports optional accessToken (e.g. from frontend after OAuth).
import { getGmailSkillState } from '../state';

const GMAIL_API_BASE = 'https://gmail.googleapis.com/gmail/v1';

async function fetchWithToken(
  accessToken: string,
  endpoint: string
): Promise<{ success: boolean; data?: any; error?: { message: string } }> {
  const url = endpoint.startsWith('/')
    ? `${GMAIL_API_BASE}${endpoint}`
    : `${GMAIL_API_BASE}/${endpoint}`;
  const headers = { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' };
  try {
    const res = await net.fetch(url, { method: 'GET', headers });
    if (res.status < 200 || res.status >= 300) {
      const body = typeof res.body === 'string' ? res.body : JSON.stringify(res.body);
      return { success: false, error: { message: body } };
    }
    const data = typeof res.body === 'string' ? JSON.parse(res.body) : res.body;
    return { success: true, data };
  } catch (err) {
    return { success: false, error: { message: err instanceof Error ? err.message : String(err) } };
  }
}

export const getProfileTool: ToolDefinition = {
  name: 'get-profile',
  description:
    'Get Gmail user profile information including email address, total message counts, and account details. Optional accessToken for frontend calls.',
  input_schema: {
    type: 'object',
    properties: {
      accessToken: {
        type: 'string',
        description: 'Optional OAuth access token (e.g. from frontend).',
      },
    },
    required: [],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const accessToken = args.accessToken as string | undefined;
      const useToken = !!accessToken;

      if (!useToken) {
        const gmailFetch = (
          globalThis as {
            gmailFetch?: (
              endpoint: string
            ) => Promise<{ success: boolean; data?: any; error?: { message: string } }>;
          }
        ).gmailFetch;
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

      const response = useToken
        ? await fetchWithToken(accessToken!, '/users/me/profile')
        : await (
            globalThis as {
              gmailFetch?: (
                e: string
              ) => Promise<{ success: boolean; data?: any; error?: { message: string } }>;
            }
          ).gmailFetch!('/users/me/profile');

      if (!response.success) {
        return JSON.stringify({
          success: false,
          error: response.error?.message || 'Failed to fetch profile',
        });
      }

      const profile = response.data;

      if (!useToken) {
        const s = getGmailSkillState();
        s.profile = {
          emailAddress: profile.emailAddress,
          messagesTotal: profile.messagesTotal || 0,
          threadsTotal: profile.threadsTotal || 0,
          historyId: profile.historyId,
        };
        if (!s.config.userEmail) {
          s.config.userEmail = profile.emailAddress;
          state.set('config', s.config);
        }
      }

      return JSON.stringify({
        success: true,
        profile: {
          email_address: profile.emailAddress,
          messages_total: profile.messagesTotal || 0,
          threads_total: profile.threadsTotal || 0,
          history_id: profile.historyId,
        },
      });
    } catch (error) {
      return JSON.stringify({
        success: false,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  },
};

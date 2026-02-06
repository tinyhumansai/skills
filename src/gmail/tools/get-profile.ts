// Tool: gmail-get-profile
// Get Gmail user profile information
import '../skill-state';

export const getProfileTool: ToolDefinition = {
  name: 'gmail-get-profile',
  description:
    'Get Gmail user profile information including email address, total message counts, and account details.',
  input_schema: { type: 'object', properties: {}, required: [] },
  execute(_args: Record<string, unknown>): string {
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

      // Get profile from Gmail API
      const response = gmailFetch('/users/me/profile');

      if (!response.success) {
        return JSON.stringify({
          success: false,
          error: response.error?.message || 'Failed to fetch profile',
        });
      }

      const profile = response.data;

      // Update skill state with profile info
      const s = globalThis.getGmailSkillState();
      s.profile = {
        emailAddress: profile.emailAddress,
        messagesTotal: profile.messagesTotal || 0,
        threadsTotal: profile.threadsTotal || 0,
        historyId: profile.historyId,
      };

      // Update config with user email if not already set
      if (!s.config.userEmail) {
        s.config.userEmail = profile.emailAddress;
        store.set('config', s.config);
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

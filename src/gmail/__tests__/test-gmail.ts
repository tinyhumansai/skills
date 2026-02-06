// test-gmail.ts — Comprehensive tests for the Gmail skill.
// Runs via the V8 test harness.

// All globals (describe, it, assert*, setupSkillTest, callTool, etc.)
// are available from the harness scripts loaded before this file.

// Helpers to access the typed globals
const _describe = (globalThis as any).describe as (name: string, fn: () => void) => void;
const _it = (globalThis as any).it as (name: string, fn: () => void) => void;
const _assert = (globalThis as any).assert as (cond: unknown, msg?: string) => void;
const _assertEqual = (globalThis as any).assertEqual as (
  a: unknown,
  b: unknown,
  msg?: string
) => void;
const _assertNotNull = (globalThis as any).assertNotNull as (v: unknown, msg?: string) => void;
const _assertContains = (globalThis as any).assertContains as (
  h: string,
  n: string,
  msg?: string
) => void;
const _setup = (globalThis as any).setupSkillTest as (opts?: any) => void;
const _callTool = (globalThis as any).callTool as (name: string, args?: any) => any;
const _getMockState = (globalThis as any).getMockState as () => any;
const _mockFetchResponse = (globalThis as any).mockFetchResponse as (
  url: string,
  status: number,
  body: string
) => void;
const _mockFetchError = (globalThis as any).mockFetchError as (
  url: string,
  message?: string
) => void;

// Sample Gmail API responses for testing
const SAMPLE_PROFILE_RESPONSE = {
  emailAddress: 'test@example.com',
  messagesTotal: 1500,
  threadsTotal: 980,
  historyId: '12345',
};

const SAMPLE_EMAIL_RESPONSE = {
  id: 'msg123',
  threadId: 'thread456',
  labelIds: ['INBOX', 'UNREAD'],
  snippet: 'This is a test email snippet...',
  sizeEstimate: 2048,
  historyId: '12346',
  internalDate: '1640995200000',
  payload: {
    partId: '',
    mimeType: 'multipart/alternative',
    filename: '',
    headers: [
      { name: 'From', value: 'John Doe <john@example.com>' },
      { name: 'To', value: 'test@example.com' },
      { name: 'Subject', value: 'Test Email Subject' },
      { name: 'Date', value: 'Sat, 01 Jan 2022 12:00:00 +0000' },
      { name: 'Message-ID', value: '<msg123@example.com>' },
    ],
    body: { size: 0 },
    parts: [
      {
        partId: '0',
        mimeType: 'text/plain',
        filename: '',
        headers: [{ name: 'Content-Type', value: 'text/plain; charset=utf-8' }],
        body: { size: 26, data: btoa('This is the email body.') },
      },
      {
        partId: '1',
        mimeType: 'text/html',
        filename: '',
        headers: [{ name: 'Content-Type', value: 'text/html; charset=utf-8' }],
        body: { size: 52, data: btoa('<p>This is the <strong>email</strong> body.</p>') },
      },
    ],
  },
};

const SAMPLE_LABELS_RESPONSE = {
  labels: [
    {
      id: 'INBOX',
      name: 'INBOX',
      type: 'system',
      messageListVisibility: 'show',
      labelListVisibility: 'labelShow',
      messagesTotal: 150,
      messagesUnread: 5,
      threadsTotal: 100,
      threadsUnread: 3,
    },
    {
      id: 'SENT',
      name: 'SENT',
      type: 'system',
      messageListVisibility: 'show',
      labelListVisibility: 'labelShow',
      messagesTotal: 50,
      messagesUnread: 0,
      threadsTotal: 45,
      threadsUnread: 0,
    },
    {
      id: 'Label_123',
      name: 'Work',
      type: 'user',
      messageListVisibility: 'show',
      labelListVisibility: 'labelShow',
      messagesTotal: 25,
      messagesUnread: 2,
      threadsTotal: 20,
      threadsUnread: 1,
      color: { textColor: '#ffffff', backgroundColor: '#0d7377' },
    },
  ],
};

const SAMPLE_EMAIL_LIST_RESPONSE = {
  messages: [
    { id: 'msg123', threadId: 'thread456' },
    { id: 'msg124', threadId: 'thread457' },
  ],
  nextPageToken: 'next123',
  resultSizeEstimate: 150,
};

const SAMPLE_SENT_EMAIL_RESPONSE = {
  id: 'sent123',
  threadId: 'thread789',
  labelIds: ['SENT'],
  sizeEstimate: 1024,
};

/**
 * Helper to setup authenticated skill test
 */
function setupAuthenticatedGmailTest(overrides?: any): void {
  _setup({
    storeData: {
      config: {
        clientId: 'test_client_id',
        clientSecret: 'test_client_secret',
        refreshToken: 'test_refresh_token',
        accessToken: 'test_access_token',
        tokenExpiry: Date.now() + 3600000, // 1 hour from now
        userEmail: 'test@example.com',
        isAuthenticated: true,
        syncEnabled: true,
        syncIntervalMinutes: 15,
        maxEmailsPerSync: 100,
        notifyOnNewEmails: true,
        ...overrides,
      },
    },
    fetchResponses: {
      'https://gmail.googleapis.com/gmail/v1/users/me/profile': {
        status: 200,
        body: JSON.stringify(SAMPLE_PROFILE_RESPONSE),
      },
      'https://gmail.googleapis.com/gmail/v1/users/me/messages': {
        status: 200,
        body: JSON.stringify(SAMPLE_EMAIL_LIST_RESPONSE),
      },
      'https://gmail.googleapis.com/gmail/v1/users/me/messages/msg123': {
        status: 200,
        body: JSON.stringify(SAMPLE_EMAIL_RESPONSE),
      },
      'https://gmail.googleapis.com/gmail/v1/users/me/messages/msg124': {
        status: 200,
        body: JSON.stringify({ ...SAMPLE_EMAIL_RESPONSE, id: 'msg124' }),
      },
      'https://gmail.googleapis.com/gmail/v1/users/me/labels': {
        status: 200,
        body: JSON.stringify(SAMPLE_LABELS_RESPONSE),
      },
      'https://gmail.googleapis.com/gmail/v1/users/me/messages/send': {
        status: 200,
        body: JSON.stringify(SAMPLE_SENT_EMAIL_RESPONSE),
      },
      'https://gmail.googleapis.com/gmail/v1/users/me/messages/batchModify': {
        status: 200,
        body: JSON.stringify({}),
      },
    },
  });

  init();
}

/**
 * Helper to setup unauthenticated skill test
 */
function setupUnauthenticatedGmailTest(): void {
  _setup({ storeData: {}, fetchResponses: {} });

  init();
}

_describe('Gmail Skill', () => {
  _describe('Initialization', () => {
    _it('should initialize with default config when no stored config exists', () => {
      setupUnauthenticatedGmailTest();

      const state = globalThis.getGmailSkillState();
      _assertNotNull(state);
      _assertEqual(state.config.isAuthenticated, false);
      _assertEqual(state.config.syncEnabled, true);
      _assertEqual(state.config.syncIntervalMinutes, 15);
    });

    _it('should load stored config on init', () => {
      setupAuthenticatedGmailTest();

      const state = globalThis.getGmailSkillState();
      _assertEqual(state.config.isAuthenticated, true);
      _assertEqual(state.config.userEmail, 'test@example.com');
      _assertEqual(state.config.clientId, 'test_client_id');
    });

    _it('should initialize database schema', () => {
      setupAuthenticatedGmailTest();

      // Check that tables exist by running a query
      const result = db.get(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='emails'",
        []
      );
      _assertNotNull(result);
    });
  });

  _describe('Gmail Profile Tool', () => {
    _it('should get Gmail profile when authenticated', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-get-profile');
      const response = JSON.parse(result);

      _assertEqual(response.success, true);
      _assertEqual(response.profile.email_address, 'test@example.com');
      _assertEqual(response.profile.messages_total, 1500);
      _assertEqual(response.profile.threads_total, 980);
    });

    _it('should fail when not authenticated', () => {
      setupUnauthenticatedGmailTest();

      const result = _callTool('gmail-get-profile');
      const response = JSON.parse(result);

      _assertEqual(response.success, false);
      _assertContains(response.error, 'authentication required');
    });
  });

  _describe('Get Emails Tool', () => {
    _it('should get emails successfully', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-get-emails', { max_results: 10 });
      const response = JSON.parse(result);

      _assertEqual(response.success, true);
      _assertNotNull(response.emails);
      _assertEqual(response.emails.length, 2);
      _assertEqual(response.emails[0].id, 'msg123');
      _assertEqual(response.emails[0].subject, 'Test Email Subject');
      _assertEqual(response.emails[0].sender.email, 'john@example.com');
    });

    _it('should handle query parameter', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-get-emails', {
        query: 'from:john@example.com',
        max_results: 5,
      });
      const response = JSON.parse(result);

      _assertEqual(response.success, true);
      _assertEqual(response.query, 'from:john@example.com');
    });

    _it('should handle label filtering', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-get-emails', {
        label_ids: ['INBOX', 'UNREAD'],
        max_results: 10,
      });
      const response = JSON.parse(result);

      _assertEqual(response.success, true);
      _assertNotNull(response.label_ids);
    });

    _it('should respect max_results limit', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-get-emails', { max_results: 1 });
      const response = JSON.parse(result);

      _assertEqual(response.success, true);
      // Since our mock returns 2 emails, but we limited to 1,
      // the actual implementation should honor this
    });
  });

  _describe('Get Email Tool', () => {
    _it('should get specific email by ID', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-get-email', { message_id: 'msg123' });
      const response = JSON.parse(result);

      _assertEqual(response.success, true);
      _assertEqual(response.email.id, 'msg123');
      _assertEqual(response.email.thread_id, 'thread456');
      _assertEqual(response.email.headers.subject, 'Test Email Subject');
      _assertEqual(response.email.sender.email, 'john@example.com');
      _assertEqual(response.email.sender.name, 'John Doe');
    });

    _it('should extract email bodies', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-get-email', { message_id: 'msg123', include_body: true });
      const response = JSON.parse(result);

      _assertEqual(response.success, true);
      _assertNotNull(response.email.body);
      _assertEqual(response.email.body.text, 'This is the email body.');
      _assertContains(response.email.body.html, '<strong>email</strong>');
    });

    _it('should require message_id parameter', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-get-email', {});
      const response = JSON.parse(result);

      _assertEqual(response.success, false);
      _assertContains(response.error, 'message_id is required');
    });
  });

  _describe('Send Email Tool', () => {
    _it('should send email successfully', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-send-email', {
        to: [{ email: 'recipient@example.com', name: 'Recipient Name' }],
        subject: 'Test Email',
        body_text: 'This is a test email.',
      });
      const response = JSON.parse(result);

      _assertEqual(response.success, true);
      _assertEqual(response.message_id, 'sent123');
      _assertEqual(response.subject, 'Test Email');
    });

    _it('should handle CC and BCC recipients', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-send-email', {
        to: [{ email: 'to@example.com' }],
        cc: [{ email: 'cc@example.com' }],
        bcc: [{ email: 'bcc@example.com' }],
        subject: 'Test Email with CC/BCC',
        body_text: 'Test content.',
      });
      const response = JSON.parse(result);

      _assertEqual(response.success, true);
    });

    _it('should require recipients', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-send-email', {
        subject: 'Test Email',
        body_text: 'Test content.',
      });
      const response = JSON.parse(result);

      _assertEqual(response.success, false);
      _assertContains(response.error, 'recipient is required');
    });

    _it('should require subject', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-send-email', {
        to: [{ email: 'test@example.com' }],
        body_text: 'Test content.',
      });
      const response = JSON.parse(result);

      _assertEqual(response.success, false);
      _assertContains(response.error, 'Subject is required');
    });

    _it('should require body content', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-send-email', {
        to: [{ email: 'test@example.com' }],
        subject: 'Test Email',
      });
      const response = JSON.parse(result);

      _assertEqual(response.success, false);
      _assertContains(response.error, 'body_text or body_html is required');
    });
  });

  _describe('Get Labels Tool', () => {
    _it('should get all labels', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-get-labels');
      const response = JSON.parse(result);

      _assertEqual(response.success, true);
      _assertEqual(response.labels.length, 3);
      _assertEqual(response.system_count, 2);
      _assertEqual(response.user_count, 1);

      const inboxLabel = response.labels.find((l: any) => l.id === 'INBOX');
      _assertNotNull(inboxLabel);
      _assertEqual(inboxLabel.counts.messages_unread, 5);
    });

    _it('should filter by label type', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-get-labels', { type: 'system' });
      const response = JSON.parse(result);

      _assertEqual(response.success, true);
      // The actual filtering would happen in the real implementation
      // For now, just verify the tool accepts the parameter
      _assertNotNull(response.labels);
    });
  });

  _describe('Search Emails Tool', () => {
    _it('should search emails with query', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-search-emails', {
        query: 'from:john@example.com subject:test',
      });
      const response = JSON.parse(result);

      _assertEqual(response.success, true);
      _assertEqual(response.query, 'from:john@example.com subject:test');
      _assertNotNull(response.emails);
      _assertNotNull(response.search_tips);
    });

    _it('should require query parameter', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-search-emails', {});
      const response = JSON.parse(result);

      _assertEqual(response.success, false);
      _assertContains(response.error, 'query is required');
    });

    _it('should provide search tips', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-search-emails', { query: 'simple search' });
      const response = JSON.parse(result);

      _assertEqual(response.success, true);
      _assert(Array.isArray(response.search_tips));
      _assert(response.search_tips.length > 0);
    });
  });

  _describe('Mark Email Tool', () => {
    _it('should mark email as read', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-mark-email', {
        message_ids: ['msg123'],
        action: 'mark_read',
      });
      const response = JSON.parse(result);

      _assertEqual(response.success, true);
      _assertEqual(response.action, 'mark_read');
      _assertEqual(response.successful, 1);
    });

    _it('should handle multiple message IDs', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-mark-email', {
        message_ids: ['msg123', 'msg124'],
        action: 'mark_unread',
      });
      const response = JSON.parse(result);

      _assertEqual(response.success, true);
      _assertEqual(response.total_processed, 2);
    });

    _it('should require message IDs', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-mark-email', { action: 'mark_read' });
      const response = JSON.parse(result);

      _assertEqual(response.success, false);
      _assertContains(response.error, 'message ID is required');
    });

    _it('should require label_ids for label actions', () => {
      setupAuthenticatedGmailTest();

      const result = _callTool('gmail-mark-email', {
        message_ids: ['msg123'],
        action: 'add_labels',
      });
      const response = JSON.parse(result);

      _assertEqual(response.success, false);
      _assertContains(response.error, 'label_ids are required');
    });
  });

  _describe('Authentication', () => {
    _it('should handle token refresh', () => {
      // Mock expired token
      setupAuthenticatedGmailTest({
        tokenExpiry: Date.now() - 1000, // Expired 1 second ago
      });

      // Mock refresh token response
      _mockFetchResponse(
        'https://oauth2.googleapis.com/token',
        200,
        JSON.stringify({ access_token: 'new_access_token', expires_in: 3600, token_type: 'Bearer' })
      );

      // This should trigger token refresh
      const result = _callTool('gmail-get-profile');
      const response = JSON.parse(result);

      _assertEqual(response.success, true);
    });

    _it('should handle authentication failure', () => {
      setupUnauthenticatedGmailTest();

      const result = _callTool('gmail-get-emails');
      const response = JSON.parse(result);

      _assertEqual(response.success, false);
      _assertContains(response.error, 'authentication required');
    });
  });

  _describe('Error Handling', () => {
    _it('should handle API errors gracefully', () => {
      setupAuthenticatedGmailTest();

      // Mock API error
      _mockFetchResponse(
        'https://gmail.googleapis.com/gmail/v1/users/me/messages',
        400,
        JSON.stringify({
          error: {
            code: 400,
            message: 'Bad Request',
            errors: [{ domain: 'global', reason: 'badRequest', message: 'Invalid query' }],
          },
        })
      );

      const result = _callTool('gmail-get-emails');
      const response = JSON.parse(result);

      _assertEqual(response.success, false);
      _assertContains(response.error, 'Bad Request');
    });

    _it('should handle network errors', () => {
      setupAuthenticatedGmailTest();

      _mockFetchError('https://gmail.googleapis.com/gmail/v1/users/me/messages');

      const result = _callTool('gmail-get-emails');
      const response = JSON.parse(result);

      _assertEqual(response.success, false);
      _assertNotNull(response.error);
    });
  });

  _describe('Database Operations', () => {
    _it('should store emails in database', () => {
      setupAuthenticatedGmailTest();

      // Trigger email fetch which should store in DB
      _callTool('gmail-get-emails');

      // Check if emails were stored
      const emails = db.all('SELECT * FROM emails', []);
      _assert(emails.length > 0);
    });

    _it('should store labels in database', () => {
      setupAuthenticatedGmailTest();

      // Trigger label fetch
      _callTool('gmail-get-labels');

      // Check if labels were stored
      const labels = db.all('SELECT * FROM labels', []);
      _assert(labels.length > 0);
    });
  });
});

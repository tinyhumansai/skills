// Database helper functions for Gmail skill
// CRUD operations for emails, threads, labels, and attachments
import './skill-state';
import type {
  DatabaseAttachment,
  DatabaseEmail,
  DatabaseLabel,
  DatabaseThread,
  EmailSearchOptions,
  GmailLabel,
  GmailMessage,
  GmailThread,
} from './types';

/**
 * Insert or update an email in the database
 */
export function upsertEmail(message: GmailMessage): void {
  const now = Date.now();
  const headers = message.payload.headers;

  const subject = headers.find(h => h.name.toLowerCase() === 'subject')?.value || '';
  const from = headers.find(h => h.name.toLowerCase() === 'from')?.value || '';
  const to = headers.find(h => h.name.toLowerCase() === 'to')?.value || '';
  const cc = headers.find(h => h.name.toLowerCase() === 'cc')?.value || null;
  const bcc = headers.find(h => h.name.toLowerCase() === 'bcc')?.value || null;
  const dateHeader = headers.find(h => h.name.toLowerCase() === 'date')?.value;

  // Parse sender email and name from "Name <email>" format
  const fromMatch = from.match(/(.+?)\s*<([^>]+)>/) || [null, from, from];
  const senderName = fromMatch[1]?.trim().replace(/^["']|["']$/g, '') || null;
  const senderEmail = fromMatch[2]?.trim() || from;

  const date = dateHeader ? new Date(dateHeader).getTime() : parseInt(message.internalDate, 10);
  const isRead = !message.labelIds.includes('UNREAD');
  const isImportant = message.labelIds.includes('IMPORTANT');
  const isStarred = message.labelIds.includes('STARRED');
  const hasAttachments = hasEmailAttachments(message);

  db.exec(
    `INSERT OR REPLACE INTO emails (
      id, thread_id, subject, sender_email, sender_name, recipient_emails,
      cc_emails, bcc_emails, date, snippet, body_text, body_html,
      is_read, is_important, is_starred, has_attachments, labels,
      size_estimate, history_id, internal_date, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      message.id,
      message.threadId,
      subject,
      senderEmail,
      senderName,
      to,
      cc,
      bcc,
      date,
      message.snippet,
      extractTextBody(message),
      extractHtmlBody(message),
      isRead ? 1 : 0,
      isImportant ? 1 : 0,
      isStarred ? 1 : 0,
      hasAttachments ? 1 : 0,
      JSON.stringify(message.labelIds),
      message.sizeEstimate,
      message.historyId,
      message.internalDate,
      now,
    ]
  );

  // Insert attachments if any
  if (hasAttachments) {
    insertEmailAttachments(message);
  }
}

/**
 * Insert or update a thread in the database
 */
export function upsertThread(thread: GmailThread): void {
  const now = Date.now();
  const firstMessage = thread.messages[0];
  const lastMessage = thread.messages[thread.messages.length - 1];

  if (!firstMessage || !lastMessage) return;

  const subject =
    firstMessage.payload.headers.find(h => h.name.toLowerCase() === 'subject')?.value || '';
  const participants = new Set<string>();

  // Collect all participants from all messages
  thread.messages.forEach(msg => {
    const headers = msg.payload.headers;
    const from = headers.find(h => h.name.toLowerCase() === 'from')?.value;
    const to = headers.find(h => h.name.toLowerCase() === 'to')?.value;
    const cc = headers.find(h => h.name.toLowerCase() === 'cc')?.value;

    if (from) participants.add(extractEmail(from));
    if (to) to.split(',').forEach(email => participants.add(extractEmail(email.trim())));
    if (cc) cc.split(',').forEach(email => participants.add(extractEmail(email.trim())));
  });

  const lastMessageDate = parseInt(lastMessage.internalDate, 10);
  const allLabels = new Set<string>();
  let hasAttachments = false;
  let allRead = true;

  thread.messages.forEach(msg => {
    msg.labelIds.forEach(label => allLabels.add(label));
    if (hasEmailAttachments(msg)) hasAttachments = true;
    if (msg.labelIds.includes('UNREAD')) allRead = false;
  });

  db.exec(
    `INSERT OR REPLACE INTO threads (
      id, subject, snippet, message_count, participants, last_message_date,
      is_read, has_attachments, labels, history_id, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      thread.id,
      subject,
      thread.snippet,
      thread.messages.length,
      Array.from(participants).join(', '),
      lastMessageDate,
      allRead ? 1 : 0,
      hasAttachments ? 1 : 0,
      JSON.stringify(Array.from(allLabels)),
      thread.historyId,
      now,
    ]
  );
}

/**
 * Insert or update a label in the database
 */
export function upsertLabel(label: GmailLabel): void {
  const now = Date.now();

  db.exec(
    `INSERT OR REPLACE INTO labels (
      id, name, type, message_list_visibility, label_list_visibility,
      messages_total, messages_unread, threads_total, threads_unread,
      color_text, color_background, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      label.id,
      label.name,
      label.type,
      label.messageListVisibility,
      label.labelListVisibility,
      label.messagesTotal || 0,
      label.messagesUnread || 0,
      label.threadsTotal || 0,
      label.threadsUnread || 0,
      label.color?.textColor || null,
      label.color?.backgroundColor || null,
      now,
    ]
  );
}

/**
 * Get emails with optional filtering
 */
export function getEmails(options: EmailSearchOptions = {}): DatabaseEmail[] {
  let sql = 'SELECT * FROM emails WHERE 1=1';
  const params: unknown[] = [];

  if (options.query) {
    sql += ' AND (subject LIKE ? OR sender_email LIKE ? OR snippet LIKE ?)';
    const searchTerm = `%${options.query}%`;
    params.push(searchTerm, searchTerm, searchTerm);
  }

  if (options.labelIds && options.labelIds.length > 0) {
    const labelConditions = options.labelIds.map(() => 'labels LIKE ?').join(' OR ');
    sql += ` AND (${labelConditions})`;
    options.labelIds.forEach(labelId => {
      params.push(`%"${labelId}"%`);
    });
  }

  sql += ' ORDER BY date DESC';

  if (options.maxResults) {
    sql += ' LIMIT ?';
    params.push(options.maxResults);
  }

  return db.all(sql, params) as unknown as DatabaseEmail[];
}

/**
 * Get threads with optional filtering
 */
export function getThreads(options: EmailSearchOptions = {}): DatabaseThread[] {
  let sql = 'SELECT * FROM threads WHERE 1=1';
  const params: unknown[] = [];

  if (options.query) {
    sql += ' AND (subject LIKE ? OR participants LIKE ? OR snippet LIKE ?)';
    const searchTerm = `%${options.query}%`;
    params.push(searchTerm, searchTerm, searchTerm);
  }

  if (options.labelIds && options.labelIds.length > 0) {
    const labelConditions = options.labelIds.map(() => 'labels LIKE ?').join(' OR ');
    sql += ` AND (${labelConditions})`;
    options.labelIds.forEach(labelId => {
      params.push(`%"${labelId}"%`);
    });
  }

  sql += ' ORDER BY last_message_date DESC';

  if (options.maxResults) {
    sql += ' LIMIT ?';
    params.push(options.maxResults);
  }

  return db.all(sql, params) as unknown as DatabaseThread[];
}

/**
 * Get all labels
 */
export function getLabels(): DatabaseLabel[] {
  return db.all('SELECT * FROM labels ORDER BY type, name', []) as unknown as DatabaseLabel[];
}

/**
 * Get email by ID
 */
export function getEmailById(id: string): DatabaseEmail | null {
  return db.get('SELECT * FROM emails WHERE id = ?', [id]) as DatabaseEmail | null;
}

/**
 * Get thread by ID
 */
export function getThreadById(id: string): DatabaseThread | null {
  return db.get('SELECT * FROM threads WHERE id = ?', [id]) as DatabaseThread | null;
}

/**
 * Get attachments for an email
 */
export function getEmailAttachments(messageId: string): DatabaseAttachment[] {
  return db.all('SELECT * FROM attachments WHERE message_id = ?', [
    messageId,
  ]) as unknown as DatabaseAttachment[];
}

/**
 * Update email read status
 */
export function updateEmailReadStatus(emailId: string, isRead: boolean): void {
  db.exec('UPDATE emails SET is_read = ?, updated_at = ? WHERE id = ?', [
    isRead ? 1 : 0,
    Date.now(),
    emailId,
  ]);
}

/**
 * Get sync state value
 */
export function getSyncState(key: string): string | null {
  const row = db.get('SELECT value FROM sync_state WHERE key = ?', [key]) as {
    value: string;
  } | null;
  return row?.value || null;
}

/**
 * Set sync state value
 */
export function setSyncState(key: string, value: string): void {
  db.exec(
    `INSERT OR REPLACE INTO sync_state (key, value, updated_at)
     VALUES (?, ?, ?)`,
    [key, value, Date.now()]
  );
}

/**
 * Helper: Extract email address from "Name <email>" format
 */
function extractEmail(emailStr: string): string {
  const match = emailStr.match(/<([^>]+)>/);
  return match ? match[1] : emailStr.trim();
}

/**
 * Helper: Check if email has attachments
 */
function hasEmailAttachments(message: GmailMessage): boolean {
  if (message.payload.body.attachmentId) return true;
  if (message.payload.parts) {
    return message.payload.parts.some(
      part => part.body.attachmentId || (part.filename && part.filename.length > 0)
    );
  }
  return false;
}

/**
 * Helper: Extract text body from message
 */
function extractTextBody(message: GmailMessage): string | null {
  if (message.payload.mimeType === 'text/plain' && message.payload.body.data) {
    return atob(message.payload.body.data);
  }

  if (message.payload.parts) {
    for (const part of message.payload.parts) {
      if (part.mimeType === 'text/plain' && part.body.data) {
        return atob(part.body.data);
      }
    }
  }

  return null;
}

/**
 * Helper: Extract HTML body from message
 */
function extractHtmlBody(message: GmailMessage): string | null {
  if (message.payload.mimeType === 'text/html' && message.payload.body.data) {
    return atob(message.payload.body.data);
  }

  if (message.payload.parts) {
    for (const part of message.payload.parts) {
      if (part.mimeType === 'text/html' && part.body.data) {
        return atob(part.body.data);
      }
    }
  }

  return null;
}

/**
 * Helper: Insert email attachments
 */
function insertEmailAttachments(message: GmailMessage): void {
  const attachments: Array<{
    attachmentId: string;
    filename: string;
    mimeType: string;
    size: number;
    partId: string;
  }> = [];

  // Check main body
  if (message.payload.body.attachmentId && message.payload.filename) {
    attachments.push({
      attachmentId: message.payload.body.attachmentId,
      filename: message.payload.filename,
      mimeType: message.payload.mimeType,
      size: message.payload.body.size,
      partId: message.payload.partId,
    });
  }

  // Check parts
  if (message.payload.parts) {
    message.payload.parts.forEach(part => {
      if (part.body.attachmentId && part.filename) {
        attachments.push({
          attachmentId: part.body.attachmentId,
          filename: part.filename,
          mimeType: part.mimeType,
          size: part.body.size,
          partId: part.partId,
        });
      }
    });
  }

  // Insert attachments
  attachments.forEach(att => {
    db.exec(
      `INSERT OR REPLACE INTO attachments
       (message_id, attachment_id, filename, mime_type, size, part_id)
       VALUES (?, ?, ?, ?, ?, ?)`,
      [message.id, att.attachmentId, att.filename, att.mimeType, att.size, att.partId]
    );
  });
}

// Expose helper functions on globalThis for tools to use
const _g = globalThis as Record<string, unknown>;
_g.upsertEmail = upsertEmail;
_g.upsertThread = upsertThread;
_g.upsertLabel = upsertLabel;
_g.getEmails = getEmails;
_g.getThreads = getThreads;
_g.getLabels = getLabels;
_g.getEmailById = getEmailById;
_g.getThreadById = getThreadById;
_g.getEmailAttachments = getEmailAttachments;
_g.updateEmailReadStatus = updateEmailReadStatus;
_g.getSyncState = getSyncState;
_g.setSyncState = setSyncState;

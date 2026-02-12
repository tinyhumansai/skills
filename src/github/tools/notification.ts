// Notification tools (3 tools)
import { ghGet, ghPatch, ghPut } from '../api';
import { optBoolean, optNumber, reqString } from '../helpers';

export const listNotificationsTool: ToolDefinition = {
  name: 'list-notifications',
  description: 'List GitHub notifications for the authenticated user',
  input_schema: {
    type: 'object',
    properties: {
      all: { type: 'boolean', description: 'Include read notifications' },
      limit: { type: 'number', description: 'Maximum number of notifications to return' },
    },
    required: [],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const all = optBoolean(args, 'all', false);
      const limit = optNumber(args, 'limit', 30);

      const notifications = (await ghGet(`/notifications?all=${all}&per_page=${limit}`)) as any[];
      if (!notifications || notifications.length === 0)
        return JSON.stringify({ message: 'No notifications.' });

      const lines = notifications.map((n: any) => {
        const reason = n.reason || '';
        const repoName = n.repository?.full_name || '';
        const title = n.subject?.title || '';
        const ntype = n.subject?.type || '';
        const unread = n.unread ? '[unread]' : '[read]';
        return `${unread} [${repoName}] ${ntype}: ${title} (${reason})`;
      });
      return JSON.stringify({ notifications: lines.join('\n'), count: lines.length });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const markNotificationReadTool: ToolDefinition = {
  name: 'mark-notification-read',
  description: 'Mark a specific notification thread as read',
  input_schema: {
    type: 'object',
    properties: { thread_id: { type: 'string', description: 'Notification thread ID' } },
    required: ['thread_id'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const threadId = reqString(args, 'thread_id');
      await ghPatch(`/notifications/threads/${threadId}`, {});
      return JSON.stringify({ message: `Notification ${threadId} marked as read.` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const markAllNotificationsReadTool: ToolDefinition = {
  name: 'mark-all-notifications-read',
  description: 'Mark all notifications as read',
  input_schema: { type: 'object', properties: {}, required: [] },
  async execute(_args: Record<string, unknown>): Promise<string> {
    try {
      await ghPut('/notifications', { last_read_at: new Date().toISOString() });
      return JSON.stringify({ message: 'All notifications marked as read.' });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const notificationTools: ToolDefinition[] = [
  listNotificationsTool,
  markNotificationReadTool,
  markAllNotificationsReadTool,
];

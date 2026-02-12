// Issue tools (12 tools)
import { ghDelete, ghGet, ghPatch, ghPost } from '../api';
import {
  optNumber,
  optString,
  optStringList,
  reqString,
  truncate,
  validatePositiveInt,
  validateRepoSpec,
} from '../helpers';

export const listIssuesTool: ToolDefinition = {
  name: 'list-issues',
  description: 'List issues in a repository with optional filters',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      limit: { type: 'number', description: 'Maximum number of issues to return' },
      state: { type: 'string', description: 'Filter by state', enum: ['open', 'closed', 'all'] },
      label: { type: 'string', description: 'Filter by label name' },
      assignee: { type: 'string', description: 'Filter by assignee username' },
    },
    required: ['owner', 'repo'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const limit = optNumber(args, 'limit', 30);
      const issueState = optString(args, 'state') || 'open';
      const label = optString(args, 'label');
      const assignee = optString(args, 'assignee');

      let endpoint = `/repos/${spec}/issues?state=${issueState}&per_page=${limit}`;
      if (label) endpoint += `&labels=${encodeURIComponent(label)}`;
      if (assignee) endpoint += `&assignee=${encodeURIComponent(assignee)}`;

      const issues = (await ghGet(endpoint)) as any[];
      // Filter out PRs (GitHub API returns PRs as issues)
      const filtered = (issues || []).filter((i: any) => !i.pull_request).slice(0, limit);

      if (!filtered.length)
        return JSON.stringify({ message: `No ${issueState} issues in ${spec}.` });

      const lines = filtered.map((i: any) => {
        const labels = i.labels?.map((l: any) => l.name).join(', ') || '';
        const author = i.user?.login || '';
        let line = `#${i.number} [${i.state.toUpperCase()}] ${i.title.substring(0, 80)}`;
        if (author) line += ` (by @${author})`;
        if (labels) line += ` [${labels}]`;
        return line;
      });
      return JSON.stringify({ issues: lines.join('\n'), count: lines.length });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const getIssueTool: ToolDefinition = {
  name: 'get-issue',
  description: 'Get detailed information about a specific issue',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Issue number' },
    },
    required: ['owner', 'repo', 'number'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      const i = (await ghGet(`/repos/${spec}/issues/${number}`)) as any;

      const labels = i.labels?.map((l: any) => l.name) || [];
      const assignees = i.assignees?.map((a: any) => a.login) || [];
      const milestone = i.milestone?.title || '';

      const lines = [
        `Issue #${i.number}: ${i.title}`,
        `State: ${i.state}`,
        i.user ? `Author: @${i.user.login}` : '',
        labels.length ? `Labels: ${labels.join(', ')}` : '',
        assignees.length ? `Assignees: ${assignees.map((a: string) => '@' + a).join(', ')}` : '',
        milestone ? `Milestone: ${milestone}` : '',
        `Comments: ${i.comments}`,
        `Created: ${i.created_at}`,
        `Updated: ${i.updated_at}`,
        '',
        truncate(i.body || '(no description)', 3000),
      ].filter(l => l || l === '');
      return JSON.stringify({ info: lines.join('\n') });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const createIssueTool: ToolDefinition = {
  name: 'create-issue',
  description: 'Create a new issue in a repository',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      title: { type: 'string', description: 'Issue title' },
      body: { type: 'string', description: 'Issue body (Markdown supported)' },
      labels: { type: 'array', items: { type: 'string' }, description: 'Labels to apply' },
      assignees: { type: 'array', items: { type: 'string' }, description: 'Usernames to assign' },
    },
    required: ['owner', 'repo', 'title'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const title = reqString(args, 'title');
      const body = optString(args, 'body');
      const labels = optStringList(args, 'labels');
      const assignees = optStringList(args, 'assignees');

      const payload: Record<string, unknown> = { title };
      if (body) payload.body = body;
      if (labels.length) payload.labels = labels;
      if (assignees.length) payload.assignees = assignees;

      const r = (await ghPost(`/repos/${spec}/issues`, payload)) as any;
      return JSON.stringify({ message: `Issue created: ${r.html_url}` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const closeIssueTool: ToolDefinition = {
  name: 'close-issue',
  description: 'Close an issue',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Issue number' },
      reason: {
        type: 'string',
        description: 'Reason for closing',
        enum: ['completed', 'not_planned'],
      },
    },
    required: ['owner', 'repo', 'number'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      const reason = optString(args, 'reason');
      const payload: Record<string, unknown> = { state: 'closed' };
      if (reason) payload.state_reason = reason;
      await ghPatch(`/repos/${spec}/issues/${number}`, payload);
      return JSON.stringify({ message: `Issue #${number} closed.` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const reopenIssueTool: ToolDefinition = {
  name: 'reopen-issue',
  description: 'Reopen a closed issue',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Issue number' },
    },
    required: ['owner', 'repo', 'number'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      await ghPatch(`/repos/${spec}/issues/${number}`, { state: 'open' });
      return JSON.stringify({ message: `Issue #${number} reopened.` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const editIssueTool: ToolDefinition = {
  name: 'edit-issue',
  description: "Edit an existing issue's title or body",
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Issue number' },
      title: { type: 'string', description: 'New issue title' },
      body: { type: 'string', description: 'New issue body' },
    },
    required: ['owner', 'repo', 'number'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      const title = optString(args, 'title');
      const body = optString(args, 'body');

      if (!title && !body)
        return JSON.stringify({ error: 'Provide at least one field to edit (title or body).' });

      const payload: Record<string, unknown> = {};
      if (title) payload.title = title;
      if (body) payload.body = body;
      await ghPatch(`/repos/${spec}/issues/${number}`, payload);
      return JSON.stringify({ message: `Issue #${number} updated.` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const commentOnIssueTool: ToolDefinition = {
  name: 'comment-on-issue',
  description: 'Add a comment to an issue',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Issue number' },
      body: { type: 'string', description: 'Comment body (Markdown supported)' },
    },
    required: ['owner', 'repo', 'number', 'body'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      const body = reqString(args, 'body');
      const r = (await ghPost(`/repos/${spec}/issues/${number}/comments`, { body })) as any;
      return JSON.stringify({ message: `Comment added to issue #${number}: ${r.html_url}` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const listIssueCommentsTool: ToolDefinition = {
  name: 'list-issue-comments',
  description: 'List comments on an issue',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Issue number' },
      limit: { type: 'number', description: 'Maximum number of comments to return' },
    },
    required: ['owner', 'repo', 'number'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      const limit = optNumber(args, 'limit', 30);

      const comments = (await ghGet(
        `/repos/${spec}/issues/${number}/comments?per_page=${limit}`
      )) as any[];
      if (!comments || comments.length === 0)
        return JSON.stringify({ message: `No comments on issue #${number}.` });

      const lines = comments.map((c: any) => {
        const author = c.user?.login || 'unknown';
        const bodyText = (c.body || '').substring(0, 200);
        return `@${author} (${c.created_at}):\n${bodyText}\n`;
      });
      return JSON.stringify({ comments: truncate(lines.join('\n')) });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const addIssueLabelsTool: ToolDefinition = {
  name: 'add-issue-labels',
  description: 'Add labels to an issue',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Issue number' },
      labels: { type: 'array', items: { type: 'string' }, description: 'Labels to add' },
    },
    required: ['owner', 'repo', 'number', 'labels'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      const labels = optStringList(args, 'labels');
      if (!labels.length) return JSON.stringify({ error: 'At least one label is required.' });
      await ghPost(`/repos/${spec}/issues/${number}/labels`, { labels });
      return JSON.stringify({ message: `Labels added to issue #${number}: ${labels.join(', ')}` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const removeIssueLabelsTool: ToolDefinition = {
  name: 'remove-issue-labels',
  description: 'Remove labels from an issue',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Issue number' },
      labels: { type: 'array', items: { type: 'string' }, description: 'Labels to remove' },
    },
    required: ['owner', 'repo', 'number', 'labels'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      const labels = optStringList(args, 'labels');
      if (!labels.length) return JSON.stringify({ error: 'At least one label is required.' });
      for (const label of labels) {
        await ghDelete(`/repos/${spec}/issues/${number}/labels/${encodeURIComponent(label)}`);
      }
      return JSON.stringify({
        message: `Labels removed from issue #${number}: ${labels.join(', ')}`,
      });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const addIssueAssigneesTool: ToolDefinition = {
  name: 'add-issue-assignees',
  description: 'Add assignees to an issue',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Issue number' },
      assignees: { type: 'array', items: { type: 'string' }, description: 'Usernames to assign' },
    },
    required: ['owner', 'repo', 'number', 'assignees'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      const assignees = optStringList(args, 'assignees');
      if (!assignees.length) return JSON.stringify({ error: 'At least one assignee is required.' });
      await ghPost(`/repos/${spec}/issues/${number}/assignees`, { assignees });
      return JSON.stringify({
        message: `Assignees added to issue #${number}: ${assignees.join(', ')}`,
      });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const removeIssueAssigneesTool: ToolDefinition = {
  name: 'remove-issue-assignees',
  description: 'Remove assignees from an issue',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Issue number' },
      assignees: { type: 'array', items: { type: 'string' }, description: 'Usernames to remove' },
    },
    required: ['owner', 'repo', 'number', 'assignees'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      const assignees = optStringList(args, 'assignees');
      if (!assignees.length) return JSON.stringify({ error: 'At least one assignee is required.' });
      await ghDelete(`/repos/${spec}/issues/${number}/assignees`);
      return JSON.stringify({
        message: `Assignees removed from issue #${number}: ${assignees.join(', ')}`,
      });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const issueTools: ToolDefinition[] = [
  listIssuesTool,
  getIssueTool,
  createIssueTool,
  closeIssueTool,
  reopenIssueTool,
  editIssueTool,
  commentOnIssueTool,
  listIssueCommentsTool,
  addIssueLabelsTool,
  removeIssueLabelsTool,
  addIssueAssigneesTool,
  removeIssueAssigneesTool,
];

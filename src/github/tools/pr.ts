// Pull Request tools (16 tools)
import { ghDelete, ghGet, ghPatch, ghPost, ghPut } from '../api';
import {
  optBoolean,
  optNumber,
  optString,
  optStringList,
  reqString,
  truncate,
  validatePositiveInt,
  validateRepoSpec,
} from '../helpers';

export const listPrsTool: ToolDefinition = {
  name: 'list-prs',
  description: 'List pull requests in a repository with optional filters',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      limit: { type: 'number', description: 'Maximum number of pull requests to return' },
      state: { type: 'string', description: 'Filter by state', enum: ['open', 'closed', 'all'] },
      base: { type: 'string', description: 'Filter by base branch name' },
    },
    required: ['owner', 'repo'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const limit = optNumber(args, 'limit', 30);
      const prState = optString(args, 'state') || 'open';
      const base = optString(args, 'base');

      let endpoint = `/repos/${spec}/pulls?state=${prState}&per_page=${limit}`;
      if (base) endpoint += `&base=${encodeURIComponent(base)}`;

      const pulls = (await ghGet(endpoint)) as any[];
      if (!pulls || pulls.length === 0)
        return JSON.stringify({ message: `No ${prState} pull requests in ${spec}.` });

      const lines = pulls.slice(0, limit).map((p: any) => {
        const author = p.user?.login || '';
        const draft = p.draft ? ' [draft]' : '';
        const labels = p.labels?.map((l: any) => l.name).join(', ') || '';
        let line = `#${p.number} [${p.state.toUpperCase()}] ${p.title.substring(0, 80)}`;
        if (author) line += ` (by @${author})`;
        line += ` (${p.head?.ref} -> ${p.base?.ref})`;
        line += draft;
        if (labels) line += ` [${labels}]`;
        return line;
      });
      return JSON.stringify({ prs: lines.join('\n'), count: lines.length });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const getPrTool: ToolDefinition = {
  name: 'get-pr',
  description: 'Get detailed information about a specific pull request',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Pull request number' },
    },
    required: ['owner', 'repo', 'number'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      const pr = (await ghGet(`/repos/${spec}/pulls/${number}`)) as any;

      const labels = pr.labels?.map((l: any) => l.name) || [];
      const assignees = pr.assignees?.map((a: any) => a.login) || [];

      const lines = [
        `PR #${pr.number}: ${pr.title}`,
        `State: ${pr.state}${pr.draft ? ' [draft]' : ''}`,
        pr.user ? `Author: @${pr.user.login}` : '',
        `Branch: ${pr.head?.ref} -> ${pr.base?.ref}`,
        `Changes: +${pr.additions} -${pr.deletions} (${pr.changed_files} files)`,
        `Mergeable: ${pr.mergeable}`,
        labels.length ? `Labels: ${labels.join(', ')}` : '',
        assignees.length ? `Assignees: ${assignees.map((a: string) => '@' + a).join(', ')}` : '',
        `Comments: ${pr.comments}`,
        `Review Comments: ${pr.review_comments}`,
        `Created: ${pr.created_at}`,
        `Updated: ${pr.updated_at}`,
        pr.merged_at ? `Merged: ${pr.merged_at}` : '',
        '',
        truncate(pr.body || '(no description)', 3000),
      ].filter(l => l || l === '');
      return JSON.stringify({ info: lines.join('\n') });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const createPrTool: ToolDefinition = {
  name: 'create-pr',
  description: 'Create a new pull request',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      title: { type: 'string', description: 'Pull request title' },
      head: {
        type: 'string',
        description:
          "The branch containing the changes (e.g. 'feature-branch' or 'user:feature-branch')",
      },
      base: {
        type: 'string',
        description: 'The branch to merge into (defaults to repo default branch)',
      },
      body: { type: 'string', description: 'Pull request body (Markdown supported)' },
      draft: { type: 'boolean', description: 'Create as a draft pull request' },
    },
    required: ['owner', 'repo', 'title', 'head'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const title = reqString(args, 'title');
      const head = reqString(args, 'head');
      const base = optString(args, 'base') || 'main';
      const body = optString(args, 'body');
      const draft = optBoolean(args, 'draft', false);

      const payload: Record<string, unknown> = { title, head, base, draft };
      if (body) payload.body = body;

      const r = (await ghPost(`/repos/${spec}/pulls`, payload)) as any;
      return JSON.stringify({ message: `PR created: ${r.html_url}` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const closePrTool: ToolDefinition = {
  name: 'close-pr',
  description: 'Close a pull request without merging',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Pull request number' },
    },
    required: ['owner', 'repo', 'number'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      await ghPatch(`/repos/${spec}/pulls/${number}`, { state: 'closed' });
      return JSON.stringify({ message: `PR #${number} closed.` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const reopenPrTool: ToolDefinition = {
  name: 'reopen-pr',
  description: 'Reopen a closed pull request',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Pull request number' },
    },
    required: ['owner', 'repo', 'number'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      await ghPatch(`/repos/${spec}/pulls/${number}`, { state: 'open' });
      return JSON.stringify({ message: `PR #${number} reopened.` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const mergePrTool: ToolDefinition = {
  name: 'merge-pr',
  description: 'Merge a pull request',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Pull request number' },
      method: {
        type: 'string',
        description: 'Merge method to use',
        enum: ['merge', 'squash', 'rebase'],
      },
      delete_branch: { type: 'boolean', description: 'Delete the head branch after merging' },
      commit_message: { type: 'string', description: 'Custom merge commit message' },
    },
    required: ['owner', 'repo', 'number'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      const method = optString(args, 'method') || 'merge';
      const deleteBranch = optBoolean(args, 'delete_branch', false);
      const commitMessage = optString(args, 'commit_message');

      const payload: Record<string, unknown> = { merge_method: method };
      if (commitMessage) payload.commit_message = commitMessage;

      await ghPut(`/repos/${spec}/pulls/${number}/merge`, payload);
      let msg = `PR #${number} merged via ${method}.`;

      if (deleteBranch) {
        try {
          const pr = (await ghGet(`/repos/${spec}/pulls/${number}`)) as any;
          await ghDelete(`/repos/${spec}/git/refs/heads/${pr.head.ref}`);
          msg += ` Branch '${pr.head.ref}' deleted.`;
        } catch {
          msg += ' (could not delete branch)';
        }
      }
      return JSON.stringify({ message: msg });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const editPrTool: ToolDefinition = {
  name: 'edit-pr',
  description: "Edit a pull request's title, body, or base branch",
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Pull request number' },
      title: { type: 'string', description: 'New pull request title' },
      body: { type: 'string', description: 'New pull request body' },
      base: { type: 'string', description: 'New base branch' },
    },
    required: ['owner', 'repo', 'number'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      const title = optString(args, 'title');
      const body = optString(args, 'body');
      const base = optString(args, 'base');

      if (!title && !body && !base)
        return JSON.stringify({ error: 'Provide at least one field to edit.' });

      const payload: Record<string, unknown> = {};
      if (title) payload.title = title;
      if (body) payload.body = body;
      if (base) payload.base = base;
      await ghPatch(`/repos/${spec}/pulls/${number}`, payload);
      return JSON.stringify({ message: `PR #${number} updated.` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const commentOnPrTool: ToolDefinition = {
  name: 'comment-on-pr',
  description: 'Add a comment to a pull request',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Pull request number' },
      body: { type: 'string', description: 'Comment body (Markdown supported)' },
    },
    required: ['owner', 'repo', 'number', 'body'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      const body = reqString(args, 'body');
      // PR comments go through the issue API
      const r = (await ghPost(`/repos/${spec}/issues/${number}/comments`, { body })) as any;
      return JSON.stringify({ message: `Comment added to PR #${number}: ${r.html_url}` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const listPrCommentsTool: ToolDefinition = {
  name: 'list-pr-comments',
  description: 'List comments on a pull request',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Pull request number' },
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
        return JSON.stringify({ message: `No comments on PR #${number}.` });

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

export const listPrReviewsTool: ToolDefinition = {
  name: 'list-pr-reviews',
  description: 'List reviews on a pull request',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Pull request number' },
    },
    required: ['owner', 'repo', 'number'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');

      const reviews = (await ghGet(`/repos/${spec}/pulls/${number}/reviews`)) as any[];
      if (!reviews || reviews.length === 0)
        return JSON.stringify({ message: `No reviews on PR #${number}.` });

      const lines = reviews.map((r: any) => {
        const user = r.user?.login || 'unknown';
        const reviewState = r.state || '';
        const body = (r.body || '').substring(0, 150);
        return `@${user}: ${reviewState}${body ? ` - ${body}` : ''}`;
      });
      return JSON.stringify({ reviews: lines.join('\n') });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const createPrReviewTool: ToolDefinition = {
  name: 'create-pr-review',
  description: 'Submit a review on a pull request',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Pull request number' },
      event: {
        type: 'string',
        description: 'Review action to perform',
        enum: ['APPROVE', 'REQUEST_CHANGES', 'COMMENT'],
      },
      body: { type: 'string', description: 'Review comment body' },
    },
    required: ['owner', 'repo', 'number', 'event'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      const event = reqString(args, 'event').toUpperCase();
      const body = optString(args, 'body') || '';
      await ghPost(`/repos/${spec}/pulls/${number}/reviews`, { body, event });
      return JSON.stringify({ message: `Review (${event}) submitted on PR #${number}.` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const listPrFilesTool: ToolDefinition = {
  name: 'list-pr-files',
  description: 'List files changed in a pull request',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Pull request number' },
    },
    required: ['owner', 'repo', 'number'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');

      const files = (await ghGet(`/repos/${spec}/pulls/${number}/files?per_page=100`)) as any[];
      if (!files || files.length === 0)
        return JSON.stringify({ message: `No files changed in PR #${number}.` });

      const lines = files.map((f: any) => {
        const status = (f.status || '').padEnd(12);
        return `${status} +${f.additions} -${f.deletions}  ${f.filename}`;
      });
      return JSON.stringify({ files: lines.join('\n') });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const getPrDiffTool: ToolDefinition = {
  name: 'get-pr-diff',
  description: 'Get the unified diff for a pull request',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Pull request number' },
    },
    required: ['owner', 'repo', 'number'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');

      const files = (await ghGet(`/repos/${spec}/pulls/${number}/files?per_page=50`)) as any[];
      if (!files || files.length === 0) return JSON.stringify({ diff: '(empty diff)' });

      const lines: string[] = [];
      for (const f of files) {
        lines.push(`--- ${f.filename} (${f.status})`);
        if (f.patch) lines.push(f.patch.substring(0, 2000));
        lines.push('');
      }
      return JSON.stringify({ diff: truncate(lines.join('\n')) });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const getPrChecksTool: ToolDefinition = {
  name: 'get-pr-checks',
  description: 'Get CI/CD check runs and status for a pull request',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Pull request number' },
    },
    required: ['owner', 'repo', 'number'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');

      // Get the PR to find the head SHA
      const pr = (await ghGet(`/repos/${spec}/pulls/${number}`)) as any;
      const sha = pr.head?.sha;
      if (!sha) return JSON.stringify({ message: 'No commits found on this PR.' });

      const checks = (await ghGet(`/repos/${spec}/commits/${sha}/check-runs`)) as any;
      const runs = checks.check_runs || [];
      if (!runs.length) return JSON.stringify({ message: `No checks on PR #${number}.` });

      const lines = runs.map((c: any) => {
        const conclusion = (c.conclusion || c.status || 'pending').padEnd(12);
        return `${conclusion} ${c.name}`;
      });
      return JSON.stringify({ checks: lines.join('\n') });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const requestPrReviewersTool: ToolDefinition = {
  name: 'request-pr-reviewers',
  description: 'Request reviews from specific users on a pull request',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Pull request number' },
      reviewers: {
        type: 'array',
        items: { type: 'string' },
        description: 'Usernames to request review from',
      },
    },
    required: ['owner', 'repo', 'number', 'reviewers'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');
      const reviewers = optStringList(args, 'reviewers');
      if (!reviewers.length) return JSON.stringify({ error: 'At least one reviewer is required.' });
      await ghPost(`/repos/${spec}/pulls/${number}/requested_reviewers`, { reviewers });
      return JSON.stringify({ message: `Review requested from: ${reviewers.join(', ')}` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const markPrReadyTool: ToolDefinition = {
  name: 'mark-pr-ready',
  description: 'Mark a draft pull request as ready for review',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      number: { type: 'number', description: 'Pull request number' },
    },
    required: ['owner', 'repo', 'number'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const number = validatePositiveInt(args.number, 'number');

      const pr = (await ghGet(`/repos/${spec}/pulls/${number}`)) as any;
      if (!pr.draft)
        return JSON.stringify({ message: `PR #${number} is already marked as ready.` });

      // Use GraphQL mutation to mark as ready (REST API doesn't support this directly)
      await ghPut(`/repos/${spec}/pulls/${number}`, { draft: false });
      return JSON.stringify({ message: `PR #${number} marked as ready for review.` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const prTools: ToolDefinition[] = [
  listPrsTool,
  getPrTool,
  createPrTool,
  closePrTool,
  reopenPrTool,
  mergePrTool,
  editPrTool,
  commentOnPrTool,
  listPrCommentsTool,
  listPrReviewsTool,
  createPrReviewTool,
  listPrFilesTool,
  getPrDiffTool,
  getPrChecksTool,
  requestPrReviewersTool,
  markPrReadyTool,
];

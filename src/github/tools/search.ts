// Search tools (4 tools)
import { ghGet } from '../api';
import { optNumber, optString, reqString } from '../helpers';

export const searchReposTool: ToolDefinition = {
  name: 'search-repos',
  description: 'Search GitHub repositories by query',
  input_schema: {
    type: 'object',
    properties: {
      query: { type: 'string', description: 'Search query (supports GitHub search syntax)' },
      limit: { type: 'number', description: 'Maximum number of results to return' },
      sort: {
        type: 'string',
        description: 'Sort field',
        enum: ['stars', 'forks', 'help-wanted-issues', 'updated'],
      },
      order: { type: 'string', description: 'Sort order', enum: ['asc', 'desc'] },
    },
    required: ['query'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const query = reqString(args, 'query');
      const limit = optNumber(args, 'limit', 20);
      const sort = optString(args, 'sort') || 'stars';
      const order = optString(args, 'order') || 'desc';

      const r = (await ghGet(
        `/search/repositories?q=${encodeURIComponent(query)}&sort=${sort}&order=${order}&per_page=${limit}`
      )) as { items?: SearchRepoItem[] };
      const items = r.items ?? [];

      if (!items.length) return JSON.stringify({ message: `No repos found for: ${query}` });

      const lines = items.map(repo => {
        const vis = repo.private ? 'private' : 'public';
        const desc = (repo.description || '').substring(0, 80);
        const lang = repo.language || '';
        let line = `${repo.full_name} [${vis}] (${repo.stargazers_count} stars)`;
        if (lang) line += ` [${lang}]`;
        if (desc) line += ` - ${desc}`;
        return line;
      });
      return JSON.stringify({ results: lines.join('\n'), count: lines.length });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

interface SearchRepoItem {
  full_name: string;
  private?: boolean;
  description?: string;
  language?: string;
  stargazers_count: number;
}

interface SearchIssuesResponse {
  items?: SearchIssueItem[];
}

interface SearchIssueItem {
  repository_url?: string;
  user?: { login?: string };
  number?: number;
  state?: string;
  title?: string;
}

interface SearchCodeResponse {
  items?: SearchCodeItem[];
}

interface SearchCodeItem {
  repository?: { full_name?: string };
  path?: string;
}

interface SearchCommitsResponse {
  items?: SearchCommitItem[];
}

interface SearchCommitItem {
  sha?: string;
  commit?: { message?: string; author?: { name?: string } };
  repository?: { full_name?: string };
}

export const searchIssuesTool: ToolDefinition = {
  name: 'search-issues',
  description: 'Search issues and pull requests across GitHub',
  input_schema: {
    type: 'object',
    properties: {
      query: {
        type: 'string',
        description:
          "Search query (supports GitHub search syntax, e.g. 'is:issue is:open label:bug')",
      },
      limit: { type: 'number', description: 'Maximum number of results to return' },
      sort: {
        type: 'string',
        description: 'Sort field',
        enum: ['comments', 'reactions', 'created', 'updated'],
      },
    },
    required: ['query'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const query = reqString(args, 'query');
      const limit = optNumber(args, 'limit', 20);
      const sort = optString(args, 'sort') || 'created';

      const r = (await ghGet(
        `/search/issues?q=${encodeURIComponent(query)}&sort=${sort}&per_page=${limit}`
      )) as SearchIssuesResponse;
      const items = r.items ?? [];

      if (!items.length) return JSON.stringify({ message: `No issues found for: ${query}` });

      const lines = items.map(i => {
        const repoName = i.repository_url?.split('/').slice(-2).join('/') || '';
        const author = i.user?.login || '';
        const prefix = repoName ? `[${repoName}] ` : '';
        const number = i.number ?? 0;
        const state = (i.state ?? '').toUpperCase();
        const title = (i.title ?? '').substring(0, 80);
        let line = `${prefix}#${number} [${state}] ${title}`;
        if (author) line += ` (by @${author})`;
        return line;
      });
      return JSON.stringify({ results: lines.join('\n'), count: lines.length });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const searchCodeTool: ToolDefinition = {
  name: 'search-code',
  description: 'Search code across GitHub repositories',
  input_schema: {
    type: 'object',
    properties: {
      query: { type: 'string', description: 'Search query (supports GitHub code search syntax)' },
      limit: { type: 'number', description: 'Maximum number of results to return' },
      repo: {
        type: 'string',
        description: 'Restrict search to a specific repo (owner/name format)',
      },
      language: { type: 'string', description: 'Filter by programming language' },
    },
    required: ['query'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      let query = reqString(args, 'query');
      const limit = optNumber(args, 'limit', 20);
      const repo = optString(args, 'repo');
      const language = optString(args, 'language');

      if (repo) query += ` repo:${repo}`;
      if (language) query += ` language:${language}`;

      const r = (await ghGet(
        `/search/code?q=${encodeURIComponent(query)}&per_page=${limit}`
      )) as SearchCodeResponse;
      const items = r.items ?? [];

      if (!items.length) return JSON.stringify({ message: `No code matches for: ${query}` });

      const lines = items.map(c => {
        const repoName = c.repository?.full_name || '';
        return `[${repoName}] ${c.path ?? ''}`;
      });
      return JSON.stringify({ results: lines.join('\n'), count: lines.length });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const searchCommitsTool: ToolDefinition = {
  name: 'search-commits',
  description: 'Search commits across GitHub repositories',
  input_schema: {
    type: 'object',
    properties: {
      query: { type: 'string', description: 'Search query (supports GitHub commit search syntax)' },
      limit: { type: 'number', description: 'Maximum number of results to return' },
      repo: {
        type: 'string',
        description: 'Restrict search to a specific repo (owner/name format)',
      },
    },
    required: ['query'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      let query = reqString(args, 'query');
      const limit = optNumber(args, 'limit', 20);
      const repo = optString(args, 'repo');

      if (repo) query += ` repo:${repo}`;

      const r = (await ghGet(
        `/search/commits?q=${encodeURIComponent(query)}&per_page=${limit}`
      )) as SearchCommitsResponse;
      const items = r.items ?? [];

      if (!items.length) return JSON.stringify({ message: `No commits found for: ${query}` });

      const lines = items.map(c => {
        const sha = c.sha?.substring(0, 7) || '?';
        const msg = (c.commit?.message || '').split('\n')[0].substring(0, 80);
        const author = c.commit?.author?.name || '';
        const repoName = c.repository?.full_name || '';
        const prefix = repoName ? `[${repoName}] ` : '';
        return `${prefix}${sha} ${msg}${author ? ` (by ${author})` : ''}`;
      });
      return JSON.stringify({ results: lines.join('\n'), count: lines.length });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const searchTools: ToolDefinition[] = [
  searchReposTool,
  searchIssuesTool,
  searchCodeTool,
  searchCommitsTool,
];

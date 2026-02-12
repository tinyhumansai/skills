// Repository tools (12 tools + get_readme from code category = 13)
import { ghDelete, ghGet, ghPost, ghPut } from '../api';
import {
  optBoolean,
  optNumber,
  optString,
  optStringList,
  reqString,
  validateRepoSpec,
  validateUsername,
} from '../helpers';

export const listReposTool: ToolDefinition = {
  name: 'list-repos',
  description: 'List repositories for the authenticated user or a specific owner',
  input_schema: {
    type: 'object',
    properties: {
      owner: {
        type: 'string',
        description: 'Repository owner (user or org). Defaults to the authenticated user',
      },
      limit: { type: 'number', description: 'Maximum number of repositories to return' },
      visibility: {
        type: 'string',
        description: 'Filter by visibility',
        enum: ['all', 'public', 'private'],
      },
      sort: {
        type: 'string',
        description: 'Sort field',
        enum: ['created', 'updated', 'pushed', 'full_name'],
      },
    },
    required: [],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const limit = optNumber(args, 'limit', 30);
      const owner = optString(args, 'owner');
      const visibility = optString(args, 'visibility');
      const sort = optString(args, 'sort') || 'updated';

      let endpoint: string;
      if (owner) {
        endpoint = `/users/${owner}/repos?sort=${sort}&per_page=${limit}`;
      } else {
        endpoint = `/user/repos?sort=${sort}&per_page=${limit}`;
        if (visibility) endpoint += `&visibility=${visibility}`;
      }

      const repos = (await ghGet(endpoint)) as any[];
      if (!repos || repos.length === 0)
        return JSON.stringify({ message: 'No repositories found.' });

      const lines = repos.slice(0, limit).map((r: any) => {
        const vis = r.private ? 'private' : 'public';
        const desc = r.description || '';
        const lang = r.language || '';
        let line = `${r.full_name} [${vis}] (${r.stargazers_count} stars)`;
        if (lang) line += ` [${lang}]`;
        if (desc) line += ` - ${desc.substring(0, 80)}`;
        return line;
      });
      return JSON.stringify({ repos: lines.join('\n'), count: lines.length });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const getRepoTool: ToolDefinition = {
  name: 'get-repo',
  description: 'Get detailed information about a specific repository',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
    },
    required: ['owner', 'repo'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const r = (await ghGet(`/repos/${spec}`)) as any;
      const lines = [
        `Repository: ${r.full_name}`,
        `URL: ${r.html_url}`,
        `Visibility: ${r.private ? 'private' : 'public'}`,
        `Description: ${r.description || 'N/A'}`,
        `Stars: ${r.stargazers_count}`,
        `Forks: ${r.forks_count}`,
        `Open Issues: ${r.open_issues_count}`,
        `Language: ${r.language || 'N/A'}`,
        `Default Branch: ${r.default_branch}`,
        `License: ${r.license?.name || 'N/A'}`,
        `Archived: ${r.archived}`,
        `Fork: ${r.fork}`,
        `Created: ${r.created_at}`,
        `Updated: ${r.updated_at}`,
      ];
      if (r.homepage) lines.push(`Homepage: ${r.homepage}`);
      if (r.topics?.length) lines.push(`Topics: ${r.topics.join(', ')}`);
      return JSON.stringify({ info: lines.join('\n') });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const createRepoTool: ToolDefinition = {
  name: 'create-repo',
  description: 'Create a new repository for the authenticated user',
  input_schema: {
    type: 'object',
    properties: {
      name: { type: 'string', description: 'Repository name' },
      description: { type: 'string', description: 'Repository description' },
      visibility: {
        type: 'string',
        description: 'Repository visibility',
        enum: ['public', 'private'],
      },
      auto_init: { type: 'boolean', description: 'Initialize with a README' },
    },
    required: ['name'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const name = reqString(args, 'name');
      const description = optString(args, 'description');
      const visibility = optString(args, 'visibility') || 'private';
      const autoInit = optBoolean(args, 'auto_init', false);

      const body: Record<string, unknown> = {
        name,
        private: visibility === 'private',
        auto_init: autoInit,
      };
      if (description) body.description = description;

      const r = (await ghPost('/user/repos', body)) as any;
      return JSON.stringify({ message: `Repository created: ${r.html_url}` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const forkRepoTool: ToolDefinition = {
  name: 'fork-repo',
  description: "Fork a repository to the authenticated user's account",
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Owner of the repository to fork' },
      repo: { type: 'string', description: 'Repository name to fork' },
      fork_name: { type: 'string', description: 'Custom name for the forked repository' },
    },
    required: ['owner', 'repo'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const forkName = optString(args, 'fork_name');
      const body: Record<string, unknown> = {};
      if (forkName) body.name = forkName;
      const r = (await ghPost(`/repos/${spec}/forks`, body)) as any;
      return JSON.stringify({ message: `Forked to: ${r.html_url}` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const deleteRepoTool: ToolDefinition = {
  name: 'delete-repo',
  description: 'Permanently delete a repository. This action cannot be undone',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      confirm: { type: 'boolean', description: 'Must be true to confirm deletion' },
    },
    required: ['owner', 'repo', 'confirm'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const confirm = optBoolean(args, 'confirm', false);
      if (!confirm)
        return JSON.stringify({
          error: `Deleting ${spec} is irreversible. Set confirm=true to proceed.`,
        });
      await ghDelete(`/repos/${spec}`);
      return JSON.stringify({ message: `Repository ${spec} deleted.` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const cloneRepoTool: ToolDefinition = {
  name: 'clone-repo',
  description: 'Get clone URLs for a repository',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
    },
    required: ['owner', 'repo'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const r = (await ghGet(`/repos/${spec}`)) as any;
      return JSON.stringify({
        message: `Clone URL (HTTPS): ${r.clone_url}\nClone URL (SSH): ${r.ssh_url}\n\nRun: git clone ${r.clone_url}`,
      });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const listCollaboratorsTool: ToolDefinition = {
  name: 'list-collaborators',
  description: 'List collaborators on a repository',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      limit: { type: 'number', description: 'Maximum number of collaborators to return' },
    },
    required: ['owner', 'repo'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const limit = optNumber(args, 'limit', 30);
      const collabs = (await ghGet(`/repos/${spec}/collaborators?per_page=${limit}`)) as any[];
      if (!collabs || collabs.length === 0)
        return JSON.stringify({ message: 'No collaborators found.' });

      const lines = collabs.map((c: any) => {
        const perms: string[] = [];
        if (c.permissions?.admin) perms.push('admin');
        else if (c.permissions?.maintain) perms.push('maintain');
        else if (c.permissions?.push) perms.push('push');
        else if (c.permissions?.pull) perms.push('pull');
        const permStr = perms.length ? ` [${perms.join(', ')}]` : '';
        return `@${c.login}${permStr}`;
      });
      return JSON.stringify({ collaborators: lines.join('\n') });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const addCollaboratorTool: ToolDefinition = {
  name: 'add-collaborator',
  description: 'Add a collaborator to a repository',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      username: { type: 'string', description: 'GitHub username of the collaborator to add' },
      permission: {
        type: 'string',
        description: 'Permission level to grant',
        enum: ['pull', 'triage', 'push', 'maintain', 'admin'],
      },
    },
    required: ['owner', 'repo', 'username'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const username = validateUsername(reqString(args, 'username'));
      const permission = optString(args, 'permission') || 'push';
      await ghPut(`/repos/${spec}/collaborators/${username}`, { permission });
      return JSON.stringify({
        message: `Invited @${username} to ${spec} with ${permission} permission.`,
      });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const removeCollaboratorTool: ToolDefinition = {
  name: 'remove-collaborator',
  description: 'Remove a collaborator from a repository',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      username: { type: 'string', description: 'GitHub username of the collaborator to remove' },
    },
    required: ['owner', 'repo', 'username'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const username = validateUsername(reqString(args, 'username'));
      await ghDelete(`/repos/${spec}/collaborators/${username}`);
      return JSON.stringify({ message: `Removed @${username} from ${spec}.` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const listTopicsTool: ToolDefinition = {
  name: 'list-topics',
  description: 'List topics (tags) on a repository',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
    },
    required: ['owner', 'repo'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const r = (await ghGet(`/repos/${spec}/topics`)) as any;
      const topics: string[] = r.names || [];
      if (!topics.length) return JSON.stringify({ message: `No topics set on ${spec}.` });
      return JSON.stringify({ topics: topics.join(', ') });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const setTopicsTool: ToolDefinition = {
  name: 'set-topics',
  description: 'Replace all topics on a repository',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      topics: {
        type: 'array',
        items: { type: 'string' },
        description: 'List of topic names to set',
      },
    },
    required: ['owner', 'repo', 'topics'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const topics = optStringList(args, 'topics');
      if (!topics.length) return JSON.stringify({ error: 'At least one topic is required.' });
      await ghPut(`/repos/${spec}/topics`, { names: topics });
      return JSON.stringify({ message: `Topics set on ${spec}: ${topics.join(', ')}` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const listLanguagesTool: ToolDefinition = {
  name: 'list-languages',
  description: 'List programming languages detected in a repository',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
    },
    required: ['owner', 'repo'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const languages = (await ghGet(`/repos/${spec}/languages`)) as Record<string, number>;
      if (!languages || Object.keys(languages).length === 0) {
        return JSON.stringify({ message: `No languages detected in ${spec}.` });
      }
      const total = Object.values(languages).reduce((a, b) => a + b, 0);
      const lines = Object.entries(languages)
        .sort((a, b) => b[1] - a[1])
        .map(([lang, bytes]) => `${lang}: ${((bytes / total) * 100).toFixed(1)}%`);
      return JSON.stringify({ languages: lines.join('\n') });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const repoTools: ToolDefinition[] = [
  listReposTool,
  getRepoTool,
  createRepoTool,
  forkRepoTool,
  deleteRepoTool,
  cloneRepoTool,
  listCollaboratorsTool,
  addCollaboratorTool,
  removeCollaboratorTool,
  listTopicsTool,
  setTopicsTool,
  listLanguagesTool,
];

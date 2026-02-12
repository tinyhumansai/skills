// Gist tools (6 tools)
import { ghDelete, ghGet, ghPatch, ghPost } from '../api';
import { optBoolean, optNumber, optString, reqString, truncate } from '../helpers';

export const listGistsTool: ToolDefinition = {
  name: 'list-gists',
  description: 'List gists for the authenticated user or a specific user',
  input_schema: {
    type: 'object',
    properties: {
      limit: { type: 'number', description: 'Maximum number of gists to return' },
      username: {
        type: 'string',
        description: 'GitHub username. Defaults to the authenticated user',
      },
    },
    required: [],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const limit = optNumber(args, 'limit', 20);
      const username = optString(args, 'username');

      const endpoint = username
        ? `/users/${encodeURIComponent(username)}/gists?per_page=${limit}`
        : `/gists?per_page=${limit}`;

      const gists = (await ghGet(endpoint)) as any[];
      if (!gists || gists.length === 0) return JSON.stringify({ message: 'No gists found.' });

      const lines = gists.map((g: any) => {
        const files = Object.keys(g.files || {});
        let fileStr = files.slice(0, 3).join(', ');
        if (files.length > 3) fileStr += ` (+${files.length - 3} more)`;
        const pub = g.public ? 'public' : 'private';
        const desc = (g.description || '').substring(0, 60);
        return `${g.id} [${pub}] ${fileStr}${desc ? ` - ${desc}` : ''}`;
      });
      return JSON.stringify({ gists: lines.join('\n'), count: lines.length });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const getGistTool: ToolDefinition = {
  name: 'get-gist',
  description: 'Get a specific gist by ID, including its files and content',
  input_schema: {
    type: 'object',
    properties: { gist_id: { type: 'string', description: 'The gist ID' } },
    required: ['gist_id'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const gistId = reqString(args, 'gist_id');
      const g = (await ghGet(`/gists/${gistId}`)) as any;

      const owner = g.owner?.login || '';
      const files = Object.keys(g.files || {});
      const pub = g.public ? 'public' : 'private';

      const lines = [
        `Gist: ${g.id}`,
        `URL: ${g.html_url}`,
        owner ? `Owner: @${owner}` : '',
        `Visibility: ${pub}`,
        `Description: ${g.description || 'N/A'}`,
        `Files: ${files.join(', ')}`,
        `Comments: ${g.comments}`,
        `Created: ${g.created_at}`,
        `Updated: ${g.updated_at}`,
      ];

      for (const [fname, fobj] of Object.entries(g.files || {})) {
        const f = fobj as any;
        const content = f.content || '';
        lines.push(`\n--- ${fname} (${f.language || 'text'}, ${f.size} bytes) ---`);
        lines.push(truncate(content, 1500));
      }

      return JSON.stringify({ info: lines.filter(l => l || l === '').join('\n') });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const createGistTool: ToolDefinition = {
  name: 'create-gist',
  description: 'Create a new gist with one or more files',
  input_schema: {
    type: 'object',
    properties: {
      files: {
        type: 'object',
        description:
          'Map of filename to file content, e.g. {"hello.py": {"content": "print(\'hello\')"}}',
      },
      description: { type: 'string', description: 'Gist description' },
      public: { type: 'boolean', description: 'Whether the gist is public' },
    },
    required: ['files'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const filesArg = args.files;
      if (!filesArg || typeof filesArg !== 'object' || !Object.keys(filesArg as object).length) {
        return JSON.stringify({
          error: 'files must be a non-empty object of {filename: {content: string}}.',
        });
      }

      const description = optString(args, 'description') || '';
      const isPublic = optBoolean(args, 'public', false);

      const r = (await ghPost('/gists', { files: filesArg, description, public: isPublic })) as any;
      return JSON.stringify({ message: `Gist created: ${r.html_url}` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const editGistTool: ToolDefinition = {
  name: 'edit-gist',
  description: "Edit an existing gist's description or files",
  input_schema: {
    type: 'object',
    properties: {
      gist_id: { type: 'string', description: 'The gist ID' },
      description: { type: 'string', description: 'New gist description' },
      files: {
        type: 'object',
        description: 'Map of filename to new content. Set content to null to delete a file',
      },
    },
    required: ['gist_id'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const gistId = reqString(args, 'gist_id');
      const description = optString(args, 'description');
      const filesArg = args.files;

      const payload: Record<string, unknown> = {};
      if (description !== null && description !== undefined) payload.description = description;
      if (filesArg && typeof filesArg === 'object' && Object.keys(filesArg as object).length) {
        payload.files = filesArg;
      }

      if (!Object.keys(payload).length) {
        return JSON.stringify({ error: 'Provide description or files to edit.' });
      }

      await ghPatch(`/gists/${gistId}`, payload);
      return JSON.stringify({ message: `Gist ${gistId} updated.` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const deleteGistTool: ToolDefinition = {
  name: 'delete-gist',
  description: 'Permanently delete a gist',
  input_schema: {
    type: 'object',
    properties: { gist_id: { type: 'string', description: 'The gist ID to delete' } },
    required: ['gist_id'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const gistId = reqString(args, 'gist_id');
      await ghDelete(`/gists/${gistId}`);
      return JSON.stringify({ message: `Gist ${gistId} deleted.` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const cloneGistTool: ToolDefinition = {
  name: 'clone-gist',
  description: 'Get the clone URL for a gist',
  input_schema: {
    type: 'object',
    properties: { gist_id: { type: 'string', description: 'The gist ID to clone' } },
    required: ['gist_id'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const gistId = reqString(args, 'gist_id');
      const g = (await ghGet(`/gists/${gistId}`)) as any;
      return JSON.stringify({
        message: `Clone URL: ${g.git_pull_url}\n\nRun: git clone ${g.git_pull_url}`,
      });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const gistTools: ToolDefinition[] = [
  listGistsTool,
  getGistTool,
  createGistTool,
  editGistTool,
  deleteGistTool,
  cloneGistTool,
];

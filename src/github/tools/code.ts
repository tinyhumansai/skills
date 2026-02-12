// Code & Files tools (3 tools)
import { ghGet } from '../api';
import { optString, reqString, truncate, validateRepoSpec } from '../helpers';

export const viewFileTool: ToolDefinition = {
  name: 'view-file',
  description: 'View the contents of a file in a repository',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      path: { type: 'string', description: 'File path within the repository' },
      ref: {
        type: 'string',
        description: 'Git ref (branch, tag, or commit SHA). Defaults to the default branch',
      },
    },
    required: ['owner', 'repo', 'path'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const path = reqString(args, 'path');
      const ref = optString(args, 'ref');

      let endpoint = `/repos/${spec}/contents/${encodeURIComponent(path)}`;
      if (ref) endpoint += `?ref=${encodeURIComponent(ref)}`;

      const r = (await ghGet(endpoint)) as any;

      if (Array.isArray(r)) {
        return JSON.stringify({
          message: `${path} is a directory, not a file. Use list-directory instead.`,
        });
      }

      if (r.encoding === 'base64' && r.content) {
        // Decode base64 content (QuickJS has atob)
        const decoded = decodeBase64(r.content);
        return JSON.stringify({ content: truncate(decoded) });
      }

      return JSON.stringify({ content: '(binary or empty file)' });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const listDirectoryTool: ToolDefinition = {
  name: 'list-directory',
  description: 'List the contents of a directory in a repository',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      path: {
        type: 'string',
        description: 'Directory path within the repository. Defaults to the root',
      },
      ref: {
        type: 'string',
        description: 'Git ref (branch, tag, or commit SHA). Defaults to the default branch',
      },
    },
    required: ['owner', 'repo'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const path = optString(args, 'path') || '';
      const ref = optString(args, 'ref');

      let endpoint = `/repos/${spec}/contents/${encodeURIComponent(path || '/')}`;
      if (ref) endpoint += `?ref=${encodeURIComponent(ref)}`;

      const r = (await ghGet(endpoint)) as unknown;

      if (!Array.isArray(r))
        return JSON.stringify({ message: `${path} is a file, not a directory.` });

      const entries = r as { type?: string; name?: string; size?: number }[];
      const sorted = entries.sort((a, b) => {
        if (a.type === 'dir' && b.type !== 'dir') return -1;
        if (a.type !== 'dir' && b.type === 'dir') return 1;
        return (a.name ?? '').localeCompare(b.name ?? '');
      });

      const lines = sorted.map(entry => {
        const indicator = entry.type === 'dir' ? '/' : '';
        const sizeStr =
          entry.type === 'file' && entry.size !== undefined ? ` (${entry.size} bytes)` : '';
        const type = entry.type ?? '';
        const name = entry.name ?? '';
        return `${type.padEnd(4)} ${name}${indicator}${sizeStr}`;
      });
      return JSON.stringify({ directory: lines.join('\n') || 'Empty directory.' });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const getReadmeTool: ToolDefinition = {
  name: 'get-readme',
  description: 'Get the README file for a repository',
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
      const r = (await ghGet(`/repos/${spec}/readme`)) as { encoding?: string; content?: string };

      if (r.encoding === 'base64' && r.content) {
        const decoded = decodeBase64(r.content);
        return JSON.stringify({ content: truncate(decoded) });
      }
      return JSON.stringify({ content: '(empty README)' });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

function decodeBase64(encoded: string): string {
  // Remove newlines from base64 content
  const cleaned = encoded.replace(/\n/g, '');
  try {
    return atob(cleaned);
  } catch {
    return '(unable to decode content)';
  }
}

export const codeTools: ToolDefinition[] = [viewFileTool, listDirectoryTool, getReadmeTool];

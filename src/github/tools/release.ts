// Release tools (6 tools)
import { ghDelete, ghGet, ghPost } from '../api';
import {
  optBoolean,
  optNumber,
  optString,
  reqString,
  truncate,
  validateRepoSpec,
} from '../helpers';

export const listReleasesTool: ToolDefinition = {
  name: 'list-releases',
  description: 'List releases for a repository',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      limit: { type: 'number', description: 'Maximum number of releases to return' },
    },
    required: ['owner', 'repo'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const limit = optNumber(args, 'limit', 10);
      const releases = (await ghGet(`/repos/${spec}/releases?per_page=${limit}`)) as {
        tag_name?: string;
        name?: string;
        draft?: boolean;
        prerelease?: boolean;
        published_at?: string;
        created_at?: string;
      }[];

      if (!releases || releases.length === 0)
        return JSON.stringify({ message: `No releases in ${spec}.` });

      const lines = releases.map(r => {
        const tag = r.tag_name ?? '?';
        const name = r.name ?? tag;
        const flags: string[] = [];
        if (r.draft) flags.push('draft');
        if (r.prerelease) flags.push('pre-release');
        const flagStr = flags.length ? ` [${flags.join(', ')}]` : '';
        const date = r.published_at || r.created_at || '';
        return `${tag} - ${name}${flagStr} (${date})`;
      });
      return JSON.stringify({ releases: lines.join('\n') });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const getReleaseTool: ToolDefinition = {
  name: 'get-release',
  description: 'Get a specific release by tag name',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      tag: { type: 'string', description: "Release tag name (e.g. 'v1.0.0')" },
    },
    required: ['owner', 'repo', 'tag'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const tag = reqString(args, 'tag');
      const r = (await ghGet(`/repos/${spec}/releases/tags/${encodeURIComponent(tag)}`)) as {
        name?: string;
        tag_name?: string;
        author?: { login?: string };
        draft?: boolean;
        prerelease?: boolean;
        published_at?: string;
        assets?: { name?: string; size?: number; download_count?: number }[];
        body?: string;
      };

      const author = r.author?.login || '';
      const assets = r.assets || [];
      const assetLines = assets.map(
        a => `  - ${a.name ?? '(asset)'} (${a.size ?? 0} bytes, ${a.download_count ?? 0} downloads)`
      );

      const lines = [
        `Release: ${r.name || r.tag_name}`,
        `Tag: ${r.tag_name}`,
        author ? `Author: @${author}` : '',
        `Draft: ${r.draft}`,
        `Pre-release: ${r.prerelease}`,
        `Published: ${r.published_at || ''}`,
      ];
      if (assetLines.length) {
        lines.push(`Assets (${assetLines.length}):`);
        lines.push(...assetLines);
      }
      lines.push('');
      lines.push(truncate(r.body || '(no release notes)', 3000));
      return JSON.stringify({ info: lines.filter(l => l || l === '').join('\n') });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const createReleaseTool: ToolDefinition = {
  name: 'create-release',
  description: 'Create a new release for a repository',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      tag: { type: 'string', description: "Tag name for the release (e.g. 'v1.0.0')" },
      title: { type: 'string', description: 'Release title' },
      notes: { type: 'string', description: 'Release notes body (Markdown supported)' },
      draft: { type: 'boolean', description: 'Create as a draft release' },
      prerelease: { type: 'boolean', description: 'Mark as a pre-release' },
      target: {
        type: 'string',
        description: 'Target commitish (branch or commit SHA) for the tag',
      },
      generate_notes: { type: 'boolean', description: 'Auto-generate release notes from commits' },
    },
    required: ['owner', 'repo', 'tag'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const tag = reqString(args, 'tag');
      const title = optString(args, 'title') || tag;
      const notes = optString(args, 'notes') || '';
      const draft = optBoolean(args, 'draft', false);
      const prerelease = optBoolean(args, 'prerelease', false);
      const target = optString(args, 'target');
      const generateNotes = optBoolean(args, 'generate_notes', false);

      const payload: Record<string, unknown> = {
        tag_name: tag,
        name: title,
        body: notes,
        draft,
        prerelease,
        generate_release_notes: generateNotes,
      };
      if (target) payload.target_commitish = target;

      const r = (await ghPost(`/repos/${spec}/releases`, payload)) as { html_url?: string };
      return JSON.stringify({ message: `Release created: ${r.html_url ?? ''}` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const deleteReleaseTool: ToolDefinition = {
  name: 'delete-release',
  description: 'Delete a release by tag name',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      tag: { type: 'string', description: 'Release tag name to delete' },
      cleanup_tag: { type: 'boolean', description: 'Also delete the associated git tag' },
    },
    required: ['owner', 'repo', 'tag'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const tag = reqString(args, 'tag');
      const cleanupTag = optBoolean(args, 'cleanup_tag', false);

      // Get release by tag to find its ID
      const r = (await ghGet(`/repos/${spec}/releases/tags/${encodeURIComponent(tag)}`)) as {
        id?: number;
      };
      await ghDelete(`/repos/${spec}/releases/${r.id}`);

      let msg = `Release ${tag} deleted.`;
      if (cleanupTag) {
        try {
          await ghDelete(`/repos/${spec}/git/refs/tags/${encodeURIComponent(tag)}`);
          msg += ` Tag ${tag} also deleted.`;
        } catch {
          msg += ` (could not delete tag ${tag})`;
        }
      }
      return JSON.stringify({ message: msg });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const listReleaseAssetsTool: ToolDefinition = {
  name: 'list-release-assets',
  description: 'List assets (downloadable files) attached to a release',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      tag: { type: 'string', description: 'Release tag name' },
    },
    required: ['owner', 'repo', 'tag'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const tag = reqString(args, 'tag');

      const r = (await ghGet(`/repos/${spec}/releases/tags/${encodeURIComponent(tag)}`)) as {
        assets?: { name?: string; size?: number; download_count?: number }[];
      };
      const assets = r.assets || [];

      if (!assets.length) return JSON.stringify({ message: `No assets for release ${tag}.` });

      const lines = assets.map(
        a => `${a.name ?? '(asset)'} (${a.size ?? 0} bytes, ${a.download_count ?? 0} downloads)`
      );
      return JSON.stringify({ assets: lines.join('\n') });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const getLatestReleaseTool: ToolDefinition = {
  name: 'get-latest-release',
  description: 'Get the latest published release for a repository',
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
      const r = (await ghGet(`/repos/${spec}/releases/latest`)) as {
        name?: string;
        tag_name?: string;
        author?: { login?: string };
        published_at?: string;
        body?: string;
      };

      const author = r.author?.login || '';
      const lines = [
        `Latest Release: ${r.name || r.tag_name}`,
        `Tag: ${r.tag_name}`,
        author ? `Author: @${author}` : '',
        `Published: ${r.published_at || ''}`,
        '',
        truncate(r.body || '(no release notes)', 2000),
      ].filter(l => l || l === '');
      return JSON.stringify({ info: lines.join('\n') });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const releaseTools: ToolDefinition[] = [
  listReleasesTool,
  getReleaseTool,
  createReleaseTool,
  deleteReleaseTool,
  listReleaseAssetsTool,
  getLatestReleaseTool,
];

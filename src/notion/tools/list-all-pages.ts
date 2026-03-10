// Tool: notion-list-all-pages
// Uses local synced pages to avoid slow Notion API calls that can trigger "Tool async execution timed out".
import { getLocalPages } from '../db/helpers';

function formatLocalPageSummary(p: {
  id: string;
  title: string;
  url: string | null;
  created_time: string;
  last_edited_time: string;
  archived: number;
  parent_type: string;
}): Record<string, unknown> {
  return {
    id: p.id,
    title: p.title,
    url: p.url,
    created_time: p.created_time,
    last_edited_time: p.last_edited_time,
    archived: !!p.archived,
    parent_type: p.parent_type,
  };
}

export const listAllPagesTool: ToolDefinition = {
  name: 'list-all-pages',
  description:
    'List pages in the workspace (from last sync). Returns synced pages; run a sync in Settings to refresh.',
  input_schema: {
    type: 'object',
    properties: {
      page_size: {
        type: 'number',
        description: 'Number of results to return (default 20, max 100)',
      },
    },
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const pageSize = Math.min((args.page_size as number) || 20, 100);
      const localPages = getLocalPages({ limit: pageSize, includeArchived: false });
      const pages = localPages.map(p => formatLocalPageSummary(p));
      return JSON.stringify({
        count: pages.length,
        has_more: localPages.length >= pageSize,
        pages,
        source: 'local',
      });
    } catch (e) {
      return JSON.stringify({ error: e instanceof Error ? e.message : String(e) });
    }
  },
};

// Tool: notion-search
import { notionApi } from '../api/index';
import type { SearchRequest } from '../api/search';
import { formatApiError, formatPageTitle } from '../helpers';

/** Shape of one search result item matching Notion API response. */
function toSearchResultItem(item: Record<string, unknown>): Record<string, unknown> {
  const base = {
    object: item.object,
    id: item.id,
    created_time: item.created_time,
    last_edited_time: item.last_edited_time,
    in_trash: item.in_trash ?? item.archived ?? false,
    is_locked: item.is_locked ?? false,
    url: item.url ?? null,
    public_url: item.public_url ?? null,
    parent: item.parent ?? null,
    properties: item.properties ?? {},
    icon: item.icon ?? null,
    cover: item.cover ?? null,
    created_by: item.created_by ?? null,
    last_edited_by: item.last_edited_by ?? null,
  };
  if (item.object === 'page') {
    return { ...base, title: formatPageTitle(item) };
  }
  if (item.object === 'database' || item.object === 'data_source') {
    const title =
      Array.isArray(item.title) && item.title.length
        ? (item.title as Array<{ plain_text?: string }>).map(t => t.plain_text ?? '').join('')
        : '(Untitled)';
    return { ...base, title };
  }
  return base;
}

export const searchTool: ToolDefinition = {
  name: 'search',
  description:
    'Search for pages and databases in your Notion workspace. ' +
    'Supports query, filter by object type (page or database), and sort by last_edited_time.',
  input_schema: {
    type: 'object',
    properties: {
      query: { type: 'string', description: 'Search query (optional, returns recent if empty)' },
      filter: {
        type: 'string',
        enum: ['page', 'database'],
        description: 'Filter results by type: page or database',
      },
      sort_direction: {
        type: 'string',
        enum: ['ascending', 'descending'],
        description: 'Sort direction (default: descending by last_edited_time)',
      },
      page_size: {
        type: 'number',
        description: 'Number of results to return (default 20, max 100)',
      },
    },
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const query = ((args.query as string) || '').trim();
      const filter = args.filter as string | undefined;
      const sortDirection = (args.sort_direction as string) || 'descending';
      const pageSize = Math.min((args.page_size as number) || 20, 100);

      const body: SearchRequest = { page_size: pageSize };
      if (query) body.query = query;
      if (filter) {
        body.filter = { property: 'object', value: filter === 'database' ? 'database' : 'page' };
      }
      body.sort = {
        direction: sortDirection === 'ascending' ? 'ascending' : 'descending',
        timestamp: 'last_edited_time',
      };

      const result = await notionApi.search(body as Record<string, unknown>);
      const results = (result.results as Record<string, unknown>[]).map(toSearchResultItem);

      return JSON.stringify({
        object: (result as Record<string, unknown>).object ?? 'list',
        next_cursor: (result as Record<string, unknown>).next_cursor ?? null,
        has_more: result.has_more ?? false,
        results,
      });
    } catch (e) {
      return JSON.stringify({ error: formatApiError(e) });
    }
  },
};

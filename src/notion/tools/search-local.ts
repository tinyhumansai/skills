// Tool: notion-search-local
// Query local SQLite pages and databases by title/content
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const searchLocalTool: ToolDefinition = {
  name: 'notion-search-local',
  description:
    'Search locally synced Notion pages and databases by title or content. ' +
    'Much faster than API search — queries the local SQLite cache. ' +
    'Data is updated every 20 minutes via background sync.',
  input_schema: {
    type: 'object',
    properties: {
      query: {
        type: 'string',
        description: 'Search query to match against page titles and content text',
      },
      type: {
        type: 'string',
        enum: ['page', 'database', 'all'],
        description: 'Filter by type (default: all)',
      },
      limit: { type: 'number', description: 'Maximum results to return (default: 20, max: 100)' },
      include_content: {
        type: 'boolean',
        description: 'Include full content_text in results (default: false, only snippet)',
      },
      include_archived: {
        type: 'boolean',
        description: 'Include archived pages/databases (default: false)',
      },
    },
    required: ['query'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { getLocalPages, getLocalDatabases } = n();

      const query = (args.query as string) || '';
      if (!query) {
        return JSON.stringify({ error: 'Search query is required' });
      }

      const type = (args.type as string) || 'all';
      const limit = Math.min((args.limit as number) || 20, 100);
      const includeContent = (args.include_content as boolean) || false;
      const includeArchived = (args.include_archived as boolean) || false;

      const results: unknown[] = [];

      // Search pages
      if (type === 'page' || type === 'all') {
        const pages = getLocalPages({ query, limit, includeArchived }) as Array<{
          id: string;
          title: string;
          url: string | null;
          icon: string | null;
          parent_type: string;
          last_edited_time: string;
          archived: number;
          content_text: string | null;
        }>;

        for (const page of pages) {
          const entry: Record<string, unknown> = {
            object: 'page',
            id: page.id,
            title: page.title,
            url: page.url,
            icon: page.icon,
            last_edited_time: page.last_edited_time,
            parent_type: page.parent_type,
          };

          if (page.archived) entry.archived = true;

          if (includeContent && page.content_text) {
            entry.content = page.content_text;
          } else if (page.content_text) {
            // Provide a snippet (first 200 chars)
            entry.snippet = page.content_text.substring(0, 200);
            if (page.content_text.length > 200) {
              entry.snippet += '...';
            }
          }

          results.push(entry);
        }
      }

      // Search databases
      if (type === 'database' || type === 'all') {
        const databases = getLocalDatabases({ query, limit }) as Array<{
          id: string;
          title: string;
          description: string | null;
          url: string | null;
          icon: string | null;
          property_count: number;
          last_edited_time: string;
        }>;

        for (const database of databases) {
          results.push({
            object: 'database',
            id: database.id,
            title: database.title,
            description: database.description,
            url: database.url,
            icon: database.icon,
            property_count: database.property_count,
            last_edited_time: database.last_edited_time,
          });
        }
      }

      // Sort combined results by last_edited_time descending
      results.sort((a, b) => {
        const aTime = (a as Record<string, unknown>).last_edited_time as string;
        const bTime = (b as Record<string, unknown>).last_edited_time as string;
        return bTime.localeCompare(aTime);
      });

      // Apply limit to combined results
      const trimmed = results.slice(0, limit);

      return JSON.stringify({ query, count: trimmed.length, results: trimmed });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};

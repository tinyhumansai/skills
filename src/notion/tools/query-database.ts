// Tool: notion-query-database
import { notionApi } from '../api/index';
import { formatApiError, formatPageSummary, supportsMultiSourceDatabases } from '../helpers';

export const queryDatabaseTool: ToolDefinition = {
  name: 'query-database',
  description:
    'Query a database with optional filters and sorts. Returns database rows/pages. Automatically handles API version compatibility.',
  input_schema: {
    type: 'object',
    properties: {
      database_id: {
        type: 'string',
        description:
          'The database ID to query. Can be either a legacy database ID or a new data source ID - the tool will handle both automatically',
      },
      filter: {
        type: 'string',
        description: 'JSON string of filter object (Notion filter syntax)',
      },
      sorts: { type: 'string', description: 'JSON string of sorts array (Notion sort syntax)' },
      page_size: { type: 'number', description: 'Number of results (default 20, max 100)' },
    },
    required: ['database_id'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const databaseId = (args.database_id as string) || '';
      const filterJson = args.filter as string | undefined;
      const sortsJson = args.sorts as string | undefined;
      const pageSize = Math.min((args.page_size as number) || 20, 100);

      if (!databaseId) {
        return JSON.stringify({ error: 'database_id is required' });
      }

      const body: Record<string, unknown> = { page_size: pageSize };

      if (filterJson) {
        try {
          body.filter = JSON.parse(filterJson);
        } catch {
          return JSON.stringify({ error: 'Invalid filter JSON' });
        }
      }

      if (sortsJson) {
        try {
          body.sorts = JSON.parse(sortsJson);
        } catch {
          return JSON.stringify({ error: 'Invalid sorts JSON' });
        }
      }

      // Query the database using the compatibility layer
      const result = await notionApi.queryDataSource(databaseId, body);

      const rows = result.results.map((page: Record<string, unknown>) => {
        return { ...formatPageSummary(page), properties: page.properties };
      });

      // Add API version info for debugging if multi-source is supported
      const metadata: Record<string, unknown> = {
        count: rows.length,
        has_more: result.has_more,
        rows,
      };

      // Add additional metadata about API capabilities
      const supportsMultiSource = await supportsMultiSourceDatabases();
      if (supportsMultiSource) {
        metadata._api_info = {
          version: '2025-09-03',
          supports_multi_source: true,
          note: 'Using enhanced API with data source support',
        };
      }

      return JSON.stringify(metadata);
    } catch (e) {
      const error = formatApiError(e);
      console.error(`[notion][query-database] Error querying database ${args.database_id}:`, e);

      return JSON.stringify({
        error,
        database_id: args.database_id,
        troubleshooting: {
          common_solutions: [
            'Ensure the database is shared with your Notion integration',
            'Check that the database_id is correct',
            'Verify your integration has the necessary permissions',
            'If using a new database, it may need time to sync with the API',
          ],
          api_transition_note: 'This tool automatically handles both legacy and new API versions',
        },
      });
    }
  },
};

// Export for testing and debugging
export { queryDatabaseTool as default };

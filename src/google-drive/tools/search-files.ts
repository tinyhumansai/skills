// Tool: google-drive-search-files
import { driveFetch } from '../api';
import '../state';

export const searchFilesTool: ToolDefinition = {
  name: 'google-drive-search-files',
  description:
    'Search Google Drive by name, mime type, or full-text. Use Drive query syntax (e.g. name contains "report", mimeType = "application/vnd.google-apps.spreadsheet").',
  input_schema: {
    type: 'object',
    properties: {
      query: {
        type: 'string',
        description:
          'Drive search query (e.g. "name contains \'meeting\'", "mimeType = \'application/vnd.google-apps.document\'", "fullText contains \'budget\'")',
      },
      page_size: {
        type: 'number',
        description: 'Max results (default: 50, max: 1000)',
        minimum: 1,
        maximum: 1000,
      },
      page_token: { type: 'string', description: 'Page token for pagination' },
    },
    required: ['query'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      if (!oauth.getCredential()) {
        return Promise.resolve(
          JSON.stringify({
            success: false,
            error: 'Google Drive not connected. Complete OAuth setup first.',
          })
        );
      }
      const query = typeof args.query === 'string' ? args.query.trim() : '';
      if (!query) {
        return Promise.resolve(
          JSON.stringify({
            success: false,
            error: 'query is required and must be a non-empty string',
          })
        );
      }
      const parsedPageSize = Number(args.page_size);
      const pageSize = Math.max(
        1,
        Math.min(Number.isNaN(parsedPageSize) ? 50 : parsedPageSize, 1000)
      );
      const pageToken = args.page_token as string | undefined;
      const fields =
        'nextPageToken, files(id, name, mimeType, size, modifiedTime, webViewLink, parents)';
      const paramParts: string[] = [
        'q=' + encodeURIComponent(query),
        'pageSize=' + encodeURIComponent(String(pageSize)),
        'fields=' + encodeURIComponent(fields),
      ];
      if (pageToken) paramParts.push('pageToken=' + encodeURIComponent(pageToken));
      const path = '/drive/v3/files?' + paramParts.join('&');
      const response = await driveFetch(path);
      if (!response.success) {
        return Promise.resolve(
          JSON.stringify({
            success: false,
            error: response.error?.message ?? 'Failed to search files',
          })
        );
      }
      const data = response.data as {
        files?: Array<Record<string, unknown>>;
        nextPageToken?: string;
      };
      const files = (data.files ?? []).map((f: Record<string, unknown>) => ({
        id: f.id,
        name: f.name,
        mimeType: f.mimeType,
        size: f.size,
        modifiedTime: f.modifiedTime,
        webViewLink: f.webViewLink,
        parents: f.parents,
      }));
      return Promise.resolve(
        JSON.stringify({ success: true, files, next_page_token: data.nextPageToken ?? null })
      );
    } catch (e) {
      return Promise.resolve(
        JSON.stringify({ success: false, error: e instanceof Error ? e.message : String(e) })
      );
    }
  },
};

// Tool: google-drive-list-files
import { driveFetch } from '../api';
import '../state';

export const listFilesTool: ToolDefinition = {
  name: 'google-drive-list-files',
  description:
    'List files and folders in Google Drive. Optional folder ID (default: root), page size, and order.',
  input_schema: {
    type: 'object',
    properties: {
      folder_id: {
        type: 'string',
        description: 'Folder ID to list (use "root" for root). Omit to list from root.',
      },
      page_size: {
        type: 'number',
        description: 'Max number of files to return (default: 50, max: 1000)',
        minimum: 1,
        maximum: 1000,
      },
      order_by: {
        type: 'string',
        description:
          'Order: modifiedTime, name, createdTime, quotaBytesUsed, etc. Prefix with "desc" for descending.',
      },
      page_token: {
        type: 'string',
        description: 'Page token from previous response for pagination',
      },
      include_trashed: { type: 'boolean', description: 'Include trashed files (default: false)' },
    },
    required: [],
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
      const folderId = (args.folder_id as string) || 'root';
      const pageSize = Math.min(Number(args.page_size) || 50, 1000);
      const orderBy = (args.order_by as string) || 'modifiedTime desc';
      const pageToken = args.page_token as string | undefined;
      const includeTrashed = Boolean(args.include_trashed);
      const qParts: string[] = [`'${folderId}' in parents`];
      if (!includeTrashed) qParts.push('trashed = false');
      const fields =
        'nextPageToken, files(id, name, mimeType, size, modifiedTime, webViewLink, parents)';
      const paramParts: string[] = [
        'q=' + encodeURIComponent(qParts.join(' and ')),
        'pageSize=' + encodeURIComponent(String(pageSize)),
        'orderBy=' + encodeURIComponent(orderBy),
        'fields=' + encodeURIComponent(fields),
      ];
      if (pageToken) paramParts.push('pageToken=' + encodeURIComponent(pageToken));
      const path = '/drive/v3/files?' + paramParts.join('&');
      const response = await driveFetch(path);
      if (!response.success) {
        return Promise.resolve(
          JSON.stringify({
            success: false,
            error: response.error?.message ?? 'Failed to list files',
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

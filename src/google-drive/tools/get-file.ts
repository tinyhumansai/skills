// Tool: google-drive-get-file
import { driveFetch } from '../api';
import '../state';

export const getFileTool: ToolDefinition = {
  name: 'google-drive-get-file',
  description:
    'Get file metadata or export content. For native Google Docs/Sheets, use export_format to get plain text or CSV.',
  input_schema: {
    type: 'object',
    properties: {
      file_id: { type: 'string', description: 'Drive file ID' },
      export_format: {
        type: 'string',
        description:
          'For Docs/Sheets: text/plain, text/html, application/pdf, or application/vnd.openxmlformats-officedocument.spreadsheetml.sheet (xlsx). Omit for metadata only.',
      },
    },
    required: ['file_id'],
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
      const fileId = args.file_id as string;
      const exportFormat = args.export_format as string | undefined;
      if (!fileId) {
        return Promise.resolve(JSON.stringify({ success: false, error: 'file_id is required' }));
      }
      if (exportFormat) {
        const path = `/drive/v3/files/${encodeURIComponent(fileId)}/export?mimeType=${encodeURIComponent(exportFormat)}`;
        const response = await driveFetch(path, { rawBody: true });
        if (response.success) {
          return Promise.resolve(
            JSON.stringify({
              success: true,
              content: response.data as string,
              exported_as: exportFormat,
            })
          );
        }
        return Promise.resolve(
          JSON.stringify({ success: false, error: response.error?.message ?? 'Export failed' })
        );
      }
      const path = `/drive/v3/files/${encodeURIComponent(fileId)}?fields=id,name,mimeType,size,modifiedTime,webViewLink,parents,createdTime`;
      const response = await driveFetch(path);
      if (!response.success) {
        return Promise.resolve(
          JSON.stringify({ success: false, error: response.error?.message ?? 'Failed to get file' })
        );
      }
      return Promise.resolve(JSON.stringify({ success: true, file: response.data }));
    } catch (e) {
      return Promise.resolve(
        JSON.stringify({ success: false, error: e instanceof Error ? e.message : String(e) })
      );
    }
  },
};

// Tool: google-drive-create-document
// Creates a new Google Doc via Drive API (files with mimeType application/vnd.google-apps.document)
import { driveFetch } from '../api';
import '../state';

export const createDocumentTool: ToolDefinition = {
  name: 'google-drive-create-document',
  description:
    'Create a new Google Docs document in Drive. Optionally in a folder. Returns file id and webViewLink.',
  input_schema: {
    type: 'object',
    properties: {
      name: { type: 'string', description: 'Document title / file name' },
      folder_id: { type: 'string', description: 'Parent folder ID (omit for root)' },
    },
    required: ['name'],
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
      const name = args.name as string;
      const folderId = args.folder_id as string | undefined;
      if (!name) {
        return Promise.resolve(JSON.stringify({ success: false, error: 'name is required' }));
      }
      const body: Record<string, unknown> = {
        name,
        mimeType: 'application/vnd.google-apps.document',
      };
      if (folderId) {
        body.parents = [folderId];
      }
      const response = await driveFetch('/drive/v3/files', {
        method: 'POST',
        body: JSON.stringify(body),
      });
      if (!response.success) {
        return Promise.resolve(
          JSON.stringify({
            success: false,
            error: response.error?.message || 'Failed to create document',
          })
        );
      }
      const data = response.data as { id?: string; name?: string; webViewLink?: string };
      return Promise.resolve(
        JSON.stringify({
          success: true,
          id: data.id,
          name: data.name,
          webViewLink: data.webViewLink,
        })
      );
    } catch (e) {
      return Promise.resolve(
        JSON.stringify({ success: false, error: e instanceof Error ? e.message : String(e) })
      );
    }
  },
};

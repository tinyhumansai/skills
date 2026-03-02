// Tool: google-drive-get-document (Docs API)
import { driveFetch } from '../api';
import '../state';
import { DOCS_BASE } from '../types';

export const getDocumentTool: ToolDefinition = {
  name: 'google-drive-get-document',
  description:
    'Get Google Docs document structure and text content. document_id is the Drive file ID (mimeType application/vnd.google-apps.document).',
  input_schema: {
    type: 'object',
    properties: { document_id: { type: 'string', description: 'Google Doc ID (Drive file ID)' } },
    required: ['document_id'],
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
      const documentId = args.document_id as string;
      if (!documentId) {
        return Promise.resolve(
          JSON.stringify({ success: false, error: 'document_id is required' })
        );
      }
      const path = `/v1/documents/${encodeURIComponent(documentId)}`;
      const response = await driveFetch(path, { baseUrl: DOCS_BASE });
      if (!response.success) {
        return Promise.resolve(
          JSON.stringify({
            success: false,
            error: response.error?.message || 'Failed to get document',
          })
        );
      }
      const data = response.data as {
        documentId?: string;
        title?: string;
        body?: {
          content?: Array<{ paragraph?: { elements?: Array<{ textRun?: { content?: string } }> } }>;
        };
      };
      const parts: string[] = [];
      (data.body?.content ?? []).forEach(
        (c: { paragraph?: { elements?: Array<{ textRun?: { content?: string } }> } }) => {
          (c.paragraph?.elements ?? []).forEach((el: { textRun?: { content?: string } }) => {
            if (el.textRun?.content) parts.push(el.textRun.content);
          });
        }
      );
      const text = parts.join('').replace(/\n$/, '');
      return Promise.resolve(
        JSON.stringify({
          success: true,
          documentId: data.documentId,
          title: data.title,
          content: text,
        })
      );
    } catch (e) {
      return Promise.resolve(
        JSON.stringify({ success: false, error: e instanceof Error ? e.message : String(e) })
      );
    }
  },
};

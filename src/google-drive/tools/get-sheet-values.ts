// Tool: google-drive-get-sheet-values (Sheets API)
import { driveFetch } from '../api';
import '../state';
import { SHEETS_BASE } from '../types';

export const getSheetValuesTool: ToolDefinition = {
  name: 'google-drive-get-sheet-values',
  description:
    'Read a range of values from a Google Sheet. Range in A1 notation (e.g. "Sheet1!A1:D10" or "A1:B2").',
  input_schema: {
    type: 'object',
    properties: {
      spreadsheet_id: { type: 'string', description: 'Spreadsheet ID' },
      range: { type: 'string', description: 'A1 notation range (e.g. "Sheet1!A1:D10" or "A1:B2")' },
    },
    required: ['spreadsheet_id', 'range'],
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
      const spreadsheetId = args.spreadsheet_id as string;
      const range = args.range as string;
      if (!spreadsheetId || !range) {
        return Promise.resolve(
          JSON.stringify({ success: false, error: 'spreadsheet_id and range are required' })
        );
      }
      const path = `/v4/spreadsheets/${encodeURIComponent(spreadsheetId)}/values/${encodeURIComponent(range)}`;
      const response = await driveFetch(path, { baseUrl: SHEETS_BASE });
      if (!response.success) {
        return Promise.resolve(
          JSON.stringify({
            success: false,
            error: response.error?.message || 'Failed to get values',
          })
        );
      }
      const data = response.data as { range?: string; values?: unknown[][] };
      return Promise.resolve(
        JSON.stringify({ success: true, range: data.range, values: data.values ?? [] })
      );
    } catch (e) {
      return Promise.resolve(
        JSON.stringify({ success: false, error: e instanceof Error ? e.message : String(e) })
      );
    }
  },
};

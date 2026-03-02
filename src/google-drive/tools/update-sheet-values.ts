// Tool: google-drive-update-sheet-values (Sheets API)
import { driveFetch } from '../api';
import '../state';
import { SHEETS_BASE } from '../types';

export const updateSheetValuesTool: ToolDefinition = {
  name: 'google-drive-update-sheet-values',
  description:
    'Update a range of cells in a Google Sheet. Values as 2D array. value_input_option: RAW or USER_ENTERED (parses formulas/dates).',
  input_schema: {
    type: 'object',
    properties: {
      spreadsheet_id: { type: 'string', description: 'Spreadsheet ID' },
      range: { type: 'string', description: 'A1 notation range (e.g. "Sheet1!A1:B2")' },
      values: {
        type: 'array',
        description: '2D array of cell values (rows of columns), e.g. [["A1","B1"],["A2","B2"]]',
      },
      value_input_option: {
        type: 'string',
        description: 'RAW (no parsing) or USER_ENTERED (formulas, numbers, dates)',
        enum: ['RAW', 'USER_ENTERED'],
      },
    },
    required: ['spreadsheet_id', 'range', 'values'],
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
      const values = args.values as unknown[];
      const valueInputOption = (args.value_input_option as string) || 'USER_ENTERED';
      const is2DArray = Array.isArray(values) && values.every((row: unknown) => Array.isArray(row));
      if (!spreadsheetId || !range || !is2DArray) {
        return Promise.resolve(
          JSON.stringify({
            success: false,
            error:
              'spreadsheet_id, range, and values (2D array) are required; values must be a 2D array',
          })
        );
      }
      const path = `/v4/spreadsheets/${encodeURIComponent(spreadsheetId)}/values/${encodeURIComponent(range)}?valueInputOption=${valueInputOption}`;
      const response = await driveFetch(path, {
        method: 'PUT',
        body: JSON.stringify({ values }),
        baseUrl: SHEETS_BASE,
      });
      if (!response.success) {
        return Promise.resolve(
          JSON.stringify({
            success: false,
            error: response.error?.message || 'Failed to update values',
          })
        );
      }
      const data = response.data as { updatedCells?: number; updatedRows?: number };
      return Promise.resolve(
        JSON.stringify({
          success: true,
          updatedCells: data.updatedCells,
          updatedRows: data.updatedRows,
        })
      );
    } catch (e) {
      return Promise.resolve(
        JSON.stringify({ success: false, error: e instanceof Error ? e.message : String(e) })
      );
    }
  },
};

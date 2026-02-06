/** query-logs tool — query the SQLite logs table with limit/offset */
export const queryLogsTool: ToolDefinition = {
  name: 'query-logs',
  description: 'Query recent log entries from the skill database.',
  input_schema: {
    type: 'object',
    properties: {
      limit: {
        type: 'number',
        description: 'Maximum number of rows to return (default: 10)',
        minimum: 1,
        maximum: 100,
      },
    },
  },
  execute(args: Record<string, unknown>): string {
    const limit = typeof args.limit === 'number' ? args.limit : 10;
    const rows = db.all(`SELECT * FROM logs ORDER BY id DESC LIMIT ${limit}`, []);
    return JSON.stringify({ count: rows.length, rows });
  },
};

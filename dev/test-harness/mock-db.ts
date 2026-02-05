/**
 * mock-db.ts - Simple SQLite mock for QuickJS skill testing
 *
 * Provides basic SQL parsing for common operations:
 * - CREATE TABLE IF NOT EXISTS
 * - INSERT INTO ... VALUES (?, ?)
 * - SELECT ... FROM ... WHERE ... LIMIT
 * - UPDATE ... SET ... WHERE
 * - DELETE FROM ... WHERE
 */

import { getMockState, type DbTable } from './mock-state';

interface ParsedSelect {
  columns: string[];
  table: string;
  where?: { column: string; operator: string; paramIndex: number };
  orderBy?: { column: string; direction: 'ASC' | 'DESC' };
  limit?: number;
}

interface ParsedInsert {
  table: string;
  columns: string[];
}

interface ParsedUpdate {
  table: string;
  setColumns: string[];
  where?: { column: string; operator: string; paramIndex: number };
}

interface ParsedDelete {
  table: string;
  where?: { column: string; operator: string; paramIndex: number };
}

/** Execute a SQL statement (INSERT, UPDATE, DELETE, CREATE, etc.) */
export function dbExec(sql: string, params: unknown[] = []): void {
  const state = getMockState();
  const trimmedSql = sql.trim().toUpperCase();

  // CREATE TABLE IF NOT EXISTS
  if (trimmedSql.startsWith('CREATE TABLE IF NOT EXISTS')) {
    const match = sql.match(/CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\(([\s\S]+)\)/i);
    if (match) {
      const tableName = match[1];
      const columnDefs = match[2];

      // Parse columns (simplified)
      const columns = columnDefs
        .split(',')
        .map(col => col.trim().split(/\s+/)[0])
        .filter(col => col && !col.toUpperCase().startsWith('PRIMARY'));

      if (!state.db.tables[tableName]) {
        state.db.tables[tableName] = { columns, rows: [] };
      }
    }
    return;
  }

  // INSERT INTO
  if (trimmedSql.startsWith('INSERT INTO')) {
    const parsed = parseInsert(sql);
    if (parsed) {
      const table = state.db.tables[parsed.table];
      if (table) {
        const row: Record<string, unknown> = {};
        const id = table.rows.length + 1;
        row['id'] = id;

        for (let i = 0; i < parsed.columns.length; i++) {
          row[parsed.columns[i]] = params[i] ?? null;
        }
        table.rows.push(row);
      }
    }
    return;
  }

  // UPDATE
  if (trimmedSql.startsWith('UPDATE')) {
    const parsed = parseUpdate(sql);
    if (parsed) {
      const table = state.db.tables[parsed.table];
      if (table) {
        const whereParamIndex = parsed.where?.paramIndex ?? -1;
        const whereValue = whereParamIndex >= 0 ? params[whereParamIndex] : null;

        for (const row of table.rows) {
          if (!parsed.where || matchesWhere(row, parsed.where, whereValue)) {
            for (let i = 0; i < parsed.setColumns.length; i++) {
              row[parsed.setColumns[i]] = params[i] ?? null;
            }
          }
        }
      }
    }
    return;
  }

  // DELETE FROM
  if (trimmedSql.startsWith('DELETE FROM')) {
    const parsed = parseDelete(sql);
    if (parsed) {
      const table = state.db.tables[parsed.table];
      if (table) {
        const whereParamIndex = parsed.where?.paramIndex ?? -1;
        const whereValue = whereParamIndex >= 0 ? params[whereParamIndex] : null;

        table.rows = table.rows.filter(row => {
          if (!parsed.where) return false;
          return !matchesWhere(row, parsed.where, whereValue);
        });
      }
    }
    return;
  }
}

/** Query a single row */
export function dbGet(sql: string, params: unknown[] = []): Record<string, unknown> | null {
  const rows = dbAll(sql, params);
  return rows.length > 0 ? rows[0] : null;
}

/** Query multiple rows */
export function dbAll(sql: string, params: unknown[] = []): Array<Record<string, unknown>> {
  const state = getMockState();
  const parsed = parseSelect(sql);
  if (!parsed) return [];

  const table = state.db.tables[parsed.table];
  if (!table) return [];

  let results = [...table.rows];

  // Apply WHERE clause
  if (parsed.where) {
    const whereValue = params[parsed.where.paramIndex] ?? null;
    results = results.filter(row => matchesWhere(row, parsed.where!, whereValue));
  }

  // Apply ORDER BY
  if (parsed.orderBy) {
    const col = parsed.orderBy.column;
    const dir = parsed.orderBy.direction === 'DESC' ? -1 : 1;
    results.sort((a, b) => {
      const aVal = a[col];
      const bVal = b[col];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return dir;
      if (bVal == null) return -dir;
      if (aVal < bVal) return -dir;
      if (aVal > bVal) return dir;
      return 0;
    });
  }

  // Apply LIMIT
  if (parsed.limit != null && parsed.limit > 0) {
    results = results.slice(0, parsed.limit);
  }

  // Select specific columns
  if (parsed.columns.length > 0 && parsed.columns[0] !== '*') {
    results = results.map(row => {
      const filtered: Record<string, unknown> = {};
      for (const col of parsed.columns) {
        filtered[col] = row[col];
      }
      return filtered;
    });
  }

  return results;
}

/** Get value from built-in key-value table */
export function dbKvGet(key: string): unknown {
  const state = getMockState();
  return state.db.kv[key] ?? null;
}

/** Set value in built-in key-value table */
export function dbKvSet(key: string, value: unknown): void {
  const state = getMockState();
  state.db.kv[key] = value;
}

// --- SQL Parsing Helpers ---

function parseSelect(sql: string): ParsedSelect | null {
  const match = sql.match(
    /SELECT\s+([\w\s,*]+)\s+FROM\s+(\w+)(?:\s+WHERE\s+(\w+)\s*(=|<|>|<=|>=|!=)\s*\?)?(?:\s+ORDER BY\s+(\w+)(?:\s+(ASC|DESC))?)?(?:\s+LIMIT\s+(\d+))?/i
  );

  if (!match) return null;

  const columns = match[1]
    .split(',')
    .map(c => c.trim())
    .filter(c => c);

  return {
    columns,
    table: match[2],
    where: match[3] ? { column: match[3], operator: match[4], paramIndex: 0 } : undefined,
    orderBy: match[5] ? { column: match[5], direction: (match[6]?.toUpperCase() as 'ASC' | 'DESC') || 'ASC' } : undefined,
    limit: match[7] ? parseInt(match[7], 10) : undefined,
  };
}

function parseInsert(sql: string): ParsedInsert | null {
  // INSERT INTO table (col1, col2, ...) VALUES (?, ?, ...)
  const match = sql.match(/INSERT INTO\s+(\w+)\s*\(([\w\s,]+)\)\s*VALUES\s*\(/i);
  if (!match) return null;

  return {
    table: match[1],
    columns: match[2]
      .split(',')
      .map(c => c.trim())
      .filter(c => c),
  };
}

function parseUpdate(sql: string): ParsedUpdate | null {
  // UPDATE table SET col1 = ?, col2 = ? WHERE id = ?
  const match = sql.match(/UPDATE\s+(\w+)\s+SET\s+([\w\s,=?]+?)(?:\s+WHERE\s+(\w+)\s*(=|<|>|<=|>=|!=)\s*\?)?$/i);
  if (!match) return null;

  const setClause = match[2];
  const setColumns = setClause
    .split(',')
    .map(part => part.trim().split(/\s*=\s*/)[0])
    .filter(c => c);

  const whereParamIndex = setColumns.length; // WHERE param comes after SET params

  return {
    table: match[1],
    setColumns,
    where: match[3] ? { column: match[3], operator: match[4], paramIndex: whereParamIndex } : undefined,
  };
}

function parseDelete(sql: string): ParsedDelete | null {
  // DELETE FROM table WHERE col = ?
  const match = sql.match(/DELETE FROM\s+(\w+)(?:\s+WHERE\s+(\w+)\s*(=|<|>|<=|>=|!=)\s*\?)?/i);
  if (!match) return null;

  return {
    table: match[1],
    where: match[2] ? { column: match[2], operator: match[3], paramIndex: 0 } : undefined,
  };
}

function matchesWhere(
  row: Record<string, unknown>,
  where: { column: string; operator: string; paramIndex: number },
  whereValue: unknown
): boolean {
  const rowValue = row[where.column];

  switch (where.operator) {
    case '=':
      return rowValue === whereValue;
    case '!=':
      return rowValue !== whereValue;
    case '<':
      return (rowValue as number) < (whereValue as number);
    case '>':
      return (rowValue as number) > (whereValue as number);
    case '<=':
      return (rowValue as number) <= (whereValue as number);
    case '>=':
      return (rowValue as number) >= (whereValue as number);
    default:
      return false;
  }
}

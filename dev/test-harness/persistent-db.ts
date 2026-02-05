/**
 * persistent-db.ts - Real SQLite database for skill dev testing
 *
 * Wraps better-sqlite3 to provide the same db bridge API interface
 * but backed by a real .db file on disk.
 */

import Database from 'better-sqlite3';
import { mkdirSync } from 'fs';
import { dirname } from 'path';

export interface PersistentDb {
  exec(sql: string, params?: unknown[]): void;
  get(sql: string, params?: unknown[]): Record<string, unknown> | null;
  all(sql: string, params?: unknown[]): Array<Record<string, unknown>>;
  kvGet(key: string): unknown;
  kvSet(key: string, value: unknown): void;
  close(): void;
}

export function createPersistentDb(dbPath: string): PersistentDb {
  mkdirSync(dirname(dbPath), { recursive: true });

  const database = new Database(dbPath);
  database.pragma('journal_mode = WAL');

  // Create the built-in KV table
  database.exec('CREATE TABLE IF NOT EXISTS __kv (key TEXT PRIMARY KEY, value TEXT)');

  return {
    exec(sql: string, params: unknown[] = []): void {
      if (params.length === 0) {
        database.exec(sql);
      } else {
        database.prepare(sql).run(...params);
      }
    },

    get(sql: string, params: unknown[] = []): Record<string, unknown> | null {
      const row = database.prepare(sql).get(...params);
      return (row as Record<string, unknown>) ?? null;
    },

    all(sql: string, params: unknown[] = []): Array<Record<string, unknown>> {
      return database.prepare(sql).all(...params) as Array<Record<string, unknown>>;
    },

    kvGet(key: string): unknown {
      const row = database.prepare('SELECT value FROM __kv WHERE key = ?').get(key) as
        | { value: string }
        | undefined;
      if (!row) return null;
      try {
        return JSON.parse(row.value);
      } catch {
        return row.value;
      }
    },

    kvSet(key: string, value: unknown): void {
      database.prepare('INSERT OR REPLACE INTO __kv (key, value) VALUES (?, ?)').run(key, JSON.stringify(value));
    },

    close(): void {
      database.close();
    },
  };
}

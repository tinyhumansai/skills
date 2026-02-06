/**
 * persistent-store.ts - JSON file-backed key-value store for skill dev testing
 *
 * Loads from file on creation, flushes on every write.
 * Provides the same store bridge API interface.
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'fs';
import { dirname } from 'path';

export interface PersistentStore {
  get(key: string): unknown;
  set(key: string, value: unknown): void;
  delete(key: string): void;
  keys(): string[];
}

export function createPersistentStore(filePath: string): PersistentStore {
  mkdirSync(dirname(filePath), { recursive: true });

  let data: Record<string, unknown> = {};

  // Load existing data if file exists
  if (existsSync(filePath)) {
    try {
      data = JSON.parse(readFileSync(filePath, 'utf-8'));
    } catch {
      data = {};
    }
  }

  function flush(): void {
    writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8');
  }

  return {
    get(key: string): unknown {
      return data[key] ?? null;
    },

    set(key: string, value: unknown): void {
      data[key] = value;
      flush();
    },

    delete(key: string): void {
      delete data[key];
      flush();
    },

    keys(): string[] {
      return Object.keys(data);
    },
  };
}

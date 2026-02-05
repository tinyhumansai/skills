/**
 * persistent-state.ts - JSON file-backed published state for skill dev testing
 *
 * Loads from file on creation, flushes on every write.
 * Provides the same state bridge API interface.
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'fs';
import { dirname } from 'path';

export interface PersistentState {
  get(key: string): unknown;
  set(key: string, value: unknown): void;
  setPartial(partial: Record<string, unknown>): void;
}

export function createPersistentState(filePath: string): PersistentState {
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
      return data[key];
    },

    set(key: string, value: unknown): void {
      data[key] = value;
      flush();
    },

    setPartial(partial: Record<string, unknown>): void {
      Object.assign(data, partial);
      flush();
    },
  };
}

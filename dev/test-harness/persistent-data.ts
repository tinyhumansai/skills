/**
 * persistent-data.ts - Real filesystem I/O for skill dev testing
 *
 * Provides the same data bridge API interface but backed by real files
 * in a scoped directory. Creates intermediate directories for nested paths.
 * Includes path traversal guard.
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'fs';
import { dirname, join, resolve } from 'path';

export interface PersistentData {
  read(filename: string): string | null;
  write(filename: string, content: string): void;
}

export function createPersistentData(filesDir: string): PersistentData {
  mkdirSync(filesDir, { recursive: true });

  function safePath(filename: string): string {
    const resolved = resolve(filesDir, filename);
    if (!resolved.startsWith(filesDir + '/') && resolved !== filesDir) {
      throw new Error(`Path traversal detected: "${filename}"`);
    }
    return resolved;
  }

  return {
    read(filename: string): string | null {
      const filePath = safePath(filename);
      if (!existsSync(filePath)) return null;
      return readFileSync(filePath, 'utf-8');
    },

    write(filename: string, content: string): void {
      const filePath = safePath(filename);
      mkdirSync(dirname(filePath), { recursive: true });
      writeFileSync(filePath, content, 'utf-8');
    },
  };
}

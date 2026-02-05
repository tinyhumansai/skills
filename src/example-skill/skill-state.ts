/**
 * skill-state.ts — globalThis state pattern
 *
 * This pattern ensures state is accessible from both lifecycle hooks
 * and tool execute() functions, in production QuickJS and in the test harness.
 */
import type { ExampleConfig } from './types';
import { DEFAULT_CONFIG } from './types';

export interface ExampleSkillState {
  config: ExampleConfig;
  fetchCount: number;
  errorCount: number;
  lastFetchTime: string | null;
  isRunning: boolean;
}

declare global {
  function getSkillState(): ExampleSkillState;
  // eslint-disable-next-line no-var
  var __skillState: ExampleSkillState;
}

const state: ExampleSkillState = {
  config: { ...DEFAULT_CONFIG },
  fetchCount: 0,
  errorCount: 0,
  lastFetchTime: null,
  isRunning: false,
};
globalThis.__skillState = state;

globalThis.getSkillState = function (): ExampleSkillState {
  return globalThis.__skillState;
};

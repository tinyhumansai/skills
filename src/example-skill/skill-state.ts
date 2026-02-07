/**
 * skill-state.ts — globalThis state pattern
 *
 * This pattern ensures state is accessible from both lifecycle hooks
 * and tool execute() functions, in production QuickJS and in the test harness.
 */
import { DEFAULT_CONFIG, type ExampleConfig } from './types';

export interface ExampleSkillState {
  config: ExampleConfig;
  fetchCount: number;
  errorCount: number;
  lastFetchTime: string | null;
  isRunning: boolean;
}

const _g = globalThis as Record<string, unknown>;

const state: ExampleSkillState = {
  config: { ...DEFAULT_CONFIG },
  fetchCount: 0,
  errorCount: 0,
  lastFetchTime: null,
  isRunning: false,
};
_g.__skillState = state;

_g.getSkillState = function (): ExampleSkillState {
  return _g.__skillState as ExampleSkillState;
};

/** Typed accessor for use within this skill's source files. Delegates to globalThis so bundle works. */
export function getState(): ExampleSkillState {
  return (_g.getSkillState as () => ExampleSkillState)();
}

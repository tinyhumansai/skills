// Shared skill state module for GitHub skill.
// State is stored on globalThis for the runtime host; use getGitHubSkillState() elsewhere.
import type { GitHubConfig } from './types';

export interface GitHubSkillState {
  config: GitHubConfig;
  authenticated: boolean;
  activeSessions: string[];
}

declare global {
  function getGitHubSkillState(): GitHubSkillState;
  var __githubSkillState: GitHubSkillState;
}

function initGitHubSkillState(): GitHubSkillState {
  const stateObj: GitHubSkillState = {
    config: {
      token: '',
      username: '',
      refreshToken: '',
      tokenExpiresAt: 0,
      refreshTokenExpiresAt: 0,
      clientId: '',
      enableRepoTools: true,
      enableIssueTools: true,
      enablePrTools: true,
      enableSearchTools: true,
      enableCodeTools: true,
      enableReleaseTools: false,
      enableGistTools: true,
      enableWorkflowTools: false,
      enableNotificationTools: false,
    },
    authenticated: false,
    activeSessions: [],
  };

  globalThis.__githubSkillState = stateObj;
  return stateObj;
}

initGitHubSkillState();

globalThis.getGitHubSkillState = function getGitHubSkillState(): GitHubSkillState {
  const s = globalThis.__githubSkillState;
  if (!s) {
    throw new Error('[github] Skill state not initialized');
  }
  return s;
};

export function getGitHubSkillState(): GitHubSkillState {
  const s = globalThis.__githubSkillState;
  if (!s) throw new Error('[github] Skill state not initialized');
  return s;
}

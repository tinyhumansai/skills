/**
 * Gmail skill: globalThis augmentation for getGmailSkillState and related
 * helpers assigned by gmail/index.ts at runtime.
 */
interface GmailSkillStateLike {
  config: {
    maxEmailsPerSync: number;
    userEmail: string;
    showSensitiveMessages?: boolean;
    [key: string]: unknown;
  };
  profile: {
    emailAddress: string;
    messagesTotal: number;
    threadsTotal: number;
    historyId: string;
  } | null;
  syncStatus: Record<string, unknown>;
  lastApiError: string | null;
  [key: string]: unknown;
}

declare global {
  interface GlobalThis {
    getGmailSkillState?: () => GmailSkillStateLike;
    getEmails?: (opts: { maxResults?: number }) => Array<Record<string, unknown>>;
    upsertEmail?: (msg: unknown) => void;
  }
}

export {};

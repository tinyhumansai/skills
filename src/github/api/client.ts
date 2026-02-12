// GitHub REST API client using net.fetch
import { getGitHubSkillState } from '../state';

const API_BASE = 'https://api.github.com';

function getHeaders(): Record<string, string> {
  const s = getGitHubSkillState();
  // Use token from state, or fallback to GITHUB_TOKEN env (e.g. REPL or different state store)
  const token = s.config.token || (typeof platform !== 'undefined' && platform.env('GITHUB_TOKEN'));
  return {
    Authorization: `Bearer ${token || ''}`,
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'User-Agent': 'AlphaHuman-GitHub-Skill/1.0',
  };
}

export interface GHResponse {
  status: number;
  body: string;
  data: unknown;
}

export async function ghFetch(
  endpoint: string,
  options?: { method?: string; body?: unknown; accept?: string }
): Promise<GHResponse> {
  // Auto-refresh OAuth token if close to expiry
  if (globalThis.githubOAuth?.ensureValidToken) {
    await globalThis.githubOAuth.ensureValidToken();
  }

  const method = options?.method ?? 'GET';
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  const headers = getHeaders();

  if (options?.accept) {
    headers['Accept'] = options.accept;
  }

  const fetchOpts: {
    method: string;
    headers: Record<string, string>;
    body?: string;
    timeout?: number;
  } = { method, headers, timeout: 30000 };

  if (options?.body && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
    headers['Content-Type'] = 'application/json';
    fetchOpts.body = JSON.stringify(options.body);
  }

  const response = await net.fetch(url, fetchOpts);

  let data: unknown = null;
  if (response.body && response.body.trim()) {
    try {
      data = JSON.parse(response.body);
    } catch {
      data = response.body;
    }
  }

  if (response.status >= 400) {
    const msg =
      typeof data === 'object' && data !== null && 'message' in data
        ? (data as { message: string }).message
        : `HTTP ${response.status}`;
    throw new Error(`GitHub API error (${response.status}): ${msg}`);
  }

  return { status: response.status, body: response.body, data };
}

export async function ghGet(endpoint: string): Promise<unknown> {
  return (await ghFetch(endpoint)).data;
}

export async function ghPost(endpoint: string, body?: unknown): Promise<unknown> {
  return (await ghFetch(endpoint, { method: 'POST', body })).data;
}

export async function ghPut(endpoint: string, body?: unknown): Promise<unknown> {
  return (await ghFetch(endpoint, { method: 'PUT', body })).data;
}

export async function ghPatch(endpoint: string, body?: unknown): Promise<unknown> {
  return (await ghFetch(endpoint, { method: 'PATCH', body })).data;
}

export async function ghDelete(endpoint: string): Promise<unknown> {
  return (await ghFetch(endpoint, { method: 'DELETE' })).data;
}

export async function checkAuth(): Promise<{ authenticated: boolean; username: string }> {
  try {
    const user = (await ghGet('/user')) as { login: string };
    return { authenticated: true, username: user.login };
  } catch {
    return { authenticated: false, username: '' };
  }
}

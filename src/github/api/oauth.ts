// GitHub App — Device Flow authentication
// Reference: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app
import { getGitHubSkillState } from '../state';
import type { DeviceCodeResponse, OAuthErrorResponse, OAuthTokenResponse } from '../types';

const GITHUB_OAUTH_BASE = 'https://github.com';

// ---------------------------------------------------------------------------
// Device Flow — Step 1: Request device & user codes
// ---------------------------------------------------------------------------

export async function requestDeviceCode(clientId: string): Promise<DeviceCodeResponse> {
  const response = await net.fetch(`${GITHUB_OAUTH_BASE}/login/device/code`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_id: clientId }),
    timeout: 15000,
  });

  if (response.status !== 200) {
    throw new Error(`Failed to request device code: HTTP ${response.status} — ${response.body}`);
  }

  const data = JSON.parse(response.body) as DeviceCodeResponse;
  if (!data.device_code || !data.user_code) {
    throw new Error(
      'Invalid device code response from GitHub. Ensure "Enable Device Flow" is checked in your GitHub App settings.'
    );
  }

  return data;
}

// ---------------------------------------------------------------------------
// Device Flow — Step 2: Poll for user authorization
// ---------------------------------------------------------------------------

export async function pollForAccessToken(
  clientId: string,
  deviceCode: string
): Promise<OAuthTokenResponse | OAuthErrorResponse> {
  const response = await net.fetch(`${GITHUB_OAUTH_BASE}/login/oauth/access_token`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({
      client_id: clientId,
      device_code: deviceCode,
      grant_type: 'urn:ietf:params:oauth:grant-type:device_code',
    }),
    timeout: 15000,
  });

  if (response.status !== 200) {
    throw new Error(`Token poll failed: HTTP ${response.status}`);
  }

  const data = JSON.parse(response.body) as OAuthTokenResponse & OAuthErrorResponse;

  // GitHub returns 200 even for errors in the device flow — check the error field
  if (data.error) {
    return {
      error: data.error,
      error_description: data.error_description,
      error_uri: data.error_uri,
      interval: data.interval,
    } as OAuthErrorResponse;
  }

  return data as OAuthTokenResponse;
}

// ---------------------------------------------------------------------------
// Token Refresh
// ---------------------------------------------------------------------------

export async function refreshAccessToken(
  clientId: string,
  clientSecret: string,
  refreshToken: string
): Promise<OAuthTokenResponse> {
  const response = await net.fetch(`${GITHUB_OAUTH_BASE}/login/oauth/access_token`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({
      client_id: clientId,
      client_secret: clientSecret,
      grant_type: 'refresh_token',
      refresh_token: refreshToken,
    }),
    timeout: 15000,
  });

  if (response.status !== 200) {
    throw new Error(`Token refresh failed: HTTP ${response.status}`);
  }

  const data = JSON.parse(response.body) as OAuthTokenResponse & OAuthErrorResponse;
  if (data.error) {
    throw new Error(`Token refresh error: ${data.error} — ${data.error_description ?? ''}`);
  }

  return data as OAuthTokenResponse;
}

// ---------------------------------------------------------------------------
// Auto-refresh: check if token is close to expiring and refresh if needed
// ---------------------------------------------------------------------------

export async function ensureValidToken(): Promise<void> {
  const s = getGitHubSkillState();

  if (!s.config.refreshToken) return;

  const now = Date.now();
  const bufferMs = 5 * 60 * 1000; // 5 minutes before expiry

  // Token still valid
  if (s.config.tokenExpiresAt > 0 && now < s.config.tokenExpiresAt - bufferMs) {
    return;
  }

  // Refresh token expired — user must re-authorize
  if (s.config.refreshTokenExpiresAt > 0 && now >= s.config.refreshTokenExpiresAt) {
    console.error('[github] Refresh token expired — user must re-authorize');
    s.authenticated = false;
    s.config.token = '';
    s.config.refreshToken = '';
    state.set('config', s.config);
    return;
  }

  // Attempt refresh
  const clientSecret = platform.env('GITHUB_APP_CLIENT_SECRET') ?? '';
  if (!clientSecret) {
    console.error('[github] Cannot refresh token: GITHUB_APP_CLIENT_SECRET not set');
    return;
  }

  try {
    console.log('[github] Access token expiring, refreshing...');
    const result = await refreshAccessToken(s.config.clientId, clientSecret, s.config.refreshToken);

    s.config.token = result.access_token;
    if (result.refresh_token) {
      s.config.refreshToken = result.refresh_token;
    }
    if (result.expires_in) {
      s.config.tokenExpiresAt = Date.now() + result.expires_in * 1000;
    }
    if (result.refresh_token_expires_in) {
      s.config.refreshTokenExpiresAt = Date.now() + result.refresh_token_expires_in * 1000;
    }

    state.set('config', s.config);
    console.log('[github] Token refreshed successfully');
  } catch (e) {
    console.error(`[github] Token refresh failed: ${e}`);
  }
}

// ---------------------------------------------------------------------------
// Store GitHub App tokens in state
// ---------------------------------------------------------------------------

export function storeTokens(
  clientId: string,
  tokenResponse: OAuthTokenResponse,
  username: string
): void {
  const s = getGitHubSkillState();

  s.config.token = tokenResponse.access_token;
  s.config.clientId = clientId;
  s.config.username = username;

  if (tokenResponse.refresh_token) {
    s.config.refreshToken = tokenResponse.refresh_token;
  }
  if (tokenResponse.expires_in) {
    s.config.tokenExpiresAt = Date.now() + tokenResponse.expires_in * 1000;
  }
  if (tokenResponse.refresh_token_expires_in) {
    s.config.refreshTokenExpiresAt = Date.now() + tokenResponse.refresh_token_expires_in * 1000;
  }

  s.authenticated = true;
  state.set('config', s.config);
}

// Register on globalThis for access from other modules
declare global {
  var githubOAuth: {
    requestDeviceCode: typeof requestDeviceCode;
    pollForAccessToken: typeof pollForAccessToken;
    refreshAccessToken: typeof refreshAccessToken;
    ensureValidToken: typeof ensureValidToken;
    storeTokens: typeof storeTokens;
  };
}

globalThis.githubOAuth = {
  requestDeviceCode,
  pollForAccessToken,
  refreshAccessToken,
  ensureValidToken,
  storeTokens,
};

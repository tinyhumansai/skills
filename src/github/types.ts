export interface GitHubConfig {
  token: string;
  username: string;
  refreshToken: string;
  tokenExpiresAt: number; // Unix timestamp (ms) when access token expires
  refreshTokenExpiresAt: number; // Unix timestamp (ms) when refresh token expires
  clientId: string; // GitHub App Client ID used for this auth
  enableRepoTools: boolean;
  enableIssueTools: boolean;
  enablePrTools: boolean;
  enableSearchTools: boolean;
  enableCodeTools: boolean;
  enableReleaseTools: boolean;
  enableGistTools: boolean;
  enableWorkflowTools: boolean;
  enableNotificationTools: boolean;
}

export interface GitHubApiResponse {
  status: number;
  headers: Record<string, string>;
  body: string;
}

// GitHub App Device Flow types
export interface DeviceCodeResponse {
  device_code: string;
  user_code: string;
  verification_uri: string;
  expires_in: number;
  interval: number;
}

export interface OAuthTokenResponse {
  access_token: string;
  token_type: string;
  scope: string;
  expires_in?: number; // seconds until expiry (if expiration enabled)
  refresh_token?: string;
  refresh_token_expires_in?: number; // seconds until refresh token expiry
}

export interface OAuthErrorResponse {
  error: string;
  error_description?: string;
  error_uri?: string;
  interval?: number; // Updated interval for slow_down errors
}

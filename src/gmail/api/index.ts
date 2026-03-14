// ---------------------------------------------------------------------------
// Gmail API helper (uses oauth.fetch proxy)
import { getGmailSkillState } from '../state';

/** Max retries on 429 rate-limit responses. */
const MAX_RETRIES = 3;

/** Default backoff in ms when Retry-After header is absent. */
const DEFAULT_BACKOFF_MS = 5_000;

/** Blocking sleep — works in the synchronous QuickJS/V8 runtime. */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export async function gmailFetch(
  endpoint: string,
  options: {
    method?: string;
    body?: string;
    headers?: Record<string, string>;
    timeout?: number;
  } = {}
): Promise<{ success: boolean; data?: any; error?: { code: number; message: string } }> {
  const credential = oauth.getCredential();

  if (!credential) {
    console.log('[gmail] gmailFetch: no credential (OAuth not connected)');
    return {
      success: false,
      error: { code: 401, message: 'Gmail not connected. Complete OAuth setup first.' },
    };
  }

  const path = endpoint;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      console.log(
        '🚀 ~ gmailFetch ~ path:',
        path,
        JSON.stringify({
          method: options.method || 'GET',
          headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
          body: options.body,
          timeout: options.timeout || 30,
        })
      );
      const response = await oauth.fetch(path, {
        method: options.method || 'GET',
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
        body: options.body ? JSON.stringify(options.body) : undefined,
        timeout: options.timeout || 30,
      });
      console.log('🚀 ~ gmailFetch ~ response:', JSON.stringify(response));

      const s = getGmailSkillState();

      // -- 429 Rate Limit: back off and retry --------------------------------
      if (response.status === 429 && attempt < MAX_RETRIES) {
        const retryAfter = response.headers['retry-after'];
        const waitMs = retryAfter
          ? parseInt(retryAfter, 10) * 1000
          : DEFAULT_BACKOFF_MS * (attempt + 1);
        console.log(
          `[gmail] gmailFetch: 429 rate-limited path=${path} — retrying in ${waitMs}ms (attempt ${attempt + 1}/${MAX_RETRIES})`
        );
        await sleep(waitMs);
        continue;
      }

      if (response.status === 401) {
        const bodyPreview = response.body ? response.body.slice(0, 200) : '(empty)';
        console.log(
          `[gmail] gmailFetch: 401 Unauthorized path=${path} credentialId=${credential.credentialId} body=${bodyPreview}`
        );
      } else if (response.status >= 400) {
        const bodyPreview = response.body ? response.body.slice(0, 200) : '(empty)';
        console.log(
          `[gmail] gmailFetch: error path=${path} status=${response.status} body=${bodyPreview}`
        );
      }

      // Update rate limit info from headers
      if (response.headers['x-ratelimit-remaining']) {
        s.rateLimitRemaining = parseInt(response.headers['x-ratelimit-remaining'], 10);
      }
      if (response.headers['x-ratelimit-reset']) {
        s.rateLimitReset = parseInt(response.headers['x-ratelimit-reset'], 10) * 1000;
      }

      if (response.status >= 200 && response.status < 300) {
        const data = response.body ? JSON.parse(response.body) : null;
        s.lastApiError = null;
        return { success: true, data };
      } else {
        const error = response.body
          ? JSON.parse(response.body)
          : { code: response.status, message: 'API request failed' };
        s.lastApiError = error.message || `HTTP ${response.status}`;
        return { success: false, error };
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      const s = getGmailSkillState();
      s.lastApiError = errorMsg;
      return { success: false, error: { code: 500, message: errorMsg } };
    }
  }

  // Exhausted retries (only reachable after repeated 429s)
  return { success: false, error: { code: 429, message: 'Rate limit exceeded after retries' } };
}

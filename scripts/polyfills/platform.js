/**
 * Platform detection polyfill for V8 runtime.
 * Tells gramjs that we're running in a browser-like environment.
 */

// In V8 sandboxed runtime, we want browser-like behavior
export const isBrowser = true;
export const isNode = false;
export const isDeno = false;

// Check if we have WebSocket support
export const hasWebSocket = typeof WebSocket !== 'undefined';

// Check if we have Web Crypto
export const hasWebCrypto = typeof crypto !== 'undefined' && crypto.subtle !== undefined;

// Platform info
export function getPlatform() {
  if (typeof platform !== 'undefined' && platform.os) {
    return platform.os();
  }
  return 'v8-runtime';
}

export default { isBrowser, isNode, isDeno, hasWebSocket, hasWebCrypto, getPlatform };

/**
 * socks polyfill - stub for V8 runtime.
 * gramjs uses SOCKS for proxy support, which we don't need in V8.
 * The browser fallback in gramjs should be used instead.
 */

export class SocksClient {
  static createConnection() {
    throw new Error('SOCKS proxy not supported in V8 runtime. Use WebSocket connection instead.');
  }
}

export default { SocksClient };

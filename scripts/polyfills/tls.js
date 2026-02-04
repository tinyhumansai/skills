/**
 * Node.js tls module stub for V8 runtime.
 * gramjs uses WebSocket transport in browser mode with wss:// for TLS.
 */

export class TLSSocket {
  constructor() {
    throw new Error(
      'tls.TLSSocket is not supported in V8 runtime. Use WebSocket with wss:// instead.'
    );
  }
}

export class Server {
  constructor() {
    throw new Error('tls.Server is not supported in V8 runtime.');
  }
}

export function connect() {
  throw new Error('tls.connect is not supported in V8 runtime. Use WebSocket with wss:// instead.');
}

export function createServer() {
  throw new Error('tls.createServer is not supported in V8 runtime.');
}

export function createSecureContext() {
  return {};
}

export const DEFAULT_ECDH_CURVE = 'auto';
export const DEFAULT_MAX_VERSION = 'TLSv1.3';
export const DEFAULT_MIN_VERSION = 'TLSv1.2';

export default {
  TLSSocket,
  Server,
  connect,
  createServer,
  createSecureContext,
  DEFAULT_ECDH_CURVE,
  DEFAULT_MAX_VERSION,
  DEFAULT_MIN_VERSION,
};

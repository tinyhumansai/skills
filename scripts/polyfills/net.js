/**
 * Node.js net module stub for V8 runtime.
 * gramjs uses WebSocket transport in browser mode, so this is mostly a stub.
 */

export class Socket {
  constructor() {
    throw new Error('net.Socket is not supported in V8 runtime. Use WebSocket instead.');
  }
}

export class Server {
  constructor() {
    throw new Error('net.Server is not supported in V8 runtime.');
  }
}

export function createConnection() {
  throw new Error('net.createConnection is not supported in V8 runtime. Use WebSocket instead.');
}

export function connect() {
  throw new Error('net.connect is not supported in V8 runtime. Use WebSocket instead.');
}

export function createServer() {
  throw new Error('net.createServer is not supported in V8 runtime.');
}

export function isIP(input) {
  return isIPv4(input) ? 4 : isIPv6(input) ? 6 : 0;
}

export function isIPv4(input) {
  const parts = input.split('.');
  if (parts.length !== 4) return false;
  for (const part of parts) {
    const num = parseInt(part, 10);
    if (isNaN(num) || num < 0 || num > 255 || String(num) !== part) {
      return false;
    }
  }
  return true;
}

export function isIPv6(input) {
  // Simplified IPv6 check
  const parts = input.split(':');
  if (parts.length < 3 || parts.length > 8) return false;
  for (const part of parts) {
    if (part === '') continue;
    if (!/^[0-9a-fA-F]{1,4}$/.test(part)) {
      return false;
    }
  }
  return true;
}

export default { Socket, Server, createConnection, connect, createServer, isIP, isIPv4, isIPv6 };

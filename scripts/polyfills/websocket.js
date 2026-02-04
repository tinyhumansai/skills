/**
 * WebSocket adapter for V8 runtime.
 * Maps w3cwebsocket to native WebSocket.
 */

// In V8 runtime with WebSocket support, use the native WebSocket
export const w3cwebsocket =
  typeof WebSocket !== 'undefined'
    ? WebSocket
    : class FakeWebSocket {
        constructor(url, protocols) {
          throw new Error('WebSocket is not available in this V8 runtime');
        }
      };

export { w3cwebsocket as W3CWebSocket };

export default { w3cwebsocket, W3CWebSocket: w3cwebsocket };

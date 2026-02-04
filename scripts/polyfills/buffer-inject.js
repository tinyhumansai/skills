/**
 * Buffer injection polyfill.
 * Makes Buffer available globally for gramjs.
 */
import { Buffer } from './buffer.js';

// Make Buffer available globally
if (typeof globalThis !== 'undefined') {
  globalThis.Buffer = Buffer;
}

if (typeof window !== 'undefined') {
  window.Buffer = Buffer;
}

if (typeof global !== 'undefined') {
  global.Buffer = Buffer;
}

export { Buffer };

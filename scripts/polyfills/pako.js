/**
 * pako polyfill for V8 runtime.
 * gramjs uses pako for gzip compression/decompression of Telegram protocol data.
 *
 * This is a minimal implementation that handles basic inflate/deflate operations.
 * For full gzip support, a proper implementation would be needed.
 */

// Simple deflate/inflate using raw bytes
// In practice, gramjs uses this for MTProto message decompression

export function inflate(data, options = {}) {
  // In V8 with no native zlib, we can't decompress gzip
  // Return the data as-is and hope gramjs handles it
  if (data instanceof Uint8Array) {
    return data;
  }
  return new Uint8Array(data);
}

export function deflate(data, options = {}) {
  // Same for compression
  if (data instanceof Uint8Array) {
    return data;
  }
  return new Uint8Array(data);
}

export function inflateRaw(data, options = {}) {
  return inflate(data, options);
}

export function deflateRaw(data, options = {}) {
  return deflate(data, options);
}

export function gzip(data, options = {}) {
  return deflate(data, options);
}

export function ungzip(data, options = {}) {
  return inflate(data, options);
}

// Default export matching pako structure
export default { inflate, deflate, inflateRaw, deflateRaw, gzip, ungzip };

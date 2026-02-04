/**
 * Crypto polyfill for V8 runtime.
 * Provides Node.js crypto-like interface using Web Crypto API.
 */
import { Buffer } from './buffer.js';

/**
 * Generate random bytes synchronously.
 */
export function randomBytes(size) {
  const arr = new Uint8Array(size);
  crypto.getRandomValues(arr);
  return Buffer.from(arr);
}

/**
 * Pseudo-random bytes (alias for randomBytes in this implementation).
 */
export function pseudoRandomBytes(size) {
  return randomBytes(size);
}

/**
 * Generate a random UUID.
 */
export function randomUUID() {
  return crypto.randomUUID();
}

/**
 * Generate random integer in range [min, max).
 */
export function randomInt(min, max, callback) {
  if (typeof min === 'function') {
    callback = min;
    min = 0;
    max = 2 ** 48 - 1;
  } else if (typeof max === 'function') {
    callback = max;
    max = min;
    min = 0;
  }

  const range = max - min;
  const bytes = Math.ceil(Math.log2(range) / 8) || 1;
  const arr = new Uint8Array(bytes);
  crypto.getRandomValues(arr);

  let value = 0;
  for (let i = 0; i < bytes; i++) {
    value = (value << 8) | arr[i];
  }
  const result = min + (value % range);

  if (callback) {
    setTimeout(() => callback(null, result), 0);
    return;
  }
  return result;
}

/**
 * Fill buffer with random bytes.
 */
export function randomFill(buffer, offset, size, callback) {
  if (typeof offset === 'function') {
    callback = offset;
    offset = 0;
    size = buffer.length;
  } else if (typeof size === 'function') {
    callback = size;
    size = buffer.length - offset;
  }

  const bytes = randomBytes(size);
  buffer.set(bytes, offset);

  if (callback) {
    setTimeout(() => callback(null, buffer), 0);
    return;
  }
  return buffer;
}

export function randomFillSync(buffer, offset = 0, size) {
  if (size === undefined) {
    size = buffer.length - offset;
  }
  const bytes = randomBytes(size);
  buffer.set(bytes, offset);
  return buffer;
}

/**
 * Simple sync hash implementation for common algorithms.
 * Note: Web Crypto's digest is async, so we provide basic implementations.
 */
class SyncHash {
  constructor(algorithm) {
    this.algorithm = algorithm.toLowerCase().replace('-', '');
    this.data = [];
  }

  update(data, encoding) {
    if (typeof data === 'string') {
      data = Buffer.from(data, encoding || 'utf8');
    } else if (!(data instanceof Uint8Array)) {
      data = Buffer.from(data);
    }
    this.data.push(data);
    return this;
  }

  digest(encoding) {
    const combined = Buffer.concat(this.data);
    let result;

    switch (this.algorithm) {
      case 'sha1':
        result = sha1(combined);
        break;
      case 'sha256':
        result = sha256(combined);
        break;
      case 'md5':
        result = md5(combined);
        break;
      default:
        throw new Error(`Unsupported hash algorithm: ${this.algorithm}`);
    }

    if (encoding) {
      return result.toString(encoding);
    }
    return result;
  }
}

/**
 * Create a hash object.
 */
export function createHash(algorithm) {
  return new SyncHash(algorithm);
}

/**
 * SHA-1 implementation.
 */
function sha1(data) {
  const msg = data instanceof Uint8Array ? data : new Uint8Array(data);
  let h0 = 0x67452301;
  let h1 = 0xefcdab89;
  let h2 = 0x98badcfe;
  let h3 = 0x10325476;
  let h4 = 0xc3d2e1f0;

  // Pre-processing
  const msgLen = msg.length;
  const bitLen = msgLen * 8;
  const padLen = ((msgLen + 8) % 64 === 0 ? 64 : 64 - ((msgLen + 8) % 64)) + msgLen + 8;
  const padded = new Uint8Array(padLen);
  padded.set(msg);
  padded[msgLen] = 0x80;
  // Length in bits (big-endian)
  const view = new DataView(padded.buffer);
  view.setUint32(padLen - 4, bitLen, false);

  // Process 64-byte chunks
  const w = new Uint32Array(80);
  for (let i = 0; i < padLen; i += 64) {
    for (let j = 0; j < 16; j++) {
      w[j] = view.getUint32(i + j * 4, false);
    }
    for (let j = 16; j < 80; j++) {
      w[j] = rotl(w[j - 3] ^ w[j - 8] ^ w[j - 14] ^ w[j - 16], 1);
    }

    let a = h0,
      b = h1,
      c = h2,
      d = h3,
      e = h4;
    for (let j = 0; j < 80; j++) {
      let f, k;
      if (j < 20) {
        f = (b & c) | (~b & d);
        k = 0x5a827999;
      } else if (j < 40) {
        f = b ^ c ^ d;
        k = 0x6ed9eba1;
      } else if (j < 60) {
        f = (b & c) | (b & d) | (c & d);
        k = 0x8f1bbcdc;
      } else {
        f = b ^ c ^ d;
        k = 0xca62c1d6;
      }
      const temp = (rotl(a, 5) + f + e + k + w[j]) >>> 0;
      e = d;
      d = c;
      c = rotl(b, 30);
      b = a;
      a = temp;
    }
    h0 = (h0 + a) >>> 0;
    h1 = (h1 + b) >>> 0;
    h2 = (h2 + c) >>> 0;
    h3 = (h3 + d) >>> 0;
    h4 = (h4 + e) >>> 0;
  }

  const result = Buffer.alloc(20);
  result.writeUInt32BE(h0, 0);
  result.writeUInt32BE(h1, 4);
  result.writeUInt32BE(h2, 8);
  result.writeUInt32BE(h3, 12);
  result.writeUInt32BE(h4, 16);
  return result;
}

function rotl(n, s) {
  return ((n << s) | (n >>> (32 - s))) >>> 0;
}

/**
 * SHA-256 implementation.
 */
function sha256(data) {
  const K = new Uint32Array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ]);

  let H = new Uint32Array([
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
  ]);

  const msg = data instanceof Uint8Array ? data : new Uint8Array(data);
  const msgLen = msg.length;
  const bitLen = BigInt(msgLen) * 8n;

  // Calculate padding
  const padLen = msgLen % 64 < 56 ? 56 - (msgLen % 64) : 120 - (msgLen % 64);
  const totalLen = msgLen + padLen + 8;
  const padded = new Uint8Array(totalLen);
  padded.set(msg);
  padded[msgLen] = 0x80;

  // Append length (big-endian)
  const view = new DataView(padded.buffer);
  view.setBigUint64(totalLen - 8, bitLen, false);

  const W = new Uint32Array(64);

  for (let i = 0; i < totalLen; i += 64) {
    for (let t = 0; t < 16; t++) {
      W[t] = view.getUint32(i + t * 4, false);
    }
    for (let t = 16; t < 64; t++) {
      const s0 = rotr(W[t - 15], 7) ^ rotr(W[t - 15], 18) ^ (W[t - 15] >>> 3);
      const s1 = rotr(W[t - 2], 17) ^ rotr(W[t - 2], 19) ^ (W[t - 2] >>> 10);
      W[t] = (W[t - 16] + s0 + W[t - 7] + s1) >>> 0;
    }

    let [a, b, c, d, e, f, g, h] = H;

    for (let t = 0; t < 64; t++) {
      const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      const ch = (e & f) ^ (~e & g);
      const temp1 = (h + S1 + ch + K[t] + W[t]) >>> 0;
      const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const temp2 = (S0 + maj) >>> 0;

      h = g;
      g = f;
      f = e;
      e = (d + temp1) >>> 0;
      d = c;
      c = b;
      b = a;
      a = (temp1 + temp2) >>> 0;
    }

    H[0] = (H[0] + a) >>> 0;
    H[1] = (H[1] + b) >>> 0;
    H[2] = (H[2] + c) >>> 0;
    H[3] = (H[3] + d) >>> 0;
    H[4] = (H[4] + e) >>> 0;
    H[5] = (H[5] + f) >>> 0;
    H[6] = (H[6] + g) >>> 0;
    H[7] = (H[7] + h) >>> 0;
  }

  const result = Buffer.alloc(32);
  for (let i = 0; i < 8; i++) {
    result.writeUInt32BE(H[i], i * 4);
  }
  return result;
}

function rotr(n, s) {
  return ((n >>> s) | (n << (32 - s))) >>> 0;
}

/**
 * MD5 implementation.
 */
function md5(data) {
  const msg = data instanceof Uint8Array ? data : new Uint8Array(data);

  const K = new Uint32Array([
    0xd76aa478, 0xe8c7b756, 0x242070db, 0xc1bdceee, 0xf57c0faf, 0x4787c62a, 0xa8304613, 0xfd469501,
    0x698098d8, 0x8b44f7af, 0xffff5bb1, 0x895cd7be, 0x6b901122, 0xfd987193, 0xa679438e, 0x49b40821,
    0xf61e2562, 0xc040b340, 0x265e5a51, 0xe9b6c7aa, 0xd62f105d, 0x02441453, 0xd8a1e681, 0xe7d3fbc8,
    0x21e1cde6, 0xc33707d6, 0xf4d50d87, 0x455a14ed, 0xa9e3e905, 0xfcefa3f8, 0x676f02d9, 0x8d2a4c8a,
    0xfffa3942, 0x8771f681, 0x6d9d6122, 0xfde5380c, 0xa4beea44, 0x4bdecfa9, 0xf6bb4b60, 0xbebfbc70,
    0x289b7ec6, 0xeaa127fa, 0xd4ef3085, 0x04881d05, 0xd9d4d039, 0xe6db99e5, 0x1fa27cf8, 0xc4ac5665,
    0xf4292244, 0x432aff97, 0xab9423a7, 0xfc93a039, 0x655b59c3, 0x8f0ccc92, 0xffeff47d, 0x85845dd1,
    0x6fa87e4f, 0xfe2ce6e0, 0xa3014314, 0x4e0811a1, 0xf7537e82, 0xbd3af235, 0x2ad7d2bb, 0xeb86d391,
  ]);

  const S = [
    7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9,
    14, 20, 5, 9, 14, 20, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 6, 10, 15, 21,
    6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21,
  ];

  let a0 = 0x67452301;
  let b0 = 0xefcdab89;
  let c0 = 0x98badcfe;
  let d0 = 0x10325476;

  // Padding
  const msgLen = msg.length;
  const bitLen = msgLen * 8;
  const padLen = msgLen % 64 < 56 ? 56 - (msgLen % 64) : 120 - (msgLen % 64);
  const totalLen = msgLen + padLen + 8;
  const padded = new Uint8Array(totalLen);
  padded.set(msg);
  padded[msgLen] = 0x80;

  const view = new DataView(padded.buffer);
  view.setUint32(totalLen - 8, bitLen, true);

  for (let i = 0; i < totalLen; i += 64) {
    const M = new Uint32Array(16);
    for (let j = 0; j < 16; j++) {
      M[j] = view.getUint32(i + j * 4, true);
    }

    let A = a0,
      B = b0,
      C = c0,
      D = d0;

    for (let j = 0; j < 64; j++) {
      let F, g;
      if (j < 16) {
        F = (B & C) | (~B & D);
        g = j;
      } else if (j < 32) {
        F = (D & B) | (~D & C);
        g = (5 * j + 1) % 16;
      } else if (j < 48) {
        F = B ^ C ^ D;
        g = (3 * j + 5) % 16;
      } else {
        F = C ^ (B | ~D);
        g = (7 * j) % 16;
      }
      F = (F + A + K[j] + M[g]) >>> 0;
      A = D;
      D = C;
      C = B;
      B = (B + rotl(F, S[j])) >>> 0;
    }

    a0 = (a0 + A) >>> 0;
    b0 = (b0 + B) >>> 0;
    c0 = (c0 + C) >>> 0;
    d0 = (d0 + D) >>> 0;
  }

  const result = Buffer.alloc(16);
  result.writeUInt32LE(a0, 0);
  result.writeUInt32LE(b0, 4);
  result.writeUInt32LE(c0, 8);
  result.writeUInt32LE(d0, 12);
  return result;
}

/**
 * HMAC implementation.
 */
class Hmac {
  constructor(algorithm, key) {
    this.algorithm = algorithm;
    this.blockSize = algorithm === 'sha256' ? 64 : 64;

    if (typeof key === 'string') {
      key = Buffer.from(key);
    }

    if (key.length > this.blockSize) {
      key = createHash(algorithm).update(key).digest();
    }

    this.key = Buffer.alloc(this.blockSize);
    this.key.set(key);

    this.inner = createHash(algorithm);
    this.outer = createHash(algorithm);

    const ipad = Buffer.alloc(this.blockSize, 0x36);
    const opad = Buffer.alloc(this.blockSize, 0x5c);

    for (let i = 0; i < this.blockSize; i++) {
      ipad[i] ^= this.key[i];
      opad[i] ^= this.key[i];
    }

    this.inner.update(ipad);
    this.outer.update(opad);
  }

  update(data, encoding) {
    this.inner.update(data, encoding);
    return this;
  }

  digest(encoding) {
    const innerHash = this.inner.digest();
    this.outer.update(innerHash);
    return this.outer.digest(encoding);
  }
}

export function createHmac(algorithm, key) {
  return new Hmac(algorithm, key);
}

/**
 * PBKDF2 implementation.
 */
export function pbkdf2Sync(password, salt, iterations, keylen, digest = 'sha256') {
  if (typeof password === 'string') password = Buffer.from(password);
  if (typeof salt === 'string') salt = Buffer.from(salt);

  const hashLen = digest === 'sha256' ? 32 : digest === 'sha1' ? 20 : 16;
  const numBlocks = Math.ceil(keylen / hashLen);
  const result = Buffer.alloc(numBlocks * hashLen);

  for (let i = 1; i <= numBlocks; i++) {
    const blockNum = Buffer.alloc(4);
    blockNum.writeUInt32BE(i, 0);

    let U = createHmac(digest, password)
      .update(Buffer.concat([salt, blockNum]))
      .digest();
    let F = U;

    for (let j = 1; j < iterations; j++) {
      U = createHmac(digest, password).update(U).digest();
      for (let k = 0; k < hashLen; k++) {
        F[k] ^= U[k];
      }
    }

    result.set(F, (i - 1) * hashLen);
  }

  return result.subarray(0, keylen);
}

export function pbkdf2(password, salt, iterations, keylen, digest, callback) {
  try {
    const result = pbkdf2Sync(password, salt, iterations, keylen, digest);
    setTimeout(() => callback(null, result), 0);
  } catch (e) {
    setTimeout(() => callback(e), 0);
  }
}

/**
 * AES-CTR implementation for Node.js crypto compatibility.
 * Used by gramjs for TCPObfuscated connection obfuscation.
 */

// S-box for AES
const SBOX = new Uint8Array([
  0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
  0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
  0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
  0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
  0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
  0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
  0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
  0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
  0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
  0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
  0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
  0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
  0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
  0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
  0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
  0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16,
]);

// Round constants for AES key expansion
const RCON = new Uint32Array([
  0x01000000, 0x02000000, 0x04000000, 0x08000000, 0x10000000, 0x20000000, 0x40000000, 0x80000000,
  0x1b000000, 0x36000000,
]);

// Galois field multiplication
function gmul(a, b) {
  let p = 0;
  for (let i = 0; i < 8; i++) {
    if (b & 1) p ^= a;
    const hi = a & 0x80;
    a = (a << 1) & 0xff;
    if (hi) a ^= 0x1b;
    b >>= 1;
  }
  return p;
}

// Pre-compute multiplication tables
const MUL2 = new Uint8Array(256);
const MUL3 = new Uint8Array(256);
for (let i = 0; i < 256; i++) {
  MUL2[i] = gmul(i, 2);
  MUL3[i] = gmul(i, 3);
}

/**
 * Internal AES block cipher for CTR mode.
 */
class AESBlockCipher {
  constructor(key) {
    // Convert key bytes to 32-bit words (big-endian)
    const keyBytes = key instanceof Uint8Array ? key : new Uint8Array(key);
    const keyWords = new Uint32Array(keyBytes.length / 4);
    for (let i = 0; i < keyWords.length; i++) {
      keyWords[i] =
        (keyBytes[i * 4] << 24) |
        (keyBytes[i * 4 + 1] << 16) |
        (keyBytes[i * 4 + 2] << 8) |
        keyBytes[i * 4 + 3];
    }

    this.keySize = keyWords.length; // 4, 6, or 8 for AES-128, 192, 256
    this.rounds = this.keySize + 6;
    this.expandedKey = this.expandKey(keyWords);
  }

  expandKey(key) {
    const nk = this.keySize;
    const nr = this.rounds;
    const expanded = new Uint32Array(4 * (nr + 1));

    for (let i = 0; i < nk; i++) {
      expanded[i] = key[i];
    }

    for (let i = nk; i < 4 * (nr + 1); i++) {
      let temp = expanded[i - 1];

      if (i % nk === 0) {
        temp =
          ((SBOX[(temp >> 16) & 0xff] << 24) |
            (SBOX[(temp >> 8) & 0xff] << 16) |
            (SBOX[temp & 0xff] << 8) |
            SBOX[(temp >> 24) & 0xff]) ^
          RCON[Math.floor(i / nk) - 1];
      } else if (nk > 6 && i % nk === 4) {
        temp =
          (SBOX[(temp >> 24) & 0xff] << 24) |
          (SBOX[(temp >> 16) & 0xff] << 16) |
          (SBOX[(temp >> 8) & 0xff] << 8) |
          SBOX[temp & 0xff];
      }

      expanded[i] = expanded[i - nk] ^ temp;
    }

    return expanded;
  }

  subBytes(state) {
    for (let i = 0; i < 4; i++) {
      state[i] =
        (SBOX[(state[i] >> 24) & 0xff] << 24) |
        (SBOX[(state[i] >> 16) & 0xff] << 16) |
        (SBOX[(state[i] >> 8) & 0xff] << 8) |
        SBOX[state[i] & 0xff];
    }
  }

  shiftRows(state) {
    // Extract bytes
    const s = new Uint8Array(16);
    for (let i = 0; i < 4; i++) {
      s[i * 4] = (state[i] >> 24) & 0xff;
      s[i * 4 + 1] = (state[i] >> 16) & 0xff;
      s[i * 4 + 2] = (state[i] >> 8) & 0xff;
      s[i * 4 + 3] = state[i] & 0xff;
    }

    // Shift rows
    const t = new Uint8Array(16);
    for (let row = 0; row < 4; row++) {
      for (let col = 0; col < 4; col++) {
        t[col * 4 + row] = s[((col + row) % 4) * 4 + row];
      }
    }

    // Pack back
    for (let i = 0; i < 4; i++) {
      state[i] = (t[i * 4] << 24) | (t[i * 4 + 1] << 16) | (t[i * 4 + 2] << 8) | t[i * 4 + 3];
    }
  }

  mixColumns(state) {
    for (let i = 0; i < 4; i++) {
      const s0 = (state[i] >> 24) & 0xff;
      const s1 = (state[i] >> 16) & 0xff;
      const s2 = (state[i] >> 8) & 0xff;
      const s3 = state[i] & 0xff;

      const t0 = MUL2[s0] ^ MUL3[s1] ^ s2 ^ s3;
      const t1 = s0 ^ MUL2[s1] ^ MUL3[s2] ^ s3;
      const t2 = s0 ^ s1 ^ MUL2[s2] ^ MUL3[s3];
      const t3 = MUL3[s0] ^ s1 ^ s2 ^ MUL2[s3];

      state[i] = (t0 << 24) | (t1 << 16) | (t2 << 8) | t3;
    }
  }

  // Encrypt a single 16-byte block
  encryptBlock(block) {
    // Convert bytes to state (column-major order for AES)
    const state = new Uint32Array(4);
    for (let i = 0; i < 4; i++) {
      state[i] =
        (block[i * 4] << 24) | (block[i * 4 + 1] << 16) | (block[i * 4 + 2] << 8) | block[i * 4 + 3];
    }

    const w = this.expandedKey;

    // Initial round
    for (let i = 0; i < 4; i++) {
      state[i] ^= w[i];
    }

    // Main rounds
    for (let round = 1; round < this.rounds; round++) {
      this.subBytes(state);
      this.shiftRows(state);
      this.mixColumns(state);
      for (let i = 0; i < 4; i++) {
        state[i] ^= w[round * 4 + i];
      }
    }

    // Final round
    this.subBytes(state);
    this.shiftRows(state);
    for (let i = 0; i < 4; i++) {
      state[i] ^= w[this.rounds * 4 + i];
    }

    // Convert back to bytes
    const result = new Uint8Array(16);
    for (let i = 0; i < 4; i++) {
      result[i * 4] = (state[i] >> 24) & 0xff;
      result[i * 4 + 1] = (state[i] >> 16) & 0xff;
      result[i * 4 + 2] = (state[i] >> 8) & 0xff;
      result[i * 4 + 3] = state[i] & 0xff;
    }

    return result;
  }
}

/**
 * AES-CTR cipher stream.
 * CTR mode uses AES to encrypt a counter, then XORs with plaintext.
 */
class CTRCipher {
  constructor(key, iv) {
    this.aes = new AESBlockCipher(key);
    // Counter is the IV (16 bytes)
    this.counter = new Uint8Array(iv instanceof Uint8Array ? iv : new Uint8Array(iv));
    // Keystream buffer for partial blocks
    this.keystream = null;
    this.keystreamOffset = 16; // Start exhausted to generate first block
  }

  // Increment the counter (big-endian)
  incrementCounter() {
    for (let i = 15; i >= 0; i--) {
      this.counter[i]++;
      if (this.counter[i] !== 0) break;
    }
  }

  update(data) {
    const input = data instanceof Uint8Array ? data : Buffer.from(data);
    const output = new Uint8Array(input.length);

    for (let i = 0; i < input.length; i++) {
      // Generate new keystream block if needed
      if (this.keystreamOffset >= 16) {
        this.keystream = this.aes.encryptBlock(this.counter);
        this.incrementCounter();
        this.keystreamOffset = 0;
      }

      output[i] = input[i] ^ this.keystream[this.keystreamOffset++];
    }

    return Buffer.from(output);
  }

  final() {
    return Buffer.alloc(0);
  }
}

/**
 * Create a cipher for encryption.
 */
export function createCipheriv(algorithm, key, iv) {
  const algo = algorithm.toUpperCase();
  if (algo === 'AES-256-CTR') {
    return new CTRCipher(key, iv);
  }
  throw new Error(`createCipheriv not implemented for ${algorithm}`);
}

/**
 * Create a decipher for decryption.
 * Note: CTR mode is symmetric - encryption and decryption are the same operation.
 */
export function createDecipheriv(algorithm, key, iv) {
  const algo = algorithm.toUpperCase();
  if (algo === 'AES-256-CTR') {
    return new CTRCipher(key, iv); // CTR is symmetric
  }
  throw new Error(`createDecipheriv not implemented for ${algorithm}`);
}

// Export constants
export const constants = {
  SSL_OP_ALL: 0,
  SSL_OP_NO_SSLv2: 0,
  SSL_OP_NO_SSLv3: 0,
  SSL_OP_NO_TLSv1: 0,
};

// Default export
export default {
  randomBytes,
  pseudoRandomBytes,
  randomUUID,
  randomInt,
  randomFill,
  randomFillSync,
  createHash,
  createHmac,
  pbkdf2,
  pbkdf2Sync,
  createCipheriv,
  createDecipheriv,
  constants,
};

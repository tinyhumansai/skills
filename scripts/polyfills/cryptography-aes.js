/**
 * @cryptography/aes polyfill for V8 runtime.
 * Implements AES-256 encryption that gramjs uses for MTProto.
 * Includes IGE mode for MTProto encryption.
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

// Inverse S-box for AES decryption
const SBOX_INV = new Uint8Array([
  0x52, 0x09, 0x6a, 0xd5, 0x30, 0x36, 0xa5, 0x38, 0xbf, 0x40, 0xa3, 0x9e, 0x81, 0xf3, 0xd7, 0xfb,
  0x7c, 0xe3, 0x39, 0x82, 0x9b, 0x2f, 0xff, 0x87, 0x34, 0x8e, 0x43, 0x44, 0xc4, 0xde, 0xe9, 0xcb,
  0x54, 0x7b, 0x94, 0x32, 0xa6, 0xc2, 0x23, 0x3d, 0xee, 0x4c, 0x95, 0x0b, 0x42, 0xfa, 0xc3, 0x4e,
  0x08, 0x2e, 0xa1, 0x66, 0x28, 0xd9, 0x24, 0xb2, 0x76, 0x5b, 0xa2, 0x49, 0x6d, 0x8b, 0xd1, 0x25,
  0x72, 0xf8, 0xf6, 0x64, 0x86, 0x68, 0x98, 0x16, 0xd4, 0xa4, 0x5c, 0xcc, 0x5d, 0x65, 0xb6, 0x92,
  0x6c, 0x70, 0x48, 0x50, 0xfd, 0xed, 0xb9, 0xda, 0x5e, 0x15, 0x46, 0x57, 0xa7, 0x8d, 0x9d, 0x84,
  0x90, 0xd8, 0xab, 0x00, 0x8c, 0xbc, 0xd3, 0x0a, 0xf7, 0xe4, 0x58, 0x05, 0xb8, 0xb3, 0x45, 0x06,
  0xd0, 0x2c, 0x1e, 0x8f, 0xca, 0x3f, 0x0f, 0x02, 0xc1, 0xaf, 0xbd, 0x03, 0x01, 0x13, 0x8a, 0x6b,
  0x3a, 0x91, 0x11, 0x41, 0x4f, 0x67, 0xdc, 0xea, 0x97, 0xf2, 0xcf, 0xce, 0xf0, 0xb4, 0xe6, 0x73,
  0x96, 0xac, 0x74, 0x22, 0xe7, 0xad, 0x35, 0x85, 0xe2, 0xf9, 0x37, 0xe8, 0x1c, 0x75, 0xdf, 0x6e,
  0x47, 0xf1, 0x1a, 0x71, 0x1d, 0x29, 0xc5, 0x89, 0x6f, 0xb7, 0x62, 0x0e, 0xaa, 0x18, 0xbe, 0x1b,
  0xfc, 0x56, 0x3e, 0x4b, 0xc6, 0xd2, 0x79, 0x20, 0x9a, 0xdb, 0xc0, 0xfe, 0x78, 0xcd, 0x5a, 0xf4,
  0x1f, 0xdd, 0xa8, 0x33, 0x88, 0x07, 0xc7, 0x31, 0xb1, 0x12, 0x10, 0x59, 0x27, 0x80, 0xec, 0x5f,
  0x60, 0x51, 0x7f, 0xa9, 0x19, 0xb5, 0x4a, 0x0d, 0x2d, 0xe5, 0x7a, 0x9f, 0x93, 0xc9, 0x9c, 0xef,
  0xa0, 0xe0, 0x3b, 0x4d, 0xae, 0x2a, 0xf5, 0xb0, 0xc8, 0xeb, 0xbb, 0x3c, 0x83, 0x53, 0x99, 0x61,
  0x17, 0x2b, 0x04, 0x7e, 0xba, 0x77, 0xd6, 0x26, 0xe1, 0x69, 0x14, 0x63, 0x55, 0x21, 0x0c, 0x7d,
]);

// Round constants for key expansion
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

// Pre-compute multiplication tables for encryption
const MUL2 = new Uint8Array(256);
const MUL3 = new Uint8Array(256);
// Pre-compute multiplication tables for decryption
const MUL9 = new Uint8Array(256);
const MUL11 = new Uint8Array(256);
const MUL13 = new Uint8Array(256);
const MUL14 = new Uint8Array(256);

for (let i = 0; i < 256; i++) {
  MUL2[i] = gmul(i, 2);
  MUL3[i] = gmul(i, 3);
  MUL9[i] = gmul(i, 9);
  MUL11[i] = gmul(i, 11);
  MUL13[i] = gmul(i, 13);
  MUL14[i] = gmul(i, 14);
}

class AES {
  constructor(key) {
    // key is expected to be an array of 32-bit words
    this.keyWords = key;
    this.keySize = key.length; // 4, 6, or 8 words for AES-128, 192, 256
    this.rounds = this.keySize + 6; // 10, 12, or 14 rounds
    this.expandedKey = this.expandKey(key);
  }

  expandKey(key) {
    const nk = this.keySize;
    const nr = this.rounds;
    const expanded = new Uint32Array(4 * (nr + 1));

    // Copy the original key
    for (let i = 0; i < nk; i++) {
      expanded[i] = key[i];
    }

    // Expand the key
    for (let i = nk; i < 4 * (nr + 1); i++) {
      let temp = expanded[i - 1];

      if (i % nk === 0) {
        // RotWord and SubWord
        temp =
          ((SBOX[(temp >> 16) & 0xff] << 24) |
            (SBOX[(temp >> 8) & 0xff] << 16) |
            (SBOX[temp & 0xff] << 8) |
            SBOX[(temp >> 24) & 0xff]) ^
          RCON[Math.floor(i / nk) - 1];
      } else if (nk > 6 && i % nk === 4) {
        // SubWord for AES-256
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

  encrypt(block) {
    // block is expected to be an array of 4 32-bit words
    const state = new Uint32Array(block);
    const w = this.expandedKey;

    // Initial round key addition
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

    // Final round (no MixColumns)
    this.subBytes(state);
    this.shiftRows(state);
    for (let i = 0; i < 4; i++) {
      state[i] ^= w[this.rounds * 4 + i];
    }

    return Array.from(state);
  }

  decrypt(block) {
    // block is expected to be an array of 4 32-bit words
    const state = new Uint32Array(block);
    const w = this.expandedKey;

    // Initial round key addition (with last round key)
    for (let i = 0; i < 4; i++) {
      state[i] ^= w[this.rounds * 4 + i];
    }

    // Main rounds (in reverse)
    for (let round = this.rounds - 1; round > 0; round--) {
      this.invShiftRows(state);
      this.invSubBytes(state);
      for (let i = 0; i < 4; i++) {
        state[i] ^= w[round * 4 + i];
      }
      this.invMixColumns(state);
    }

    // Final round (no InvMixColumns)
    this.invShiftRows(state);
    this.invSubBytes(state);
    for (let i = 0; i < 4; i++) {
      state[i] ^= w[i];
    }

    return Array.from(state);
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

  invSubBytes(state) {
    for (let i = 0; i < 4; i++) {
      state[i] =
        (SBOX_INV[(state[i] >> 24) & 0xff] << 24) |
        (SBOX_INV[(state[i] >> 16) & 0xff] << 16) |
        (SBOX_INV[(state[i] >> 8) & 0xff] << 8) |
        SBOX_INV[state[i] & 0xff];
    }
  }

  shiftRows(state) {
    // Extract bytes from the state (column-major order)
    const s = new Uint8Array(16);
    for (let col = 0; col < 4; col++) {
      s[col * 4] = (state[col] >> 24) & 0xff;
      s[col * 4 + 1] = (state[col] >> 16) & 0xff;
      s[col * 4 + 2] = (state[col] >> 8) & 0xff;
      s[col * 4 + 3] = state[col] & 0xff;
    }

    // Shift rows left
    let t = s[1];
    s[1] = s[5];
    s[5] = s[9];
    s[9] = s[13];
    s[13] = t;

    t = s[2];
    s[2] = s[10];
    s[10] = t;
    t = s[6];
    s[6] = s[14];
    s[14] = t;

    t = s[15];
    s[15] = s[11];
    s[11] = s[7];
    s[7] = s[3];
    s[3] = t;

    // Put back into state
    for (let col = 0; col < 4; col++) {
      state[col] =
        (s[col * 4] << 24) | (s[col * 4 + 1] << 16) | (s[col * 4 + 2] << 8) | s[col * 4 + 3];
    }
  }

  invShiftRows(state) {
    // Extract bytes from the state (column-major order)
    const s = new Uint8Array(16);
    for (let col = 0; col < 4; col++) {
      s[col * 4] = (state[col] >> 24) & 0xff;
      s[col * 4 + 1] = (state[col] >> 16) & 0xff;
      s[col * 4 + 2] = (state[col] >> 8) & 0xff;
      s[col * 4 + 3] = state[col] & 0xff;
    }

    // Shift rows right (inverse of left shift)
    let t = s[13];
    s[13] = s[9];
    s[9] = s[5];
    s[5] = s[1];
    s[1] = t;

    t = s[2];
    s[2] = s[10];
    s[10] = t;
    t = s[6];
    s[6] = s[14];
    s[14] = t;

    t = s[3];
    s[3] = s[7];
    s[7] = s[11];
    s[11] = s[15];
    s[15] = t;

    // Put back into state
    for (let col = 0; col < 4; col++) {
      state[col] =
        (s[col * 4] << 24) | (s[col * 4 + 1] << 16) | (s[col * 4 + 2] << 8) | s[col * 4 + 3];
    }
  }

  mixColumns(state) {
    for (let col = 0; col < 4; col++) {
      const s0 = (state[col] >> 24) & 0xff;
      const s1 = (state[col] >> 16) & 0xff;
      const s2 = (state[col] >> 8) & 0xff;
      const s3 = state[col] & 0xff;

      state[col] =
        ((MUL2[s0] ^ MUL3[s1] ^ s2 ^ s3) << 24) |
        ((s0 ^ MUL2[s1] ^ MUL3[s2] ^ s3) << 16) |
        ((s0 ^ s1 ^ MUL2[s2] ^ MUL3[s3]) << 8) |
        (MUL3[s0] ^ s1 ^ s2 ^ MUL2[s3]);
    }
  }

  invMixColumns(state) {
    for (let col = 0; col < 4; col++) {
      const s0 = (state[col] >> 24) & 0xff;
      const s1 = (state[col] >> 16) & 0xff;
      const s2 = (state[col] >> 8) & 0xff;
      const s3 = state[col] & 0xff;

      state[col] =
        ((MUL14[s0] ^ MUL11[s1] ^ MUL13[s2] ^ MUL9[s3]) << 24) |
        ((MUL9[s0] ^ MUL14[s1] ^ MUL11[s2] ^ MUL13[s3]) << 16) |
        ((MUL13[s0] ^ MUL9[s1] ^ MUL14[s2] ^ MUL11[s3]) << 8) |
        (MUL11[s0] ^ MUL13[s1] ^ MUL9[s2] ^ MUL14[s3]);
    }
  }
}

/**
 * IGE (Infinite Garble Extension) mode for AES.
 * Used by Telegram's MTProto protocol.
 */
class IGE {
  constructor(key, iv) {
    // Key should be 32 bytes (256 bits) for AES-256
    // IV should be 32 bytes (two 16-byte blocks)
    if (key instanceof Uint8Array || Array.isArray(key)) {
      this.keyBytes = new Uint8Array(key);
    } else {
      this.keyBytes = key;
    }

    if (iv instanceof Uint8Array || Array.isArray(iv)) {
      this.ivBytes = new Uint8Array(iv);
    } else {
      this.ivBytes = iv;
    }

    // Convert key to 32-bit words for AES
    const keyWords = [];
    for (let i = 0; i < this.keyBytes.length; i += 4) {
      keyWords.push(
        (this.keyBytes[i] << 24) |
          (this.keyBytes[i + 1] << 16) |
          (this.keyBytes[i + 2] << 8) |
          this.keyBytes[i + 3]
      );
    }
    this.aes = new AES(keyWords);

    // Split IV into two 16-byte parts
    this.iv1 = this.ivBytes.slice(0, 16);
    this.iv2 = this.ivBytes.slice(16, 32);
  }

  encrypt(plaintext) {
    const data = new Uint8Array(plaintext);
    const result = new Uint8Array(data.length);

    let prevCipherBlock = new Uint8Array(this.iv2);
    let prevPlainBlock = new Uint8Array(this.iv1);

    for (let offset = 0; offset < data.length; offset += 16) {
      const block = data.slice(offset, offset + 16);

      // XOR plaintext with previous ciphertext
      const xored = new Uint8Array(16);
      for (let i = 0; i < 16; i++) {
        xored[i] = block[i] ^ prevCipherBlock[i];
      }

      // Encrypt
      const encrypted = this.encryptBlock(xored);

      // XOR with previous plaintext
      const cipherBlock = new Uint8Array(16);
      for (let i = 0; i < 16; i++) {
        cipherBlock[i] = encrypted[i] ^ prevPlainBlock[i];
      }

      result.set(cipherBlock, offset);
      prevPlainBlock = block;
      prevCipherBlock = cipherBlock;
    }

    return result;
  }

  decrypt(ciphertext) {
    const data = new Uint8Array(ciphertext);
    const result = new Uint8Array(data.length);

    let prevCipherBlock = new Uint8Array(this.iv2);
    let prevPlainBlock = new Uint8Array(this.iv1);

    for (let offset = 0; offset < data.length; offset += 16) {
      const block = data.slice(offset, offset + 16);

      // XOR ciphertext with previous plaintext
      const xored = new Uint8Array(16);
      for (let i = 0; i < 16; i++) {
        xored[i] = block[i] ^ prevPlainBlock[i];
      }

      // Decrypt
      const decrypted = this.decryptBlock(xored);

      // XOR with previous ciphertext
      const plainBlock = new Uint8Array(16);
      for (let i = 0; i < 16; i++) {
        plainBlock[i] = decrypted[i] ^ prevCipherBlock[i];
      }

      result.set(plainBlock, offset);
      prevCipherBlock = block;
      prevPlainBlock = plainBlock;
    }

    return result;
  }

  encryptBlock(block) {
    // Convert 16 bytes to 4 words
    const words = [];
    for (let i = 0; i < 16; i += 4) {
      words.push((block[i] << 24) | (block[i + 1] << 16) | (block[i + 2] << 8) | block[i + 3]);
    }

    const encrypted = this.aes.encrypt(words);

    // Convert back to bytes
    const result = new Uint8Array(16);
    for (let i = 0; i < 4; i++) {
      result[i * 4] = (encrypted[i] >> 24) & 0xff;
      result[i * 4 + 1] = (encrypted[i] >> 16) & 0xff;
      result[i * 4 + 2] = (encrypted[i] >> 8) & 0xff;
      result[i * 4 + 3] = encrypted[i] & 0xff;
    }
    return result;
  }

  decryptBlock(block) {
    // Convert 16 bytes to 4 words
    const words = [];
    for (let i = 0; i < 16; i += 4) {
      words.push((block[i] << 24) | (block[i + 1] << 16) | (block[i + 2] << 8) | block[i + 3]);
    }

    const decrypted = this.aes.decrypt(words);

    // Convert back to bytes
    const result = new Uint8Array(16);
    for (let i = 0; i < 4; i++) {
      result[i * 4] = (decrypted[i] >> 24) & 0xff;
      result[i * 4 + 1] = (decrypted[i] >> 16) & 0xff;
      result[i * 4 + 2] = (decrypted[i] >> 8) & 0xff;
      result[i * 4 + 3] = decrypted[i] & 0xff;
    }
    return result;
  }
}

export default AES;
export { AES, IGE };

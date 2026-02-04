/**
 * Buffer polyfill for V8 runtime.
 * Provides a Node.js-compatible Buffer implementation using Uint8Array.
 */

const BASE64_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
const BASE64_URL_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';

/**
 * Convert a value to a number, handling BigInt, big-integer library objects, and regular numbers.
 */
function toNumber(v) {
  if (typeof v === 'number') return v;
  if (typeof v === 'bigint') return Number(v);
  // big-integer library wrapper object (has .value property with native BigInt)
  if (v && typeof v === 'object') {
    if (typeof v.toJSNumber === 'function') {
      return v.toJSNumber();
    }
    if (typeof v.value === 'bigint') {
      return Number(v.value);
    }
    if (typeof v.valueOf === 'function') {
      const val = v.valueOf();
      if (typeof val === 'bigint') return Number(val);
      if (typeof val === 'number') return val;
    }
  }
  return Number(v);
}

function base64Encode(bytes, urlSafe = false) {
  const chars = urlSafe ? BASE64_URL_CHARS : BASE64_CHARS;
  let result = '';
  const len = bytes.length;
  let i = 0;

  while (i < len) {
    const a = bytes[i++];
    const b = i < len ? bytes[i++] : 0;
    const c = i < len ? bytes[i++] : 0;

    const triplet = (a << 16) | (b << 8) | c;

    result += chars[(triplet >> 18) & 0x3f];
    result += chars[(triplet >> 12) & 0x3f];
    result += i > len + 1 ? (urlSafe ? '' : '=') : chars[(triplet >> 6) & 0x3f];
    result += i > len ? (urlSafe ? '' : '=') : chars[triplet & 0x3f];
  }

  return result;
}

function base64Decode(str) {
  // Handle base64url
  str = str.replace(/-/g, '+').replace(/_/g, '/');
  // Add padding if needed
  while (str.length % 4) str += '=';

  const chars = BASE64_CHARS;
  const lookup = new Uint8Array(256);
  for (let i = 0; i < chars.length; i++) {
    lookup[chars.charCodeAt(i)] = i;
  }

  const len = str.length;
  let bufferLength = (len * 3) / 4;
  if (str[len - 1] === '=') bufferLength--;
  if (str[len - 2] === '=') bufferLength--;

  const bytes = new Uint8Array(bufferLength);
  let p = 0;

  for (let i = 0; i < len; i += 4) {
    const encoded1 = lookup[str.charCodeAt(i)];
    const encoded2 = lookup[str.charCodeAt(i + 1)];
    const encoded3 = lookup[str.charCodeAt(i + 2)];
    const encoded4 = lookup[str.charCodeAt(i + 3)];

    bytes[p++] = (encoded1 << 2) | (encoded2 >> 4);
    if (p < bufferLength) bytes[p++] = ((encoded2 & 15) << 4) | (encoded3 >> 2);
    if (p < bufferLength) bytes[p++] = ((encoded3 & 3) << 6) | encoded4;
  }

  return bytes;
}

export class Buffer extends Uint8Array {
  /**
   * Create a new Buffer. Handles BigInt and big-integer library objects.
   */
  constructor(arg1, arg2, arg3) {
    // Handle BigInt or big-integer library object for size
    if (typeof arg1 === 'bigint' || (arg1 && typeof arg1 === 'object' && typeof arg1.toJSNumber === 'function')) {
      super(toNumber(arg1));
    } else if (typeof arg1 === 'number') {
      super(arg1);
    } else if (arg1 instanceof ArrayBuffer) {
      // ArrayBuffer with optional offset and length
      const offset = toNumber(arg2) || 0;
      const length = arg3 !== undefined ? toNumber(arg3) : undefined;
      if (length !== undefined) {
        super(arg1, offset, length);
      } else {
        super(arg1, offset);
      }
    } else if (ArrayBuffer.isView(arg1)) {
      super(arg1);
    } else if (Array.isArray(arg1)) {
      // Convert any BigInt/big-integer elements to Numbers before passing to Uint8Array
      const numArr = arg1.map(toNumber);
      super(numArr);
    } else if (arg1 && typeof arg1.length === 'number') {
      // Array-like object - convert BigInt/big-integer elements to Numbers
      const arr = Array.from(arg1, toNumber);
      super(arr);
    } else {
      super(arg1);
    }
  }

  /**
   * Create a Buffer from various input types.
   */
  static from(data, encodingOrOffset, length) {
    // Handle BigInt or big-integer library object - convert to bytes
    if (typeof data === 'bigint' || (data && typeof data === 'object' && typeof data.toJSNumber === 'function')) {
      // Get native BigInt value
      let bigVal = typeof data === 'bigint' ? data : data.value;
      if (typeof bigVal !== 'bigint') bigVal = BigInt(data.valueOf());

      // Convert BigInt to byte array (little-endian, signed)
      const isNegative = bigVal < 0n;
      if (isNegative) bigVal = -bigVal;
      const bytes = [];
      while (bigVal > 0n) {
        bytes.push(Number(bigVal & 0xffn));
        bigVal >>= 8n;
      }
      // Ensure at least one byte
      if (bytes.length === 0) bytes.push(0);
      // Handle sign for negative numbers (two's complement)
      if (isNegative) {
        // Two's complement
        let carry = 1;
        for (let i = 0; i < bytes.length; i++) {
          const val = (~bytes[i] & 0xff) + carry;
          bytes[i] = val & 0xff;
          carry = val >> 8;
        }
        // Extend with 0xff if needed for sign
        if ((bytes[bytes.length - 1] & 0x80) === 0) {
          bytes.push(0xff);
        }
      } else {
        // Ensure positive numbers don't look negative
        if ((bytes[bytes.length - 1] & 0x80) !== 0) {
          bytes.push(0);
        }
      }
      return new Buffer(bytes);
    }
    if (data instanceof ArrayBuffer) {
      return new Buffer(data, encodingOrOffset || 0, length);
    }
    if (ArrayBuffer.isView(data)) {
      return new Buffer(data.buffer, data.byteOffset, data.byteLength);
    }
    if (typeof data === 'string') {
      const encoding = encodingOrOffset || 'utf8';
      return Buffer.fromString(data, encoding);
    }
    if (Array.isArray(data)) {
      // Convert any BigInt/big-integer elements in the array to Numbers
      const numData = data.map(toNumber);
      return new Buffer(numData);
    }
    if (typeof data === 'object' && data !== null && typeof data.length === 'number') {
      // Array-like object - convert BigInt/big-integer elements to Numbers
      const arr = Array.from(data, toNumber);
      return new Buffer(arr);
    }
    throw new TypeError(
      'First argument must be a string, Buffer, ArrayBuffer, Array, or array-like object'
    );
  }

  static fromString(str, encoding) {
    encoding = (encoding || 'utf8').toLowerCase();
    switch (encoding) {
      case 'utf8':
      case 'utf-8':
        return new Buffer(new TextEncoder().encode(str));
      case 'hex':
        return Buffer.fromHex(str);
      case 'base64':
        return new Buffer(base64Decode(str));
      case 'base64url':
        return new Buffer(base64Decode(str));
      case 'binary':
      case 'latin1':
        const bytes = new Uint8Array(str.length);
        for (let i = 0; i < str.length; i++) {
          bytes[i] = str.charCodeAt(i) & 0xff;
        }
        return new Buffer(bytes);
      default:
        throw new Error(`Unknown encoding: ${encoding}`);
    }
  }

  static fromHex(hex) {
    hex = hex.replace(/\s/g, '');
    if (hex.length % 2 !== 0) {
      throw new Error('Invalid hex string');
    }
    const bytes = new Uint8Array(hex.length / 2);
    for (let i = 0; i < hex.length; i += 2) {
      bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
    }
    return new Buffer(bytes);
  }

  static alloc(size, fill = 0, encoding) {
    // Convert BigInt to Number for size
    const numSize = typeof size === 'bigint' ? Number(size) : size;
    const buf = new Buffer(numSize);
    if (fill !== 0) {
      if (typeof fill === 'string') {
        const fillBuf = Buffer.from(fill, encoding);
        for (let i = 0; i < numSize; i++) {
          buf[i] = fillBuf[i % fillBuf.length];
        }
      } else if (typeof fill === 'number') {
        buf.fill(fill);
      }
    }
    return buf;
  }

  static allocUnsafe(size) {
    // Convert BigInt to Number for size
    const numSize = typeof size === 'bigint' ? Number(size) : size;
    return new Buffer(numSize);
  }

  static allocUnsafeSlow(size) {
    // Convert BigInt to Number for size
    const numSize = typeof size === 'bigint' ? Number(size) : size;
    return new Buffer(numSize);
  }

  static concat(list, totalLength) {
    if (!Array.isArray(list)) {
      throw new TypeError('list argument must be an array');
    }
    if (list.length === 0) {
      return Buffer.alloc(0);
    }
    if (totalLength === undefined) {
      totalLength = list.reduce((sum, buf) => sum + buf.length, 0);
    }
    const result = Buffer.alloc(totalLength);
    let offset = 0;
    for (const buf of list) {
      const len = Math.min(buf.length, totalLength - offset);
      result.set(buf.subarray(0, len), offset);
      offset += len;
      if (offset >= totalLength) break;
    }
    return result;
  }

  static isBuffer(obj) {
    return obj instanceof Buffer || obj instanceof Uint8Array;
  }

  static isEncoding(encoding) {
    return ['utf8', 'utf-8', 'hex', 'base64', 'base64url', 'binary', 'latin1'].includes(
      (encoding || '').toLowerCase()
    );
  }

  static byteLength(string, encoding = 'utf8') {
    if (typeof string !== 'string') {
      return string.length;
    }
    return Buffer.from(string, encoding).length;
  }

  static compare(a, b) {
    if (!(a instanceof Uint8Array) || !(b instanceof Uint8Array)) {
      throw new TypeError('Arguments must be Buffers');
    }
    const len = Math.min(a.length, b.length);
    for (let i = 0; i < len; i++) {
      if (a[i] < b[i]) return -1;
      if (a[i] > b[i]) return 1;
    }
    if (a.length < b.length) return -1;
    if (a.length > b.length) return 1;
    return 0;
  }

  toString(encoding = 'utf8', start = 0, end = this.length) {
    encoding = encoding.toLowerCase();
    const slice = this.subarray(start, end);
    switch (encoding) {
      case 'utf8':
      case 'utf-8':
        return new TextDecoder().decode(slice);
      case 'hex':
        return Array.from(slice)
          .map(b => b.toString(16).padStart(2, '0'))
          .join('');
      case 'base64':
        return base64Encode(slice, false);
      case 'base64url':
        return base64Encode(slice, true);
      case 'binary':
      case 'latin1':
        return Array.from(slice)
          .map(b => String.fromCharCode(b))
          .join('');
      default:
        throw new Error(`Unknown encoding: ${encoding}`);
    }
  }

  toJSON() {
    return { type: 'Buffer', data: Array.from(this) };
  }

  equals(other) {
    if (!(other instanceof Uint8Array)) return false;
    if (this.length !== other.length) return false;
    for (let i = 0; i < this.length; i++) {
      if (this[i] !== other[i]) return false;
    }
    return true;
  }

  compare(
    target,
    targetStart = 0,
    targetEnd = target.length,
    sourceStart = 0,
    sourceEnd = this.length
  ) {
    const source = this.subarray(sourceStart, sourceEnd);
    const targetSlice = target.subarray(targetStart, targetEnd);
    return Buffer.compare(source, targetSlice);
  }

  copy(target, targetStart = 0, sourceStart = 0, sourceEnd = this.length) {
    const source = this.subarray(sourceStart, sourceEnd);
    target.set(source, targetStart);
    return source.length;
  }

  slice(start, end) {
    return new Buffer(
      this.buffer,
      this.byteOffset + (start || 0),
      (end || this.length) - (start || 0)
    );
  }

  subarray(start, end) {
    const sub = super.subarray(start, end);
    return new Buffer(sub.buffer, sub.byteOffset, sub.byteLength);
  }

  write(string, offset = 0, length = this.length - offset, encoding = 'utf8') {
    const buf = Buffer.from(string, encoding);
    const len = Math.min(buf.length, length);
    this.set(buf.subarray(0, len), offset);
    return len;
  }

  // Read methods
  readUInt8(offset = 0) {
    return this[offset];
  }

  readUInt16LE(offset = 0) {
    return this[offset] | (this[offset + 1] << 8);
  }

  readUInt16BE(offset = 0) {
    return (this[offset] << 8) | this[offset + 1];
  }

  readUInt32LE(offset = 0) {
    return (
      (this[offset] |
        (this[offset + 1] << 8) |
        (this[offset + 2] << 16) |
        (this[offset + 3] << 24)) >>>
      0
    );
  }

  readUInt32BE(offset = 0) {
    return (
      ((this[offset] << 24) |
        (this[offset + 1] << 16) |
        (this[offset + 2] << 8) |
        this[offset + 3]) >>>
      0
    );
  }

  readInt8(offset = 0) {
    const val = this[offset];
    return val & 0x80 ? val - 0x100 : val;
  }

  readInt16LE(offset = 0) {
    const val = this[offset] | (this[offset + 1] << 8);
    return val & 0x8000 ? val - 0x10000 : val;
  }

  readInt16BE(offset = 0) {
    const val = (this[offset] << 8) | this[offset + 1];
    return val & 0x8000 ? val - 0x10000 : val;
  }

  readInt32LE(offset = 0) {
    return (
      this[offset] | (this[offset + 1] << 8) | (this[offset + 2] << 16) | (this[offset + 3] << 24)
    );
  }

  readInt32BE(offset = 0) {
    return (
      (this[offset] << 24) | (this[offset + 1] << 16) | (this[offset + 2] << 8) | this[offset + 3]
    );
  }

  readBigInt64LE(offset = 0) {
    const lo = this.readUInt32LE(offset);
    const hi = this.readInt32LE(offset + 4);
    return BigInt(lo) | (BigInt(hi) << 32n);
  }

  readBigInt64BE(offset = 0) {
    const hi = this.readInt32BE(offset);
    const lo = this.readUInt32BE(offset + 4);
    return BigInt(lo) | (BigInt(hi) << 32n);
  }

  readBigUInt64LE(offset = 0) {
    const lo = this.readUInt32LE(offset);
    const hi = this.readUInt32LE(offset + 4);
    return BigInt(lo) | (BigInt(hi) << 32n);
  }

  readBigUInt64BE(offset = 0) {
    const hi = this.readUInt32BE(offset);
    const lo = this.readUInt32BE(offset + 4);
    return BigInt(lo) | (BigInt(hi) << 32n);
  }

  readFloatLE(offset = 0) {
    const view = new DataView(this.buffer, this.byteOffset + offset, 4);
    return view.getFloat32(0, true);
  }

  readFloatBE(offset = 0) {
    const view = new DataView(this.buffer, this.byteOffset + offset, 4);
    return view.getFloat32(0, false);
  }

  readDoubleLE(offset = 0) {
    const view = new DataView(this.buffer, this.byteOffset + offset, 8);
    return view.getFloat64(0, true);
  }

  readDoubleBE(offset = 0) {
    const view = new DataView(this.buffer, this.byteOffset + offset, 8);
    return view.getFloat64(0, false);
  }

  // Write methods
  writeUInt8(value, offset = 0) {
    this[offset] = value & 0xff;
    return offset + 1;
  }

  writeUInt16LE(value, offset = 0) {
    this[offset] = value & 0xff;
    this[offset + 1] = (value >> 8) & 0xff;
    return offset + 2;
  }

  writeUInt16BE(value, offset = 0) {
    this[offset] = (value >> 8) & 0xff;
    this[offset + 1] = value & 0xff;
    return offset + 2;
  }

  writeUInt32LE(value, offset = 0) {
    this[offset] = value & 0xff;
    this[offset + 1] = (value >> 8) & 0xff;
    this[offset + 2] = (value >> 16) & 0xff;
    this[offset + 3] = (value >> 24) & 0xff;
    return offset + 4;
  }

  writeUInt32BE(value, offset = 0) {
    this[offset] = (value >> 24) & 0xff;
    this[offset + 1] = (value >> 16) & 0xff;
    this[offset + 2] = (value >> 8) & 0xff;
    this[offset + 3] = value & 0xff;
    return offset + 4;
  }

  writeInt8(value, offset = 0) {
    if (value < 0) value = 0x100 + value;
    this[offset] = value & 0xff;
    return offset + 1;
  }

  writeInt16LE(value, offset = 0) {
    this[offset] = value & 0xff;
    this[offset + 1] = (value >> 8) & 0xff;
    return offset + 2;
  }

  writeInt16BE(value, offset = 0) {
    this[offset] = (value >> 8) & 0xff;
    this[offset + 1] = value & 0xff;
    return offset + 2;
  }

  writeInt32LE(value, offset = 0) {
    this[offset] = value & 0xff;
    this[offset + 1] = (value >> 8) & 0xff;
    this[offset + 2] = (value >> 16) & 0xff;
    this[offset + 3] = (value >> 24) & 0xff;
    return offset + 4;
  }

  writeInt32BE(value, offset = 0) {
    this[offset] = (value >> 24) & 0xff;
    this[offset + 1] = (value >> 16) & 0xff;
    this[offset + 2] = (value >> 8) & 0xff;
    this[offset + 3] = value & 0xff;
    return offset + 4;
  }

  writeBigInt64LE(value, offset = 0) {
    const lo = Number(value & 0xffffffffn);
    const hi = Number((value >> 32n) & 0xffffffffn);
    this.writeUInt32LE(lo, offset);
    this.writeInt32LE(hi, offset + 4);
    return offset + 8;
  }

  writeBigInt64BE(value, offset = 0) {
    const lo = Number(value & 0xffffffffn);
    const hi = Number((value >> 32n) & 0xffffffffn);
    this.writeInt32BE(hi, offset);
    this.writeUInt32BE(lo, offset + 4);
    return offset + 8;
  }

  writeBigUInt64LE(value, offset = 0) {
    const lo = Number(value & 0xffffffffn);
    const hi = Number((value >> 32n) & 0xffffffffn);
    this.writeUInt32LE(lo, offset);
    this.writeUInt32LE(hi, offset + 4);
    return offset + 8;
  }

  writeBigUInt64BE(value, offset = 0) {
    const lo = Number(value & 0xffffffffn);
    const hi = Number((value >> 32n) & 0xffffffffn);
    this.writeUInt32BE(hi, offset);
    this.writeUInt32BE(lo, offset + 4);
    return offset + 8;
  }

  writeFloatLE(value, offset = 0) {
    const view = new DataView(this.buffer, this.byteOffset + offset, 4);
    view.setFloat32(0, value, true);
    return offset + 4;
  }

  writeFloatBE(value, offset = 0) {
    const view = new DataView(this.buffer, this.byteOffset + offset, 4);
    view.setFloat32(0, value, false);
    return offset + 4;
  }

  writeDoubleLE(value, offset = 0) {
    const view = new DataView(this.buffer, this.byteOffset + offset, 8);
    view.setFloat64(0, value, true);
    return offset + 8;
  }

  writeDoubleBE(value, offset = 0) {
    const view = new DataView(this.buffer, this.byteOffset + offset, 8);
    view.setFloat64(0, value, false);
    return offset + 8;
  }

  // Swap methods
  swap16() {
    for (let i = 0; i < this.length; i += 2) {
      const a = this[i];
      this[i] = this[i + 1];
      this[i + 1] = a;
    }
    return this;
  }

  swap32() {
    for (let i = 0; i < this.length; i += 4) {
      const a = this[i];
      const b = this[i + 1];
      this[i] = this[i + 3];
      this[i + 1] = this[i + 2];
      this[i + 2] = b;
      this[i + 3] = a;
    }
    return this;
  }

  swap64() {
    for (let i = 0; i < this.length; i += 8) {
      for (let j = 0; j < 4; j++) {
        const a = this[i + j];
        this[i + j] = this[i + 7 - j];
        this[i + 7 - j] = a;
      }
    }
    return this;
  }

  indexOf(value, byteOffset = 0, encoding = 'utf8') {
    if (typeof value === 'string') {
      value = Buffer.from(value, encoding);
    } else if (typeof value === 'number') {
      for (let i = byteOffset; i < this.length; i++) {
        if (this[i] === value) return i;
      }
      return -1;
    }

    outer: for (let i = byteOffset; i <= this.length - value.length; i++) {
      for (let j = 0; j < value.length; j++) {
        if (this[i + j] !== value[j]) continue outer;
      }
      return i;
    }
    return -1;
  }

  includes(value, byteOffset = 0, encoding = 'utf8') {
    return this.indexOf(value, byteOffset, encoding) !== -1;
  }
}

export default Buffer;

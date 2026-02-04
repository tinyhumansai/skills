/**
 * Node.js util module polyfill for V8 runtime.
 * Provides utility functions commonly used in Node.js.
 */

export function format(fmt, ...args) {
  if (typeof fmt !== 'string') {
    return [fmt, ...args].map(v => inspect(v)).join(' ');
  }

  let i = 0;
  return (
    fmt.replace(/%[sdjifoOc%]/g, match => {
      if (match === '%%') return '%';
      if (i >= args.length) return match;
      const arg = args[i++];
      switch (match) {
        case '%s':
          return String(arg);
        case '%d':
          return Number(arg).toString();
        case '%i':
          return parseInt(arg, 10).toString();
        case '%f':
          return parseFloat(arg).toString();
        case '%j':
          return safeStringify(arg);
        case '%o':
        case '%O':
          return inspect(arg);
        case '%c':
          return ''; // CSS styling not supported
        default:
          return match;
      }
    }) +
    (i < args.length
      ? ' ' +
        args
          .slice(i)
          .map(v => inspect(v))
          .join(' ')
      : '')
  );
}

function safeStringify(obj) {
  try {
    return JSON.stringify(obj);
  } catch (e) {
    return '[Circular]';
  }
}

export function inspect(obj, options = {}) {
  const seen = new WeakSet();

  function _inspect(value, depth = 0) {
    if (value === null) return 'null';
    if (value === undefined) return 'undefined';

    const type = typeof value;

    if (type === 'boolean') return value.toString();
    if (type === 'number') return Object.is(value, -0) ? '-0' : value.toString();
    if (type === 'bigint') return value.toString() + 'n';
    if (type === 'string') return `'${value}'`;
    if (type === 'symbol') return value.toString();
    if (type === 'function') {
      const name = value.name || 'anonymous';
      return `[Function: ${name}]`;
    }

    if (type !== 'object') return String(value);

    if (seen.has(value)) return '[Circular]';
    seen.add(value);

    const maxDepth = options.depth === null ? Infinity : options.depth || 2;
    if (depth > maxDepth) return '[Object]';

    if (Array.isArray(value)) {
      if (value.length === 0) return '[]';
      const items = value.map(v => _inspect(v, depth + 1)).join(', ');
      return `[ ${items} ]`;
    }

    if (value instanceof Date) {
      return value.toISOString();
    }

    if (value instanceof RegExp) {
      return value.toString();
    }

    if (value instanceof Error) {
      return value.stack || value.toString();
    }

    if (value instanceof Map) {
      const items = [...value.entries()]
        .map(([k, v]) => `${_inspect(k, depth + 1)} => ${_inspect(v, depth + 1)}`)
        .join(', ');
      return `Map(${value.size}) { ${items} }`;
    }

    if (value instanceof Set) {
      const items = [...value].map(v => _inspect(v, depth + 1)).join(', ');
      return `Set(${value.size}) { ${items} }`;
    }

    if (value instanceof ArrayBuffer) {
      return `ArrayBuffer { byteLength: ${value.byteLength} }`;
    }

    if (ArrayBuffer.isView(value)) {
      const name = value.constructor.name;
      return `${name}(${value.length}) [ ... ]`;
    }

    // Plain object
    const keys = Object.keys(value);
    if (keys.length === 0) return '{}';

    const items = keys.map(k => `${k}: ${_inspect(value[k], depth + 1)}`).join(', ');
    return `{ ${items} }`;
  }

  return _inspect(obj);
}

export function deprecate(fn, msg) {
  let warned = false;
  return function (...args) {
    if (!warned) {
      console.warn('DeprecationWarning:', msg);
      warned = true;
    }
    return fn.apply(this, args);
  };
}

export function inherits(ctor, superCtor) {
  if (superCtor) {
    ctor.super_ = superCtor;
    Object.setPrototypeOf(ctor.prototype, superCtor.prototype);
  }
}

export function promisify(fn) {
  return function (...args) {
    return new Promise((resolve, reject) => {
      fn(...args, (err, result) => {
        if (err) {
          reject(err);
        } else {
          resolve(result);
        }
      });
    });
  };
}

export function callbackify(fn) {
  return function (...args) {
    const callback = args.pop();
    Promise.resolve(fn(...args))
      .then(result => callback(null, result))
      .catch(err => callback(err));
  };
}

export function isArray(arg) {
  return Array.isArray(arg);
}

export function isBoolean(arg) {
  return typeof arg === 'boolean';
}

export function isNull(arg) {
  return arg === null;
}

export function isNullOrUndefined(arg) {
  return arg === null || arg === undefined;
}

export function isNumber(arg) {
  return typeof arg === 'number';
}

export function isString(arg) {
  return typeof arg === 'string';
}

export function isSymbol(arg) {
  return typeof arg === 'symbol';
}

export function isUndefined(arg) {
  return arg === undefined;
}

export function isRegExp(arg) {
  return arg instanceof RegExp;
}

export function isObject(arg) {
  return typeof arg === 'object' && arg !== null;
}

export function isDate(arg) {
  return arg instanceof Date;
}

export function isError(arg) {
  return arg instanceof Error;
}

export function isFunction(arg) {
  return typeof arg === 'function';
}

export function isPrimitive(arg) {
  return (
    arg === null ||
    typeof arg === 'boolean' ||
    typeof arg === 'number' ||
    typeof arg === 'string' ||
    typeof arg === 'symbol' ||
    typeof arg === 'undefined'
  );
}

export function isBuffer(arg) {
  return arg instanceof Uint8Array;
}

export function debuglog(section) {
  const debug = false; // Could check environment
  return debug ? (...args) => console.error(`${section.toUpperCase()}:`, ...args) : () => {};
}

export const types = {
  isArrayBuffer: v => v instanceof ArrayBuffer,
  isArrayBufferView: v => ArrayBuffer.isView(v),
  isAsyncFunction: v => v?.constructor?.name === 'AsyncFunction',
  isBigInt64Array: v => v instanceof BigInt64Array,
  isBigUint64Array: v => v instanceof BigUint64Array,
  isDataView: v => v instanceof DataView,
  isDate: v => v instanceof Date,
  isFloat32Array: v => v instanceof Float32Array,
  isFloat64Array: v => v instanceof Float64Array,
  isGeneratorFunction: v => v?.constructor?.name === 'GeneratorFunction',
  isGeneratorObject: v => v?.constructor?.name === 'Generator',
  isInt8Array: v => v instanceof Int8Array,
  isInt16Array: v => v instanceof Int16Array,
  isInt32Array: v => v instanceof Int32Array,
  isMap: v => v instanceof Map,
  isMapIterator: v => v?.[Symbol.toStringTag] === 'Map Iterator',
  isNativeError: v => v instanceof Error,
  isPromise: v => v instanceof Promise,
  isRegExp: v => v instanceof RegExp,
  isSet: v => v instanceof Set,
  isSetIterator: v => v?.[Symbol.toStringTag] === 'Set Iterator',
  isSharedArrayBuffer: v =>
    typeof SharedArrayBuffer !== 'undefined' && v instanceof SharedArrayBuffer,
  isTypedArray: v => ArrayBuffer.isView(v) && !(v instanceof DataView),
  isUint8Array: v => v instanceof Uint8Array,
  isUint8ClampedArray: v => v instanceof Uint8ClampedArray,
  isUint16Array: v => v instanceof Uint16Array,
  isUint32Array: v => v instanceof Uint32Array,
  isWeakMap: v => v instanceof WeakMap,
  isWeakSet: v => v instanceof WeakSet,
};

export class TextEncoder {
  constructor() {
    this.encoding = 'utf-8';
  }
  encode(str) {
    return new globalThis.TextEncoder().encode(str);
  }
}

export class TextDecoder {
  constructor(encoding = 'utf-8') {
    this.encoding = encoding;
  }
  decode(input) {
    return new globalThis.TextDecoder(this.encoding).decode(input);
  }
}

export default {
  format,
  inspect,
  deprecate,
  inherits,
  promisify,
  callbackify,
  isArray,
  isBoolean,
  isNull,
  isNullOrUndefined,
  isNumber,
  isString,
  isSymbol,
  isUndefined,
  isRegExp,
  isObject,
  isDate,
  isError,
  isFunction,
  isPrimitive,
  isBuffer,
  debuglog,
  types,
  TextEncoder,
  TextDecoder,
};

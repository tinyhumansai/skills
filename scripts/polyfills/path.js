/**
 * Node.js path module polyfill for V8 runtime.
 * Provides basic path manipulation utilities.
 */

const isWindows = typeof platform !== 'undefined' ? platform.os() === 'windows' : false;

const sep = isWindows ? '\\' : '/';
const delimiter = isWindows ? ';' : ':';

export function basename(path, ext) {
  if (typeof path !== 'string') {
    throw new TypeError('Path must be a string');
  }

  let start = 0;
  let end = path.length;

  // Find the last separator
  for (let i = path.length - 1; i >= 0; i--) {
    if (path[i] === '/' || path[i] === '\\') {
      start = i + 1;
      break;
    }
  }

  // Remove trailing separator
  if (end > start && (path[end - 1] === '/' || path[end - 1] === '\\')) {
    end--;
  }

  const base = path.slice(start, end);

  if (ext && base.endsWith(ext)) {
    return base.slice(0, -ext.length);
  }

  return base;
}

export function dirname(path) {
  if (typeof path !== 'string') {
    throw new TypeError('Path must be a string');
  }

  if (path.length === 0) return '.';

  // Find the last separator
  let end = -1;
  for (let i = path.length - 1; i >= 0; i--) {
    if (path[i] === '/' || path[i] === '\\') {
      // Skip trailing separators
      if (i < path.length - 1) {
        end = i;
        break;
      }
    }
  }

  if (end === -1) {
    return path[0] === '/' || path[0] === '\\' ? path[0] : '.';
  }

  if (end === 0) {
    return path[0];
  }

  return path.slice(0, end);
}

export function extname(path) {
  if (typeof path !== 'string') {
    throw new TypeError('Path must be a string');
  }

  let startDot = -1;
  let startPart = 0;

  for (let i = path.length - 1; i >= 0; i--) {
    const char = path[i];
    if (char === '/' || char === '\\') {
      startPart = i + 1;
      break;
    }
    if (char === '.' && startDot === -1) {
      startDot = i;
    }
  }

  if (startDot === -1 || startDot === startPart || startDot === startPart + 1) {
    return '';
  }

  return path.slice(startDot);
}

export function join(...paths) {
  if (paths.length === 0) return '.';

  let joined = '';
  for (const path of paths) {
    if (typeof path !== 'string') {
      throw new TypeError('Path must be a string');
    }
    if (path.length > 0) {
      if (joined.length === 0) {
        joined = path;
      } else {
        joined += '/' + path;
      }
    }
  }

  return normalize(joined);
}

export function normalize(path) {
  if (typeof path !== 'string') {
    throw new TypeError('Path must be a string');
  }

  if (path.length === 0) return '.';

  const isAbsolute = path[0] === '/' || path[0] === '\\';
  const trailingSep = path[path.length - 1] === '/' || path[path.length - 1] === '\\';

  // Normalize separators
  path = path.replace(/\\/g, '/').replace(/\/+/g, '/');

  const parts = path.split('/').filter(Boolean);
  const stack = [];

  for (const part of parts) {
    if (part === '..') {
      if (stack.length > 0 && stack[stack.length - 1] !== '..') {
        stack.pop();
      } else if (!isAbsolute) {
        stack.push('..');
      }
    } else if (part !== '.') {
      stack.push(part);
    }
  }

  let result = stack.join('/');

  if (isAbsolute) {
    result = '/' + result;
  }

  if (trailingSep && result.length > 0 && result !== '/') {
    result += '/';
  }

  return result || '.';
}

export function resolve(...paths) {
  let resolvedPath = '';
  let resolvedAbsolute = false;

  for (let i = paths.length - 1; i >= -1 && !resolvedAbsolute; i--) {
    const path = i >= 0 ? paths[i] : '/';

    if (typeof path !== 'string') {
      throw new TypeError('Path must be a string');
    }

    if (path.length === 0) continue;

    resolvedPath = path + '/' + resolvedPath;
    resolvedAbsolute = path[0] === '/' || path[0] === '\\';
  }

  resolvedPath = normalize(resolvedPath);

  if (resolvedAbsolute) {
    return '/' + resolvedPath.replace(/^\//, '');
  }

  return resolvedPath || '.';
}

export function isAbsolute(path) {
  if (typeof path !== 'string') {
    throw new TypeError('Path must be a string');
  }

  return path.length > 0 && (path[0] === '/' || path[0] === '\\');
}

export function relative(from, to) {
  if (typeof from !== 'string' || typeof to !== 'string') {
    throw new TypeError('Path must be a string');
  }

  from = resolve(from);
  to = resolve(to);

  if (from === to) return '';

  const fromParts = from.split('/').filter(Boolean);
  const toParts = to.split('/').filter(Boolean);

  let commonLength = 0;
  const minLength = Math.min(fromParts.length, toParts.length);

  for (let i = 0; i < minLength; i++) {
    if (fromParts[i] === toParts[i]) {
      commonLength++;
    } else {
      break;
    }
  }

  const upCount = fromParts.length - commonLength;
  const remaining = toParts.slice(commonLength);

  const result = [];
  for (let i = 0; i < upCount; i++) {
    result.push('..');
  }
  result.push(...remaining);

  return result.join('/') || '.';
}

export function parse(path) {
  if (typeof path !== 'string') {
    throw new TypeError('Path must be a string');
  }

  const result = { root: '', dir: '', base: '', ext: '', name: '' };

  if (path.length === 0) return result;

  result.root = isAbsolute(path) ? '/' : '';
  result.base = basename(path);
  result.ext = extname(path);
  result.name = result.base.slice(0, result.base.length - result.ext.length);
  result.dir = dirname(path);

  return result;
}

export function format(pathObject) {
  if (typeof pathObject !== 'object' || pathObject === null) {
    throw new TypeError('Path object must be an object');
  }

  const dir = pathObject.dir || pathObject.root;
  const base = pathObject.base || (pathObject.name || '') + (pathObject.ext || '');

  if (!dir) return base;
  if (dir === pathObject.root) return dir + base;
  return dir + '/' + base;
}

// posix and win32 namespaces (both point to the same implementation)
export const posix = {
  sep: '/',
  delimiter: ':',
  basename,
  dirname,
  extname,
  join,
  normalize,
  resolve,
  isAbsolute,
  relative,
  parse,
  format,
};

export const win32 = {
  sep: '\\',
  delimiter: ';',
  basename,
  dirname,
  extname,
  join,
  normalize,
  resolve,
  isAbsolute,
  relative,
  parse,
  format,
};

export { sep, delimiter };

export default {
  sep,
  delimiter,
  basename,
  dirname,
  extname,
  join,
  normalize,
  resolve,
  isAbsolute,
  relative,
  parse,
  format,
  posix,
  win32,
};

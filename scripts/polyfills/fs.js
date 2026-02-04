/**
 * Node.js fs module stub for V8 runtime.
 * File operations should use the V8 data bridge instead.
 */

// Check if V8 data bridge is available
const hasData = typeof data !== 'undefined';

export function readFileSync(path, options) {
  if (hasData) {
    const content = data.read(path);
    if (content === null) {
      const error = new Error(`ENOENT: no such file or directory, open '${path}'`);
      error.code = 'ENOENT';
      throw error;
    }
    if (typeof options === 'string' || (options && options.encoding)) {
      return content;
    }
    return Buffer.from(content);
  }
  throw new Error('fs.readFileSync is not supported in V8 runtime. Use data.read() instead.');
}

export function writeFileSync(path, data, options) {
  if (hasData) {
    const content = typeof data === 'string' ? data : data.toString();
    data.write(path, content);
    return;
  }
  throw new Error('fs.writeFileSync is not supported in V8 runtime. Use data.write() instead.');
}

export function existsSync(path) {
  if (hasData) {
    return data.read(path) !== null;
  }
  return false;
}

export function mkdirSync() {
  // No-op - directories not supported in V8 data bridge
}

export function unlinkSync(path) {
  if (hasData) {
    data.write(path, '');
  }
}

export function readdirSync() {
  return [];
}

export function statSync(path) {
  if (hasData) {
    const content = data.read(path);
    if (content === null) {
      const error = new Error(`ENOENT: no such file or directory, stat '${path}'`);
      error.code = 'ENOENT';
      throw error;
    }
    return {
      isFile: () => true,
      isDirectory: () => false,
      isSymbolicLink: () => false,
      size: content.length,
      mtime: new Date(),
      ctime: new Date(),
      atime: new Date(),
    };
  }
  throw new Error('fs.statSync is not supported in V8 runtime.');
}

// Async versions
export function readFile(path, options, callback) {
  if (typeof options === 'function') {
    callback = options;
    options = undefined;
  }
  try {
    const result = readFileSync(path, options);
    setTimeout(() => callback(null, result), 0);
  } catch (e) {
    setTimeout(() => callback(e), 0);
  }
}

export function writeFile(path, data, options, callback) {
  if (typeof options === 'function') {
    callback = options;
    options = undefined;
  }
  try {
    writeFileSync(path, data, options);
    setTimeout(() => callback(null), 0);
  } catch (e) {
    setTimeout(() => callback(e), 0);
  }
}

export function exists(path, callback) {
  const result = existsSync(path);
  setTimeout(() => callback(result), 0);
}

export function mkdir(path, options, callback) {
  if (typeof options === 'function') {
    callback = options;
  }
  setTimeout(() => callback && callback(null), 0);
}

export function unlink(path, callback) {
  try {
    unlinkSync(path);
    setTimeout(() => callback(null), 0);
  } catch (e) {
    setTimeout(() => callback(e), 0);
  }
}

export function readdir(path, options, callback) {
  if (typeof options === 'function') {
    callback = options;
  }
  setTimeout(() => callback(null, []), 0);
}

export function stat(path, options, callback) {
  if (typeof options === 'function') {
    callback = options;
  }
  try {
    const result = statSync(path);
    setTimeout(() => callback(null, result), 0);
  } catch (e) {
    setTimeout(() => callback(e), 0);
  }
}

// Promises API
export const promises = {
  readFile: (path, options) =>
    new Promise((resolve, reject) =>
      readFile(path, options, (err, data) => (err ? reject(err) : resolve(data)))
    ),
  writeFile: (path, data, options) =>
    new Promise((resolve, reject) =>
      writeFile(path, data, options, err => (err ? reject(err) : resolve()))
    ),
  mkdir: (path, options) => new Promise(resolve => mkdir(path, options, () => resolve())),
  unlink: path =>
    new Promise((resolve, reject) => unlink(path, err => (err ? reject(err) : resolve()))),
  readdir: (path, options) =>
    new Promise((resolve, reject) =>
      readdir(path, options, (err, files) => (err ? reject(err) : resolve(files)))
    ),
  stat: (path, options) =>
    new Promise((resolve, reject) =>
      stat(path, options, (err, stats) => (err ? reject(err) : resolve(stats)))
    ),
  access: () => Promise.resolve(),
};

export const constants = { F_OK: 0, R_OK: 4, W_OK: 2, X_OK: 1 };

export default {
  readFileSync,
  writeFileSync,
  existsSync,
  mkdirSync,
  unlinkSync,
  readdirSync,
  statSync,
  readFile,
  writeFile,
  exists,
  mkdir,
  unlink,
  readdir,
  stat,
  promises,
  constants,
};

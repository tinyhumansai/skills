/**
 * Node.js os module polyfill for V8 runtime.
 * Provides basic OS information using V8 platform bridge when available.
 */

// Check if V8 platform bridge is available
// Use globalThis to avoid name collision when esbuild renames the exported 'platform' function
const __bridgePlatform =
  typeof globalThis !== 'undefined' && typeof globalThis.platform === 'object' ? globalThis.platform : null;

export function platform() {
  if (__bridgePlatform && typeof __bridgePlatform.os === 'function') {
    const os = __bridgePlatform.os();
    switch (os) {
      case 'windows':
        return 'win32';
      case 'macos':
        return 'darwin';
      case 'linux':
        return 'linux';
      case 'android':
        return 'android';
      case 'ios':
        return 'ios';
      default:
        return os;
    }
  }
  return 'unknown';
}

export function arch() {
  // V8 runtime typically runs on the host architecture
  return 'x64';
}

export function type() {
  const p = platform();
  switch (p) {
    case 'win32':
      return 'Windows_NT';
    case 'darwin':
      return 'Darwin';
    case 'linux':
      return 'Linux';
    default:
      return 'Unknown';
  }
}

export function release() {
  return '0.0.0';
}

export function hostname() {
  return 'localhost';
}

export function homedir() {
  return '/';
}

export function tmpdir() {
  return '/tmp';
}

export function endianness() {
  const buf = new ArrayBuffer(2);
  new DataView(buf).setInt16(0, 256, true);
  return new Int16Array(buf)[0] === 256 ? 'LE' : 'BE';
}

export function cpus() {
  return [{ model: 'V8 Runtime', speed: 0 }];
}

export function totalmem() {
  return 0;
}

export function freemem() {
  return 0;
}

export function uptime() {
  return 0;
}

export function loadavg() {
  return [0, 0, 0];
}

export function networkInterfaces() {
  return {};
}

export function userInfo() {
  return { uid: -1, gid: -1, username: 'v8-runtime', homedir: '/', shell: null };
}

export function version() {
  return '';
}

export function machine() {
  return arch();
}

// Constants
export const EOL = '\n';
export const devNull = '/dev/null';

export const constants = {
  UV_UDP_REUSEADDR: 4,
  signals: {},
  errno: {},
  priority: {
    PRIORITY_LOW: 19,
    PRIORITY_BELOW_NORMAL: 10,
    PRIORITY_NORMAL: 0,
    PRIORITY_ABOVE_NORMAL: -7,
    PRIORITY_HIGH: -14,
    PRIORITY_HIGHEST: -20,
  },
};

export default {
  platform,
  arch,
  type,
  release,
  hostname,
  homedir,
  tmpdir,
  endianness,
  cpus,
  totalmem,
  freemem,
  uptime,
  loadavg,
  networkInterfaces,
  userInfo,
  version,
  machine,
  EOL,
  devNull,
  constants,
};

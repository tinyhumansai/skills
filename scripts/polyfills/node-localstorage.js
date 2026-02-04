/**
 * node-localstorage polyfill for V8 runtime.
 * gramjs uses this for session storage on Node.js.
 * We redirect to the V8 store bridge API.
 */

class LocalStorage {
  constructor(location) {
    this.location = location || 'default';
    this._prefix = `localstorage:${this.location}:`;
  }

  getItem(key) {
    if (typeof store !== 'undefined') {
      return store.get(this._prefix + key);
    }
    return null;
  }

  setItem(key, value) {
    if (typeof store !== 'undefined') {
      store.set(this._prefix + key, value);
    }
  }

  removeItem(key) {
    if (typeof store !== 'undefined') {
      store.delete(this._prefix + key);
    }
  }

  clear() {
    if (typeof store !== 'undefined') {
      const keys = store.keys();
      for (const key of keys) {
        if (key.startsWith(this._prefix)) {
          store.delete(key);
        }
      }
    }
  }

  key(index) {
    if (typeof store !== 'undefined') {
      const keys = store.keys().filter(k => k.startsWith(this._prefix));
      if (index < keys.length) {
        return keys[index].substring(this._prefix.length);
      }
    }
    return null;
  }

  get length() {
    if (typeof store !== 'undefined') {
      return store.keys().filter(k => k.startsWith(this._prefix)).length;
    }
    return 0;
  }
}

export { LocalStorage };
export default { LocalStorage };

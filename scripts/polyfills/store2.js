/**
 * store2 polyfill for V8 runtime.
 * Adapts the V8 store bridge API to the store2 interface used by gramjs.
 */

// Check if V8 store bridge is available
const hasStore = typeof store !== 'undefined';

/**
 * Create a namespaced storage area.
 */
function createArea(namespace) {
  const prefix = namespace ? `${namespace}:` : '';

  return {
    get(key, defaultValue) {
      if (!hasStore) {
        console.warn('[store2] V8 store bridge not available');
        return defaultValue;
      }
      const fullKey = prefix + key;
      const value = store.get(fullKey);
      return value !== null && value !== undefined ? value : defaultValue;
    },

    set(key, value) {
      if (!hasStore) {
        console.warn('[store2] V8 store bridge not available');
        return this;
      }
      const fullKey = prefix + key;
      store.set(fullKey, value);
      return this;
    },

    setAll(data) {
      if (!hasStore) return this;
      for (const [key, value] of Object.entries(data)) {
        this.set(key, value);
      }
      return this;
    },

    getAll() {
      if (!hasStore) return {};
      const result = {};
      const keys = store.keys();
      for (const key of keys) {
        if (key.startsWith(prefix)) {
          const localKey = key.slice(prefix.length);
          result[localKey] = store.get(key);
        }
      }
      return result;
    },

    remove(key) {
      if (!hasStore) return this;
      const fullKey = prefix + key;
      store.delete(fullKey);
      return this;
    },

    clear() {
      if (!hasStore) return this;
      const keys = store.keys();
      for (const key of keys) {
        if (key.startsWith(prefix)) {
          store.delete(key);
        }
      }
      return this;
    },

    has(key) {
      if (!hasStore) return false;
      const fullKey = prefix + key;
      return store.get(fullKey) !== null;
    },

    keys() {
      if (!hasStore) return [];
      const result = [];
      const allKeys = store.keys();
      for (const key of allKeys) {
        if (key.startsWith(prefix)) {
          result.push(key.slice(prefix.length));
        }
      }
      return result;
    },

    size() {
      return this.keys().length;
    },

    each(callback) {
      if (!hasStore) return this;
      const keys = this.keys();
      for (const key of keys) {
        const value = this.get(key);
        if (callback(key, value) === false) {
          break;
        }
      }
      return this;
    },

    // Create a sub-namespace
    namespace(ns) {
      return createArea(prefix + ns);
    },

    // Alias
    area(ns) {
      return this.namespace(ns);
    },
  };
}

// Main store2 interface
const store2 = {
  ...createArea(''),

  // Create a namespaced area
  area(namespace) {
    return createArea(namespace);
  },

  namespace(namespace) {
    return createArea(namespace);
  },

  // Local and session storage aliases (all map to the same V8 store)
  local: createArea('local'),
  session: createArea('session'),

  // Check if storage is available
  isFake() {
    return !hasStore;
  },

  // Version info
  _version: '2.14.2',
};

export default store2;
export { store2 };

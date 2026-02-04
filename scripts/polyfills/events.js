/**
 * EventEmitter polyfill for V8 runtime.
 * Provides a Node.js-compatible EventEmitter implementation.
 */

export class EventEmitter {
  constructor() {
    this._events = new Map();
    this._maxListeners = 10;
  }

  get defaultMaxListeners() {
    return EventEmitter.defaultMaxListeners;
  }

  set defaultMaxListeners(n) {
    EventEmitter.defaultMaxListeners = n;
  }

  setMaxListeners(n) {
    this._maxListeners = n;
    return this;
  }

  getMaxListeners() {
    return this._maxListeners !== undefined ? this._maxListeners : EventEmitter.defaultMaxListeners;
  }

  emit(type, ...args) {
    const listeners = this._events.get(type);
    if (!listeners || listeners.length === 0) {
      if (type === 'error') {
        const err = args[0];
        if (err instanceof Error) {
          throw err;
        }
        throw new Error('Uncaught, unspecified "error" event.');
      }
      return false;
    }

    // Copy to avoid mutation during iteration
    const handlers = [...listeners];
    for (const handler of handlers) {
      try {
        if (handler.once) {
          this.removeListener(type, handler.listener || handler);
        }
        const fn = handler.listener || handler;
        fn.apply(this, args);
      } catch (e) {
        console.error('Error in event handler:', e);
      }
    }
    return true;
  }

  on(type, listener) {
    return this.addListener(type, listener);
  }

  addListener(type, listener) {
    if (typeof listener !== 'function') {
      throw new TypeError('The "listener" argument must be of type Function');
    }

    let listeners = this._events.get(type);
    if (!listeners) {
      listeners = [];
      this._events.set(type, listeners);
    }

    listeners.push(listener);

    // Check for listener leak
    const max = this.getMaxListeners();
    if (max > 0 && listeners.length > max) {
      console.warn(
        `MaxListenersExceededWarning: Possible EventEmitter memory leak detected. ` +
          `${listeners.length} ${type} listeners added. ` +
          `Use emitter.setMaxListeners() to increase limit`
      );
    }

    this.emit('newListener', type, listener);
    return this;
  }

  once(type, listener) {
    if (typeof listener !== 'function') {
      throw new TypeError('The "listener" argument must be of type Function');
    }

    const wrapper = { listener, once: true };

    let listeners = this._events.get(type);
    if (!listeners) {
      listeners = [];
      this._events.set(type, listeners);
    }

    listeners.push(wrapper);
    return this;
  }

  off(type, listener) {
    return this.removeListener(type, listener);
  }

  removeListener(type, listener) {
    const listeners = this._events.get(type);
    if (!listeners) {
      return this;
    }

    const index = listeners.findIndex(
      l => l === listener || (l.listener && l.listener === listener)
    );

    if (index !== -1) {
      listeners.splice(index, 1);
      this.emit('removeListener', type, listener);
    }

    if (listeners.length === 0) {
      this._events.delete(type);
    }

    return this;
  }

  removeAllListeners(type) {
    if (type !== undefined) {
      const listeners = this._events.get(type);
      if (listeners) {
        for (const listener of listeners) {
          this.emit('removeListener', type, listener.listener || listener);
        }
        this._events.delete(type);
      }
    } else {
      for (const [eventType, listeners] of this._events) {
        if (eventType === 'removeListener') continue;
        for (const listener of listeners) {
          this.emit('removeListener', eventType, listener.listener || listener);
        }
      }
      this._events.clear();
    }
    return this;
  }

  listeners(type) {
    const listeners = this._events.get(type);
    if (!listeners) {
      return [];
    }
    return listeners.map(l => l.listener || l);
  }

  rawListeners(type) {
    const listeners = this._events.get(type);
    if (!listeners) {
      return [];
    }
    return [...listeners];
  }

  listenerCount(type) {
    const listeners = this._events.get(type);
    return listeners ? listeners.length : 0;
  }

  prependListener(type, listener) {
    if (typeof listener !== 'function') {
      throw new TypeError('The "listener" argument must be of type Function');
    }

    let listeners = this._events.get(type);
    if (!listeners) {
      listeners = [];
      this._events.set(type, listeners);
    }

    listeners.unshift(listener);
    this.emit('newListener', type, listener);
    return this;
  }

  prependOnceListener(type, listener) {
    if (typeof listener !== 'function') {
      throw new TypeError('The "listener" argument must be of type Function');
    }

    const wrapper = { listener, once: true };

    let listeners = this._events.get(type);
    if (!listeners) {
      listeners = [];
      this._events.set(type, listeners);
    }

    listeners.unshift(wrapper);
    return this;
  }

  eventNames() {
    return [...this._events.keys()];
  }
}

EventEmitter.defaultMaxListeners = 10;

// Static method
EventEmitter.listenerCount = function (emitter, type) {
  return emitter.listenerCount(type);
};

// Alias
EventEmitter.EventEmitter = EventEmitter;

export default EventEmitter;

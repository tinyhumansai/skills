/**
 * Async Mutex polyfill for V8 runtime.
 * Provides Mutex and Semaphore implementations for async synchronization.
 */

/**
 * A simple Mutex implementation for async operations.
 */
export class Mutex {
  constructor() {
    this._queue = [];
    this._locked = false;
  }

  isLocked() {
    return this._locked;
  }

  async acquire() {
    return new Promise(resolve => {
      const tryAcquire = () => {
        if (!this._locked) {
          this._locked = true;
          resolve(this._createReleaser());
        } else {
          this._queue.push(tryAcquire);
        }
      };
      tryAcquire();
    });
  }

  _createReleaser() {
    let released = false;
    return () => {
      if (released) return;
      released = true;
      this._locked = false;
      const next = this._queue.shift();
      if (next) {
        next();
      }
    };
  }

  async runExclusive(callback) {
    const release = await this.acquire();
    try {
      return await callback();
    } finally {
      release();
    }
  }

  cancel() {
    this._queue = [];
  }

  waitForUnlock() {
    return new Promise(resolve => {
      if (!this._locked) {
        resolve();
      } else {
        const check = () => {
          if (!this._locked) {
            resolve();
          } else {
            this._queue.push(check);
          }
        };
        this._queue.push(check);
      }
    });
  }
}

/**
 * A Semaphore implementation for limiting concurrent access.
 */
export class Semaphore {
  constructor(maxConcurrency) {
    if (maxConcurrency < 1) {
      throw new Error('Semaphore maxConcurrency must be at least 1');
    }
    this._maxConcurrency = maxConcurrency;
    this._currentCount = 0;
    this._queue = [];
  }

  isLocked() {
    return this._currentCount >= this._maxConcurrency;
  }

  async acquire(weight = 1) {
    if (weight > this._maxConcurrency) {
      throw new Error(`Weight ${weight} exceeds max concurrency ${this._maxConcurrency}`);
    }

    return new Promise(resolve => {
      const tryAcquire = () => {
        if (this._currentCount + weight <= this._maxConcurrency) {
          this._currentCount += weight;
          resolve([weight, this._createReleaser(weight)]);
        } else {
          this._queue.push({ weight, callback: tryAcquire });
        }
      };
      tryAcquire();
    });
  }

  _createReleaser(weight) {
    let released = false;
    return () => {
      if (released) return;
      released = true;
      this._currentCount -= weight;
      this._processQueue();
    };
  }

  _processQueue() {
    while (this._queue.length > 0) {
      const next = this._queue[0];
      if (this._currentCount + next.weight <= this._maxConcurrency) {
        this._queue.shift();
        next.callback();
      } else {
        break;
      }
    }
  }

  async runExclusive(callback, weight = 1) {
    const [, release] = await this.acquire(weight);
    try {
      return await callback();
    } finally {
      release();
    }
  }

  cancel() {
    this._queue = [];
  }

  getValue() {
    return this._maxConcurrency - this._currentCount;
  }

  setValue(value) {
    this._maxConcurrency = value + this._currentCount;
    this._processQueue();
  }

  release(weight = 1) {
    if (this._currentCount - weight < 0) {
      throw new Error('Cannot release more than acquired');
    }
    this._currentCount -= weight;
    this._processQueue();
  }
}

/**
 * A simple lock that can be used with `with` statement in JavaScript.
 */
export function withTimeout(mutex, timeout, timeoutError) {
  return {
    async acquire() {
      return new Promise((resolve, reject) => {
        const timeoutId = setTimeout(() => {
          reject(timeoutError || new Error('Mutex acquire timeout'));
        }, timeout);

        mutex.acquire().then(release => {
          clearTimeout(timeoutId);
          resolve(release);
        });
      });
    },
    async runExclusive(callback) {
      const release = await this.acquire();
      try {
        return await callback();
      } finally {
        release();
      }
    },
  };
}

/**
 * Try to acquire mutex immediately without waiting.
 */
export function tryAcquire(mutex) {
  if (mutex.isLocked()) {
    throw new Error('Mutex is already locked');
  }
  return mutex.acquire();
}

export default { Mutex, Semaphore, withTimeout, tryAcquire };

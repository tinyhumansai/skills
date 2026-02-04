/**
 * Node.js stream module stub for V8 runtime.
 * Provides minimal stream implementations for compatibility.
 */
import { EventEmitter } from './events.js';

export class Stream extends EventEmitter {
  pipe(destination) {
    this.on('data', chunk => {
      destination.write(chunk);
    });
    this.on('end', () => {
      destination.end();
    });
    this.on('error', err => {
      destination.emit('error', err);
    });
    return destination;
  }
}

export class Readable extends Stream {
  constructor(options = {}) {
    super();
    this.readable = true;
    this._readableState = {
      objectMode: options.objectMode || false,
      highWaterMark: options.highWaterMark || 16384,
      buffer: [],
      ended: false,
      flowing: null,
    };
  }

  read(size) {
    return null;
  }

  push(chunk) {
    if (chunk === null) {
      this._readableState.ended = true;
      this.emit('end');
      return false;
    }
    this._readableState.buffer.push(chunk);
    this.emit('data', chunk);
    return true;
  }

  unshift(chunk) {
    this._readableState.buffer.unshift(chunk);
  }

  setEncoding(encoding) {
    this._encoding = encoding;
    return this;
  }

  pause() {
    this._readableState.flowing = false;
    return this;
  }

  resume() {
    this._readableState.flowing = true;
    return this;
  }

  isPaused() {
    return this._readableState.flowing === false;
  }

  destroy(err) {
    if (err) this.emit('error', err);
    this.emit('close');
    return this;
  }
}

export class Writable extends Stream {
  constructor(options = {}) {
    super();
    this.writable = true;
    this._writableState = {
      objectMode: options.objectMode || false,
      highWaterMark: options.highWaterMark || 16384,
      ended: false,
      finished: false,
    };
  }

  write(chunk, encoding, callback) {
    if (typeof encoding === 'function') {
      callback = encoding;
      encoding = undefined;
    }
    this._write(chunk, encoding, callback || (() => {}));
    return true;
  }

  _write(chunk, encoding, callback) {
    callback();
  }

  end(chunk, encoding, callback) {
    if (typeof chunk === 'function') {
      callback = chunk;
      chunk = undefined;
    } else if (typeof encoding === 'function') {
      callback = encoding;
      encoding = undefined;
    }

    if (chunk !== undefined) {
      this.write(chunk, encoding);
    }

    this._writableState.ended = true;
    this._writableState.finished = true;
    this.emit('finish');
    if (callback) callback();
    return this;
  }

  destroy(err) {
    if (err) this.emit('error', err);
    this.emit('close');
    return this;
  }

  setDefaultEncoding(encoding) {
    this._defaultEncoding = encoding;
    return this;
  }

  cork() {}
  uncork() {}
}

export class Duplex extends Readable {
  constructor(options = {}) {
    super(options);
    Writable.call(this, options);
    this.writable = true;
  }
}

// Mix in Writable methods
Object.assign(Duplex.prototype, {
  write: Writable.prototype.write,
  _write: Writable.prototype._write,
  end: Writable.prototype.end,
  cork: Writable.prototype.cork,
  uncork: Writable.prototype.uncork,
  setDefaultEncoding: Writable.prototype.setDefaultEncoding,
});

export class Transform extends Duplex {
  constructor(options = {}) {
    super(options);
  }

  _transform(chunk, encoding, callback) {
    callback(null, chunk);
  }

  _flush(callback) {
    callback();
  }
}

export class PassThrough extends Transform {
  constructor(options) {
    super(options);
  }

  _transform(chunk, encoding, callback) {
    callback(null, chunk);
  }
}

export function pipeline(...streams) {
  const callback = typeof streams[streams.length - 1] === 'function' ? streams.pop() : () => {};

  let source = streams[0];
  for (let i = 1; i < streams.length; i++) {
    source = source.pipe(streams[i]);
  }

  source.on('finish', () => callback());
  source.on('error', callback);

  return source;
}

export function finished(stream, options, callback) {
  if (typeof options === 'function') {
    callback = options;
    options = {};
  }

  const onFinish = () => callback();
  const onError = err => callback(err);

  stream.on('finish', onFinish);
  stream.on('end', onFinish);
  stream.on('error', onError);
  stream.on('close', onFinish);

  return () => {
    stream.off('finish', onFinish);
    stream.off('end', onFinish);
    stream.off('error', onError);
    stream.off('close', onFinish);
  };
}

export default { Stream, Readable, Writable, Duplex, Transform, PassThrough, pipeline, finished };

/**
 * ts-custom-error polyfill.
 * Provides a CustomError base class that properly extends Error.
 */

export class CustomError extends Error {
  constructor(message) {
    super(message);
    this.name = this.constructor.name;

    // Maintains proper stack trace for where our error was thrown (only available on V8)
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, this.constructor);
    }
  }
}

export default CustomError;

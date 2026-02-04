/**
 * big-integer polyfill using native BigInt.
 * Returns wrapper objects with methods like .pow(), .mod(), .add(), etc.
 * that gramjs expects from the big-integer library.
 */

class BigInteger {
  constructor(value) {
    if (value instanceof BigInteger) {
      this.value = value.value;
    } else if (typeof value === 'bigint') {
      this.value = value;
    } else if (typeof value === 'number') {
      this.value = BigInt(Math.floor(value));
    } else if (typeof value === 'string') {
      // Handle hex strings
      if (value.startsWith('0x') || value.startsWith('0X')) {
        this.value = BigInt(value);
      } else {
        this.value = BigInt(value);
      }
    } else if (value instanceof Uint8Array || Array.isArray(value)) {
      let result = 0n;
      for (let i = 0; i < value.length; i++) {
        result = (result << 8n) | BigInt(value[i]);
      }
      this.value = result;
    } else if (value === undefined || value === null) {
      this.value = 0n;
    } else {
      this.value = BigInt(value);
    }
  }

  // Arithmetic operations
  add(n) {
    return new BigInteger(this.value + bigInt(n).value);
  }

  subtract(n) {
    return new BigInteger(this.value - bigInt(n).value);
  }

  minus(n) {
    return this.subtract(n);
  }

  multiply(n) {
    return new BigInteger(this.value * bigInt(n).value);
  }

  times(n) {
    return this.multiply(n);
  }

  divide(n) {
    return new BigInteger(this.value / bigInt(n).value);
  }

  over(n) {
    return this.divide(n);
  }

  mod(n) {
    const divisor = bigInt(n).value;
    let result = this.value % divisor;
    // Ensure positive result like big-integer library
    if (result < 0n) result += divisor < 0n ? -divisor : divisor;
    return new BigInteger(result);
  }

  remainder(n) {
    return new BigInteger(this.value % bigInt(n).value);
  }

  pow(n) {
    const exp = bigInt(n).value;
    if (exp < 0n) {
      throw new Error('Negative exponents are not supported');
    }
    return new BigInteger(this.value ** exp);
  }

  modPow(exp, mod) {
    const e = bigInt(exp).value;
    const m = bigInt(mod).value;
    if (e < 0n) throw new Error('Negative exponent');
    if (m === 0n) throw new Error('Division by zero');

    let result = 1n;
    let base = this.value % m;
    let exponent = e;

    while (exponent > 0n) {
      if (exponent % 2n === 1n) {
        result = (result * base) % m;
      }
      exponent = exponent / 2n;
      base = (base * base) % m;
    }

    return new BigInteger(result);
  }

  modInv(mod) {
    const m = bigInt(mod).value;
    let a = this.value % m;
    if (a < 0n) a += m;

    let [old_r, r] = [a, m];
    let [old_s, s] = [1n, 0n];

    while (r !== 0n) {
      const q = old_r / r;
      [old_r, r] = [r, old_r - q * r];
      [old_s, s] = [s, old_s - q * s];
    }

    if (old_r !== 1n) {
      throw new Error('Modular inverse does not exist');
    }

    return new BigInteger(old_s < 0n ? old_s + m : old_s);
  }

  // Comparison operations
  compare(n) {
    const other = bigInt(n).value;
    if (this.value < other) return -1;
    if (this.value > other) return 1;
    return 0;
  }

  compareTo(n) {
    return this.compare(n);
  }

  equals(n) {
    return this.value === bigInt(n).value;
  }

  eq(n) {
    return this.equals(n);
  }

  notEquals(n) {
    return !this.equals(n);
  }

  neq(n) {
    return this.notEquals(n);
  }

  greater(n) {
    return this.value > bigInt(n).value;
  }

  gt(n) {
    return this.greater(n);
  }

  greaterOrEquals(n) {
    return this.value >= bigInt(n).value;
  }

  geq(n) {
    return this.greaterOrEquals(n);
  }

  lesser(n) {
    return this.value < bigInt(n).value;
  }

  lt(n) {
    return this.lesser(n);
  }

  lesserOrEquals(n) {
    return this.value <= bigInt(n).value;
  }

  leq(n) {
    return this.lesserOrEquals(n);
  }

  // Bitwise operations
  and(n) {
    return new BigInteger(this.value & bigInt(n).value);
  }

  or(n) {
    return new BigInteger(this.value | bigInt(n).value);
  }

  xor(n) {
    return new BigInteger(this.value ^ bigInt(n).value);
  }

  not() {
    return new BigInteger(~this.value);
  }

  shiftLeft(n) {
    return new BigInteger(this.value << BigInt(n));
  }

  shiftRight(n) {
    return new BigInteger(this.value >> BigInt(n));
  }

  // Unary operations
  abs() {
    return new BigInteger(this.value < 0n ? -this.value : this.value);
  }

  negate() {
    return new BigInteger(-this.value);
  }

  // Utility methods
  isPositive() {
    return this.value > 0n;
  }

  isNegative() {
    return this.value < 0n;
  }

  isZero() {
    return this.value === 0n;
  }

  isOdd() {
    return (this.value & 1n) === 1n;
  }

  isEven() {
    return (this.value & 1n) === 0n;
  }

  isUnit() {
    return this.value === 1n || this.value === -1n;
  }

  isDivisibleBy(n) {
    return this.value % bigInt(n).value === 0n;
  }

  // Conversion methods
  toString(radix = 10) {
    return this.value.toString(radix);
  }

  toJSON() {
    return this.toString();
  }

  valueOf() {
    return this.value;
  }

  toJSNumber() {
    return Number(this.value);
  }

  toArray(base = 10) {
    const str = this.abs().toString(base);
    const digits = str.split('').map((c) => parseInt(c, base));
    return {
      value: digits,
      isNegative: this.isNegative(),
    };
  }

  bitLength() {
    let v = this.value < 0n ? -this.value : this.value;
    let bits = 0;
    while (v > 0n) {
      bits++;
      v >>= 1n;
    }
    return bits;
  }
}

// Main factory function
function bigInt(value, radix) {
  if (value instanceof BigInteger) return value;
  if (radix !== undefined && typeof value === 'string') {
    return new BigInteger(BigInt(parseInt(value, radix)));
  }
  return new BigInteger(value);
}

// Static properties
bigInt.zero = new BigInteger(0n);
bigInt.one = new BigInteger(1n);
bigInt.minusOne = new BigInteger(-1n);

// Static methods
bigInt.fromArray = function (digits, base = 10, isNegative = false) {
  let result = 0n;
  const bigBase = BigInt(base);
  for (const digit of digits) {
    result = result * bigBase + BigInt(digit);
  }
  return new BigInteger(isNegative ? -result : result);
};

bigInt.gcd = function (a, b) {
  a = bigInt(a).value;
  b = bigInt(b).value;
  if (a < 0n) a = -a;
  if (b < 0n) b = -b;
  while (b !== 0n) {
    [a, b] = [b, a % b];
  }
  return new BigInteger(a);
};

bigInt.lcm = function (a, b) {
  a = bigInt(a);
  b = bigInt(b);
  return a.multiply(b).divide(bigInt.gcd(a, b));
};

bigInt.isInstance = function (x) {
  return x instanceof BigInteger;
};

bigInt.max = function (...args) {
  const values = args.map((a) => bigInt(a));
  return values.reduce((a, b) => (a.value > b.value ? a : b));
};

bigInt.min = function (...args) {
  const values = args.map((a) => bigInt(a));
  return values.reduce((a, b) => (a.value < b.value ? a : b));
};

bigInt.randBetween = function (min, max) {
  min = bigInt(min);
  max = bigInt(max);
  const range = max.subtract(min).value;
  const bits = range.toString(2).length;
  const bytes = Math.ceil(bits / 8);
  const arr = new Uint8Array(bytes);
  crypto.getRandomValues(arr);
  let result = 0n;
  for (const byte of arr) {
    result = (result << 8n) | BigInt(byte);
  }
  return new BigInteger(min.value + (result % (range + 1n)));
};

export default bigInt;
export { bigInt, BigInteger };

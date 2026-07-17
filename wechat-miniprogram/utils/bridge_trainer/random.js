"use strict";

/**
 * Python 3 random.Random (MT19937) compatible RNG for WeChat miniprogram.
 * Int seeding uses CPython's init_by_array path (not plain init_genrand).
 */

var N = 624;
var M = 397;
var MATRIX_A = 0x9908b0df;
var UPPER_MASK = 0x80000000;
var LOWER_MASK = 0x7fffffff;

function PythonRandom(seed) {
  this.mt = new Array(N);
  this.mti = N + 1;
  if (seed === undefined || seed === null) {
    this.seed(Date.now());
  } else {
    this.seed(seed);
  }
}

PythonRandom.prototype._initGenrand = function (s) {
  this.mt[0] = s >>> 0;
  for (var i = 1; i < N; i += 1) {
    var prev = this.mt[i - 1] >>> 0;
    this.mt[i] = (Math.imul(1812433253, prev ^ (prev >>> 30)) + i) >>> 0;
  }
  this.mti = N;
};

PythonRandom.prototype._initByArray = function (key) {
  this._initGenrand(19650218);
  var i = 1;
  var j = 0;
  var k = N > key.length ? N : key.length;
  for (; k > 0; k -= 1) {
    var prev = this.mt[i - 1] >>> 0;
    this.mt[i] =
      ((this.mt[i] ^ Math.imul(prev ^ (prev >>> 30), 1664525)) + key[j] + j) >>> 0;
    i += 1;
    j += 1;
    if (i >= N) {
      this.mt[0] = this.mt[N - 1];
      i = 1;
    }
    if (j >= key.length) {
      j = 0;
    }
  }
  for (k = N - 1; k > 0; k -= 1) {
    prev = this.mt[i - 1] >>> 0;
    this.mt[i] =
      ((this.mt[i] ^ Math.imul(prev ^ (prev >>> 30), 1566083941)) - i) >>> 0;
    i += 1;
    if (i >= N) {
      this.mt[0] = this.mt[N - 1];
      i = 1;
    }
  }
  this.mt[0] = 0x80000000;
  this.mti = N;
};

PythonRandom.prototype.seed = function (seed) {
  var n = Number(seed);
  if (!isFinite(n)) {
    n = 0;
  }
  n = n < 0 ? Math.ceil(n) : Math.floor(n);
  if (n < 0) {
    n = -n;
  }
  var key = [];
  if (n === 0) {
    key.push(0);
  } else {
    while (n > 0) {
      key.push(n >>> 0);
      n = Math.floor(n / 0x100000000);
    }
  }
  this._initByArray(key);
};

PythonRandom.prototype._genrandInt32 = function () {
  var y;
  var mag01 = [0, MATRIX_A];

  if (this.mti >= N) {
    var kk;
    for (kk = 0; kk < N - M; kk += 1) {
      y = (this.mt[kk] & UPPER_MASK) | (this.mt[kk + 1] & LOWER_MASK);
      this.mt[kk] = (this.mt[kk + M] ^ (y >>> 1) ^ mag01[y & 0x1]) >>> 0;
    }
    for (; kk < N - 1; kk += 1) {
      y = (this.mt[kk] & UPPER_MASK) | (this.mt[kk + 1] & LOWER_MASK);
      this.mt[kk] = (this.mt[kk + (M - N)] ^ (y >>> 1) ^ mag01[y & 0x1]) >>> 0;
    }
    y = (this.mt[N - 1] & UPPER_MASK) | (this.mt[0] & LOWER_MASK);
    this.mt[N - 1] = (this.mt[M - 1] ^ (y >>> 1) ^ mag01[y & 0x1]) >>> 0;
    this.mti = 0;
  }

  y = this.mt[this.mti];
  this.mti += 1;

  y ^= y >>> 11;
  y ^= (y << 7) & 0x9d2c5680;
  y ^= (y << 15) & 0xefc60000;
  y ^= y >>> 18;
  return y >>> 0;
};

PythonRandom.prototype.random = function () {
  var a = this._genrandInt32() >>> 5;
  var b = this._genrandInt32() >>> 6;
  return (a * 67108864.0 + b) * (1.0 / 9007199254740992.0);
};

PythonRandom.prototype.getrandbits = function (k) {
  if (k <= 0) {
    return 0;
  }
  if (k <= 32) {
    return this._genrandInt32() >>> (32 - k);
  }
  var result = 0;
  var remaining = k;
  while (remaining > 0) {
    var chunk = Math.min(32, remaining);
    result = result * Math.pow(2, chunk) + this.getrandbits(chunk);
    remaining -= chunk;
  }
  return result;
};

PythonRandom.prototype.randrange = function (stop) {
  var n = Math.floor(Number(stop));
  if (!(n > 0)) {
    throw new Error("empty range for randrange(" + stop + ")");
  }
  var bits = n.toString(2).length;
  while (true) {
    var r = this.getrandbits(bits);
    if (r < n) {
      return r;
    }
  }
};

PythonRandom.prototype.shuffle = function (array) {
  for (var i = array.length - 1; i > 0; i -= 1) {
    var j = this.randrange(i + 1);
    var tmp = array[i];
    array[i] = array[j];
    array[j] = tmp;
  }
  return array;
};

PythonRandom.prototype.choice = function (array) {
  if (!array || array.length === 0) {
    throw new Error("Cannot choose from empty sequence");
  }
  return array[this.randrange(array.length)];
};

module.exports = {
  PythonRandom: PythonRandom,
};

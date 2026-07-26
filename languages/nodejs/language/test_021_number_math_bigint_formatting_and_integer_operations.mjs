// polyglot-covers:
// - nodejs.language.number-parsing-and-validation
// - nodejs.language.number-formatting-methods
// - nodejs.language.math-rounding-and-signed-zero
// - nodejs.language.math-precision-and-integer-operations
// - nodejs.language.math-aggregation-and-special-values
// - nodejs.language.bigint-conversion-and-width-clamping

import assert from 'node:assert/strict';
import test from 'node:test';

test('Number 转换整个输入，parseInt/parseFloat 接受有效前缀', () => {
  assert.equal(Number('0b101'), 5);
  assert.equal(Number('0x10'), 16);
  assert.equal(Number('  '), 0);
  assert.ok(Number.isNaN(Number('12px')));

  assert.equal(Number.parseInt('12px', 10), 12);
  assert.equal(Number.parseFloat('12.5px'), 12.5);
  assert.equal(Number.parseInt('0xff', 16), 255);
  assert.equal(Number.parseInt('11', 2), 3);

  // radix 应显式传入；parseInt 不是取整工具，数值取整使用 Math.trunc。
  assert.equal(Number.parseInt('08', 10), 8);
  assert.equal(Math.trunc(12.9), 12);
});

test('Number 静态判定不做隐式数值转换', () => {
  assert.equal(Number.isNaN(Number.NaN), true);
  assert.equal(Number.isNaN('not a number'), false);
  assert.equal(Number.isFinite(42), true);
  assert.equal(Number.isFinite('42'), false);
  assert.equal(Number.isInteger(42), true);
  assert.equal(Number.isInteger(42.1), false);
  assert.equal(Number.isSafeInteger(2 ** 53 - 1), true);
  assert.equal(Number.isSafeInteger(2 ** 53), false);

  // 旧式全局 isNaN/isFinite 会先转换参数，容易把空字符串等值判成有限数字。
  assert.equal(globalThis.isNaN('not a number'), true);
  assert.equal(globalThis.isFinite(''), true);
});

test('toString 支持进制，定点和有效数字格式会执行舍入', () => {
  assert.equal((255).toString(16), 'ff');
  assert.equal((10).toString(2), '1010');
  assert.equal((1234.5).toExponential(2), '1.23e+3');
  assert.equal((12.345).toPrecision(4), '12.35');
  assert.equal((12.345).toFixed(2), '12.35');

  // 十进制小数先以二进制近似存储，所以 toFixed 不是精确十进制金额算法。
  assert.equal((2.55).toFixed(1), '2.5');
  assert.equal((2.35).toFixed(1), '2.4');
  assert.throws(() => (1).toString(1), RangeError);
});

test('floor、ceil、trunc 和 round 对负数采用不同方向', () => {
  assert.equal(Math.floor(1.9), 1);
  assert.equal(Math.ceil(1.1), 2);
  assert.equal(Math.trunc(1.9), 1);

  assert.equal(Math.floor(-1.1), -2);
  assert.equal(Math.ceil(-1.9), -1);
  assert.equal(Math.trunc(-1.9), -1);

  // Math.round 的半值朝 +Infinity，而不是远离零；-0.5 因此产生可观察的负零。
  assert.equal(Math.round(1.5), 2);
  assert.equal(Math.round(-1.5), -1);
  assert.equal(Object.is(Math.round(-0.5), -0), true);
});

test('sign、abs、min/max 保留 IEEE 754 的特殊值规则', () => {
  assert.equal(Math.abs(-7), 7);
  assert.equal(Math.sign(7), 1);
  assert.equal(Math.sign(-7), -1);
  assert.equal(Object.is(Math.sign(-0), -0), true);
  assert.equal(Math.min(), Infinity);
  assert.equal(Math.max(), -Infinity);
  assert.ok(Number.isNaN(Math.max(1, Number.NaN, 3)));

  const values = [3, 1, 8, 2];
  assert.equal(Math.max(...values), 8);
  // 对极大数组展开参数可能超过调用参数上限，生产代码可用 reduce 或循环聚合。
});

test('hypot 降低平方和溢出风险，clz32/imul 明确使用 32 位语义', () => {
  assert.equal(Math.hypot(3, 4), 5);
  assert.equal(Number.isFinite(Math.hypot(3e200, 4e200)), true);
  assert.equal(Math.clz32(1), 31);
  assert.equal(Math.clz32(0), 32);
  assert.equal(Math.imul(0xffff_ffff, 5), -5);

  // 普通乘法保持 Number；Math.imul 返回 C 风格低 32 位有符号结果。
  assert.equal(0xffff_ffff * 5, 21_474_836_475);
});

test('fround 暴露 Float32 舍入，EPSILON 只代表 1 附近的间距', () => {
  assert.equal(Math.fround(1.5), 1.5);
  assert.notEqual(Math.fround(1.337), 1.337);
  assert.equal(Math.fround(1.337), 1.3370000123977661);

  assert.equal(1 + Number.EPSILON > 1, true);
  assert.equal(1e16 + Number.EPSILON, 1e16);

  const approximatelyEqual = (left, right, tolerance) => (
    Math.abs(left - right) <= tolerance * Math.max(1, Math.abs(left), Math.abs(right))
  );
  assert.equal(approximatelyEqual(1e12 + 0.1, 1e12, 1e-12), true);
});

test('BigInt 从整数或整数字符串转换，不接受小数和隐式混合', () => {
  assert.equal(BigInt(42), 42n);
  assert.equal(BigInt('0xff'), 255n);
  assert.equal(BigInt(true), 1n);
  assert.throws(() => BigInt(1.5), RangeError);
  assert.throws(() => BigInt('1.5'), SyntaxError);
  assert.throws(() => Number(1n) + 1n, TypeError);

  assert.equal(Number(9007199254740993n), 9007199254740992);
  // BigInt 转 Number 是显式允许但可能丢精度的窄化操作。
});

test('asIntN/asUintN 按给定位宽执行二补码截断', () => {
  assert.equal(BigInt.asUintN(8, -1n), 255n);
  assert.equal(BigInt.asIntN(8, 255n), -1n);
  assert.equal(BigInt.asUintN(8, 256n), 0n);
  assert.equal(BigInt.asIntN(8, 128n), -128n);

  const wide = 0x1234n;
  assert.equal(BigInt.asUintN(8, wide), 0x34n);
});

// polyglot-covers:
// - nodejs.language.primitive-values-and-typeof
// - nodejs.language.wrapper-objects-and-boxing
// - nodejs.language.number-ieee-754-and-safe-integers
// - nodejs.language.bigint
// - nodejs.language.boolean-conversion
// - nodejs.language.explicit-primitive-conversion
// - nodejs.language.strict-loose-and-same-value-equality
// - nodejs.language.relational-comparison
// - nodejs.language.nullish-values
// - nodejs.language.symbols-and-symbol-registry

// 跨语言迁移提示：ToBoolean 不调用对象协议，空数组和空对象仍为真；这不同于 Python
// 的空容器规则。JavaScript 还要区分 ===、Object.is 与会强制转换的 ==，不能套用 C++ 比较模型。

import assert from 'node:assert/strict';
import test from 'node:test';

test('原始值类型与 typeof 的历史例外', () => {
  const values = [
    undefined,
    null,
    true,
    42,
    42n,
    'text',
    Symbol('token'),
  ];

  assert.deepEqual(
    values.map((value) => typeof value),
    ['undefined', 'object', 'boolean', 'number', 'bigint', 'string', 'symbol'],
  );

  // null 是原始值，但 typeof null 因早期兼容性固定返回 "object"。判断 null 应使用
  // 严格相等，而不是 typeof。函数属于可调用对象，却有专门的 "function" 结果。
  assert.equal(values[1], null);
  assert.equal(typeof (() => undefined), 'function');
  assert.equal(typeof {}, 'object');
});

test('原始值自动装箱不等于持久的包装对象', () => {
  const text = 'polyglot';
  const wrappedText = new String(text);

  // 读取原始字符串的方法时会发生临时装箱，所以可以调用原型方法；原始值本身没有被
  // 替换成对象。显式 new String 则会制造真对象，通常只会让类型与相等判断更复杂。
  assert.equal(text.toUpperCase(), 'POLYGLOT');
  assert.equal(typeof text, 'string');
  assert.equal(typeof wrappedText, 'object');
  assert.notEqual(wrappedText, text);
  assert.equal(wrappedText.valueOf(), text);

  const boxedNumber = Object(7);
  assert.equal(boxedNumber.valueOf(), 7);
  assert.equal(boxedNumber + 1, 8);
});

test('Number 使用 IEEE 754 并只精确表示安全整数范围', () => {
  assert.equal(0.1 + 0.2, 0.30000000000000004);
  assert.ok(Math.abs(0.1 + 0.2 - 0.3) < Number.EPSILON);

  assert.ok(Number.isSafeInteger(Number.MAX_SAFE_INTEGER));
  assert.equal(Number.isSafeInteger(Number.MAX_SAFE_INTEGER + 1), false);

  // 超过安全范围后，相邻数学整数可能映射到同一个二进制浮点值。把超大十进制整数先写成
  // Number 再转 BigInt 已经太晚；需要从 BigInt 字面量或十进制字符串开始。
  assert.equal(Number.MAX_SAFE_INTEGER + 1, Number.MAX_SAFE_INTEGER + 2);
  assert.equal(BigInt('9007199254740993'), 9007199254740993n);

  assert.equal(1 / 0, Infinity);
  assert.equal(Number.isFinite(Infinity), false);
  assert.equal(Number.isFinite('42'), false);
  assert.equal(Number.isNaN(Number.NaN), true);
  assert.equal(Number.NaN === Number.NaN, false);
});

test('负零与 NaN 展示不同的相等算法', () => {
  assert.equal(0 === -0, true);
  assert.equal(Object.is(0, -0), false);
  assert.equal(Object.is(Number.NaN, Number.NaN), true);

  // Map、Set 和 Array.prototype.includes 使用 SameValueZero：它把 NaN 视为自身相等，
  // 同时把 +0 与 -0 视为相等。indexOf 使用严格相等，因而找不到 NaN。
  assert.equal([Number.NaN].includes(Number.NaN), true);
  assert.equal([Number.NaN].indexOf(Number.NaN), -1);
  assert.equal(new Set([0, -0]).size, 1);
  assert.equal(new Map([[Number.NaN, 'value']]).get(Number.NaN), 'value');
});

test('BigInt 保留任意精度整数，但不能与 Number 混合算术', () => {
  const huge = 2n ** 100n;
  assert.equal(huge + 1n - huge, 1n);
  assert.equal(7n / 3n, 2n);
  assert.equal(-7n / 3n, -2n);

  assert.throws(
    () => 1n + 1,
    TypeError,
  );

  // 比较运算允许跨 Number 与 BigInt 比较，但运算前最好明确领域：浮点数、NaN、Infinity
  // 与超大整数混在一起会让代码意图不清。JSON 也不会默认序列化 BigInt。
  assert.equal(10n > 9, true);
  assert.throws(
    () => JSON.stringify({ count: 1n }),
    TypeError,
  );
});

test('ToBoolean 的假值集合很小，对象包装的假值仍是真值', () => {
  const falsyValues = [false, 0, -0, 0n, '', null, undefined, Number.NaN];
  assert.ok(falsyValues.every((value) => !value));

  assert.equal(Boolean([]), true);
  assert.equal(Boolean({}), true);
  assert.equal(Boolean(new Boolean(false)), true);

  // 空数组和字符串比较时会先转成原始值，最终出现 0 == 0；if ([]) 却只执行
  // ToBoolean，不发生同一套转换。这是宽松相等最容易产生误读的例子之一。
  assert.equal([] == false, true); // eslint-disable-line eqeqeq
  assert.equal(Boolean([]), true);
});

test('显式转换让解析规则与失败信号更清楚', () => {
  assert.equal(Number(' 42 '), 42);
  assert.equal(Number(''), 0);
  assert.ok(Number.isNaN(Number('42px')));

  assert.equal(Number.parseInt('42px', 10), 42);
  assert.equal(Number.parseFloat('3.14rem'), 3.14);
  assert.ok(Number.isNaN(Number.parseInt('px42', 10)));

  assert.equal(String(null), 'null');
  assert.equal(String(Symbol('id')), 'Symbol(id)');
  assert.equal(Boolean('false'), true);
  assert.equal(BigInt('9007199254740993'), 9007199254740993n);
});

test('严格相等避免大多数隐式转换，宽松相等只适合有意使用的规则', () => {
  assert.equal(0 === false, false);
  assert.equal('' === 0, false);
  assert.equal('42' === 42, false);

  assert.equal(0 == false, true); // eslint-disable-line eqeqeq
  assert.equal('' == 0, true); // eslint-disable-line eqeqeq
  assert.equal('42' == 42, true); // eslint-disable-line eqeqeq

  // x == null 是少数常见的有意写法：它只同时接受 null 与 undefined，不会接受 0、
  // false 或空字符串。若无需这个双值检查，仍优先写 ===。
  const isNullish = (value) => value == null; // eslint-disable-line eqeqeq
  assert.equal(isNullish(null), true);
  assert.equal(isNullish(undefined), true);
  assert.equal(isNullish(0), false);
});

test('关系比较可能进行字符串字典序或数值转换', () => {
  assert.equal('20' < '3', true);
  assert.equal('20' < 3, false);
  assert.equal('2' < 10, true);

  // NaN 与任何值的有序比较都为 false，因此 !(a < b) 不能普遍推导 a >= b。
  assert.equal(Number.NaN < 1, false);
  assert.equal(Number.NaN >= 1, false);
});

test('空值合并只处理 nullish，逻辑或还会替换其他假值', () => {
  const storedCount = 0;
  const storedLabel = '';

  assert.equal(storedCount ?? 10, 0);
  assert.equal(storedCount || 10, 10);
  assert.equal(storedLabel ?? 'default', '');
  assert.equal(storedLabel || 'default', 'default');
  assert.equal(null ?? 'fallback', 'fallback');
  assert.equal(undefined ?? 'fallback', 'fallback');
});

test('Symbol 是唯一原始值，也可以通过全局注册表共享', () => {
  const first = Symbol('request');
  const second = Symbol('request');
  assert.notEqual(first, second);
  assert.equal(first.description, 'request');

  const registered = Symbol.for('polyglot.request');
  assert.equal(Symbol.for('polyglot.request'), registered);
  assert.equal(Symbol.keyFor(registered), 'polyglot.request');
  assert.equal(Symbol.keyFor(first), undefined);

  const record = {
    visible: 1,
    [first]: 2,
  };

  // Symbol 键可以避免普通字符串键冲突；常规枚举和 JSON 会忽略它，需要用
  // Reflect.ownKeys 或 Object.getOwnPropertySymbols 明确读取。
  assert.deepEqual(Object.keys(record), ['visible']);
  assert.deepEqual(Object.getOwnPropertySymbols(record), [first]);
  assert.deepEqual(Reflect.ownKeys(record), ['visible', first]);
  assert.equal(JSON.stringify(record), '{"visible":1}');
});

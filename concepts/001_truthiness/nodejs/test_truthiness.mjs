// 横向概念 001｜真假值与逻辑运算结果。
// 共同问题：数值零、空文本、空集合和空值如何判断；自定义对象能否定义真假；
// 逻辑运算符返回布尔值还是原操作数。
//
// polyglot-concept: truthiness
// polyglot-related: languages/nodejs/language/test_001_primitive_values_numeric_models_and_equality.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('零、空文本和 nullish 值为假', () => {
  const falsyValues = [0, -0, 0n, '', null, undefined, Number.NaN];

  assert.ok(falsyValues.every((value) => Boolean(value) === false));
  assert.equal(Boolean(1), true);
  assert.equal(Boolean('0'), true);
});

test('空数组、空对象和空集合仍然为真', () => {
  assert.equal(Boolean([]), true);
  assert.equal(Boolean({}), true);
  assert.equal(Boolean(new Set()), true);
  assert.equal(Boolean(new Map()), true);

  // ToBoolean 只看“对象”这一类型，不询问 length、size 或集合内容。
});

test('对象不能用转换钩子覆盖 ToBoolean', () => {
  let conversionCalls = 0;
  const value = {
    [Symbol.toPrimitive]() {
      conversionCalls += 1;
      return 0;
    },
  };

  assert.equal(Boolean(value), true);
  assert.equal(conversionCalls, 0);
});

test('逻辑运算符返回被选中的原操作数', () => {
  const emptyArray = [];
  const fallback = { source: 'default' };
  const payload = ['ready'];

  assert.equal(emptyArray || fallback, emptyArray);
  assert.equal('' || fallback, fallback);
  assert.equal(payload && fallback, fallback);
  assert.deepEqual(0 && fallback, 0);

  // 第一条故意证明空数组本身已是真值；它不会像 Python 的 [] 那样选择 fallback。
});

// polyglot-covers:
// - nodejs.core.assert-strict-and-loose-legacy-mode
// - nodejs.core.assert-deep-strict-equality
// - nodejs.core.assert-partial-deep-strict-equal
// - nodejs.core.assert-throws-and-does-not-throw
// - nodejs.core.assert-rejects-and-does-not-reject
// - nodejs.core.assert-match-if-error-and-fail
// - nodejs.core.assertion-error-fields-and-diff

import assert from 'node:assert/strict';
import test from 'node:test';

import legacyAssert from 'node:assert';

test('strict 模式的 equal/notEqual 使用严格相等', () => {
  assert.equal(1, 1);
  assert.notEqual(1, '1');
  assert.throws(() => assert.equal(1, '1'), assert.AssertionError);

  // node:assert/strict 会把旧名称 deepEqual/equal 也切换为严格版本。
  assert.equal(assert.equal, assert.strictEqual);
  assert.equal(assert.deepEqual, assert.deepStrictEqual);

  legacyAssert.equal(1, '1');
  assert.throws(() => legacyAssert.strictEqual(1, '1'), legacyAssert.AssertionError);
});

test('deepStrictEqual 比较类型、原型、可枚举属性和内置值语义', () => {
  assert.deepEqual({ value: Number.NaN }, { value: Number.NaN });
  assert.throws(() => assert.deepEqual({ value: 0 }, { value: -0 }), assert.AssertionError);
  assert.deepEqual(new Set([{ id: 1 }]), new Set([{ id: 1 }]));
  assert.deepEqual(new Map([[{ id: 1 }, { value: 2 }]]), new Map([
    [{ id: 1 }, { value: 2 }],
  ]));

  class Record {
    constructor(id) {
      this.id = id;
    }
  }
  assert.throws(() => assert.deepEqual(new Record(1), { id: 1 }), assert.AssertionError);
});

test('deepStrictEqual 支持循环图，但不要求相同的共享引用拓扑', () => {
  const first = { value: 1 };
  first.self = first;
  const second = { value: 1 };
  second.self = second;

  assert.deepEqual(first, second);

  const shared = {};
  const withSharedChild = { left: shared, right: shared };
  const withSeparateChildren = { left: {}, right: {} };
  assert.deepEqual(withSharedChild, withSeparateChildren);

  // deepStrictEqual 比较可观察结构，而不是对象图同构；需要检查别名关系时应另写 === 断言。
  assert.equal(withSharedChild.left, withSharedChild.right);
  assert.notEqual(withSeparateChildren.left, withSeparateChildren.right);
});

test('partialDeepStrictEqual 递归要求 expected 子集并保留严格类型语义', () => {
  const actual = {
    metadata: {
      id: 7,
      labels: ['stable', 'documented'],
    },
    status: 'ready',
  };

  assert.partialDeepStrictEqual(actual, {
    metadata: {
      id: 7,
    },
  });
  assert.throws(
    () => assert.partialDeepStrictEqual(actual, { metadata: { id: '7' } }),
    assert.AssertionError,
  );
});

test('throws 可按构造器、正则、对象字段或验证函数匹配', () => {
  const cause = new Error('low level');
  const operation = () => {
    throw new TypeError('invalid payload', { cause });
  };

  assert.throws(operation, TypeError);
  assert.throws(operation, /invalid payload/);
  assert.throws(operation, {
    cause,
    message: 'invalid payload',
    name: 'TypeError',
  });
  assert.throws(operation, (error) => error.cause === cause);

  // 验证函数必须返回 truthy；抛出新错误会掩盖原本正在验证的异常。
});

test('doesNotThrow 只包装预期同步区域，不应吞掉未知异常', () => {
  assert.doesNotThrow(() => JSON.parse('{"ok":true}'));
  assert.throws(
    () => assert.doesNotThrow(() => {
      throw new Error('unexpected');
    }),
    assert.AssertionError,
  );
});

test('rejects/doesNotReject 等待 Promise 或返回 Promise 的函数', async () => {
  await assert.rejects(Promise.reject(new RangeError('out of range')), RangeError);
  await assert.rejects(
    async () => {
      throw new Error('async failure');
    },
    /async failure/,
  );
  await assert.doesNotReject(async () => 42);

  // assert.throws 不会等待 async 函数；调用后立即得到 Promise，必须使用 rejects。
  assert.throws(
    () => assert.throws(async () => 1),
    assert.AssertionError,
  );
});

test('match、doesNotMatch、ok、ifError 与 fail 覆盖常用意图', () => {
  assert.match('polyglot-nodejs', /nodejs$/);
  assert.doesNotMatch('polyglot-nodejs', /^python/);
  assert.ok({});
  assert.ifError(null);
  assert.ifError(undefined);

  assert.throws(() => assert.ok(0, 'must be truthy'), /must be truthy/);
  assert.throws(() => assert.ifError(new Error('callback failed')), /callback failed/);
  assert.throws(() => assert.fail('explicit failure'), /explicit failure/);
});

test('AssertionError 暴露 actual、expected、operator 和 generatedMessage', () => {
  let captured;
  try {
    assert.deepEqual({ value: 1 }, { value: 2 });
  } catch (error) {
    captured = error;
  }

  assert.equal(captured instanceof assert.AssertionError, true);
  assert.deepEqual(captured.actual, { value: 1 });
  assert.deepEqual(captured.expected, { value: 2 });
  assert.equal(captured.operator, 'deepStrictEqual');
  assert.equal(captured.generatedMessage, true);
  assert.ok(captured.message.includes('Expected values to be strictly deep-equal'));
});

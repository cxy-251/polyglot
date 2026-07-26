// polyglot-covers:
// - nodejs.language.conditionals-and-switch
// - nodejs.language-loop-statements
// - nodejs.language.labels-break-and-continue
// - nodejs.language.try-catch-finally-completion
// - nodejs.language.throw-and-error-cause
// - nodejs.language.aggregate-error
// - nodejs.language.catch-binding

import assert from 'node:assert/strict';
import test from 'node:test';

test('if 检查真值而不要求 Boolean，switch 使用严格相等', () => {
  const classify = (value) => {
    if (value) {
      return 'truthy';
    }
    return 'falsy';
  };

  assert.equal(classify([]), 'truthy');
  assert.equal(classify(0), 'falsy');

  const match = (value) => {
    switch (value) {
      case 1:
        return 'number';
      case '1':
        return 'string';
      default:
        return 'other';
    }
  };

  assert.equal(match(1), 'number');
  assert.equal(match('1'), 'string');
});

test('switch 默认贯穿 case，显式 break 才结束匹配后的执行', () => {
  const permissions = (role) => {
    const granted = [];
    switch (role) {
      case 'admin':
        granted.push('manage');
        // 有意贯穿：管理员也继承编辑者和查看者的权限。
      case 'editor':
        granted.push('edit');
      case 'viewer':
        granted.push('read');
        break;
      default:
        granted.push('none');
    }
    return granted;
  };

  assert.deepEqual(permissions('admin'), ['manage', 'edit', 'read']);
  assert.deepEqual(permissions('editor'), ['edit', 'read']);
  assert.deepEqual(permissions('unknown'), ['none']);
});

test('while、do-while 和经典 for 的条件检查时点不同', () => {
  let whileCount = 0;
  while (whileCount < 0) {
    whileCount += 1;
  }

  let doCount = 0;
  do {
    doCount += 1;
  } while (doCount < 0);

  const visited = [];
  for (let index = 0; index < 3; index += 1) {
    visited.push(index);
  }

  assert.equal(whileCount, 0);
  assert.equal(doCount, 1);
  assert.deepEqual(visited, [0, 1, 2]);
});

test('标签允许一次跳出多层结构，但不应代替普通函数分解', () => {
  const cells = [];

  outer: for (let row = 0; row < 3; row += 1) {
    for (let column = 0; column < 3; column += 1) {
      if (row === 1 && column === 1) {
        break outer;
      }
      cells.push([row, column]);
    }
  }

  assert.deepEqual(cells, [
    [0, 0],
    [0, 1],
    [0, 2],
    [1, 0],
  ]);

  const oddCells = [];
  rows: for (let row = 0; row < 2; row += 1) {
    for (let column = 0; column < 3; column += 1) {
      if (column % 2 === 0) {
        continue rows;
      }
      oddCells.push([row, column]);
    }
  }
  assert.deepEqual(oddCells, []);
});

test('for-in 枚举字符串键，for-of 消费 iterable 的值', () => {
  const prototype = { inherited: 1 };
  const record = Object.create(prototype);
  record.own = 2;
  Object.defineProperty(record, 'hidden', {
    enumerable: false,
    value: 3,
  });

  const keys = [];
  for (const key in record) {
    keys.push(key);
  }

  const values = [];
  for (const value of new Set(['a', 'b'])) {
    values.push(value);
  }

  assert.deepEqual(keys, ['own', 'inherited']);
  assert.deepEqual(values, ['a', 'b']);
  // for-in 会包含可枚举的继承属性；只要自有键时优先使用 Object.keys/entries。
});

test('catch 可以省略绑定，也拥有独立词法作用域', () => {
  let message = 'outer';

  try {
    throw new Error('inner');
  } catch (error) {
    let message = error.message;
    assert.equal(message, 'inner');
  }

  assert.equal(message, 'outer');

  let caught = false;
  try {
    JSON.parse('{');
  } catch {
    caught = true;
  }
  assert.equal(caught, true);
});

test('finally 总会执行，而且它自己的控制完成会覆盖先前结果', () => {
  const events = [];
  const ordinaryReturn = () => {
    try {
      events.push('try');
      return 'try result';
    } finally {
      events.push('finally');
    }
  };

  const overridingReturn = () => {
    try {
      throw new Error('lost error');
    } finally {
      // 这是危险写法：finally 的 return 会吞掉 try 的异常或返回值。
      return 'finally result';
    }
  };

  assert.equal(ordinaryReturn(), 'try result');
  assert.deepEqual(events, ['try', 'finally']);
  assert.equal(overridingReturn(), 'finally result');
});

test('Error cause 保留包装层级，AggregateError 表示多个失败', () => {
  const lowLevel = new TypeError('invalid payload');
  const highLevel = new Error('request failed', { cause: lowLevel });

  assert.equal(highLevel.message, 'request failed');
  assert.equal(highLevel.cause, lowLevel);
  assert.ok(highLevel.stack.includes('request failed'));

  const combined = new AggregateError(
    [new Error('first'), new RangeError('second')],
    'all attempts failed',
    { cause: highLevel },
  );
  assert.equal(combined.name, 'AggregateError');
  assert.deepEqual(
    [...combined.errors].map((error) => error.message),
    ['first', 'second'],
  );
  assert.equal(combined.cause, highLevel);
});

test('throw 后禁止换行，抛出的值却不要求是 Error', () => {
  assert.throws(
    () => new Function('throw\nnew Error("broken");'),
    SyntaxError,
  );

  try {
    throw 'plain value';
  } catch (error) {
    assert.equal(error, 'plain value');
  }

  // 语言允许抛出任意值，但生产代码应抛 Error：类型、cause 与 stack 才能稳定传递上下文。
});

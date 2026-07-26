// polyglot-covers:
// - nodejs.language.to-primitive-hints-and-symbol-to-primitive
// - nodejs.language.value-of-and-to-string-fallback
// - nodejs.language.symbol-to-string-tag
// - nodejs.language.symbol-has-instance
// - nodejs.language.symbol-match-search-replace-and-split
// - nodejs.language.symbol-unscopables
// - nodejs.language.well-known-symbol-protocol-entry-points

import assert from 'node:assert/strict';
import test from 'node:test';

test('Symbol.toPrimitive 观察 number、string 与 default hint', () => {
  const hints = [];
  const value = {
    [Symbol.toPrimitive](hint) {
      hints.push(hint);
      if (hint === 'number') {
        return 7;
      }
      if (hint === 'string') {
        return 'seven';
      }
      return 'default';
    },
  };

  assert.equal(Number(value), 7);
  assert.equal(String(value), 'seven');
  assert.equal(`${value}`, 'seven');
  assert.equal(value + '!', 'default!');
  assert.deepEqual(hints, ['number', 'string', 'string', 'default']);
});

test('普通对象在 number hint 下先 valueOf，再 toString', () => {
  const events = [];
  const value = {
    valueOf() {
      events.push('valueOf');
      return {};
    },
    toString() {
      events.push('toString');
      return '12';
    },
  };

  assert.equal(Number(value), 12);
  assert.deepEqual(events, ['valueOf', 'toString']);

  const invalid = {
    valueOf: () => ({}),
    toString: () => ({}),
  };
  assert.throws(() => Number(invalid), TypeError);
});

test('Date 的 default hint 偏向 string，普通对象偏向 number', () => {
  const ordinary = {
    valueOf: () => 3,
    toString: () => 'object',
  };
  const date = new Date(0);

  assert.equal(ordinary + 1, 4);
  assert.equal(typeof (date + 1), 'string');
  assert.equal(+date, 0);

  // 二元 + 在 primitive 转换后，任一操作数为字符串就拼接；否则执行数值加法。
});

test('Symbol.toStringTag 自定义 Object.prototype.toString 的品牌文本', () => {
  class Collection {
    get [Symbol.toStringTag]() {
      return 'PolyglotCollection';
    }
  }

  const value = new Collection();
  assert.equal(Object.prototype.toString.call(value), '[object PolyglotCollection]');
  assert.equal(value[Symbol.toStringTag], 'PolyglotCollection');

  assert.equal(Object.prototype.toString.call(new Map()), '[object Map]');
  assert.equal(Object.prototype.toString.call(null), '[object Null]');
});

test('Symbol.hasInstance 可定制 instanceof，协议方法优先于普通可调用检查', () => {
  class EvenNumber {
    static [Symbol.hasInstance](value) {
      return Number.isInteger(value) && value % 2 === 0;
    }
  }

  assert.equal(2 instanceof EvenNumber, true);
  assert.equal(3 instanceof EvenNumber, false);
  assert.equal('2' instanceof EvenNumber, false);

  const protocol = {
    [Symbol.hasInstance]: (value) => value?.kind === 'record',
  };
  assert.equal(({ kind: 'record' }) instanceof protocol, true);

  const invalidProtocol = {
    [Symbol.hasInstance]: true,
  };
  assert.throws(() => ({}) instanceof invalidProtocol, TypeError);
});

test('String 正则方法从 well-known Symbol 查找协议方法', () => {
  const matcher = {
    [Symbol.match](text) {
      return { input: text, matched: text.startsWith('poly') };
    },
  };
  const replacer = {
    [Symbol.replace](text, replacement) {
      return `${replacement}<${text}>`;
    },
  };
  const splitter = {
    [Symbol.split](text) {
      return [...text];
    },
  };

  assert.deepEqual('polyglot'.match(matcher), {
    input: 'polyglot',
    matched: true,
  });
  assert.equal('value'.replace(replacer, 'prefix'), 'prefix<value>');
  assert.deepEqual('ABC'.split(splitter), ['A', 'B', 'C']);
});

test('Symbol.match 也影响某些 API 是否把对象视为 RegExp', () => {
  const pattern = /value/;
  assert.throws(() => 'value'.includes(pattern), TypeError);

  pattern[Symbol.match] = false;
  assert.equal('prefix/value/suffix'.includes(pattern), true);

  const disguised = {
    [Symbol.match]: true,
    toString: () => 'value',
  };
  assert.throws(() => 'value'.includes(disguised), TypeError);
});

test('Symbol.unscopables 只影响旧式 with 名称解析', () => {
  const inspect = new Function(
    'object',
    'outer',
    'with (object) { return [visible, hidden, outer]; }',
  );
  const object = {
    hidden: 'object hidden',
    visible: 'object visible',
    [Symbol.unscopables]: {
      hidden: true,
    },
  };

  globalThis.hidden = 'outer hidden';
  try {
    assert.deepEqual(inspect(object, 'argument outer'), [
      'object visible',
      'outer hidden',
      'argument outer',
    ]);
  } finally {
    delete globalThis.hidden;
  }

  // ESM/严格模式禁止 with；该案例只用于解释 Array.prototype 的兼容协议，不推荐使用。
});

test('常见 well-known Symbol 把表层语法映射到对象协议', () => {
  assert.equal(typeof Symbol.iterator, 'symbol');
  assert.equal(typeof Symbol.asyncIterator, 'symbol');
  assert.equal(typeof Symbol.species, 'symbol');
  assert.equal(typeof Symbol.isConcatSpreadable, 'symbol');
  assert.equal(typeof Symbol.toPrimitive, 'symbol');
  assert.equal(typeof Symbol.dispose, 'symbol');
  assert.equal(typeof Symbol.asyncDispose, 'symbol');

  assert.equal(Array.prototype[Symbol.iterator], Array.prototype.values);
  assert.equal(RegExp.prototype[Symbol.match] instanceof Function, true);
});

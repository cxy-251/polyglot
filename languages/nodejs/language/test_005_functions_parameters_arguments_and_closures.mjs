// polyglot-covers:
// - nodejs.language.function-declaration-expression-and-name
// - nodejs.language.function-call-and-construct
// - nodejs.language.parameter-defaults-and-rest
// - nodejs.language.arguments-object
// - nodejs.language.lexical-closures
// - nodejs.language.function-length-and-name
// - nodejs.language.recursion-and-named-function-expression
// - nodejs.language.new-target

// 跨语言迁移提示：JavaScript 调用通常用 undefined 填补缺参并保留多余实参；
// Python 会按签名报错，C++ 会在编译期筛选重载。默认参数求值时机也不能跨语言类推。

import assert from 'node:assert/strict';
import test from 'node:test';

test('函数声明、匿名表达式和命名表达式具有不同名称可见性', () => {
  assert.equal(declared(2), 4);

  function declared(value) {
    return value * 2;
  }

  const inferredName = function (value) {
    return value + 1;
  };
  const factorial = function recurse(value) {
    return value <= 1 ? 1 : value * recurse(value - 1);
  };

  assert.equal(inferredName.name, 'inferredName');
  assert.equal(factorial(5), 120);
  assert.equal(typeof recurse, 'undefined');
});

test('默认参数只处理 undefined，并可引用前面的参数', () => {
  const connect = (
    host = 'localhost',
    port = host === 'localhost' ? 3000 : 443,
  ) => ({ host, port });

  assert.deepEqual(connect(), { host: 'localhost', port: 3000 });
  assert.deepEqual(connect('example.test'), { host: 'example.test', port: 443 });
  assert.deepEqual(connect(null, 0), { host: null, port: 0 });

  const invalidOrder = (first = second, second = 2) => first + second;
  assert.throws(() => invalidOrder(), ReferenceError);
  assert.equal(invalidOrder(1), 3);
});

test('默认表达式在每次调用时按需执行', () => {
  let nextId = 0;
  const create = (id = ++nextId) => ({ id });

  assert.deepEqual(create(), { id: 1 });
  assert.deepEqual(create(), { id: 2 });
  assert.deepEqual(create(20), { id: 20 });
  assert.equal(nextId, 2);
});

test('rest 参数是真数组，arguments 是兼容旧代码的类数组对象', () => {
  function inspect(first, ...remaining) {
    return {
      first,
      remaining,
      allArguments: Array.from(arguments),
      restIsArray: Array.isArray(remaining),
      argumentsIsArray: Array.isArray(arguments),
    };
  }

  assert.deepEqual(inspect('a', 'b', 'c'), {
    first: 'a',
    remaining: ['b', 'c'],
    allArguments: ['a', 'b', 'c'],
    restIsArray: true,
    argumentsIsArray: false,
  });
});

test('严格模式参数与 arguments 不共享可变存储', () => {
  function update(parameter) {
    parameter = 'parameter changed';
    const afterParameterWrite = arguments[0];
    arguments[0] = 'argument changed';
    return { parameter, afterParameterWrite };
  }

  // ESM 总是严格模式。旧式 sloppy 简单参数列表可能把二者映射到一起，不应依赖该行为。
  assert.deepEqual(update('initial'), {
    parameter: 'parameter changed',
    afterParameterWrite: 'initial',
  });
});

test('闭包捕获的是词法环境中的绑定，而不是创建时的值快照', () => {
  const createCounter = (initial = 0) => {
    let count = initial;
    return {
      increment() {
        count += 1;
        return count;
      },
      read() {
        return count;
      },
    };
  };

  const first = createCounter(10);
  const second = createCounter(20);
  assert.equal(first.increment(), 11);
  assert.equal(first.read(), 11);
  assert.equal(second.read(), 20);
});

test('函数 length 在首个默认参数前停止，rest 不计入长度', () => {
  function ordinary(first, second, third) {}
  function withDefault(first, second = 2, third) {}
  function withRest(first, ...remaining) {}

  assert.equal(ordinary.length, 3);
  assert.equal(withDefault.length, 1);
  assert.equal(withRest.length, 1);
  assert.equal(ordinary.name, 'ordinary');
});

test('普通函数可调用也可构造，箭头函数不可构造', () => {
  function Record(value) {
    this.value = value;
  }

  const callable = Record.call({ existing: true }, 3);
  const constructed = new Record(7);
  const arrow = (value) => ({ value });

  assert.equal(callable, undefined);
  assert.equal(constructed.value, 7);
  assert.equal(constructed instanceof Record, true);
  assert.deepEqual(arrow(9), { value: 9 });
  assert.throws(() => new arrow(9), TypeError);
});

test('new.target 让同一个函数区分普通调用与构造调用', () => {
  function InvocationKind() {
    return new.target === undefined ? 'call' : new.target.name;
  }

  assert.equal(InvocationKind(), 'call');

  const instance = new InvocationKind();
  // 构造函数返回原始值时，该值会被忽略，最终仍返回新对象。
  assert.equal(instance instanceof InvocationKind, true);

  function Factory() {
    return { replacement: true };
  }
  assert.deepEqual(new Factory(), { replacement: true });
});

test('call、apply 与 Reflect.apply 显式提供接收者和参数', () => {
  function describe(prefix, suffix) {
    return `${prefix}${this.name}${suffix}`;
  }
  const receiver = { name: 'Ada' };

  assert.equal(describe.call(receiver, '<', '>'), '<Ada>');
  assert.equal(describe.apply(receiver, ['[', ']']), '[Ada]');
  assert.equal(Reflect.apply(describe, receiver, ['(', ')']), '(Ada)');
});

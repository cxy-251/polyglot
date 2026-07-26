// polyglot-covers:
// - nodejs.language.lexical-grammar-and-automatic-semicolon-insertion
// - nodejs.language.let-const-var-bindings
// - nodejs.language.temporal-dead-zone
// - nodejs.language.lexical-and-function-scope
// - nodejs.language.destructuring-binding
// - nodejs.language.binding-default-initializers
// - nodejs.language.rest-binding

// 跨语言迁移提示：let / const 有词法作用域和暂时性死区，var 则提升到函数作用域；
// Python 由代码块内是否赋值决定 local，C++ 的声明位置、存储期与捕获方式又是另一套规则。

import assert from 'node:assert/strict';
import test from 'node:test';

test('let、const 与 var 建立不同范围的绑定', () => {
  function inspectScopes() {
    var functionScoped = 'outer';
    let lexical = 'outer';

    {
      var functionScoped = 'block update';
      let lexical = 'block only';
      const fixedBinding = { count: 1 };

      // const 固定的是绑定，不会递归冻结对象。需要不可变对象时应显式使用冻结策略。
      fixedBinding.count += 1;
      assert.equal(lexical, 'block only');
      assert.deepEqual(fixedBinding, { count: 2 });
    }

    return { functionScoped, lexical };
  }

  assert.deepEqual(inspectScopes(), {
    functionScoped: 'block update',
    lexical: 'outer',
  });
});

test('var 声明提升但赋值不提升，词法绑定在初始化前处于 TDZ', () => {
  function readVarBeforeDeclaration() {
    const before = value;
    var value = 7;
    return { before, after: value };
  }

  assert.deepEqual(readVarBeforeDeclaration(), {
    before: undefined,
    after: 7,
  });

  function readLetBeforeDeclaration() {
    return value;
    // 这条声明虽然不可达，仍为整个块创建绑定；读取发生在初始化之前。
    let value = 7;
  }

  assert.throws(readLetBeforeDeclaration, ReferenceError);

  let outer = 'outer';
  assert.throws(
    () => {
      // 内层 let 会遮蔽外层同名变量；不能借由外层值初始化自己。
      let outer = `${outer} changed`;
      return outer;
    },
    ReferenceError,
  );
  assert.equal(outer, 'outer');
});

test('每轮循环的词法绑定让闭包捕获不同值', () => {
  const lexicalReaders = [];
  for (let index = 0; index < 3; index += 1) {
    lexicalReaders.push(() => index);
  }

  const functionReaders = [];
  for (var index = 0; index < 3; index += 1) {
    functionReaders.push(() => index);
  }

  assert.deepEqual(lexicalReaders.map((read) => read()), [0, 1, 2]);
  assert.deepEqual(functionReaders.map((read) => read()), [3, 3, 3]);
});

test('对象解构区分绑定名、属性名、默认值和剩余属性', () => {
  const source = {
    user_name: 'Ada',
    preferences: {
      theme: undefined,
    },
    active: false,
    extra: 9,
  };

  const {
    user_name: name,
    preferences: { theme = 'dark' },
    active = true,
    missing = 'fallback',
    ...metadata
  } = source;

  // 默认初始化只在值为 undefined 时触发，不会替换 false、0、空字符串或 null。
  assert.equal(name, 'Ada');
  assert.equal(theme, 'dark');
  assert.equal(active, false);
  assert.equal(missing, 'fallback');
  assert.deepEqual(metadata, { extra: 9 });
});

test('数组解构使用迭代协议并支持跳位、默认值和 rest', () => {
  const [first, , third = 30, ...remaining] = [10, 20, undefined, 40, 50];

  assert.equal(first, 10);
  assert.equal(third, 30);
  assert.deepEqual(remaining, [40, 50]);

  const [head, tail = 'fallback'] = ['only', null];
  assert.equal(head, 'only');
  assert.equal(tail, null);
});

test('解构默认表达式按需、从左到右求值', () => {
  const events = [];
  const create = (label, value) => {
    events.push(label);
    return value;
  };

  const [first = create('first', 1), second = create('second', first + 1)] = [
    undefined,
    undefined,
  ];
  const { present = create('not used', 3) } = { present: 9 };

  assert.deepEqual({ first, second, present }, { first: 1, second: 2, present: 9 });
  assert.deepEqual(events, ['first', 'second']);
});

test('已有变量使用对象解构赋值时需要用括号消除语法歧义', () => {
  let left;
  let right;
  ({ left, right } = { left: 1, right: 2 });

  assert.deepEqual([left, right], [1, 2]);

  // 不带括号时，开头的 { 会被解析成块而不是对象解构赋值目标。
  assert.throws(
    () => new Function('let value; { value } = { value: 1 };'),
    SyntaxError,
  );
});

test('自动分号插入会改变 return 换行后的含义', () => {
  const returnsObject = new Function('return { value: 1 };');
  const returnsUndefined = new Function('return\n{ value: 1 };');

  assert.deepEqual(returnsObject(), { value: 1 });
  assert.equal(returnsUndefined(), undefined);

  // return、throw、break、continue 与后续表达式之间存在受限换行规则。工程代码应避免
  // 依赖 ASI 猜测语句边界，特别是下一行从 (, [, `, + 或 - 开始时。
});

test('数字分隔符改善可读性但不属于运行时字符串语法', () => {
  assert.equal(1_000_000, 1000000);
  assert.equal(0xff_ff, 65535);
  assert.equal(0b1010_0001, 161);

  assert.ok(Number.isNaN(Number('1_000')));
  assert.equal(BigInt('1000'), 1000n);
  assert.throws(() => BigInt('1_000'), SyntaxError);
});

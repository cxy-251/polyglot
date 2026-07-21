// polyglot-covers:
// - nodejs.language.direct-eval-and-lexical-scope
// - nodejs.language-indirect-eval-and-global-scope
// - nodejs.language.strict-eval-bindings
// - nodejs.language.function-constructor-scope
// - nodejs.language.eval-completion-value
// - nodejs.language.dynamic-code-syntax-and-security-pitfalls

import assert from 'node:assert/strict';
import test from 'node:test';

test('直接 eval 在当前词法环境求值', () => {
  const outer = 7;
  const result = eval('outer * 2');

  assert.equal(result, 14);

  {
    const blockValue = 9;
    assert.equal(eval('blockValue + outer'), 16);
  }
});

test('ESM 中 direct eval 是严格模式，声明不会泄漏到外围', () => {
  const result = eval(`
    var functionScoped = 1;
    let lexical = 2;
    const fixed = 3;
    functionScoped + lexical + fixed;
  `);

  assert.equal(result, 6);
  assert.equal(typeof functionScoped, 'undefined');
  assert.equal(typeof lexical, 'undefined');
  assert.equal(typeof fixed, 'undefined');

  assert.throws(() => eval('var eval = 1;'), SyntaxError);
});

test('间接 eval 在全局作用域运行，不能读取调用点局部变量', () => {
  const local = 'local';
  const indirect = (0, eval);

  assert.equal(indirect('typeof local'), 'undefined');
  assert.equal(eval?.('typeof local'), 'undefined');
  assert.equal(indirect('globalThis === this'), true);

  const key = '__polyglot_indirect_eval__';
  try {
    indirect(`globalThis.${key} = 7`);
    assert.equal(globalThis[key], 7);
  } finally {
    delete globalThis[key];
  }
});

test('Function 构造器只捕获全局环境，不形成调用点闭包', () => {
  const local = 7;
  const add = new Function('left', 'right', 'return left + right;');
  const inspect = new Function('return typeof local;');

  assert.equal(add(2, 3), 5);
  assert.equal(inspect(), 'undefined');
  assert.equal(local, 7);

  // 构造器参数可以分段提供，但都会作为源码解析；绝不能拼接不可信输入。
  const multiply = Function('left', 'right', 'return left * right;');
  assert.equal(multiply(3, 4), 12);
});

test('Function 构造器默认是 sloppy，函数体可用指令切换严格模式', () => {
  const sloppyThis = new Function('return this;');
  const strictThis = new Function('"use strict"; return this;');

  assert.equal(sloppyThis(), globalThis);
  assert.equal(strictThis(), undefined);

  const sloppyAssignment = new Function(
    'globalThis.__polyglot_dynamic__ = 1; return __polyglot_dynamic__;',
  );
  try {
    assert.equal(sloppyAssignment(), 1);
  } finally {
    delete globalThis.__polyglot_dynamic__;
  }
});

test('eval 返回脚本的完成值，声明语句本身通常没有值', () => {
  assert.equal(eval('1 + 2'), 3);
  assert.equal(eval('let value = 1;'), undefined);
  assert.equal(eval('let value = 1; value += 2; value;'), 3);
  assert.equal(eval('if (true) { 7; } else { 8; }'), 7);
});

test('动态代码在执行前解析，语法错误不会运行前置片段', () => {
  const key = '__polyglot_parse_guard__';
  delete globalThis[key];

  assert.throws(
    () => eval(`globalThis.${key} = 1; let = ;`),
    SyntaxError,
  );
  assert.equal(globalThis[key], undefined);
  assert.throws(() => new Function('return )'), SyntaxError);
});

test('数据解析应使用专用 API，而不是把数据当源码执行', () => {
  const json = '{"expression":"2 + 3"}';
  const parsed = JSON.parse(json);

  assert.deepEqual(parsed, { expression: '2 + 3' });
  assert.equal(parsed.expression, '2 + 3');

  // eval/new Function 会获得语言全部能力，除注入外还破坏 CSP、静态分析和优化。
  assert.equal(eval(parsed.expression), 5);
});

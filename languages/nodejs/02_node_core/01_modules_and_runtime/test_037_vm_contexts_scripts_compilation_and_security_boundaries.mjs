// polyglot-covers:
// - nodejs.core.vm-contextify-and-run-in-context
// - nodejs.core.vm-script-compilation-and-reuse
// - nodejs.core.vm-context-global-and-intrinsics
// - nodejs.core.vm-timeout-and-break-on-sigint
// - nodejs.core.vm-compile-function
// - nodejs.core.vm-code-generation-policy
// - nodejs.core.vm-cached-data
// - nodejs.core.vm-is-not-a-security-boundary

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  Script,
  compileFunction,
  createContext,
  isContext,
  runInContext,
  runInNewContext,
} from 'node:vm';

test('createContext 把普通对象变成独立 global 环境的接口', () => {
  const sandbox = {
    input: 7,
    output: undefined,
  };
  const context = createContext(sandbox, { name: 'polyglot-context' });

  assert.equal(context, sandbox);
  assert.equal(isContext(context), true);
  runInContext('output = input * 2; globalThis.created = "inside";', context);

  assert.equal(sandbox.output, 14);
  assert.equal(sandbox.created, 'inside');
  assert.equal(globalThis.created, undefined);
});

test('context 拥有不同 realm 的内置对象与原型', () => {
  const foreign = runInNewContext('({ array: [], map: new Map(), error: new Error("x") })');

  assert.equal(foreign.array instanceof Array, false);
  assert.equal(Array.isArray(foreign.array), true);
  assert.equal(foreign.map instanceof Map, false);
  assert.equal(Object.prototype.toString.call(foreign.map), '[object Map]');
  assert.equal(foreign.error instanceof Error, false);

  // 跨 realm 品牌判定优先使用 Array.isArray、util.types 或协议，而非 instanceof。
});

test('Script 把编译和执行分离，可在多个 context 重用', () => {
  const script = new Script('counter += step; counter;', {
    filename: 'counter.vm.js',
  });
  const first = createContext({ counter: 0, step: 2 });
  const second = createContext({ counter: 10, step: 3 });

  assert.equal(script.runInContext(first), 2);
  assert.equal(script.runInContext(first), 4);
  assert.equal(script.runInContext(second), 13);
  assert.deepEqual(
    { first: first.counter, second: second.counter },
    { first: 4, second: 13 },
  );
});

test('Script timeout 中断同步长循环并返回带 code 的错误', () => {
  const script = new Script('while (true) {}');

  assert.throws(
    () => script.runInNewContext({}, { timeout: 10 }),
    (error) => {
      assert.equal(error.code, 'ERR_SCRIPT_EXECUTION_TIMEOUT');
      assert.match(error.message, /timed out/);
      return true;
    },
  );

  // timeout 有运行时开销，只约束同步执行片段，不能代替进程/worker 级资源隔离。
});

test('compileFunction 显式提供参数和 context extensions', () => {
  const multiply = compileFunction('return left * right * factor;', ['left', 'right'], {
    contextExtensions: [{ factor: 10 }],
    filename: 'multiply.vm.js',
  });

  assert.equal(multiply(2, 3), 60);
  assert.equal(multiply.length, 2);
  assert.equal(typeof multiply, 'function');
});

test('contextCodeGeneration 可禁止字符串和 Wasm 动态代码生成', () => {
  const context = createContext({}, {
    codeGeneration: {
      strings: false,
      wasm: false,
    },
  });

  assert.throws(
    () => runInContext('eval("1 + 1")', context),
    (error) => error.name === 'EvalError' && /Code generation/.test(error.message),
  );
  assert.throws(
    () => runInContext('new Function("return 1")', context),
    (error) => error.name === 'EvalError' && /Code generation/.test(error.message),
  );
});

test('cachedData 可复用编译信息，但不包含运行时状态', () => {
  const source = 'globalThis.count = (globalThis.count ?? 0) + 1; count;';
  const compiled = new Script(source, { produceCachedData: true });
  const cachedData = compiled.createCachedData();

  assert.equal(cachedData instanceof Buffer, true);
  assert.ok(cachedData.length > 0);

  const reused = new Script(source, { cachedData });
  assert.equal(reused.cachedDataRejected, false);
  assert.equal(reused.runInNewContext({}), 1);
  assert.equal(reused.runInNewContext({}), 1);
});

test('sandbox 中注入的对象仍可把宿主能力带入 context', () => {
  const secret = { value: 'host secret' };
  const sandbox = {
    readSecret: () => secret.value,
  };

  assert.equal(runInNewContext('readSecret()', sandbox), 'host secret');

  // node:vm 不是安全隔离机制；传入的函数、对象、原型和资源都可能成为越界能力。
  assert.equal(typeof runInNewContext('Object'), 'function');
});

// polyglot-covers:
// - nodejs.core.util-format-format-with-options-and-style-text
// - nodejs.core.util-inspect-and-custom-inspect
// - nodejs.core.util-types-runtime-predicates
// - nodejs.core.util-promisify-and-custom-promisify
// - nodejs.core.util-callbackify
// - nodejs.core.util-parse-args
// - nodejs.core.util-text-encoder-decoder-and-mime

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  MIMEType,
  TextDecoder,
  TextEncoder,
  callbackify,
  format,
  formatWithOptions,
  inspect,
  parseArgs,
  promisify,
  styleText,
  types,
} from 'node:util';

test('format 使用占位符，额外参数按 inspect 风格追加', () => {
  assert.equal(format('%s:%d:%j', 'count', 7, { ok: true }), 'count:7:{"ok":true}');
  assert.equal(format('value=%o', { nested: { id: 1 } }), 'value={ nested: { id: 1 } }');
  assert.equal(format('plain', 1, { ok: true }), 'plain 1 { ok: true }');
  assert.equal(format('100%% ready'), '100%% ready');
  assert.equal(format('100%% ready: %s', 'yes'), '100% ready: yes');

  const compact = formatWithOptions({ colors: false, depth: 0 }, '%O', {
    nested: { id: 1 },
  });
  assert.equal(compact, '{ nested: [Object] }');
});

test('inspect 处理循环引用、深度、排序和 getter 策略', () => {
  const value = { z: 1, a: { nested: true } };
  value.self = value;

  const rendered = inspect(value, {
    colors: false,
    depth: 1,
    sorted: true,
  });
  assert.ok(rendered.includes('<ref *1>'));
  assert.ok(rendered.includes('self: [Circular *1]'));
  assert.ok(rendered.indexOf('a:') < rendered.indexOf('z:'));

  let reads = 0;
  const accessor = {
    get value() {
      reads += 1;
      return 7;
    },
  };
  assert.equal(inspect(accessor), '{ value: [Getter] }');
  assert.equal(reads, 0);
  assert.equal(inspect(accessor, { getters: true }), '{ value: [Getter: 7] }');
  assert.equal(reads, 1);
});

test('util.inspect.custom 为诊断输出提供专用协议', () => {
  class Secret {
    constructor(value) {
      this.value = value;
    }

    [inspect.custom](depth, options, inspectValue) {
      assert.equal(typeof depth, 'number');
      return `Secret(${inspectValue(this.value, options)})`;
    }
  }

  assert.equal(inspect(new Secret({ id: 7 })), 'Secret({ id: 7 })');

  // 自定义 inspect 不影响 JSON、属性枚举或业务序列化，只服务调试和控制台显示。
});

test('util.types 跨 realm 判断内置品牌，比 instanceof 更稳健', async () => {
  const { runInNewContext } = await import('node:vm');
  const foreignMap = runInNewContext('new Map([["key", 1]])');
  const foreignPromise = runInNewContext('Promise.resolve(1)');

  assert.equal(foreignMap instanceof Map, false);
  assert.equal(types.isMap(foreignMap), true);
  assert.equal(types.isPromise(foreignPromise), true);
  assert.equal(types.isTypedArray(new Uint8Array()), true);
  assert.equal(types.isArrayBufferView(new DataView(new ArrayBuffer(1))), true);
  assert.equal(types.isNativeError(new TypeError('invalid')), true);
});

test('promisify 把 error-first callback 的一次完成转换成 Promise', async () => {
  const legacyAdd = (left, right, callback) => {
    queueMicrotask(() => {
      if (!Number.isFinite(left) || !Number.isFinite(right)) {
        callback(new TypeError('finite numbers required'));
        return;
      }
      callback(null, left + right);
    });
  };
  const add = promisify(legacyAdd);

  assert.equal(await add(2, 3), 5);
  await assert.rejects(add(Number.NaN, 1), TypeError);
});

test('promisify.custom 可定义非标准 callback API 的 Promise 形状', async () => {
  const legacy = (callback) => callback(null, 'first', 'second');
  legacy[promisify.custom] = async () => ({ first: 'first', second: 'second' });

  const converted = promisify(legacy);
  assert.equal(converted, legacy[promisify.custom]);
  assert.deepEqual(await converted(), { first: 'first', second: 'second' });
});

test('callbackify 把 async 结果排入 callback，并包装 falsy rejection', async () => {
  const converted = callbackify(async (value) => value * 2);
  const result = await new Promise((resolve, reject) => {
    converted(4, (error, value) => error ? reject(error) : resolve(value));
  });
  assert.equal(result, 8);

  const rejecting = callbackify(async () => Promise.reject(null));
  const error = await new Promise((resolve) => {
    rejecting((actual) => resolve(actual));
  });
  assert.equal(error instanceof Error, true);
  assert.equal(error.reason, null);
});

test('parseArgs 声明选项类型、多值、短名和位置参数', () => {
  const parsed = parseArgs({
    allowPositionals: true,
    args: ['--verbose', '-n', 'Ada', '--tag=one', '--tag', 'two', 'input.txt'],
    options: {
      name: { short: 'n', type: 'string' },
      tag: { multiple: true, type: 'string' },
      verbose: { type: 'boolean' },
    },
  });

  assert.deepEqual({ ...parsed.values }, {
    name: 'Ada',
    tag: ['one', 'two'],
    verbose: true,
  });
  assert.deepEqual(parsed.positionals, ['input.txt']);
});

test('tokens 模式保留解析过程，strict 模式拒绝未知选项', () => {
  const parsed = parseArgs({
    allowPositionals: true,
    args: ['--name=Ada', 'file.txt'],
    options: {
      name: { type: 'string' },
    },
    tokens: true,
  });

  assert.deepEqual(parsed.tokens.map(({ kind }) => kind), ['option', 'positional']);
  assert.equal(parsed.tokens[0].inlineValue, true);
  assert.throws(
    () => parseArgs({ args: ['--unknown'], options: {}, strict: true }),
    (error) => error.code === 'ERR_PARSE_ARGS_UNKNOWN_OPTION',
  );
});

test('TextEncoder/TextDecoder 与 MIMEType 提供 Web 兼容数据模型', () => {
  const encoder = new TextEncoder();
  const bytes = encoder.encode('A中');
  assert.deepEqual([...bytes], [65, 228, 184, 173]);
  assert.equal(new TextDecoder('utf-8', { fatal: true }).decode(bytes), 'A中');
  assert.throws(
    () => new TextDecoder('utf-8', { fatal: true }).decode(Uint8Array.of(0xff)),
    TypeError,
  );

  const mime = new MIMEType('Text/HTML; Charset=UTF-8');
  assert.equal(mime.type, 'text');
  assert.equal(mime.subtype, 'html');
  assert.equal(mime.params.get('charset'), 'UTF-8');
  assert.equal(mime.essence, 'text/html');
});

test('styleText 可按 NO_COLOR 和颜色能力选择 ANSI 样式', () => {
  const styled = styleText('red', 'failure', {
    validateStream: false,
  });
  assert.equal(styled, '\u001b[31mfailure\u001b[39m');
  assert.equal(styleText(['bold', 'blue'], 'info', {
    validateStream: false,
  }), '\u001b[1m\u001b[34minfo\u001b[39m\u001b[22m');
});

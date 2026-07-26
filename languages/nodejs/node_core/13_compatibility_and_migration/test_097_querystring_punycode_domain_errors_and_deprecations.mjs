// polyglot-covers:
// - nodejs.core.querystring-parse-null-prototype-repeated-values-and-pollution-safety
// - nodejs.core.querystring-stringify-supported-values-arrays-and-url-search-params-difference
// - nodejs.core.querystring-custom-separators-max-keys-codecs-and-malformed-escape-fallback
// - nodejs.core.punycode-deprecated-module-label-domain-and-ucs2-operations
// - nodejs.core.punycode-runtime-deprecation-and-url-domain-alternative
// - nodejs.core.domain-active-run-enter-exit-add-remove-and-error-routing
// - nodejs.core.domain-bind-intercept-error-first-callbacks-and-deprecated-status
// - nodejs.core.errors-synchronous-callback-promise-and-error-event-propagation
// - nodejs.core.errors-system-error-code-errno-syscall-path-and-util-mapping
// - nodejs.core.errors-cause-capture-stack-trace-and-code-over-message-contract
// - nodejs.core.util-deprecate-once-result-code-and-warning-event
// - nodejs.core.deprecation-no-trace-throw-and-pending-cli-controls

import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { EventEmitter } from 'node:events';
import { readFile as readFileCallback, readFileSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import querystring from 'node:querystring';
import test from 'node:test';
import {
  getSystemErrorMap,
  getSystemErrorMessage,
  getSystemErrorName,
} from 'node:util';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

async function runNode(argumentsList, source) {
  try {
    const result = await execFileAsync(process.execPath, [
      ...argumentsList,
      '--input-type=module',
      '--eval',
      source,
    ], { encoding: 'utf8' });
    return { code: 0, ...result };
  } catch (error) {
    return {
      code: error.code,
      signal: error.signal,
      stdout: error.stdout,
      stderr: error.stderr,
    };
  }
}

test('querystring.parse 返回无原型对象，并把重复键收集成数组', () => {
  const parsed = querystring.parse(
    'name=Ada%20Lovelace&tag=node&tag=compat&empty=&__proto__=safe',
  );

  assert.equal(Object.getPrototypeOf(parsed), null);
  assert.deepEqual({ ...parsed }, {
    name: 'Ada Lovelace',
    tag: ['node', 'compat'],
    empty: '',
    ['__proto__']: 'safe',
  });
  assert.equal(parsed.toString, undefined);
  assert.equal(Object.prototype.polluted, undefined);
  assert.equal(querystring.decode, querystring.parse);
  // 无原型结果既避免键名撞到 toString，也阻止 __proto__ 经原型 setter
  // 污染对象。
});

test(
  'stringify 展开数组，只可靠序列化标量，并区别 URLSearchParams 空格规则',
  () => {
  const encoded = querystring.stringify({
    name: 'Ada Lovelace',
    tag: ['node', 'compat'],
    count: 2,
    large: 3n,
    enabled: true,
    missing: null,
    nested: { ignored: true },
    infinity: Number.POSITIVE_INFINITY,
  });
  assert.equal(
    encoded,
    'name=Ada%20Lovelace&tag=node&tag=compat&count=2&large=3&enabled=true'
      + '&missing=&nested=&infinity=',
  );
  assert.equal(querystring.encode, querystring.stringify);

  const standard = new URLSearchParams({ name: 'Ada Lovelace' });
  assert.equal(standard.toString(), 'name=Ada+Lovelace');
  assert.equal(querystring.stringify({ name: 'Ada Lovelace' }), 'name=Ada%20Lovelace');
  // querystring 是稳定的 Node 专用格式；浏览器互操作通常优先 URLSearchParams。
  },
);

test(
  'querystring 支持自定义分隔符、键上限和编码器，坏转义不会让解析崩溃',
  () => {
  assert.deepEqual(
    { ...querystring.parse('left:1;right:2;extra:3', ';', ':', { maxKeys: 2 }) },
    { left: '1', right: '2' },
  );
  assert.deepEqual(
    { ...querystring.parse('left=>1|right=>2', '|', '=>') },
    { left: '1', right: '2' },
  );
  assert.equal(querystring.unescape('%E4%B8%AD'), '中');
  assert.equal(querystring.unescape('%E0%A4%A'), '�%A');

  const decoded = querystring.parse('word=ABC', '&', '=', {
    decodeURIComponent: (value) => value.toLowerCase(),
  });
  assert.deepEqual({ ...decoded }, { word: 'abc' });
  const encoded = querystring.stringify({ word: 'abc' }, '&', '=', {
    encodeURIComponent: (value) => value.toUpperCase(),
  });
  assert.equal(encoded, 'WORD=ABC');
    // maxKeys 默认 1000，是解析不可信大输入时的资源上限；0 才表示不限制。
  },
);

test(
  '内置 punycode 展示标签算法，但 URL 域名应使用标准化替代接口',
  async () => {
  const source = `
    import punycode from 'node:punycode';
    import { domainToASCII, domainToUnicode } from 'node:url';
    process.stdout.write(JSON.stringify({
      encodedLabel: punycode.encode('mañana'),
      decodedLabel: punycode.decode('maana-pta'),
      asciiDomain: punycode.toASCII('mañana.com'),
      unicodeDomain: punycode.toUnicode('xn--maana-pta.com'),
      codePoints: punycode.ucs2.decode('A𝌆'),
      reconstructed: punycode.ucs2.encode([0x41, 0x1d306]),
      version: punycode.version,
      standardASCII: domainToASCII('mañana.com'),
      standardUnicode: domainToUnicode('xn--maana-pta.com'),
    }));
  `;
  const result = await runNode([], source);

  assert.equal(result.code, 0);
  assert.deepEqual(JSON.parse(result.stdout), {
    encodedLabel: 'maana-pta',
    decodedLabel: 'mañana',
    asciiDomain: 'xn--maana-pta.com',
    unicodeDomain: 'mañana.com',
    codePoints: [0x41, 0x1d306],
    reconstructed: 'A𝌆',
    version: '2.1.0',
    standardASCII: 'xn--maana-pta.com',
    standardUnicode: 'mañana.com',
  });
  assert.match(result.stderr, /\[DEP0040\]/);
  assert.match(result.stderr, /punycode.*module is deprecated/i);
    // Punycode 编码本身不执行完整 IDNA/WHATWG 主机名校验，不能混为一谈。
  },
);

test(
  'domain 隔离旧式动态作用域，并路由显式加入的 EventEmitter 错误',
  async () => {
  const source = `
    import domain from 'node:domain';
    import { EventEmitter } from 'node:events';
    const scope = domain.create();
    const emitter = new EventEmitter();
    const captured = [];
    scope.on('error', (error) => captured.push(error));
    const before = domain.active ?? null;
    let activeInside;
    scope.run(() => {
      activeInside = domain.active === scope;
      scope.add(emitter);
    });
    const after = domain.active ?? null;
    const wasMember = scope.members.includes(emitter);
    const routed = new Error('routed');
    emitter.emit('error', routed);
    scope.remove(emitter);
    let local;
    emitter.once('error', (error) => { local = error; });
    emitter.emit('error', new Error('local'));
    process.stdout.write(JSON.stringify({
      before,
      activeInside,
      after,
      wasMember,
      isMemberAfterRemove: scope.members.includes(emitter),
      capturedMessage: captured[0].message,
      domainMatches: routed.domain === scope,
      emitterMatches: routed.domainEmitter === emitter,
      domainThrown: routed.domainThrown,
      localMessage: local.message,
    }));
  `;
  const result = await runNode(['--no-deprecation'], source);

  assert.equal(result.code, 0);
  assert.equal(result.stderr, '');
  assert.deepEqual(JSON.parse(result.stdout), {
    before: null,
    activeInside: true,
    after: null,
    wasMember: true,
    isMemberAfterRemove: false,
    capturedMessage: 'routed',
    domainMatches: true,
    emitterMatches: true,
    domainThrown: false,
    localMessage: 'local',
    });
  },
);

test('domain bind/intercept 兼容旧 callback，但模块整体已弃用', async () => {
  const behaviorSource = `
    import domain from 'node:domain';
    const scope = domain.create();
    const captured = [];
    scope.on('error', (error) => captured.push(error));
    const bound = scope.bind((value) => ({
      value,
      active: domain.active === scope,
    }));
    let callbackValues;
    const intercepted = scope.intercept((...values) => { callbackValues = values; });
    const boundResult = bound(4);
    intercepted(null, 'first', 'second');
    const callbackError = new Error('callback failure');
    intercepted(callbackError);
    process.stdout.write(JSON.stringify({
      boundResult,
      callbackValues,
      capturedMessage: captured[0].message,
      domainMatches: callbackError.domain === scope,
    }));
  `;
  const behavior = await runNode(['--no-deprecation'], behaviorSource);
  assert.equal(behavior.code, 0);
  assert.deepEqual(JSON.parse(behavior.stdout), {
    boundResult: { value: 4, active: true },
    callbackValues: ['first', 'second'],
    capturedMessage: 'callback failure',
    domainMatches: true,
  });

  // domain 会隐式捕获远处错误，容易让资源处在未知状态；新代码用显式
  // Promise、try/catch、AbortSignal 与进程级故障退出策略。
  // 文档弃用不保证运行时发警告。
});

test('Node API 按同步、callback、Promise 或 error 事件选择错误通道', async () => {
  const missing = `/tmp/polyglot-nodejs-missing-${process.pid}`;
  assert.throws(() => readFileSync(missing), (error) => error.code === 'ENOENT');

  const callbackError = await new Promise((resolve) => {
    readFileCallback(missing, (error) => resolve(error));
  });
  assert.equal(callbackError.code, 'ENOENT');
  await assert.rejects(readFile(missing), (error) => error.code === 'ENOENT');

  const emitter = new EventEmitter();
  const emitted = new Error('event failure');
  assert.throws(() => emitter.emit('error', emitted), (error) => error === emitted);
  emitter.on('error', () => undefined);
  assert.equal(emitter.emit('error', emitted), true);
  // 调用 API 前就能发现的参数错误常同步抛出，
  // 即使工作结果通常异步返回。
});

test('SystemError 关联 libuv errno、操作名和路径，程序应按 code 分支', async () => {
  const missing = `/tmp/polyglot-nodejs-system-error-${process.pid}`;
  const error = await readFile(missing).catch((reason) => reason);

  assert.ok(error instanceof Error);
  assert.equal(error.code, 'ENOENT');
  assert.equal(typeof error.errno, 'number');
  assert.ok(error.errno < 0);
  assert.equal(error.syscall, 'open');
  assert.equal(error.path, missing);
  assert.equal(getSystemErrorName(error.errno), 'ENOENT');
  assert.match(getSystemErrorMessage(error.errno), /no such file or directory/i);
  assert.deepEqual(getSystemErrorMap().get(error.errno), [
    'ENOENT',
    getSystemErrorMessage(error.errno),
  ]);
  // message 来自平台并可能改写；code 只在 Node 主版本间才可能改变，
  // 是更稳定的分支键。
});

test('Error cause 保留错误链，captureStackTrace 可隐藏构造辅助帧', () => {
  const root = new Error('database unavailable');
  const wrapped = new Error('request failed', { cause: root });
  assert.equal(wrapped.cause, root);
  assert.match(wrapped.stack, /^Error: request failed/);
  assert.equal(wrapped.stack.includes('database unavailable'), false);

  function makeDiagnostic() {
    const diagnostic = { code: 'POLYGLOT_DIAGNOSTIC' };
    Error.captureStackTrace(diagnostic, makeDiagnostic);
    return diagnostic;
  }
  const diagnostic = makeDiagnostic();
  assert.match(diagnostic.stack, /^Error/);
  assert.equal(diagnostic.stack.includes('makeDiagnostic'), false);
  assert.equal(diagnostic.code, 'POLYGLOT_DIAGNOSTIC');
  // cause 不会自动拼入 stack；日志器若要显示整条因果链，必须显式遍历。
});

test('util.deprecate 透传结果且每个包装器只警告一次', async () => {
  const source = `
    import { deprecate } from 'node:util';
    const warnings = [];
    process.on('warning', (warning) => warnings.push({
      name: warning.name,
      code: warning.code,
      message: warning.message,
    }));
    const oldDouble = deprecate((value) => value * 2, 'use doubleV2', 'DEP_POLYGLOT');
    const values = [oldDouble(2), oldDouble(3)];
    setImmediate(() => process.stdout.write(JSON.stringify({ values, warnings })));
  `;
  const result = await runNode([], source);

  assert.equal(result.code, 0);
  assert.deepEqual(JSON.parse(result.stdout), {
    values: [4, 6],
    warnings: [{
      name: 'DeprecationWarning',
      code: 'DEP_POLYGLOT',
      message: 'use doubleV2',
    }],
  });
  assert.match(result.stderr, /\[DEP_POLYGLOT\] DeprecationWarning: use doubleV2/);
});

test('弃用 CLI 开关分别隐藏、追踪或抛出 DeprecationWarning', async () => {
  const source = `
    process.emitWarning('legacy call', {
      type: 'DeprecationWarning',
      code: 'DEP_POLYGLOT_FLAGS',
    });
    process.stdout.write('continued');
  `;
  const hidden = await runNode(['--no-deprecation'], source);
  assert.equal(hidden.code, 0);
  assert.equal(hidden.stdout, 'continued');
  assert.equal(hidden.stderr, '');

  const traced = await runNode(['--trace-deprecation'], source);
  assert.equal(traced.code, 0);
  assert.equal(traced.stdout, 'continued');
  assert.match(traced.stderr, /\[DEP_POLYGLOT_FLAGS\]/);
  assert.match(traced.stderr, /at file:/);

  const thrown = await runNode(['--throw-deprecation'], source);
  assert.equal(thrown.code, 1);
  assert.equal(thrown.stdout, 'continued');
  assert.match(thrown.stderr, /DeprecationWarning: legacy call/);
  assert.match(thrown.stderr, /code: 'DEP_POLYGLOT_FLAGS'/);
  // --pending-deprecation 额外启用“仅待定”的警告；
  // 不会改变已是运行时弃用的 API。
});

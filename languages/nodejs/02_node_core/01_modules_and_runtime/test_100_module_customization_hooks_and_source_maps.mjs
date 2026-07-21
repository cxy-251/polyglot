// polyglot-covers:
// - nodejs.core.module-register-hooks-resolve-load-context-and-next-chain
// - nodejs.core.module-register-hooks-short-circuit-and-virtual-modules
// - nodejs.core.module-register-hooks-source-transform-and-supported-formats
// - nodejs.core.module-register-hooks-commonjs-require-in-thread-behavior
// - nodejs.core.module-register-hooks-lifo-order-and-deregister
// - nodejs.core.module-register-hooks-next-or-short-circuit-contract
// - nodejs.core.module-register-hooks-preload-static-import-and-dynamic-import-order
// - nodejs.core.module-asynchronous-register-deprecated-and-sync-hooks-preferred
// - nodejs.core.module-source-map-payload-find-entry-and-find-origin-indexing
// - nodejs.core.module-source-map-support-options-cache-and-stack-remapping

import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import {
  SourceMap,
  createRequire,
  registerHooks,
} from 'node:module';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

async function runNode(argumentsList, options = {}) {
  try {
    const result = await execFileAsync(process.execPath, argumentsList, {
      encoding: 'utf8',
      ...options,
    });
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

async function createProject() {
  const project = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-module-hooks-'));
  await writeFile(join(project, 'package.json'), '{"type":"module"}');
  return project;
}

test('resolve 与 load 可短路默认链，合成无需落盘的虚拟 ES 模块', async () => {
  const observations = [];
  const registration = registerHooks({
    resolve(specifier, context, nextResolve) {
      if (specifier !== 'lesson:virtual-settings') {
        return nextResolve(specifier, context);
      }
      observations.push({
        hook: 'resolve',
        parentURL: context.parentURL,
        hasNodeCondition: context.conditions.includes('node'),
        attributes: context.importAttributes,
      });
      return {
        url: 'polyglot:virtual-settings',
        shortCircuit: true,
      };
    },
    load(url, context, nextLoad) {
      if (url !== 'polyglot:virtual-settings') {
        return nextLoad(url, context);
      }
      observations.push({
        hook: 'load',
        formatHint: context.format,
        attributes: context.importAttributes,
      });
      return {
        format: 'module',
        source: 'export const settings = Object.freeze({ mode: "study" });',
        shortCircuit: true,
      };
    },
  });

  try {
    const loaded = await import('lesson:virtual-settings');
    assert.deepEqual(loaded.settings, { mode: 'study' });
    assert.equal(observations[0].hook, 'resolve');
    assert.equal(observations[0].parentURL, import.meta.url);
    assert.equal(observations[0].hasNodeCondition, true);
    assert.equal(Object.getPrototypeOf(observations[0].attributes), null);
    assert.deepEqual(Object.keys(observations[0].attributes), []);
    assert.equal(observations[1].hook, 'load');
    assert.equal(observations[1].formatHint, undefined);
    assert.equal(Object.getPrototypeOf(observations[1].attributes), null);
    assert.deepEqual(Object.keys(observations[1].attributes), []);
  } finally {
    registration.deregister();
  }
  // 不调用 nextResolve/nextLoad 时必须显式 shortCircuit，
  // 避免无意截断其他加载器。
});

test('resolve 可实现别名，load 可在默认读取后转换源码', async () => {
  const project = await createProject();
  const target = join(project, 'message.mjs');
  await writeFile(target, 'export const message = "before hook";');
  const targetURL = pathToFileURL(target).href;
  const observations = [];
  const registration = registerHooks({
    resolve(specifier, context, nextResolve) {
      if (specifier === '#lesson-message') {
        observations.push({ parentURL: context.parentURL });
        return nextResolve(targetURL, context);
      }
      return nextResolve(specifier, context);
    },
    load(url, context, nextLoad) {
      const loaded = nextLoad(url, context);
      if (url !== targetURL) {
        return loaded;
      }
      observations.push({
        formatHint: context.format,
        finalFormat: loaded.format,
        sourceKind: loaded.source.constructor.name,
      });
      const source = Buffer.from(loaded.source)
        .toString('utf8')
        .replace('before hook', 'after hook');
      return { ...loaded, source };
    },
  });

  try {
    const loaded = await import('#lesson-message');
    assert.equal(loaded.message, 'after hook');
    assert.equal(observations[0].parentURL, import.meta.url);
    assert.deepEqual(observations[1], {
      formatHint: 'module',
      finalFormat: 'module',
      sourceKind: 'Buffer',
    });
  } finally {
    registration.deregister();
    await rm(project, { recursive: true, force: true });
  }
  // 转译钩子适合开发和测试；生产构建通常应预编译，
  // 避免每次加载都做同步转换。
});

test('同步钩子也覆盖 CommonJS require，并保留完整 CommonJS API', async () => {
  const project = await createProject();
  const target = join(project, 'lesson.cjs');
  await writeFile(target, `
    module.exports = {
      value: 'original',
      hasCache: Boolean(require.cache),
      canResolve: typeof require.resolve === 'function',
    };
  `);
  const targetURL = pathToFileURL(target).href;
  const registration = registerHooks({
    resolve(specifier, context, nextResolve) {
      if (specifier === 'lesson-commonjs') {
        return { url: targetURL, shortCircuit: true };
      }
      return nextResolve(specifier, context);
    },
    load(url, context, nextLoad) {
      const loaded = nextLoad(url, context);
      if (url !== targetURL) {
        return loaded;
      }
      assert.equal(loaded.format, 'commonjs');
      assert.notEqual(loaded.source, null);
      const source = Buffer.from(loaded.source)
        .toString('utf8')
        .replace("value: 'original'", "value: 'customized'");
      return { ...loaded, source };
    },
  });

  try {
    const require = createRequire(import.meta.url);
    assert.deepEqual(require('lesson-commonjs'), {
      value: 'customized',
      hasCache: true,
      canResolve: true,
    });
  } finally {
    registration.deregister();
    await rm(project, { recursive: true, force: true });
  }
  // 单独加载线程上的旧异步钩子有 CJS 限制；
  // 同线程同步钩子没有这些缺口。
});

test(
  '多组同步钩子按后注册先调用嵌套，deregister 只移除对应一层',
  async () => {
  const project = await createProject();
  const targets = [];
  for (const name of ['first.mjs', 'second.mjs', 'third.mjs']) {
    const path = join(project, name);
    await writeFile(path, `export default ${JSON.stringify(name)};`);
    targets.push(pathToFileURL(path).href);
  }
  const events = [];
  function hook(label) {
    return {
      resolve(specifier, context, nextResolve) {
        if (!targets.includes(specifier)) {
          return nextResolve(specifier, context);
        }
        events.push(`${label}:resolve:before`);
        const result = nextResolve(specifier, context);
        events.push(`${label}:resolve:after`);
        return result;
      },
      load(url, context, nextLoad) {
        if (!targets.includes(url)) {
          return nextLoad(url, context);
        }
        events.push(`${label}:load:before`);
        const result = nextLoad(url, context);
        events.push(`${label}:load:after`);
        return result;
      },
    };
  }

  const older = registerHooks(hook('older'));
  const newer = registerHooks(hook('newer'));
  try {
    assert.equal((await import(targets[0])).default, 'first.mjs');
    assert.deepEqual(events, [
      'newer:resolve:before',
      'older:resolve:before',
      'older:resolve:after',
      'newer:resolve:after',
      'newer:load:before',
      'older:load:before',
      'older:load:after',
      'newer:load:after',
    ]);

    events.length = 0;
    newer.deregister();
    assert.equal((await import(targets[1])).default, 'second.mjs');
    assert.deepEqual(events, [
      'older:resolve:before',
      'older:resolve:after',
      'older:load:before',
      'older:load:after',
    ]);

    events.length = 0;
    older.deregister();
    assert.equal((await import(targets[2])).default, 'third.mjs');
    assert.deepEqual(events, []);
  } finally {
    newer.deregister();
    older.deregister();
    await rm(project, { recursive: true, force: true });
    }
  },
);

test('钩子既不继续调用也不声明短路时，Node 会拒绝无效返回值', async () => {
  const registration = registerHooks({
    resolve(specifier, context, nextResolve) {
      if (specifier === 'lesson:incomplete') {
        return { url: 'polyglot:incomplete' };
      }
      return nextResolve(specifier, context);
    },
  });
  try {
    await assert.rejects(
      import('lesson:incomplete'),
      (error) => {
        assert.equal(error.code, 'ERR_INVALID_RETURN_PROPERTY_VALUE');
        assert.match(error.message, /Expected true.*"shortCircuit".*got undefined/);
        return true;
      },
    );
  } finally {
    registration.deregister();
  }
});

test(
  '--import 在入口依赖图前注册钩子；入口内注册则必须动态 import',
  async () => {
  const project = await createProject();
  const targetURL = pathToFileURL(join(project, 'target.mjs')).href;
  await writeFile(join(project, 'target.mjs'), 'export const value = 42;');
  await writeFile(join(project, 'register.mjs'), `
    import { registerHooks } from 'node:module';
    registerHooks({
      resolve(specifier, context, nextResolve) {
        if (specifier === 'lesson-preloaded') {
          return { url: ${JSON.stringify(targetURL)}, shortCircuit: true };
        }
        return nextResolve(specifier, context);
      },
    });
  `);
  await writeFile(join(project, 'static-entry.mjs'), `
    import { value } from 'lesson-preloaded';
    process.stdout.write(String(value));
  `);
  await writeFile(join(project, 'dynamic-entry.mjs'), `
    import './register.mjs';
    const { value } = await import('lesson-preloaded');
    process.stdout.write(String(value));
  `);
  await writeFile(join(project, 'too-late-entry.mjs'), `
    import './register.mjs';
    import { value } from 'lesson-preloaded';
    process.stdout.write(String(value));
  `);

  try {
    const preloaded = await runNode([
      '--import',
      join(project, 'register.mjs'),
      join(project, 'static-entry.mjs'),
    ]);
    assert.equal(preloaded.code, 0);
    assert.equal(preloaded.stdout, '42');

    const dynamic = await runNode([join(project, 'dynamic-entry.mjs')]);
    assert.equal(dynamic.code, 0);
    assert.equal(dynamic.stdout, '42');

    const tooLate = await runNode([join(project, 'too-late-entry.mjs')]);
    assert.equal(tooLate.code, 1);
    assert.match(tooLate.stderr, /ERR_MODULE_NOT_FOUND/);
  } finally {
    await rm(project, { recursive: true, force: true });
  }
    // 静态 import 在模块主体运行前解析，
    // 因此写在 registerHooks 调用“后面”也仍然太早。
  },
);

test(
  '旧 module.register 已弃用，新代码应优先使用同线程 registerHooks',
  async () => {
  const result = await runNode([
    '--input-type=module',
    '--eval',
    `
      import { register, registerHooks } from 'node:module';
      process.stdout.write(JSON.stringify({
        registerType: typeof register,
        registerHooksType: typeof registerHooks,
      }));
    `,
  ]);
  assert.equal(result.code, 0);
  assert.deepEqual(JSON.parse(result.stdout), {
    registerType: 'function',
    registerHooksType: 'function',
  });
    // register 的弃用是文档级状态，不保证每次引用都发出警告；
    // 不要用“没有警告”判断稳定性。
  },
);

test('SourceMap 区分零基偏移与调用栈的一基行列', () => {
  const payload = {
    version: 3,
    file: 'compiled.js',
    sourceRoot: 'file:///project/src/',
    sources: ['lesson.ts'],
    sourcesContent: ['const answer: number = 42;'],
    names: ['answer'],
    mappings: 'AAAAA',
  };
  const sourceMap = new SourceMap(payload, { lineLengths: [18] });

  assert.deepEqual(sourceMap.payload, payload);
  const entry = {
    generatedLine: 0,
    generatedColumn: 0,
    originalSource: 'lesson.ts',
    originalLine: 0,
    originalColumn: 0,
    name: 'answer',
  };
  assert.deepEqual(sourceMap.findEntry(0, 0), entry);
  assert.deepEqual(sourceMap.findEntry(0, 17), entry);
  assert.deepEqual(sourceMap.findOrigin(1, 1), {
    name: 'answer',
    fileName: 'lesson.ts',
    lineNumber: 1,
    columnNumber: 1,
  });
  // 查询的是包含给定位置的映射范围，不要求位置恰好落在 VLQ 段起点。
});

test(
  '启用 source map 后只缓存随后加载的模块，并把错误栈映射回源文件',
  async () => {
  const project = await createProject();
  const compiled = join(project, 'compiled.mjs');
  const sourceMapPath = join(project, 'compiled.mjs.map');
  await writeFile(sourceMapPath, JSON.stringify({
    version: 3,
    file: 'compiled.mjs',
    sourceRoot: '',
    sources: ['original.ts'],
    sourcesContent: ['throw new Error("mapped failure");'],
    names: [],
    mappings: 'AAAA',
  }));
  await writeFile(compiled, `
throw new Error('mapped failure');
//# sourceMappingURL=compiled.mjs.map
  `.trimStart());

  const script = `
    import {
      findSourceMap,
      getSourceMapsSupport,
      setSourceMapsSupport,
    } from 'node:module';
    import { pathToFileURL } from 'node:url';
    const before = getSourceMapsSupport();
    setSourceMapsSupport(true, { nodeModules: false, generatedCode: true });
    const enabled = getSourceMapsSupport();
    let stack;
    try {
      await import(pathToFileURL(${JSON.stringify(compiled)}));
    } catch (error) {
      stack = error.stack;
    }
    const cached = findSourceMap(${JSON.stringify(compiled)});
    process.stdout.write(JSON.stringify({
      before,
      enabled,
      cached: cached?.payload.sources,
      stack,
    }));
  `;
  try {
    const result = await runNode(['--input-type=module', '--eval', script]);
    assert.equal(result.code, 0);
    const output = JSON.parse(result.stdout);
    assert.deepEqual(output.before, {
      enabled: false,
      nodeModules: false,
      generatedCode: false,
    });
    assert.deepEqual(output.enabled, {
      enabled: true,
      nodeModules: false,
      generatedCode: true,
    });
    assert.deepEqual(output.cached, [pathToFileURL(join(project, 'original.ts')).href]);
    assert.match(output.stack, /original\.ts:1:1/);
  } finally {
    await rm(project, { recursive: true, force: true });
  }
    // setSourceMapsSupport 不会追溯已经加载的模块；
    // 入口尽早用 CLI 开关更不易漏缓存。
  },
);

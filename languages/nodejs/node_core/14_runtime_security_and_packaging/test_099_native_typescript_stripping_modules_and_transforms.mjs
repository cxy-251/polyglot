// polyglot-covers:
// - nodejs.core.typescript-default-stable-type-stripping-erasable-syntax-and-no-checking
// - nodejs.core.typescript-no-strip-types-cli-disable
// - nodejs.core.typescript-ts-package-type-mts-cts-and-tsx-module-determination
// - nodejs.core.typescript-explicit-ts-extension-and-extensionless-import-failure
// - nodejs.core.typescript-import-type-inline-type-import-and-runtime-import-trap
// - nodejs.core.typescript-non-erasable-enum-namespace-parameter-property-and-import-alias
// - nodejs.core.typescript-experimental-transform-types-and-source-map-behavior
// - nodejs.core.typescript-tsconfig-ignored-path-alias-and-package-import-alternative
// - nodejs.core.typescript-node-modules-stripping-refusal
// - nodejs.core.typescript-eval-check-and-non-file-input-limits
// - nodejs.core.module-strip-typescript-types-strip-transform-source-url-and-map
// - nodejs.core.typescript-whitespace-preserves-lines-but-output-is-not-stable-api

import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
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

async function createProject(prefix = 'polyglot-nodejs-typescript-') {
  return mkdtemp(join(tmpdir(), prefix));
}

test('默认剥离可擦除类型语法，但不会执行 TypeScript 类型检查', async () => {
  const project = await createProject();
  const entry = join(project, 'erasable.ts');
  await writeFile(join(project, 'package.json'), '{"type":"module"}');
  await writeFile(entry, `
    type UserId = number;
    interface User { id: UserId; name: string }
    type Box<T> = { value: T };
    namespace TypeOnly { export type Label = string }

    function identity<T>(value: T): T { return value; }
    const user: User = { id: 7, name: 'Ada' };
    const box = { value: user } satisfies Box<User>;
    const unchecked: number = 'runtime string' as never;
    const label: TypeOnly.Label = identity<string>('ready');
    process.stdout.write(JSON.stringify({ box, unchecked, label }));
  `);
  try {
    const result = await runNode([entry]);
    assert.equal(result.code, 0);
    assert.equal(result.stderr, '');
    assert.deepEqual(JSON.parse(result.stdout), {
      box: { value: { id: 7, name: 'Ada' } },
      unchecked: 'runtime string',
      label: 'ready',
    });

    const disabled = await runNode(['--no-strip-types', entry]);
    assert.equal(disabled.code, 1);
    assert.match(disabled.stderr, /ERR_UNKNOWN_FILE_EXTENSION/);
    assert.match(disabled.stderr, /Unknown file extension "\.ts"/);
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  // 内置支持只删类型，不读取 tsconfig、不调用类型检查器，
  // 也不会替应用降级 JS 语法。
});

test('.ts 跟随 package type，.mts/.cts 固定模块系统，.tsx 不受支持', async () => {
  const project = await createProject();
  const moduleTS = join(project, 'module.ts');
  const moduleMTS = join(project, 'always-module.mts');
  const commonCTS = join(project, 'always-common.cts');
  const unsupportedTSX = join(project, 'component.tsx');
  await writeFile(join(project, 'package.json'), '{"type":"module"}');
  await writeFile(moduleTS, `
    const value: number = 1;
    process.stdout.write(JSON.stringify({
      format: 'esm-ts',
      hasImportMeta: typeof import.meta.url === 'string',
      value,
    }));
  `);
  await writeFile(moduleMTS, `
    const value: number = 2;
    process.stdout.write(JSON.stringify({ format: 'esm-mts', value }));
  `);
  await writeFile(commonCTS, `
    const value: number = 3;
    process.stdout.write(JSON.stringify({
      format: 'commonjs-cts',
      hasRequire: typeof require === 'function',
      value,
    }));
  `);
  await writeFile(unsupportedTSX, 'const view: string = <div />;');
  try {
    assert.deepEqual(JSON.parse((await runNode([moduleTS])).stdout), {
      format: 'esm-ts',
      hasImportMeta: true,
      value: 1,
    });
    assert.deepEqual(JSON.parse((await runNode([moduleMTS])).stdout), {
      format: 'esm-mts',
      value: 2,
    });
    assert.deepEqual(JSON.parse((await runNode([commonCTS])).stdout), {
      format: 'commonjs-cts',
      hasRequire: true,
      value: 3,
    });

    const tsx = await runNode([unsupportedTSX]);
    assert.equal(tsx.code, 1);
    assert.match(tsx.stderr, /ERR_UNKNOWN_FILE_EXTENSION/);
    assert.match(tsx.stderr, /\.tsx/);
  } finally {
    await rm(project, { recursive: true, force: true });
  }
});

test('TypeScript 相对导入必须写 .ts 扩展名，Node 不替换成猜测路径', async () => {
  const project = await createProject();
  await writeFile(join(project, 'package.json'), '{"type":"module"}');
  await writeFile(join(project, 'value.ts'), 'export const value: number = 42;');
  const explicit = join(project, 'explicit.ts');
  const extensionless = join(project, 'extensionless.ts');
  await writeFile(explicit, `
    import { value } from './value.ts';
    process.stdout.write(String(value));
  `);
  await writeFile(extensionless, `
    import { value } from './value';
    process.stdout.write(String(value));
  `);
  try {
    const success = await runNode([explicit]);
    assert.equal(success.code, 0);
    assert.equal(success.stdout, '42');

    const failure = await runNode([extensionless]);
    assert.equal(failure.code, 1);
    assert.match(failure.stderr, /ERR_MODULE_NOT_FOUND/);
    assert.match(failure.stderr, /Cannot find module/);
  } finally {
    await rm(project, { recursive: true, force: true });
  }
});

test('type import 必须显式标记，否则剥离后仍会作为运行时导入', async () => {
  const project = await createProject();
  await writeFile(join(project, 'package.json'), '{"type":"module"}');
  await writeFile(join(project, 'library.ts'), `
    export interface User { name: string }
    export type GreetingOptions = { punctuation: string };
    export function greet(user: User, options: GreetingOptions): string {
      return 'Hello ' + user.name + options.punctuation;
    }
  `);
  const good = join(project, 'good.ts');
  const bad = join(project, 'bad.ts');
  await writeFile(good, `
    import type { User } from './library.ts';
    import { greet, type GreetingOptions } from './library.ts';
    const user: User = { name: 'Ada' };
    const options: GreetingOptions = { punctuation: '!' };
    process.stdout.write(greet(user, options));
  `);
  await writeFile(bad, `
    import { User } from './library.ts';
    const user: User = { name: 'Ada' };
    process.stdout.write(user.name);
  `);
  try {
    const success = await runNode([good]);
    assert.equal(success.code, 0);
    assert.equal(success.stdout, 'Hello Ada!');

    const failure = await runNode([bad]);
    assert.equal(failure.code, 1);
    assert.match(failure.stderr, /does not provide an export named 'User'/);
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  // 建议开启 verbatimModuleSyntax，让 tsc 与 Node 对 type import 的保留规则一致。
});

test(
  '需要生成 JavaScript 的 TS 语法默认报错，transform-types 才会转换',
  async () => {
  const project = await createProject();
  const entry = join(project, 'transform.cts');
  await writeFile(entry, `
    import path = require('node:path');
    enum Direction { Up = 1, Down }
    namespace Runtime { export const value = 7; }
    class Point {
      constructor(public x: number, readonly y: number) {}
    }
    const point = new Point(2, 3);
    process.stdout.write(JSON.stringify({
      direction: Direction.Down,
      runtime: Runtime.value,
      point,
      basename: path.basename('/tmp/demo.txt'),
    }));
  `);
  try {
    const defaultRun = await runNode([entry]);
    assert.equal(defaultRun.code, 1);
    assert.match(defaultRun.stderr, /ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX/);
    assert.match(
      defaultRun.stderr,
      /TypeScript import equals declaration is not supported in strip-only mode/,
    );

    const transformed = await runNode(['--experimental-transform-types', entry]);
    assert.equal(transformed.code, 0);
    assert.deepEqual(JSON.parse(transformed.stdout), {
      direction: 2,
      runtime: 7,
      point: { x: 2, y: 3 },
      basename: 'demo.txt',
    });
    assert.match(transformed.stderr, /Transform Types is an experimental feature/);
  } finally {
    await rm(project, { recursive: true, force: true });
  }
    // enum、带值 namespace、参数属性与 import = 都需要生成运行时代码，
    // 不能只擦空格。
  },
);

test('Node 忽略 tsconfig paths；package imports 是可执行的运行时替代', async () => {
  const project = await createProject();
  await mkdir(join(project, 'src'));
  await writeFile(join(project, 'package.json'), JSON.stringify({
    type: 'module',
    imports: {
      '#runtime-value': './src/value.ts',
    },
  }));
  await writeFile(join(project, 'tsconfig.json'), JSON.stringify({
    compilerOptions: {
      baseUrl: '.',
      paths: {
        '@source/*': ['./src/*'],
      },
    },
  }));
  await writeFile(join(project, 'src/value.ts'), 'export const value: number = 9;');
  const alias = join(project, 'alias.ts');
  const packageImport = join(project, 'package-import.ts');
  await writeFile(alias, `
    import { value } from '@source/value';
    process.stdout.write(String(value));
  `);
  await writeFile(packageImport, `
    import { value } from '#runtime-value';
    process.stdout.write(String(value));
  `);
  try {
    const ignored = await runNode([alias]);
    assert.equal(ignored.code, 1);
    assert.match(ignored.stderr, /ERR_MODULE_NOT_FOUND/);
    assert.match(ignored.stderr, /Cannot find package '@source\/value'/);

    const supported = await runNode([packageImport]);
    assert.equal(supported.code, 0);
    assert.equal(supported.stdout, '9');
  } finally {
    await rm(project, { recursive: true, force: true });
  }
});

test(
  'Node 拒绝剥离 node_modules 内的 TypeScript，包作者应发布 JavaScript',
  async () => {
  const project = await createProject();
  const dependency = join(project, 'node_modules', 'typed-dependency');
  await mkdir(dependency, { recursive: true });
  await writeFile(join(project, 'package.json'), '{"type":"module"}');
  await writeFile(join(dependency, 'package.json'), JSON.stringify({
    name: 'typed-dependency',
    type: 'module',
    exports: './index.ts',
  }));
  await writeFile(join(dependency, 'index.ts'), 'export const value: number = 1;');
  const entry = join(project, 'main.ts');
  await writeFile(entry, `
    import { value } from 'typed-dependency';
    process.stdout.write(String(value));
  `);
  try {
    const result = await runNode([entry]);
    assert.equal(result.code, 1);
    assert.match(result.stderr, /ERR_UNSUPPORTED_NODE_MODULES_TYPE_STRIPPING/);
    assert.match(result.stderr, /node_modules.*index\.ts/);
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  },
);

test('--eval 可剥离类型，--check 则不支持 TypeScript 文件', async () => {
  const plainModule = await runNode([
    '--input-type=module',
    '--eval',
    'const value: number = 6;',
  ]);
  assert.equal(plainModule.code, 1);
  assert.match(plainModule.stderr, /SyntaxError/);

  const evaluated = await runNode([
    '--input-type=module-typescript',
    '--eval',
    `const value: number = 6;
     function double<T extends number>(input: T): number { return input * 2; }
     process.stdout.write(String(double(value)));`,
  ]);
  assert.equal(evaluated.code, 0);
  assert.equal(evaluated.stdout, '12');

  const project = await createProject();
  const entry = join(project, 'check.ts');
  await writeFile(entry, 'const value: number = 1;');
  try {
    const checked = await runNode(['--check', entry]);
    assert.equal(checked.code, 1);
    assert.match(checked.stderr, /SyntaxError: Missing initializer in const declaration/);
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  // REPL 与 inspect 同样不做类型剥离；需要交互调试时应先产出 JavaScript。
});

test(
  'stripTypeScriptTypes 提供可嵌入的 strip/transform，但输出文本不稳定',
  async () => {
  const source = `
    import { stripTypeScriptTypes } from 'node:module';
    const erasable = 'const value: number = 1;\\nfunction id<T>(x: T): T { return x; }';
    const stripped = stripTypeScriptTypes(erasable, {
      mode: 'strip',
      sourceUrl: 'lesson.ts',
    });
    let stripMapError;
    try {
      stripTypeScriptTypes(erasable, { mode: 'strip', sourceMap: true });
    } catch (error) {
      stripMapError = { name: error.name, code: error.code };
    }
    const transformed = stripTypeScriptTypes(
      'enum State { Ready = 1, Done }',
      { mode: 'transform', sourceMap: true, sourceUrl: 'state.ts' },
    );
    process.stdout.write(JSON.stringify({
      stripped,
      stripMapError,
      transformed,
    }));
  `;
  const result = await runNode([
    '--input-type=module',
    '--eval',
    source,
  ]);

  assert.equal(result.code, 0);
  const output = JSON.parse(result.stdout);
  assert.equal(output.stripped.split('\n').length, 4);
  assert.match(output.stripped, /const value\s+= 1/);
  assert.match(output.stripped, /function id\s+\(x\s+\)\s+\{ return x; \}/);
  assert.match(output.stripped, /\/\/# sourceURL=lesson\.ts/);
  assert.deepEqual(output.stripMapError, {
    name: 'TypeError',
    code: 'ERR_INVALID_ARG_VALUE',
  });
  assert.match(output.transformed, /State\[State\["Ready"\] = 1\] = "Ready"/);
  assert.match(output.transformed, /sourceMappingURL=data:application\/json;base64/);
  assert.match(result.stderr, /stripTypeScriptTypes is an experimental feature/);
    // 只能依赖执行语义，不要 snapshot 完整输出；
    // Node 升级 TypeScript parser 后排版可变。
  },
);

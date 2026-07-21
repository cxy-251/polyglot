// polyglot-covers:
// - nodejs.core.permission-model-flag-runtime-api-scopes-and-default-deny
// - nodejs.core.permission-has-scope-reference-unknown-scope-and-invalid-type
// - nodejs.core.permission-fs-read-denial-error-and-file-grant
// - nodejs.core.permission-fs-write-directory-grant-and-ungranted-path-denial
// - nodejs.core.permission-existing-directory-implied-wildcard-and-explicit-future-wildcard
// - nodejs.core.permission-symbolic-link-resolution-limit-and-seat-belt-threat-model
// - nodejs.core.permission-child-process-denial-grant-and-inherited-node-options
// - nodejs.core.permission-worker-denial-grant-inherited-restrictions-and-security-warning
// - nodejs.core.permission-addons-wasi-and-inspector-restrictions
// - nodejs.core.permission-error-code-permission-resource-and-not-a-security-boundary

import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import {
  mkdir,
  mkdtemp,
  readFile,
  rm,
  symlink,
  writeFile,
} from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
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

test(
  'process.permission 只在 --permission 下出现，所有受控能力默认拒绝',
  async () => {
  assert.equal(process.permission, undefined);
  const result = await runNode(['--permission'], `
    const scopes = ['fs.read', 'fs.write', 'child', 'worker', 'addons', 'wasi', 'inspector'];
    process.stdout.write(JSON.stringify({
      present: typeof process.permission?.has === 'function',
      grants: Object.fromEntries(scopes.map((scope) => [
        scope,
        process.permission.has(scope),
      ])),
    }));
  `);

  assert.equal(result.code, 0);
  assert.deepEqual(JSON.parse(result.stdout), {
    present: true,
    grants: {
      'fs.read': false,
      'fs.write': false,
      child: false,
      worker: false,
      addons: false,
      wasi: false,
      inspector: false,
    },
  });
    assert.equal(result.stderr, '');
  },
);

test(
  '文件读取拒绝提供结构化错误，单文件 grant 可由 has 精确查询',
  async () => {
  const directory = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-permission-read-'));
  const allowed = join(directory, 'allowed.txt');
  const denied = join(directory, 'denied.txt');
  await writeFile(allowed, 'allowed content');
  await writeFile(denied, 'denied content');
  try {
    const source = `
      import { readFileSync } from 'node:fs';
      const shape = (error) => ({
        name: error.name,
        code: error.code,
        permission: error.permission,
        resource: error.resource,
      });
      const results = {
        hasAll: process.permission.has('fs.read'),
        hasAllowed: process.permission.has('fs.read', ${JSON.stringify(allowed)}),
        hasDenied: process.permission.has('fs.read', ${JSON.stringify(denied)}),
      };
      try { results.allowed = readFileSync(${JSON.stringify(allowed)}, 'utf8'); }
      catch (error) { results.allowedError = shape(error); }
      try { results.denied = readFileSync(${JSON.stringify(denied)}, 'utf8'); }
      catch (error) { results.deniedError = shape(error); }
      process.stdout.write(JSON.stringify(results));
    `;
    const result = await runNode([
      '--permission',
      `--allow-fs-read=${allowed}`,
    ], source);

    assert.equal(result.code, 0);
    assert.deepEqual(JSON.parse(result.stdout), {
      hasAll: false,
      hasAllowed: true,
      hasDenied: false,
      allowed: 'allowed content',
      deniedError: {
        name: 'Error',
        code: 'ERR_ACCESS_DENIED',
        permission: 'FileSystemRead',
        resource: denied,
      },
    });
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
  },
);

test('已有目录 grant 自动覆盖后代，但读写权限仍彼此独立', async () => {
  const root = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-permission-write-'));
  const allowedDirectory = join(root, 'allowed');
  const deniedDirectory = join(root, 'denied');
  await mkdir(allowedDirectory);
  await mkdir(deniedDirectory);
  const allowedFile = join(allowedDirectory, 'nested.txt');
  const deniedFile = join(deniedDirectory, 'blocked.txt');
  try {
    const result = await runNode([
      '--permission',
      `--allow-fs-write=${allowedDirectory}`,
    ], `
      import { writeFileSync } from 'node:fs';
      const output = {
        writeAll: process.permission.has('fs.write'),
        writeAllowed: process.permission.has(
          'fs.write',
          ${JSON.stringify(allowedFile)},
        ),
        readAllowed: process.permission.has(
          'fs.read',
          ${JSON.stringify(allowedFile)},
        ),
      };
      writeFileSync(${JSON.stringify(allowedFile)}, 'created');
      try { writeFileSync(${JSON.stringify(deniedFile)}, 'blocked'); }
      catch (error) {
        output.denied = {
          code: error.code,
          permission: error.permission,
          resource: error.resource,
        };
      }
      process.stdout.write(JSON.stringify(output));
    `);

    assert.equal(result.code, 0);
    assert.deepEqual(JSON.parse(result.stdout), {
      writeAll: false,
      writeAllowed: true,
      readAllowed: false,
      denied: {
        code: 'ERR_ACCESS_DENIED',
        permission: 'FileSystemWrite',
        resource: deniedFile,
      },
    });
    assert.equal(await readFile(allowedFile, 'utf8'), 'created');
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test('尚不存在的目录需要显式 *，否则 grant 只覆盖那个路径本身', async () => {
  const root = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-permission-future-'));
  const future = join(root, 'future');
  const nested = join(future, 'nested.txt');
  try {
    const exact = await runNode([
      '--permission',
      `--allow-fs-write=${future}`,
    ], `
      process.stdout.write(JSON.stringify({
        directory: process.permission.has('fs.write', ${JSON.stringify(future)}),
        nested: process.permission.has('fs.write', ${JSON.stringify(nested)}),
      }));
    `);
    assert.deepEqual(JSON.parse(exact.stdout), {
      directory: true,
      nested: false,
    });

    const wildcard = await runNode([
      '--permission',
      `--allow-fs-write=${future}/*`,
    ], `
      process.stdout.write(JSON.stringify({
        directory: process.permission.has('fs.write', ${JSON.stringify(future)}),
        nested: process.permission.has('fs.write', ${JSON.stringify(nested)}),
      }));
    `);
    assert.deepEqual(JSON.parse(wildcard.stdout), {
      directory: true,
      nested: true,
    });
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test(
  '允许目录中的相对符号链接可越界读取，说明模型只是 seat belt',
  async () => {
  const root = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-permission-link-'));
  const allowedDirectory = join(root, 'allowed');
  const secret = join(root, 'secret.txt');
  const link = join(allowedDirectory, 'link.txt');
  await mkdir(allowedDirectory);
  await writeFile(secret, 'outside grant');
  await symlink('../secret.txt', link);
  try {
    const result = await runNode([
      '--permission',
      `--allow-fs-read=${allowedDirectory}`,
    ], `
      import { readFileSync } from 'node:fs';
      process.stdout.write(JSON.stringify({
        hasLink: process.permission.has('fs.read', ${JSON.stringify(link)}),
        hasSecret: process.permission.has('fs.read', ${JSON.stringify(secret)}),
        value: readFileSync(${JSON.stringify(link)}, 'utf8'),
      }));
    `);
    assert.equal(result.code, 0);
    assert.deepEqual(JSON.parse(result.stdout), {
      hasLink: true,
      hasSecret: false,
      value: 'outside grant',
    });
  } finally {
    await rm(root, { recursive: true, force: true });
  }
    // Permission Model 明确不抵御恶意代码；隔离不可信代码仍要依赖容器、
    // OS 用户和 syscall/文件系统边界，而不是把 --permission 当安全沙箱。
  },
);

test('child_process 默认被拒绝，grant 后子 Node 继承 permission 选项', async () => {
  const denied = await runNode(['--permission'], `
    import { spawnSync } from 'node:child_process';
    try { spawnSync(process.execPath, ['--version']); }
    catch (error) {
      process.stdout.write(JSON.stringify({
        code: error.code,
        permission: error.permission,
        resource: error.resource,
      }));
    }
  `);
  assert.equal(denied.code, 0);
  assert.deepEqual(JSON.parse(denied.stdout), {
    code: 'ERR_ACCESS_DENIED',
    permission: 'ChildProcess',
    resource: process.execPath,
  });

  const allowed = await runNode([
    '--permission',
    '--allow-child-process',
  ], `
    import { spawnSync } from 'node:child_process';
    const child = spawnSync(process.execPath, [
      '--input-type=module',
      '--eval',
      'process.stdout.write(JSON.stringify({'
        + 'present: typeof process.permission?.has === "function",'
        + 'fsRead: process.permission?.has("fs.read"),'
        + 'child: process.permission?.has("child")'
        + '}))',
    ], { encoding: 'utf8' });
    process.stdout.write(JSON.stringify({
      hasChild: process.permission.has('child'),
      status: child.status,
      childPermission: child.stdout,
    }));
  `);
  assert.equal(allowed.code, 0);
  assert.deepEqual(JSON.parse(allowed.stdout), {
    hasChild: true,
    status: 0,
    childPermission: JSON.stringify({
      present: true,
      fsRead: false,
      child: true,
    }),
  });
});

test('Worker 默认被拒绝；allow-worker 后线程仍受同一文件限制', async () => {
  const root = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-permission-worker-'));
  const secret = join(root, 'worker-secret.txt');
  await writeFile(secret, 'worker can read');
  try {
    const denied = await runNode(['--permission'], `
      import { Worker } from 'node:worker_threads';
      try { new Worker('', { eval: true }); }
      catch (error) {
        process.stdout.write(JSON.stringify({
          code: error.code,
          permission: error.permission,
        }));
      }
    `);
    assert.deepEqual(JSON.parse(denied.stdout), {
      code: 'ERR_ACCESS_DENIED',
      permission: 'WorkerThreads',
    });

    const allowed = await runNode([
      '--permission',
      '--allow-worker',
    ], `
      import { once } from 'node:events';
      import { Worker } from 'node:worker_threads';
      const worker = new Worker(\`
        import { readFileSync } from 'node:fs';
        import { parentPort } from 'node:worker_threads';
        const message = {
          permission: typeof process.permission,
          hasRead: process.permission.has(
            'fs.read',
            ${JSON.stringify(secret)},
          ),
        };
        try { message.value = readFileSync(${JSON.stringify(secret)}, 'utf8'); }
        catch (error) {
          message.error = {
            code: error.code,
            permission: error.permission,
            resource: error.resource,
          };
        }
        parentPort.postMessage(message);
      \`, { eval: true });
      const exited = once(worker, 'exit');
      const [message] = await once(worker, 'message');
      await exited;
      process.stdout.write(JSON.stringify({
        hasWorker: process.permission.has('worker'),
        message,
      }));
    `);
    assert.equal(allowed.code, 0, allowed.stderr);
    assert.deepEqual(JSON.parse(allowed.stdout), {
      hasWorker: true,
      message: {
        permission: 'object',
        hasRead: false,
        error: {
          code: 'ERR_ACCESS_DENIED',
          permission: 'FileSystemRead',
          resource: secret,
        },
      },
    });
    assert.match(allowed.stderr, /--allow-worker must be used with extreme caution/);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test('addons、WASI 与本进程 inspector 各有独立权限门', async () => {
  const result = await runNode(['--permission'], `
    import inspector from 'node:inspector';
    import { WASI } from 'node:wasi';
    const shape = (error) => ({
      code: error.code,
      permission: error.permission,
      resource: error.resource,
    });
    const output = {};
    try { process.dlopen({ exports: {} }, '/tmp/polyglot-missing-addon.node'); }
    catch (error) { output.addon = shape(error); }
    try { new WASI({ version: 'preview1' }); }
    catch (error) { output.wasi = shape(error); }
    try { inspector.open(0, '127.0.0.1', false); }
    catch (error) { output.inspector = shape(error); }
    output.has = Object.fromEntries([
      'addons',
      'wasi',
      'inspector',
    ].map((scope) => [scope, process.permission.has(scope)]));
    process.stdout.write(JSON.stringify(output));
  `);

  assert.equal(result.code, 0);
  const output = JSON.parse(result.stdout);
  assert.deepEqual(output.has, {
    addons: false,
    wasi: false,
    inspector: false,
  });
  assert.equal(output.addon.code, 'ERR_DLOPEN_DISABLED');
  assert.equal(output.wasi.code, 'ERR_ACCESS_DENIED');
  assert.equal(output.wasi.permission, 'WASI');
  assert.equal(output.inspector.code, 'ERR_ACCESS_DENIED');
  assert.equal(output.inspector.permission, 'Inspector');
  assert.match(result.stderr, /WASI is an experimental feature/);
  // dlopen 使用专门的禁用错误；即使路径可读，仍必须再提供 --allow-addons。
});

test('permission.has 对未知 scope 返回 false，并拒绝非字符串 scope', async () => {
  const result = await runNode(['--permission'], `
    const output = { unknown: process.permission.has('network') };
    try { process.permission.has(42); }
    catch (error) {
      output.invalid = {
        name: error.name,
        code: error.code,
        message: error.message,
      };
    }
    process.stdout.write(JSON.stringify(output));
  `);
  assert.equal(result.code, 0);
  const output = JSON.parse(result.stdout);
  assert.equal(output.unknown, false);
  assert.equal(output.invalid.name, 'TypeError');
  assert.equal(output.invalid.code, 'ERR_INVALID_ARG_TYPE');
  assert.match(output.invalid.message, /scope/);
  // 网络本身不在 Node 24 Permission Model 的可配置范围内；这也是它不能替代
  // 网络 namespace、防火墙或容器策略的另一原因。
});

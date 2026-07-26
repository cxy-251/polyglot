// polyglot-covers:
// - nodejs.core.os-platform-arch-machine-type-release-and-version
// - nodejs.core.os-endianness-eol-tmpdir-and-dev-null
// - nodejs.core.os-available-parallelism-and-cpu-descriptors
// - nodejs.core.os-total-free-memory-and-load-average
// - nodejs.core.os-uptime
// - nodejs.core.os-network-interfaces
// - nodejs.core.os-tmpdir-environment-precedence
// - nodejs.core.os-process-priority
// - nodejs.core.os-signal-error-priority-and-dlopen-constants

import assert from 'node:assert/strict';
import test from 'node:test';

import os from 'node:os';
import { isAbsolute } from 'node:path';

test('OS 身份 API 与 process 平台信息一致，但 machine 比 arch 更贴近内核名称', () => {
  assert.equal(os.platform(), process.platform);
  assert.equal(os.arch(), process.arch);
  assert.equal(typeof os.machine(), 'string');
  assert.ok(os.machine().length > 0);
  assert.equal(typeof os.type(), 'string');
  assert.equal(typeof os.release(), 'string');
  assert.equal(typeof os.version(), 'string');

  assert.ok(['BE', 'LE'].includes(os.endianness()));
  assert.equal(os.EOL, process.platform === 'win32' ? '\r\n' : '\n');
  assert.equal(isAbsolute(os.tmpdir()), true);
  assert.equal(os.devNull, process.platform === 'win32' ? '\\\\.\\nul' : '/dev/null');
});

test('availableParallelism 是调度并行度提示，不应用 cpus().length 替代', () => {
  const parallelism = os.availableParallelism();
  const cpus = os.cpus();

  assert.ok(Number.isInteger(parallelism) && parallelism > 0);
  assert.ok(cpus.length > 0);
  for (const cpu of cpus) {
    assert.equal(typeof cpu.model, 'string');
    assert.ok(cpu.speed >= 0);
    assert.ok(cpu.times.user >= 0);
    assert.ok(cpu.times.sys >= 0);
    assert.ok(cpu.times.idle >= 0);
  }
  // 容器 CPU 配额和亲和性可能让 parallelism 小于宿主逻辑 CPU 数。
});

test('内存、负载和 uptime 是瞬时系统指标，只验证单位与不变量', () => {
  const total = os.totalmem();
  const free = os.freemem();
  const load = os.loadavg();

  assert.ok(total > 0);
  assert.ok(free >= 0);
  assert.ok(load.length === 3 && load.every((value) => value >= 0));
  assert.ok(os.uptime() >= 0);
  // 不锁定具体数值：它们随容器限制、系统负载和采样时刻变化。
});

test('networkInterfaces 返回按接口分组的地址，loopback 不依赖外部网络', () => {
  const interfaces = os.networkInterfaces();
  const addresses = Object.values(interfaces).flatMap((items) => items ?? []);

  assert.ok(addresses.length > 0);
  assert.ok(addresses.some((item) => item.internal));
  for (const item of addresses) {
    assert.ok(['IPv4', 'IPv6'].includes(item.family));
    assert.equal(typeof item.address, 'string');
    assert.equal(typeof item.netmask, 'string');
    assert.equal(typeof item.internal, 'boolean');
    assert.ok(item.cidr === null || item.cidr.includes('/'));
  }
});

test('tmpdir 按平台环境变量选择临时根，并规范化结尾分隔符', () => {
  const names = ['TMPDIR', 'TMP', 'TEMP'];
  const previous = Object.fromEntries(names.map((name) => [name, process.env[name]]));
  try {
    process.env.TMPDIR = '/tmp/polyglot-custom-temp/';
    process.env.TMP = '/tmp/lower-priority';
    process.env.TEMP = '/tmp/lowest-priority';
    assert.equal(os.tmpdir(), '/tmp/polyglot-custom-temp');

    delete process.env.TMPDIR;
    assert.equal(os.tmpdir(), '/tmp/lower-priority');
  } finally {
    for (const name of names) {
      if (previous[name] === undefined) delete process.env[name];
      else process.env[name] = previous[name];
    }
  }
  // 路径只用于展示选择规则，不访问该目录，也不依赖真实用户目录。
});

test('getPriority 查询当前调度优先级；常量提供跨平台的命名边界', () => {
  const priority = os.getPriority();
  assert.ok(Number.isInteger(priority));
  assert.ok(priority >= os.constants.priority.PRIORITY_HIGHEST);
  assert.ok(priority <= os.constants.priority.PRIORITY_LOW);

  assert.equal(typeof os.constants.signals.SIGTERM, 'number');
  assert.equal(typeof os.constants.errno.EACCES, 'number');
  assert.equal(typeof os.constants.dlopen.RTLD_NOW, 'number');
  assert.throws(
    () => os.getPriority(2 ** 31 - 1),
    (error) => error.code === 'ERR_SYSTEM_ERROR' && error.info.code === 'ESRCH',
  );
  // setPriority 会改变真实进程调度状态，本学习案例只读，不污染测试容器。
});

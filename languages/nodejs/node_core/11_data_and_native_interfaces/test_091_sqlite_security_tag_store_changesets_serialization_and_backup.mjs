// polyglot-covers:
// - nodejs.core.sqlite-authorizer-action-arguments-deny-ignore-and-clear
// - nodejs.core.sqlite-extension-loading-opt-in-and-runtime-disable
// - nodejs.core.sqlite-defensive-mode-writable-schema-protection
// - nodejs.core.sqlite-runtime-limits-read-set-enforce-and-reset
// - nodejs.core.sqlite-sql-tag-store-safe-binding-run-get-all-and-iterate
// - nodejs.core.sqlite-sql-tag-store-lru-capacity-size-database-and-clear
// - nodejs.core.sqlite-session-changeset-patchset-table-filter-close-and-dispose
// - nodejs.core.sqlite-apply-changeset-filter-conflict-abort-omit-and-replace
// - nodejs.core.sqlite-serialize-deserialize-clone-and-statement-finalization
// - nodejs.core.sqlite-file-location-url-read-only-and-lock-timeout-options
// - nodejs.core.sqlite-backup-progress-overwrite-and-readable-result
// - nodejs.core.sqlite-conflict-and-authorization-constants

import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { pathToFileURL } from 'node:url';

import { backup, constants, DatabaseSync } from 'node:sqlite';

function plain(row) {
  return row === undefined ? undefined : { ...row };
}

function createSchema(database) {
  database.exec(`
    CREATE TABLE items(id INTEGER PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE audit(id INTEGER PRIMARY KEY, message TEXT NOT NULL);
  `);
}

test('authorizer 可审计并拒绝 SQL 操作，返回 IGNORE 时读取列变成 NULL', () => {
  using database = new DatabaseSync(':memory:');
  database.exec(`
    CREATE TABLE secrets(id INTEGER PRIMARY KEY, public TEXT, private TEXT);
    INSERT INTO secrets VALUES (1, 'visible', 'hidden');
  `);
  const observed = [];
  database.setAuthorizer((action, arg1, arg2, dbName, triggerOrView) => {
    observed.push({ action, arg1, arg2, dbName, triggerOrView });
    if (action === constants.SQLITE_DROP_TABLE) return constants.SQLITE_DENY;
    if (
      action === constants.SQLITE_READ
      && arg1 === 'secrets'
      && arg2 === 'private'
    ) {
      return constants.SQLITE_IGNORE;
    }
    return constants.SQLITE_OK;
  });

  assert.deepEqual(
    plain(database.prepare('SELECT public, private FROM secrets').get()),
    { public: 'visible', private: null },
  );
  assert.ok(observed.some(({ action }) => action === constants.SQLITE_SELECT));
  assert.ok(observed.some(({ dbName }) => dbName === 'main'));
  assert.throws(() => database.exec('DROP TABLE secrets'), /not authorized/i);

  database.setAuthorizer(null);
  assert.equal(database.prepare('SELECT private FROM secrets').get().private, 'hidden');
  database.exec('DROP TABLE secrets');
});

test('扩展加载必须在构造时选择，运行时只能在既有安全上限内切换', () => {
  using locked = new DatabaseSync(':memory:');
  assert.throws(
    () => locked.enableLoadExtension(true),
    /disabled at database creation|not allowed/i,
  );
  assert.throws(() => locked.loadExtension('/tmp/does-not-exist.so'), /extension loading/i);

  using optedIn = new DatabaseSync(':memory:', { allowExtension: true });
  optedIn.enableLoadExtension(false);
  assert.throws(() => optedIn.loadExtension('/tmp/does-not-exist.so'), /extension loading/i);
  optedIn.enableLoadExtension(true);
  assert.throws(() => optedIn.loadExtension('/tmp/does-not-exist.so'), /does-not-exist|open/i);
  // 不能把构造时的 false 升级为 true，避免业务代码在运行中扩大原生代码加载权限。
});

test('defensive 默认阻止 writable_schema，显式关闭后才允许危险兼容能力', () => {
  using database = new DatabaseSync(':memory:');
  database.exec('PRAGMA writable_schema = ON');
  assert.equal(database.prepare('PRAGMA writable_schema').get().writable_schema, 0);

  database.enableDefensive(false);
  database.exec('PRAGMA writable_schema = ON');
  assert.equal(database.prepare('PRAGMA writable_schema').get().writable_schema, 1);
  database.exec('PRAGMA writable_schema = OFF');
  database.enableDefensive(true);
  // writable_schema 可绕开普通一致性检查；这里仅在内存库观察开关，不修改系统表。
});

test('limits 暴露运行时资源上限，可收紧并用 Infinity 恢复编译期最大值', () => {
  using database = new DatabaseSync(':memory:');
  const names = [
    'length',
    'sqlLength',
    'column',
    'exprDepth',
    'compoundSelect',
    'vdbeOp',
    'functionArg',
    'attach',
    'likePatternLength',
    'variableNumber',
    'triggerDepth',
  ];
  assert.ok(names.every((name) => Number.isInteger(database.limits[name])));
  const original = database.limits.sqlLength;
  database.limits.sqlLength = 40;
  assert.equal(database.limits.sqlLength, 40);
  assert.throws(
    () => database.prepare(`SELECT '${'x'.repeat(80)}'`),
    /string or blob too big|SQLITE_TOOBIG/i,
  );
  database.limits.sqlLength = Infinity;
  assert.equal(database.limits.sqlLength, original);
});

test('SQLTagStore 把模板插值绑定为参数，并缓存 run/get/all/iterate 的语句', () => {
  using database = new DatabaseSync(':memory:');
  database.exec('CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT)');
  const sql = database.createTagStore(8);
  const insert = (id, name) => sql.run`
    INSERT INTO users(id, name) VALUES (${id}, ${name})
  `;
  insert(1, 'Ada');
  insert(2, "Grace'); DROP TABLE users; --");
  assert.equal(sql.size, 1);

  const id = 2;
  assert.deepEqual(plain(sql.get`SELECT * FROM users WHERE id = ${id}`), {
    id: 2,
    name: "Grace'); DROP TABLE users; --",
  });
  assert.deepEqual(sql.all`SELECT * FROM users ORDER BY id`.map(plain), [
    { id: 1, name: 'Ada' },
    { id: 2, name: "Grace'); DROP TABLE users; --" },
  ]);
  const iterator = sql.iterate`SELECT name FROM users ORDER BY id`;
  assert.deepEqual([...iterator].map(plain), [{ name: 'Ada' }, {
    name: "Grace'); DROP TABLE users; --",
  }]);
  // ${value} 是绑定位置，不是普通模板字符串插值，因此内容无法闭合 SQL 后追加语句。
});

test('SQLTagStore 是有容量的 LRU，并公开所属数据库和可控清空入口', () => {
  using database = new DatabaseSync(':memory:');
  const sql = database.createTagStore(2);
  assert.equal(sql.capacity, 2);
  assert.equal(sql.size, 0);
  assert.equal(sql.db, database);

  sql.get`SELECT 1 AS value`;
  sql.get`SELECT 2 AS value`;
  assert.equal(sql.size, 2);
  sql.get`SELECT 3 AS value`;
  assert.equal(sql.size, 2);
  sql.clear();
  assert.equal(sql.size, 0);
  // 容量限制的是编译后的 statement 数量；淘汰不影响已经返回的普通行值。
});

test('session 为指定表生成 changeset/patchset，并支持显式与幂等资源释放', () => {
  using source = new DatabaseSync(':memory:');
  using changesTarget = new DatabaseSync(':memory:');
  using patchTarget = new DatabaseSync(':memory:');
  for (const database of [source, changesTarget, patchTarget]) createSchema(database);

  const session = source.createSession({ table: 'items' });
  source.exec(`
    INSERT INTO items VALUES (1, 'first');
    INSERT INTO items VALUES (2, 'second');
    INSERT INTO audit VALUES (1, 'not tracked');
  `);
  const changeset = session.changeset();
  const patchset = session.patchset();
  assert.ok(changeset instanceof Uint8Array && changeset.byteLength > 0);
  assert.ok(patchset instanceof Uint8Array && patchset.byteLength > 0);
  assert.equal(changesTarget.applyChangeset(changeset), true);
  assert.equal(patchTarget.applyChangeset(patchset), true);
  assert.equal(changesTarget.prepare('SELECT count(*) AS n FROM items').get().n, 2);
  assert.equal(changesTarget.prepare('SELECT count(*) AS n FROM audit').get().n, 0);
  assert.equal(patchTarget.prepare('SELECT count(*) AS n FROM items').get().n, 2);

  session.close();
  assert.throws(() => session.changeset(), /session is not open/i);
  session[Symbol.dispose]();
});

test('applyChangeset 可按表过滤，并对主键冲突选择 abort、omit 或 replace', () => {
  using source = new DatabaseSync(':memory:');
  createSchema(source);
  const session = source.createSession();
  source.exec(`
    INSERT INTO items VALUES (1, 'from-source');
    INSERT INTO audit VALUES (1, 'source-audit');
  `);
  const changeset = session.changeset();

  using aborted = new DatabaseSync(':memory:');
  createSchema(aborted);
  aborted.exec("INSERT INTO items VALUES (1, 'target-value')");
  assert.equal(aborted.applyChangeset(changeset), false);
  assert.equal(aborted.prepare('SELECT value FROM items').get().value, 'target-value');
  assert.equal(aborted.prepare('SELECT count(*) AS n FROM audit').get().n, 0);

  using omitted = new DatabaseSync(':memory:');
  createSchema(omitted);
  omitted.exec("INSERT INTO items VALUES (1, 'target-value')");
  const omitConflicts = [];
  assert.equal(omitted.applyChangeset(changeset, {
    filter: (table) => table === 'items',
    onConflict: (conflict) => {
      omitConflicts.push(conflict);
      return constants.SQLITE_CHANGESET_OMIT;
    },
  }), true);
  assert.deepEqual(omitConflicts, [constants.SQLITE_CHANGESET_CONFLICT]);
  assert.equal(omitted.prepare('SELECT value FROM items').get().value, 'target-value');
  assert.equal(omitted.prepare('SELECT count(*) AS n FROM audit').get().n, 0);

  using replaced = new DatabaseSync(':memory:');
  createSchema(replaced);
  replaced.exec("INSERT INTO items VALUES (1, 'target-value')");
  assert.equal(replaced.applyChangeset(changeset, {
    filter: (table) => table === 'items',
    onConflict: () => constants.SQLITE_CHANGESET_REPLACE,
  }), true);
  assert.equal(replaced.prepare('SELECT value FROM items').get().value, 'from-source');
});

test('serialize/deserialize 克隆内存库，并使替换前编译的 statement 失效', () => {
  using source = new DatabaseSync(':memory:');
  source.exec(`
    CREATE TABLE data(id INTEGER PRIMARY KEY, value TEXT);
    INSERT INTO data VALUES (1, 'serialized');
  `);
  const image = source.serialize();
  assert.ok(image instanceof Uint8Array);
  assert.ok(image.byteLength > 0);

  using target = new DatabaseSync(':memory:');
  const oldStatement = target.prepare('SELECT 1 AS old_value');
  target.deserialize(image);
  assert.deepEqual(plain(target.prepare('SELECT * FROM data').get()), {
    id: 1,
    value: 'serialized',
  });
  target.prepare("INSERT INTO data VALUES (2, 'writable clone')").run();
  assert.equal(target.prepare('SELECT count(*) AS n FROM data').get().n, 2);
  assert.throws(() => oldStatement.get(), /statement is not prepared|finalized/i);

  const current = target.prepare('SELECT count(*) AS n FROM data');
  target.deserialize(new Uint8Array([1, 2, 3]));
  assert.throws(() => current.get(), /statement is not prepared|finalized/i);
  assert.throws(
    () => target.prepare('PRAGMA schema_version').get(),
    /not a database|malformed/i,
  );
  // deserialize 先接管字节，SQLite 可能到首次读取才验证格式；旧 statements 已 finalized。
});

test('文件库报告真实位置，URL 路径和只读连接不会隐式创建或修改文件', () => {
  const directory = mkdtempSync(join(tmpdir(), 'polyglot-nodejs-sqlite-file-'));
  const path = join(directory, 'database.sqlite');
  const url = pathToFileURL(path);
  try {
    using writable = new DatabaseSync(url, { timeout: 100 });
    writable.exec("CREATE TABLE data(value TEXT); INSERT INTO data VALUES ('stored')");
    assert.equal(writable.location(), path);
    writable.close();

    using readonly = new DatabaseSync(url, { readOnly: true });
    assert.equal(readonly.prepare('SELECT value FROM data').get().value, 'stored');
    assert.throws(
      () => readonly.exec("INSERT INTO data VALUES ('blocked')"),
      /readonly database/i,
    );
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test('backup 异步复制到 URL 文件、报告页进度并覆盖既有目标', async () => {
  const directory = mkdtempSync(join(tmpdir(), 'polyglot-nodejs-sqlite-backup-'));
  const targetPath = join(directory, 'backup.sqlite');
  try {
    using source = new DatabaseSync(':memory:');
    source.exec('CREATE TABLE data(id INTEGER PRIMARY KEY, payload TEXT)');
    const insert = source.prepare('INSERT INTO data(payload) VALUES (?)');
    for (let index = 0; index < 50; index += 1) {
      insert.run(`row-${index}-${'x'.repeat(100)}`);
    }
    const progress = [];
    const pages = await backup(source, pathToFileURL(targetPath), {
      rate: 1,
      progress: (state) => progress.push({ ...state }),
    });
    assert.ok(Number.isInteger(pages) && pages > 0);
    assert.ok(progress.length >= 1);
    assert.ok(progress.every(({ remainingPages, totalPages }) => (
      remainingPages >= 0 && totalPages >= remainingPages
    )));

    using restored = new DatabaseSync(targetPath, { readOnly: true });
    assert.equal(restored.prepare('SELECT count(*) AS n FROM data').get().n, 50);

    source.exec("INSERT INTO data(payload) VALUES ('after-first-backup')");
    await backup(source, targetPath);
    using overwritten = new DatabaseSync(targetPath, { readOnly: true });
    assert.equal(overwritten.prepare('SELECT count(*) AS n FROM data').get().n, 51);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

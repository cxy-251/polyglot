// polyglot-covers:
// - nodejs.core.sqlite-database-sync-memory-open-close-is-open-location-and-dispose
// - nodejs.core.sqlite-database-exec-multiple-statements-and-transaction-state
// - nodejs.core.sqlite-database-default-foreign-keys-and-double-quoted-string-safety
// - nodejs.core.sqlite-javascript-null-number-bigint-string-and-blob-conversions
// - nodejs.core.sqlite-statement-run-changes-last-insert-rowid-and-expanded-sql
// - nodejs.core.sqlite-statement-get-all-iterate-source-sql-and-columns-metadata
// - nodejs.core.sqlite-statement-read-bigints-and-safe-integer-overflow
// - nodejs.core.sqlite-statement-return-arrays-option-and-runtime-toggle
// - nodejs.core.sqlite-named-anonymous-bare-ambiguous-and-unknown-parameters
// - nodejs.core.sqlite-prepared-parameters-prevent-sql-injection
// - nodejs.core.sqlite-user-defined-scalar-function-options-and-bigint-arguments
// - nodejs.core.sqlite-user-defined-aggregate-and-window-inverse

import assert from 'node:assert/strict';
import test from 'node:test';

import { DatabaseSync } from 'node:sqlite';

function plain(row) {
  return row === undefined ? undefined : { ...row };
}

test('DatabaseSync 可延迟打开内存库，并显式反映连接与事务状态', () => {
  const database = new DatabaseSync(':memory:', { open: false });
  assert.equal(database.isOpen, false);
  assert.throws(() => database.prepare('SELECT 1'), /database is not open/i);

  database.open();
  assert.equal(database.isOpen, true);
  assert.equal(database.location(), null);
  assert.equal(database.isTransaction, false);

  database.exec(`
    CREATE TABLE notes(id INTEGER PRIMARY KEY, body TEXT);
    BEGIN;
    INSERT INTO notes(body) VALUES ('temporary');
  `);
  assert.equal(database.isTransaction, true);
  database.exec('ROLLBACK');
  assert.equal(database.isTransaction, false);
  assert.equal(database.prepare('SELECT count(*) AS count FROM notes').get().count, 0);

  database.close();
  assert.equal(database.isOpen, false);
  assert.throws(() => database.close(), /database is not open/i);
  database[Symbol.dispose]();
  // close() 对重复关闭报错，dispose 则是幂等清理入口，适合 using/Explicit Resource Management。
});

test('默认启用外键并拒绝双引号字符串，兼容开关必须有明确理由', () => {
  using database = new DatabaseSync(':memory:');
  database.exec(`
    CREATE TABLE parent(id INTEGER PRIMARY KEY);
    CREATE TABLE child(parent_id INTEGER REFERENCES parent(id));
  `);
  assert.throws(
    () => database.exec('INSERT INTO child VALUES (999)'),
    /FOREIGN KEY constraint failed/,
  );
  assert.throws(() => database.prepare('SELECT "text"').get(), /no such column/);

  using legacy = new DatabaseSync(':memory:', {
    enableForeignKeyConstraints: false,
    enableDoubleQuotedStringLiterals: true,
  });
  legacy.exec(`
    CREATE TABLE parent(id INTEGER PRIMARY KEY);
    CREATE TABLE child(parent_id INTEGER REFERENCES parent(id));
    INSERT INTO child VALUES (999);
  `);
  assert.equal(legacy.prepare('SELECT "legacy text" AS value').get().value, 'legacy text');
});

test('绑定和读取在 SQLite 五种存储类与受支持的 JavaScript 类型间转换', () => {
  using database = new DatabaseSync(':memory:');
  database.exec(`
    CREATE TABLE values_table(
      null_value ANY,
      integer_value INTEGER,
      real_value REAL,
      text_value TEXT,
      blob_value BLOB
    ) STRICT;
  `);
  const insert = database.prepare(`
    INSERT INTO values_table VALUES (?, ?, ?, ?, ?)
  `);
  const bytes = new Uint8Array([0, 127, 255]);
  const result = insert.run(null, 42, 1.25, '中文', bytes);
  assert.equal(result.changes, 1);
  assert.equal(result.lastInsertRowid, 1);

  const row = database.prepare('SELECT * FROM values_table').get();
  assert.equal(row.null_value, null);
  assert.equal(row.integer_value, 42);
  assert.equal(row.real_value, 1.25);
  assert.equal(row.text_value, '中文');
  assert.ok(row.blob_value instanceof Uint8Array);
  assert.deepEqual([...row.blob_value], [0, 127, 255]);
  assert.throws(
    () => insert.run(null, true, 1, 'bad', bytes),
    /cannot be bound to SQLite parameter/i,
  );
  // BLOB 返回 Uint8Array；不要依赖传入的 Buffer/TypedArray 子类品牌被保留。
});

test('StatementSync 的 run/get/all/iterate 共享编译结果但返回语义不同', () => {
  using database = new DatabaseSync(':memory:');
  database.exec('CREATE TABLE tasks(id INTEGER PRIMARY KEY, title TEXT, done INTEGER)');
  const insert = database.prepare(
    'INSERT INTO tasks(title, done) VALUES (?, ?)',
  );
  assert.equal(insert.sourceSQL, 'INSERT INTO tasks(title, done) VALUES (?, ?)');
  insert.run('first', 0);
  assert.match(insert.expandedSQL, /VALUES \('first', 0(?:\.0)?\)/);
  insert.run('second', 1);
  insert.run('third', 0);

  const query = database.prepare(`
    SELECT id, title, done AS completed
    FROM tasks
    WHERE done = ?
    ORDER BY id
  `);
  assert.deepEqual(plain(query.get(0)), { id: 1, title: 'first', completed: 0 });
  assert.deepEqual(query.all(1).map(plain), [
    { id: 2, title: 'second', completed: 1 },
  ]);

  const iterator = query.iterate(0);
  const first = iterator.next();
  assert.deepEqual(plain(first.value), { id: 1, title: 'first', completed: 0 });
  assert.equal(first.done, false);
  iterator.return();
  assert.deepEqual(query.all(0).map(plain), [
    { id: 1, title: 'first', completed: 0 },
    { id: 3, title: 'third', completed: 0 },
  ]);
  // 提前结束 iterate 会 reset statement；否则同一 statement 仍在执行，不能安全复用。
});

test('columns 描述结果列来源，returnArrays 则让列顺序成为显式契约', () => {
  using database = new DatabaseSync(':memory:');
  database.exec('CREATE TABLE inventory(id INTEGER, label TEXT)');
  database.exec("INSERT INTO inventory VALUES (7, 'pen')");
  const statement = database.prepare(
    'SELECT id AS item_id, label, id + 1 AS next_id FROM inventory',
  );

  const columns = statement.columns();
  assert.deepEqual(columns.map(({ name }) => name), ['item_id', 'label', 'next_id']);
  assert.equal(columns[0].column, 'id');
  assert.equal(columns[0].table, 'inventory');
  assert.equal(columns[2].column, null);
  assert.equal(columns[2].table, null);

  statement.setReturnArrays(true);
  assert.deepEqual(statement.get(), [7, 'pen', 8]);
  statement.setReturnArrays(false);
  assert.deepEqual(plain(statement.get()), { item_id: 7, label: 'pen', next_id: 8 });

  using arrayDatabase = new DatabaseSync(':memory:', { returnArrays: true });
  assert.deepEqual(arrayDatabase.prepare('SELECT 1 AS one, 2 AS two').get(), [1, 2]);
});

test('超出安全整数的 SQLite INTEGER 必须显式选择 BigInt 读取', () => {
  using database = new DatabaseSync(':memory:');
  const large = 9_007_199_254_740_993n;
  const statement = database.prepare('SELECT ? AS value');

  assert.throws(() => statement.get(large), {
    code: 'ERR_OUT_OF_RANGE',
  });
  statement.setReadBigInts(true);
  assert.equal(statement.get(large).value, large);
  statement.setReadBigInts(false);
  assert.equal(statement.get(42n).value, 42);

  using bigintDatabase = new DatabaseSync(':memory:', { readBigInts: true });
  assert.equal(bigintDatabase.prepare('SELECT 7 AS value').get().value, 7n);
  // 写入始终接受 bigint；开关只控制从 SQLite INTEGER 返回到 JavaScript 的类型。
});

test('命名参数支持前缀和便捷裸名，但歧义、未知名与 SQL 占位符仍受约束', () => {
  using database = new DatabaseSync(':memory:');
  const named = database.prepare('SELECT $left + :right AS total');
  assert.equal(named.get({ left: 2, right: 3 }).total, 5);
  assert.equal(named.get({ $left: 4, ':right': 5 }).total, 9);
  assert.throws(() => named.get({ left: 1, right: 2, extra: 3 }), /unknown named parameter/i);

  named.setAllowUnknownNamedParameters(true);
  assert.equal(named.get({ left: 1, right: 2, extra: 3 }).total, 3);
  named.setAllowBareNamedParameters(false);
  named.setAllowUnknownNamedParameters(false);
  assert.throws(() => named.get({ left: 1, right: 2 }), /unknown named parameter/i);
  assert.equal(named.get({ $left: 1, ':right': 2 }).total, 3);

  const ambiguous = database.prepare('SELECT $value, @value');
  assert.throws(() => ambiguous.get({ value: 1 }), /conflicting names|ambiguous/i);
  assert.deepEqual(plain(ambiguous.get({ $value: 1, '@value': 2 })), {
    $value: 1,
    '@value': 2,
  });
});

test('参数绑定把数据与 SQL 结构分离，恶意样式文本不会变成第二条语句', () => {
  using database = new DatabaseSync(':memory:');
  database.exec('CREATE TABLE users(name TEXT)');
  const suspicious = "Ada'); DROP TABLE users; --";
  database.prepare('INSERT INTO users(name) VALUES (?)').run(suspicious);

  assert.equal(database.prepare('SELECT count(*) AS count FROM users').get().count, 1);
  assert.equal(database.prepare('SELECT name FROM users').get().name, suspicious);
  // 表名、列名等 SQL 标识符不能作为值参数绑定，应由代码白名单选择而非拼接用户输入。
});

test('function 注册标量函数，并用 varargs、BigInt 和 directOnly 描述调用边界', () => {
  using database = new DatabaseSync(':memory:');
  database.function('join_js', { deterministic: true, varargs: true }, (...values) => {
    return values.join('|');
  });
  database.function(
    'add_big_js',
    { deterministic: true, useBigIntArguments: true },
    (left, right) => left + right,
  );
  database.function('direct_js', { directOnly: true }, (value) => `direct:${value}`);

  assert.equal(database.prepare("SELECT join_js('a', 2, 'c') AS value").get().value, 'a|2|c');
  const big = database.prepare('SELECT add_big_js(?, ?) AS value', { readBigInts: true });
  assert.equal(big.get(10n, 20n).value, 30n);
  assert.equal(database.prepare("SELECT direct_js('ok') AS value").get().value, 'direct:ok');

  database.exec("CREATE VIEW indirect AS SELECT direct_js('blocked') AS value");
  assert.throws(
    () => database.prepare('SELECT * FROM indirect').get(),
    /unsafe use of direct_js/i,
  );
});

test('aggregate 的 step 累积整组，inverse 让同一逻辑可用于滑动窗口', () => {
  using database = new DatabaseSync(':memory:');
  database.exec(`
    CREATE TABLE readings(id INTEGER PRIMARY KEY, value INTEGER);
    INSERT INTO readings(value) VALUES (4), (5), (3), (8);
  `);
  database.aggregate('sum_js', {
    start: 0,
    step: (total, value) => total + value,
  });
  database.aggregate('moving_sum_js', {
    start: () => 0,
    step: (total, value) => total + value,
    inverse: (total, value) => total - value,
    result: (total) => total,
  });

  assert.equal(database.prepare('SELECT sum_js(value) AS total FROM readings').get().total, 20);
  const moving = database.prepare(`
    SELECT id,
           moving_sum_js(value) OVER (
             ORDER BY id ROWS BETWEEN 1 PRECEDING AND CURRENT ROW
           ) AS total
    FROM readings
    ORDER BY id
  `).all();
  assert.deepEqual(moving.map(plain), [
    { id: 1, total: 4 },
    { id: 2, total: 9 },
    { id: 3, total: 8 },
    { id: 4, total: 11 },
  ]);
});

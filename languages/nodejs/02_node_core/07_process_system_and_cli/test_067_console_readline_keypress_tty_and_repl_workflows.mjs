// polyglot-covers:
// - nodejs.core.console-custom-stdout-stderr-and-formatting
// - nodejs.core.console-group-count-assert-trace-and-table
// - nodejs.core.readline-interface-line-events-and-async-iteration
// - nodejs.core.readline-promises-question
// - nodejs.core.readline-question-abort-signal
// - nodejs.core.readline-terminal-control-functions
// - nodejs.core.readline-emit-keypress-events
// - nodejs.core.tty-isatty
// - nodejs.core.repl-custom-streams-context-and-last-result

import assert from 'node:assert/strict';
import test from 'node:test';

import { Console } from 'node:console';
import { once } from 'node:events';
import { PassThrough, Readable, Writable } from 'node:stream';
import readline, {
  clearLine,
  clearScreenDown,
  cursorTo,
  emitKeypressEvents,
  moveCursor,
} from 'node:readline';
import * as readlinePromises from 'node:readline/promises';
import repl from 'node:repl';
import tty from 'node:tty';

class CaptureStream extends Writable {
  constructor() {
    super();
    this.chunks = [];
  }

  _write(chunk, encoding, callback) {
    this.chunks.push(Buffer.from(chunk));
    callback();
  }

  text() {
    return Buffer.concat(this.chunks).toString();
  }
}

test('Console 把普通日志与错误流分开，并复用 util.format 占位规则', () => {
  const stdout = new CaptureStream();
  const stderr = new CaptureStream();
  const console = new Console({
    stdout,
    stderr,
    colorMode: false,
    groupIndentation: 2,
  });

  console.log('value=%d json=%j', 42, { ok: true });
  console.info({ name: 'Ada' });
  console.warn('warning');
  console.error('failure:%s', 'details');

  assert.match(stdout.text(), /value=42 json=\{"ok":true\}/);
  assert.match(stdout.text(), /\{ name: 'Ada' \}/);
  assert.equal(stderr.text(), 'warning\nfailure:details\n');
});

test('Console 的 group/count/assert/trace/table 适合交互诊断而非结构化日志', () => {
  const stdout = new CaptureStream();
  const stderr = new CaptureStream();
  const console = new Console({ stdout, stderr, colorMode: false });

  console.group('section');
  console.count('items');
  console.count('items');
  console.groupEnd();
  console.assert(true, 'not printed');
  console.assert(false, 'expected %d', 2);
  console.trace('trace label');
  console.table([{ name: 'Ada', language: 'JavaScript' }]);

  assert.match(stdout.text(), /section\n  items: 1\n  items: 2/);
  assert.match(stdout.text(), /Ada/);
  assert.match(stdout.text(), /JavaScript/);
  assert.match(stderr.text(), /Assertion failed: expected 2/);
  assert.match(stderr.text(), /Trace: trace label/);
  assert.doesNotMatch(stderr.text(), /not printed/);
});

test('readline 把 CRLF 和独立 CR/LF 统一成 line，并支持 async iteration', async () => {
  const input = Readable.from(['first\r', '\nsecond\rthird\nfourth']);
  const interface_ = readline.createInterface({
    input,
    crlfDelay: Infinity,
  });
  const lines = [];

  for await (const line of interface_) lines.push(line);
  assert.deepEqual(lines, ['first', 'second', 'third', 'fourth']);
  assert.equal(interface_.closed, true);
});

test('readline/promises question 写提示并等待一行回答', async () => {
  const input = new PassThrough();
  const output = new CaptureStream();
  const interface_ = readlinePromises.createInterface({
    input,
    output,
    terminal: false,
  });

  const answer = interface_.question('Name? ');
  queueMicrotask(() => input.write('Ada Lovelace\n'));
  assert.equal(await answer, 'Ada Lovelace');
  assert.equal(output.text(), 'Name? ');
  interface_.close();
});

test('question 的 AbortSignal 只取消等待，不替应用关闭整个 interface', async () => {
  const input = new PassThrough();
  const output = new CaptureStream();
  const interface_ = readlinePromises.createInterface({
    input,
    output,
    terminal: false,
  });
  const controller = new AbortController();
  const reason = new Error('stop asking');
  const answer = interface_.question('Waiting? ', { signal: controller.signal });
  controller.abort(reason);

  await assert.rejects(
    answer,
    (error) => error.name === 'AbortError' && error.cause === reason,
  );
  const nextAnswer = interface_.question('Next? ');
  queueMicrotask(() => input.write('still open\n'));
  assert.equal(await nextAnswer, 'still open');
  interface_.close();
});

test('cursorTo/moveCursor/clear* 向可写流生成终端控制序列', async () => {
  const output = new CaptureStream();
  assert.equal(cursorTo(output, 3, 2), true);
  assert.equal(moveCursor(output, -1, 1), true);
  assert.equal(clearLine(output, 0), true);
  assert.equal(clearScreenDown(output), true);
  await new Promise((resolve) => output.end(resolve));

  const bytes = output.text();
  assert.ok(bytes.includes('\u001b['));
  assert.ok(bytes.length > 4);
  // 返回值来自 stream.write 的背压信号，不表示真实终端已经完成绘制。
});

test('emitKeypressEvents 把 ANSI 输入序列解析为语义化 key 对象', async () => {
  const input = new PassThrough();
  emitKeypressEvents(input);
  const pressed = once(input, 'keypress');
  input.write('\u001b[A');
  const [text, key] = await pressed;

  assert.equal(text, undefined);
  assert.equal(key.name, 'up');
  assert.equal(key.ctrl, false);
  assert.equal(key.meta, false);
  assert.equal(key.shift, false);
});

test('tty.isatty 只回答文件描述符是否连接 TTY，不等同于流是否可写', () => {
  assert.equal(typeof tty.isatty(0), 'boolean');
  assert.equal(typeof tty.isatty(1), 'boolean');
  assert.equal(tty.isatty(-1), false);
  assert.equal(tty.isatty(2 ** 31), false);
  // run.sh 在交互 shell 与自动化进程中可能采用不同 TTY 模式，因此不锁定 fd 0/1。
});

test('REPL 可接入自定义流、隔离 context，并用下划线引用上次结果', async () => {
  const input = new PassThrough();
  const output = new CaptureStream();
  const server = repl.start({
    prompt: '',
    input,
    output,
    terminal: false,
    useGlobal: false,
    ignoreUndefined: true,
  });
  server.context.base = 10;
  const exited = once(server, 'exit');

  input.end('base + 2\n_ * 3\n.exit\n');
  await exited;
  const lines = output.text().trim().split('\n');
  assert.deepEqual(lines, ['12', '36']);
  assert.equal(globalThis.base, undefined);
});

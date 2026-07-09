import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';

test('path helpers join and inspect path components', () => {
  const joined = path.join('alpha', 'beta', '..', 'gamma.txt');

  assert.equal(joined, path.join('alpha', 'gamma.txt'));
  assert.equal(path.basename(joined), 'gamma.txt');
});

// 映射查找与缺失键。
// 共同问题：缺失查找返回值还是错误；读取是否可能插入；如何区分缺失与空值；
// 自定义映射能否提供默认策略。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: mapping_lookup_and_missing_keys
// polyglot-related: languages/nodejs/language/test_015_map_set_weak_collections_and_set_composition.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('Map.get 对缺失键返回 undefined 且不插入', () => {
  const mapping = new Map([['answer', 42]]);

  assert.equal(mapping.get('answer'), 42);
  assert.equal(mapping.get('missing'), undefined);
  assert.equal(mapping.size, 1);
});

test('has 区分缺失键和值为 undefined 的键', () => {
  const mapping = new Map([['value', undefined]]);

  assert.equal(mapping.get('value'), undefined);
  assert.equal(mapping.get('missing'), undefined);
  assert.equal(mapping.has('value'), true);
  assert.equal(mapping.has('missing'), false);
});

test('Map.set 显式插入并返回映射本身以支持链式调用', () => {
  const mapping = new Map();

  const result = mapping.set('a', 1).set('b', 2);

  assert.equal(result, mapping);
  assert.deepEqual([...mapping], [['a', 1], ['b', 2]]);
});

test('JavaScript Map 没有用户可定制的缺失键协议', () => {
  const getOrCreate = (mapping, key, factory) => {
    if (!mapping.has(key)) {
      mapping.set(key, factory());
    }
    return mapping.get(key);
  };
  const mapping = new Map();

  assert.deepEqual(getOrCreate(mapping, 'items', () => []), []);
  assert.equal(mapping.has('items'), true);
});


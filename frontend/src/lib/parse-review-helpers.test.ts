import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { parseNum, parsePrice } from './parse.ts';

test('parseNum: parses integers', () => {
  assert.equal(parseNum('42'), 42);
  assert.equal(parseNum('0'), 0);
  assert.equal(parseNum('-3'), -3);
});

test('parseNum: parses floats', () => {
  assert.equal(parseNum('3.5'), 3.5);
  assert.equal(parseNum('0.1'), 0.1);
});

test('parseNum: strips commas', () => {
  assert.equal(parseNum('1,234'), 1234);
  assert.equal(parseNum('1,234,567'), 1234567);
});

test('parseNum: returns null for dash variants', () => {
  assert.equal(parseNum('—'), null);
  assert.equal(parseNum('––'), null);
  assert.equal(parseNum('—'), null);
  assert.equal(parseNum(''), null);
  assert.equal(parseNum('  '), null);
});

test('parseNum: returns null for non-numeric', () => {
  assert.equal(parseNum('abc'), null);
  assert.equal(parseNum('N/A'), null);
});

test('parsePrice: strips dollar sign', () => {
  assert.equal(parsePrice('$0.042'), 0.042);
  assert.equal(parsePrice('$1.50'), 1.5);
});

test('parsePrice: returns null for dash', () => {
  assert.equal(parsePrice('—'), null);
});

test('parsePrice: returns null for empty', () => {
  assert.equal(parsePrice(''), null);
});
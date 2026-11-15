import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {test} from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/discovery.ts', import.meta.url), 'utf8');
const {outputText} = ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.ESNext}});
const {validDiscoveryTime, readDiscovery, discoveryLink} = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
const now = Date.parse('2026-11-15T12:00:00Z'); // 17:00 in Uzbekistan

test('Uzbekistan time is independent of the device timezone', () => {
  assert.equal(validDiscoveryTime('2026-11-15', '18:00', now), true);
  assert.equal(validDiscoveryTime('2026-11-15', '17:00', now), false);
  assert.equal(validDiscoveryTime('2026-11-16', '00:00', now), true);
});

test('invalid dates, non-hour slots and expired times are rejected', () => {
  for (const [day, time] of [['2026-02-30', '18:00'], ['2026-11-31', '18:00'], ['2026-11-16', '24:00'], ['2026-11-16', '18:30'], ['2026-11-16', '8:00'], ['', '18:00'], ['2026-11-14', '20:00']]) {
    assert.equal(validDiscoveryTime(day, time, now), false, `${day} ${time}`);
  }
  assert.equal(validDiscoveryTime('2026-11-15', '18:00', Date.parse('2026-11-15T12:55:00Z')), false);
  assert.equal(validDiscoveryTime('2026-11-15', '18:00', Date.parse('2026-11-15T12:54:59Z')), true);
  assert.equal(validDiscoveryTime('2027-01-14', '17:00', now), true);
  assert.equal(validDiscoveryTime('2027-01-14', '18:00', now), false);
});

test('only supported sports and a valid future time are restored', () => {
  for (const sport of ['all', 'football', 'table_tennis', 'billiards']) {
    assert.deepEqual(readDiscovery(`?sport=${sport}&q=Namangan&day=2026-11-15&time=18%3A00`, now), {sport, query: 'Namangan', day: '2026-11-15', time: '18:00'});
  }
  assert.deepEqual(readDiscovery('?sport=unknown&day=2026-11-14&time=20:00', now), {sport: 'all', query: '', day: '', time: ''});
  assert.equal(readDiscovery(`?q=${'a'.repeat(120)}`, now).query.length, 100);
});

test('shared URLs contain only the intended discovery filters', () => {
  const href = 'https://maydon.example/?phone=998901234567&latitude=41&longitude=71&tgWebAppData=secret&owner=1&venue=42#tgWebAppData=secret';
  const state = {sport: 'football', query: '  Markaz & stadion  ', day: '2026-11-15', time: '18:00'};
  const url = new URL(discoveryLink(href, state, now));
  assert.deepEqual([...url.searchParams.keys()], ['sport', 'q', 'day', 'time']);
  assert.equal(url.hash, '');
  assert.deepEqual(readDiscovery(url.search, now), {...state, query: state.query.trim()});
  const expired = new URL(discoveryLink(href, {...state, sport: 'invalid', day: '2026-11-14'}, now));
  assert.deepEqual([...expired.searchParams.keys()], ['q']);
});

const test = require('node:test');
const assert = require('node:assert/strict');
const {backtest, monthlyScenario} = require('../assets/finance-math.js');

test('CAGR uses elapsed time when monthly observations are missing', () => {
  const h = {labels:['2024-01','2024-06','2026-01'], dates:['2024-01-31','2024-06-28','2026-01-30'], values:[100,110,121]};
  const r = backtest(100000, h, 0, 0);
  assert.equal(r.final, 121000);
  assert.ok(Math.abs(r.years - 730 / 365.2425) < 1e-10);
  assert.ok(Math.abs(r.cagr - 10) < .02);
  assert.deepEqual(r.scenario, [100000,100000,100000]);
});

test('period selection follows calendar months rather than sample count', () => {
  const h = {labels:['2020-01','2025-12','2026-01'], dates:['2020-01-31','2025-12-31','2026-01-30'], values:[1,100,110]};
  assert.deepEqual(backtest(100, h, 12, 0).labels, ['2025-12','2026-01']);
});

test('adjusted SYS input reconciles the documented split', () => {
  const r = backtest(100000, {labels:['2025-05','2025-06'], dates:['2025-05-27','2025-06-30'], values:[107.988,107]}, 0, 0);
  assert.ok(Math.abs(r.final - 99085.0835278) < .0001);
});

test('invalid amounts and mismatched or reversed dates cannot produce a result', () => {
  const h = {labels:['2025-01','2026-01'], dates:['2025-01-31','2026-01-30'], values:[100,110]};
  for (const n of [0,-100,NaN,Infinity]) assert.throws(() => backtest(n,h,0,0));
  assert.throws(() => backtest(100,{...h,dates:['2026-01-30','2025-01-31']},0,0));
  assert.throws(() => backtest(100,{...h,dates:['2025-01-31']},0,0));
});

test('minus 100 percent scenario preserves starting capital at time zero', () => {
  const r = backtest(100, {labels:['2025-01','2026-01'], values:[100,110]}, 0, -1);
  assert.deepEqual(r.scenario,[100,0]);
});

test('zero-rate contributions and yearly step-up reconcile independently', () => {
  const r = monthlyScenario(5000,2,0,.1);
  assert.equal(r.balance,126000);
  assert.equal(r.invested,126000);
  assert.deepEqual(r.values,[0,60000,126000]);
});

test('monthly contribution timing agrees with ordinary-annuity closed form', () => {
  const r = monthlyScenario(5000,1,.12,0);
  const expected = 5000 * ((1.01 ** 12 - 1) / .01);
  assert.ok(Math.abs(r.balance - expected) < .000001);
  assert.ok(monthlyScenario(5000,1,-.12,0).balance < 60000);
});

test('invalid SIP contributions and negative or overflowing step-ups are rejected', () => {
  for (const n of [0,-1,Infinity]) assert.throws(() => monthlyScenario(n,1,0,0));
  for (const step of [-1.5,-.01,Infinity,2]) assert.throws(() => monthlyScenario(5000,10,0,step));
  assert.throws(() => monthlyScenario(5000,1.5,0,0));
});

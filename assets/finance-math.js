/* Shared, deterministic arithmetic. No network or DOM dependencies. */
(function (root) {
  'use strict';
  function monthNumber(label) {
    var match = /^(\d{4})-(\d{2})$/.exec(label);
    if (match) return Number(match[1]) * 12 + Number(match[2]) - 1;
    var old = /^([A-Za-z]{3})'(\d{2})$/.exec(label);
    var names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return old && names.indexOf(old[1]) >= 0 ? (2000 + Number(old[2])) * 12 + names.indexOf(old[1]) : NaN;
  }
  function backtest(amount, history, months, annualRate) {
    if (!(amount > 0) || !Number.isFinite(amount)) throw new Error('Enter a positive finite amount.');
    var labels = history.labels || [], values = history.values || [], dates = history.dates;
    if (labels.length !== values.length || labels.length < 2) throw new Error('Comparable price observations are unavailable.');
    if (dates && dates.length !== labels.length) throw new Error('Observation dates do not match prices.');
    if (!Number.isFinite(annualRate)) throw new Error('Enter a finite annual-rate assumption.');
    var numbers = labels.map(monthNumber), last = numbers[numbers.length - 1];
    if (numbers.some(function (n, i) { return !Number.isFinite(n) || (i > 0 && n <= numbers[i - 1]); })) throw new Error('Observation dates are invalid.');
    var start = months > 0 ? numbers.findIndex(function (n) { return n >= last - months; }) : 0;
    var L = labels.slice(start), V = values.slice(start);
    if (V.length < 2 || V.some(function (v) { return !Number.isFinite(v) || v <= 0; })) throw new Error('Valid prices are unavailable for this window.');
    var elapsed = numbers.slice(start).map(function (n, i) {
      if (dates && dates.length === labels.length) return (Date.parse(dates[start + i]) - Date.parse(dates[start])) / 86400000 / 365.2425;
      return (n - numbers[start]) / 12;
    });
    var years = elapsed[elapsed.length - 1];
    if (!(years > 0) || elapsed.some(function (y, i) { return !Number.isFinite(y) || (i > 0 && y <= elapsed[i - 1]); })) throw new Error('Elapsed time is unavailable.');
    var rate = Math.max(-1, Math.min(1, annualRate));
    var series = V.map(function (p) { return amount * p / V[0]; });
    var final = series[series.length - 1], ret = (final / amount - 1) * 100;
    return {labels:L, series:series, final:final, ret:ret, years:years,
      cagr:(Math.pow(final / amount, 1 / years) - 1) * 100,
      scenario:elapsed.map(function (y, i) { return i === 0 ? amount : amount * Math.pow(1 + rate, y); })};
  }
  function monthlyScenario(amount, years, rate, step) {
    if (!Number.isFinite(amount) || amount <= 0) throw new Error('Enter a positive finite monthly contribution.');
    if (!Number.isInteger(years) || years < 1 || years > 40) throw new Error('Enter a whole number of years from 1 to 40.');
    if (!Number.isFinite(rate) || rate < -1 || rate > 1) throw new Error('Enter a nominal annual rate from -100% to 100%.');
    if (!Number.isFinite(step) || step < 0 || step > 1) throw new Error('Enter an annual contribution step-up from 0% to 100%.');
    var balance = 0, invested = 0, contribution = amount;
    var labels = ['0'], values = [0], contributions = [0];
    for (var y = 1; y <= years; y++) {
      for (var m = 0; m < 12; m++) { balance = balance * (1 + rate / 12) + contribution; invested += contribution; }
      if (!Number.isFinite(balance) || !Number.isFinite(invested)) throw new Error('This scenario exceeds the supported numeric range.');
      labels.push('Yr ' + y); values.push(balance); contributions.push(invested);
      contribution *= 1 + step;
    }
    return {balance:balance, invested:invested, labels:labels, values:values, contributions:contributions};
  }
  var api = {backtest:backtest, monthNumber:monthNumber, monthlyScenario:monthlyScenario};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.PKFinanceMath = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync(require.resolve('../assets/portfolio-tracker.js'),'utf8');

async function renderPortfolio(holdings, data) {
  const elements = new Map();
  function element() { return {style:{}, textContent:'', innerHTML:'', children:[], appendChild(child){this.children.push(child);}, querySelectorAll(){return [];}}; }
  const document = {getElementById(id){ if (!elements.has(id)) elements.set(id,element()); return elements.get(id); },createElement:element,addEventListener(){}};
  vm.runInNewContext(script, {document, localStorage:{getItem(){return JSON.stringify(holdings);}},fetch:async()=>({json:async()=>data})});
  await new Promise(resolve=>setImmediate(resolve));
  return elements;
}

test('a holding without a price makes totals incomplete instead of valuing it at zero',async()=>{
  const el = await renderPortfolio([{type:'stock',ticker:'MISSING',qty:100},{type:'cash',qty:5000}],{stocks:[],gold:{}});
  assert.equal(el.get('pf-total').textContent,'Incomplete: missing prices');
  assert.equal(el.get('pf-chg').textContent,'Unavailable');
  assert.equal(el.get('pf-top').textContent,'-');
  assert.ok(el.get('pf-rows').children[0].innerHTML.includes('Unavailable'));
});

test('missing gold performance does not prevent valuation or become a zero return',async()=>{
  const el = await renderPortfolio([{type:'gold',qty:10}],{stocks:[],gold:{gram_24k:40000,chg1y_pct:null}});
  assert.equal(el.get('pf-total').textContent,'₨ 4,00,000');
  assert.equal(el.get('pf-chg').textContent,'Unavailable');
});

test('a real zero source return remains distinct from missing data',async()=>{
  const el = await renderPortfolio([{type:'stock',ticker:'SYS',qty:10}],{stocks:[{ticker:'SYS',name:'Systems',price:100,chg1y:0}],gold:{}});
  assert.equal(el.get('pf-total').textContent,'₨ 1,000');
  assert.equal(el.get('pf-chg').textContent,'+0.0%');
});

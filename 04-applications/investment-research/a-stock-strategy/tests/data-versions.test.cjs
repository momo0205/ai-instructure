const {test}=require('node:test');const assert=require('node:assert/strict');
const x=require('../src/strategy/interfaces/web/static/data-versions.js');
const a={id:'asset_a',symbol:'A',start:'2024-01-01',end:'2025-01-01',coverage:{research:[{start:'2024-02-01',end:'2025-01-01'}]}};
test('recommends usable latest source and keeps alternatives independent',()=>{const groups=x.groupAssets([{...a,id:'old',end:'2024-10-01'},{...a,id:'new',end:'2026-01-01',coverage:{research:[]} },a]);assert.equal(groups[0].recommended.id,'asset_a');assert.equal(groups[0].versions.length,3);assert.deepEqual(groups[0].recommended.coverage,a.coverage);});
test('equal dates do not prove duplicate, explicit fingerprints do',()=>{assert.equal(x.groupAssets([a,{...a,id:'b'}])[0].versions.length,2);assert.equal(x.groupAssets([{...a,market_sha256:'same'},{...a,id:'b',market_sha256:'same'}])[0].versions.length,1);});
test('independent source wins over generated legacy with equivalent coverage',()=>{assert.equal(x.groupAssets([{...a,id:'managed::A'},a])[0].recommended.id,'asset_a');});

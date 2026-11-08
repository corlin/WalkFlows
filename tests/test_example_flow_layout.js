const assert=require('node:assert/strict');const L=require('../walkflows/layout.js');
const bounds=[-6,-3,3,10],x=L.exampleFlow('site03_scene03',bounds);
assert.equal(x.items.length,2);assert.ok(x.items.every(z=>z.type==='zone'));assert.ok(x.items[0].y2<x.items[1].y1);
assert.deepEqual(x.items.map(z=>[z.x1,z.y1,z.x2,z.y2]),[[-6,-3,3,3],[-6,3.4,3,10]]);
assert.deepEqual(L.validateLayout(x,bounds,'site03_scene03'),x);
assert.throws(()=>L.exampleFlow('site03_scene03',[0,0,0,1]));
console.log('example flow layout tests passed');

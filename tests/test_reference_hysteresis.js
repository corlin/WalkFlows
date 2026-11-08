const assert=require('node:assert/strict');
const {stableReferenceEvents}=require('../walkflows/local_zones.js');
const z={x1:0,y1:0,x2:2,y2:2};
const point=(f,x,y=1)=>({clip_frame:f,relative_s:f/10,floor_x:x,floor_y:y});
const opt={margin:0.2,minDuration:0.2,maxInterval:0.11};
let e=stableReferenceEvents([point(0,-1),point(1,-1),point(2,-1),point(3,0.3),point(4,-0.1),point(5,-1),point(6,-1),point(7,-1)],z,opt);
assert.deepEqual(e,[]); // short excursion and boundary jitter do not confirm
 e=stableReferenceEvents([point(0,-1),point(1,-1),point(2,-1),point(3,0.3),point(4,0.3),point(5,0.3)],z,opt);
assert.equal(e.length,1);assert.equal(e[0].kind,'enter_candidate');assert.equal(e[0].first_frame,3);assert.equal(e[0].frame,5);
 e=stableReferenceEvents([point(0,-1),point(1,-1),point(2,-1),point(6,1),point(7,1),point(8,1)],z,opt);
assert.deepEqual(e.map(x=>x.kind),['gap','resumed_inside']);
 e=stableReferenceEvents([point(0,1),point(1,1),point(2,1)],z,opt);
assert.deepEqual(e.map(x=>x.kind),['initial_inside']);
 e=stableReferenceEvents([point(0,-1),point(1,-1),point(2,-1),point(3,0.3),point(4,0.1),point(5,0.3),point(6,0.3)],z,opt);
assert.deepEqual(e,[]); // boundary band resets confirmation
assert.throws(()=>stableReferenceEvents([point(1,1),point(1,1)],z,opt));
assert.throws(()=>stableReferenceEvents([],z,{...opt,margin:-1}));
e=stableReferenceEvents([point(0,-1),point(1,-1),point(2,-1),{...point(3,1),relative_s:1},{...point(4,1),relative_s:1.1},{...point(5,1),relative_s:1.2}],z,opt);
assert.deepEqual(e.map(x=>x.kind),['gap','resumed_inside']);
assert.throws(()=>stableReferenceEvents([],z,{...opt,maxInterval:0}));
console.log('stable reference event tests passed');

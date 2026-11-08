const assert=require('node:assert/strict');const layout=require('../walkflows/layout.js');
const bounds=[-6,-3,3,10],view={left:30,top:30,scale:40};
assert.deepEqual(layout.rectangleFromCanvas([70,70],[150,150],bounds,view),{x1:-5,y1:-2,x2:-3,y2:0});
assert.deepEqual(layout.rectangleFromCanvas([150,150],[70,70],bounds,view),{x1:-5,y1:-2,x2:-3,y2:0});
assert.deepEqual(layout.rectangleFromCanvas([70,70],[900,900],bounds,view),{x1:-5,y1:-2,x2:3,y2:10});
assert.throws(()=>layout.rectangleFromCanvas([0,0],[70,70],bounds,view));
assert.throws(()=>layout.rectangleFromCanvas([70,70],[71,71],bounds,view));
console.log('canvas rectangle tests passed');

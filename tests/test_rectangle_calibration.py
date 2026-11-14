import subprocess
import unittest

class RectangleCalibrationTest(unittest.TestCase):
    def test_rectangle_coordinates_and_validation(self):
        code = """
const assert = require('node:assert/strict');
const {rectanglePoints, viewRect, imageToCanvas, canvasToImage} = require('./walkflows/web/rectangle.js');
for (const side of ["full","left","right"]) {
  const view=viewRect(1792,672,side);
  const source=[view.x+view.width*.3, 330];
  const display=imageToCanvas(source,view,800,600);
  const restored=canvasToImage(display,view,800,600);
  assert.ok(Math.abs(restored[0]-source[0])<1e-8 && Math.abs(restored[1]-source[1])<1e-8);
}
assert.deepEqual(viewRect(1792,672,"right"),{x:896,y:0,width:896,height:672});
const points = [[10,10],[90,12],[80,90],[12,80]];
assert.deepEqual(rectanglePoints(points, 4, 3), {
  image_points: points, plane_points: [[0,0],[4,0],[4,3],[0,3]]
});
for (const [bad, width, height] of [
  [[[0,0],[4,4],[4,0],[0,4]], 4, 3],
  [[[0,0],[1,0],[2,0],[0,1]], 4, 3],
  [points, 0, 3], [points, 4, Infinity]
]) assert.throws(() => rectanglePoints(bad, width, height));
"""
        subprocess.run(["node", "-e", code], check=True)

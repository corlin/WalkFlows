import subprocess
import unittest

class RectangleCalibrationTest(unittest.TestCase):
    def test_rectangle_coordinates_and_validation(self):
        code = """
const assert = require('node:assert/strict');
const {rectanglePoints} = require('./walkflows/web/rectangle.js');
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

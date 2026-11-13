import subprocess
import unittest
from pathlib import Path


class GenericReviewAnalyticsTest(unittest.TestCase):
    def test_unique_and_ambiguous_cross_camera_pairs(self):
        path = Path(__file__).resolve().parents[1] / "walkflows/web/analytics.js"
        script = """
        const assert = require('assert');
        const {candidatePairs, pointInPolygon, zoneTransitions, heatGrid} = require(process.argv[1]);
        const a = [{id:'1', x:0, y:0}];
        const b = [{id:'2', x:0.1, y:0}];
        assert.equal(candidatePairs(a,b,0.2).unique.length,1);
        assert.equal(candidatePairs(a,b,0.05).unique.length,0);
        const ambiguous = candidatePairs(a,[...b,{id:'3',x:0.15,y:0}],0.2);
        assert.equal(ambiguous.unique.length,0);
        assert.equal(ambiguous.ambiguous.length,2);
        assert.throws(() => candidatePairs(a,b,0));
        const region=[[0,0],[2,0],[2,2],[0,2]];
        assert.equal(pointInPolygon([1,1],region),true);
        assert.equal(pointInPolygon([3,1],region),false);
        assert.equal(pointInPolygon([0,1],region),true);
        const track = [
          {id:'7',frame:0,x:-1,y:1,time:0},
          {id:'7',frame:1,x:1,y:1,time:1},
          {id:'7',frame:3,x:3,y:1,time:3},
          {id:'7',frame:4,x:1,y:1,time:4},
          {id:'8',frame:0,x:1,y:1,time:0}
        ];
        const events=zoneTransitions(track,region);
        assert.deepEqual(events.map(e=>[e.frame,e.type]),[[1,'enter'],[4,'enter']]);
        const duplicate = [{id:'1',frame:0,x:-1,y:1,time:0},
          {id:'1',frame:1,x:1,y:1,time:1},{id:'1',frame:1,x:1,y:1,time:1},
          {id:'1',frame:2,x:3,y:1,time:2}];
        assert.equal(zoneTransitions(duplicate,region).length,0);
        const grid=heatGrid([{x:0,y:0},{x:1,y:1},{x:1,y:1}], [0,0,1,1],2);
        assert.deepEqual(grid,[1,0,0,2]);
        """
        subprocess.run(["node", "-e", script, str(path)], check=True, capture_output=True, text=True)

import subprocess
import unittest
from pathlib import Path


class GenericReviewAnalyticsTest(unittest.TestCase):
    def test_view_bounds_ignore_invalid_points_and_handle_empty_frame(self):
        path = Path(__file__).resolve().parents[1] / "walkflows/web/analytics.js"
        script = r'''
        const assert=require('assert');
        const {pointBounds}=require(process.argv[1]);
        assert.deepEqual(pointBounds([{x:1,y:3},{x:4,y:5},{x:NaN,y:0}]),[1,3,4,5]);
        assert.equal(pointBounds([]),null);
        assert.equal(pointBounds([{x:NaN,y:0}]),null);
        '''
        subprocess.run(["node", "-e", script, str(path)], check=True, capture_output=True, text=True)

    def test_direction_requires_current_unambiguous_continuous_track(self):
        path = Path(__file__).resolve().parents[1] / "walkflows/web/analytics.js"
        script = r'''
        const assert=require('assert');
        const {continuousTrails}=require(process.argv[1]);
        const row=(id,x,y)=>({local_id:id,world_x:String(x),world_y:String(y)});
        let frames=new Map([[0,[row('1',0,0)]],[1,[row('1',1,0)]],[2,[row('1',2,0)]]]);
        let paths=continuousTrails(frames,0,2);
        assert.deepEqual(paths.get('1').map(p=>p.x),[0,1,2]);
        frames.set(1,[row('1',1,0),row('1',5,0)]);
        paths=continuousTrails(frames,0,2);
        assert.deepEqual(paths.get('1').map(p=>p.x),[2]);
        frames.delete(1);
        paths=continuousTrails(frames,0,2);
        assert.deepEqual(paths.get('1').map(p=>p.x),[2]);
        frames.delete(2);
        assert.equal(continuousTrails(frames,0,2).has('1'),false);
        '''
        subprocess.run(["node", "-e", script, str(path)], check=True, capture_output=True, text=True)

    def test_unique_and_ambiguous_cross_camera_pairs(self):
        path = Path(__file__).resolve().parents[1] / "walkflows/web/analytics.js"
        script = """
        const assert = require('assert');
        const {candidatePairs, pointInPolygon, zoneTransitions, heatGrid, regionFlows, uniqueFramePoints, sanitizeCalibration} = require(process.argv[1]);
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
        const key=JSON.stringify(['cam','1']);
        const samples=new Map([[key,new Map([[1,1],[2,1],[3,1],[4,1]])]]);
        const changes=[
          {camera:'cam',id:'1',frame:1,time:0.1,type:'exit',zone_index:0,zone:'A'},
          {camera:'cam',id:'1',frame:4,time:0.4,type:'enter',zone_index:1,zone:'B'}
        ];
        assert.equal(regionFlows(changes,samples,1).length,1);
        assert.equal(regionFlows(changes,samples,0.1).length,0);
        samples.get(key).delete(2);
        assert.equal(regionFlows(changes,samples,1).length,0);
        samples.get(key).set(2,1);
        assert.equal(regionFlows([...changes,{...changes[0],zone_index:2,zone:'C'}],samples,1).length,0);
        const duplicateWithInvalid = [{local_id:'1',world_x:'1',world_y:'1'}, {local_id:'1',world_x:'',world_y:''}];
        assert.equal(uniqueFramePoints(duplicateWithInvalid).length,0);
        assert.equal(uniqueFramePoints([{local_id:'1',world_x:'1',world_y:'1'}]).length,1);
        const contaminated=new Map([[0,[{local_id:'1',world_x:'4',world_y:'5'}]]]);
        sanitizeCalibration(contaminated,false);
        assert.equal(contaminated.get(0)[0].world_x,'');
        assert.equal(contaminated.get(0)[0].world_y,'');
        const calibrated=new Map([[0,[{local_id:'1',world_x:'4',world_y:'5'}]]]);
        sanitizeCalibration(calibrated,true);
        assert.equal(calibrated.get(0)[0].world_x,'4');
        """
        subprocess.run(["node", "-e", script, str(path)], check=True, capture_output=True, text=True)

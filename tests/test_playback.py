import subprocess
import unittest
from pathlib import Path


class PlaybackTest(unittest.TestCase):
    def test_unplayable_camera_does_not_stop_others(self):
        path=Path(__file__).resolve().parents[1]/"walkflows/web/playback.js"
        script="""
        const assert=require('assert');
        const {playAvailable}=require(process.argv[1]);
        let started=[];
        const cards=[
          {id:'ok',video:{play(){started.push('ok');return Promise.resolve();}}},
          {id:'bad',video:{play(){started.push('bad');return Promise.reject(Error('codec'));}}},
          {id:'throw',video:{play(){started.push('throw');throw Error('broken');}}}
        ];
        playAvailable(cards).then(result=>{
          assert.deepEqual(started,['ok','bad','throw']);
          assert.deepEqual(result.playing.map(c=>c.id),['ok']);
          assert.deepEqual(result.failed.map(c=>c.id),['bad','throw']);
          return playAvailable(cards.slice(1));
        }).then(result=>{
          assert.equal(result.playing.length,0);
          assert.equal(result.failed.length,2);
        }).catch(e=>{console.error(e);process.exitCode=1;});
        """
        subprocess.run(["node","-e",script,str(path)],check=True,capture_output=True,text=True)

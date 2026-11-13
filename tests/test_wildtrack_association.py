import unittest
import json
import subprocess
from pathlib import Path
from scripts.audit_wildtrack_association import candidates, evaluate_pairs


class AssociationAuditTest(unittest.TestCase):
    def test_unique_edges_and_reference_unknown(self):
        a=[{"id":"a","x":0.,"y":0.,"reference":1},
           {"id":"b","x":5.,"y":0.,"reference":None}]
        b=[{"id":"c","x":.1,"y":0.,"reference":1},
           {"id":"d","x":5.1,"y":0.,"reference":2}]
        unique,ambiguous=candidates(a,b,.5)
        self.assertEqual(len(unique),2);self.assertEqual(len(ambiguous),0)
        report=evaluate_pairs(a,b,.5)
        self.assertEqual((report["supported_correct"],report["unknown"],report["eligible_same_id"]),(1,1,1))

    def test_candidates_agree_with_browser_pair_rule(self):
        left=[{"id":"a","x":0.,"y":0.,"reference":1},
              {"id":"b","x":2.,"y":0.,"reference":2}]
        right=[{"id":"x","x":.1,"y":0.,"reference":1},
               {"id":"y","x":2.1,"y":0.,"reference":2},
               {"id":"z","x":2.2,"y":0.,"reference":None}]
        js=Path(__file__).resolve().parents[1]/"walkflows/web/analytics.js"
        script="const {candidatePairs}=require(process.argv[1]);const [a,b]=JSON.parse(process.argv[2]);const p=candidatePairs(a,b,.5);console.log(JSON.stringify([p.unique.length,p.ambiguous.length]));"
        result=subprocess.run(["node","-e",script,str(js),json.dumps([left,right])],
                              check=True,capture_output=True,text=True)
        unique,ambiguous=candidates(left,right,.5)
        self.assertEqual(json.loads(result.stdout),[len(unique),len(ambiguous)])

    def test_conflicts_are_not_unique_and_can_hide_true_pair(self):
        a=[{"id":"a","x":0.,"y":0.,"reference":1}]
        b=[{"id":"b","x":.1,"y":0.,"reference":1},
           {"id":"c","x":.2,"y":0.,"reference":2}]
        report=evaluate_pairs(a,b,.5)
        self.assertEqual(report["unique"],0)
        self.assertEqual(report["ambiguous_edges"],2)
        self.assertEqual(report["eligible_same_id"],1)
        self.assertEqual(report["supported_correct"],0)


if __name__=="__main__":
    unittest.main()

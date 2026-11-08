import unittest
from walkflows.association_diagnostic import diagnose

class AssociationDiagnosticTest(unittest.TestCase):
    def test_ambiguity_and_missing_are_not_assigned(self):
        obs = [dict(camera='a', id=1, frame=0, x=0., y=0.), dict(camera='a', id=2, frame=1, x=0., y=0.), dict(camera='b', id=3, frame=2, x=0., y=0.)]
        refs = {0:[dict(id=10,x=0.,y=0.),dict(id=11,x=.1,y=0.)], 1:[], 2:[dict(id=10,x=0.,y=0.)]}
        result=diagnose(obs,refs,.5)
        self.assertEqual([r['status'] for r in result], ['ambiguous_reference','no_candidate','matched'])
    def test_competing_observations_stay_unassigned(self):
        obs=[dict(camera='a',id=i,frame=1,x=0.,y=0.) for i in (1,2)]
        result=diagnose(obs,{1:[dict(id=9,x=0.,y=0.)]},.5)
        self.assertEqual([r['status'] for r in result],['competing_observation','competing_observation'])
    def test_different_cameras_can_match_same_reference(self):
        obs=[dict(camera=c,id=1,frame=1,x=0.,y=0.) for c in ('a','b')]
        result=diagnose(obs,{1:[dict(id=9,x=0.,y=0.)]},.5)
        self.assertEqual([r['reference_id'] for r in result],[9,9])
    def test_ambiguous_observation_still_competes_for_reference(self):
        obs=[dict(camera='a',id=1,frame=1,x=0.,y=0.),dict(camera='a',id=2,frame=1,x=.4,y=0.)]
        refs={1:[dict(id=9,x=0.,y=0.),dict(id=10,x=.8,y=0.)]}
        result=diagnose(obs,refs,.5)
        self.assertEqual([r['status'] for r in result],['competing_observation','ambiguous_reference'])
    def test_missing_reference_frame_and_boundary(self):
        obs=[dict(camera='a',id=1,frame=0,x=0.,y=0.),dict(camera='a',id=1,frame=1,x=.5,y=0.)]
        result=diagnose(obs,{1:[dict(id=2,x=0.,y=0.)]},.5)
        self.assertEqual([r['status'] for r in result],['reference_missing','matched'])
    def test_invalid_radius_rejected(self):
        for radius in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError): diagnose([],{},radius)

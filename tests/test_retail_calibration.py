import unittest
from scripts.derive_retail_plane_mapping import compose_floor_camera


class RetailCalibrationTest(unittest.TestCase):
    def test_composes_planar_global_transform(self):
        camera={"translation":[1,2,3],"rotation":[0,0,0,1],"scale":1}
        global_transform={"translation":[0.8,1.27,0],"rotation":[0,0,1,0],"scale":1}
        result=compose_floor_camera(camera,global_transform)
        self.assertAlmostEqual(result["translation"][0],-0.2)
        self.assertAlmostEqual(result["translation"][1],-0.73)
        self.assertAlmostEqual(result["translation"][2],3)
    def test_rejects_non_planar_transform(self):
        camera={"translation":[1,2,3],"rotation":[0,0,0,1],"scale":1}
        global_transform={"translation":[0,0,1],"rotation":[0,0,0,1],"scale":1}
        with self.assertRaisesRegex(ValueError,"floor"):
            compose_floor_camera(camera,global_transform)

import unittest
import cv2
import numpy as np

from walkflows.plane_motion import estimate_motion

class PlaneMotionTest(unittest.TestCase):
    def test_recovers_translation_from_textured_plane(self):
        rng = np.random.default_rng(42)
        image = rng.integers(0, 256, (360, 480), dtype=np.uint8)
        shifted = cv2.warpAffine(image, np.float32([[1,0,8],[0,1,6]]), (480,360))
        result = estimate_motion(image, shifted, [[10,10],[460,10],[460,340],[10,340]])
        self.assertEqual(result["status"], "estimated")
        matrix = np.array(result["current_to_reference"])
        point = matrix @ [250, 180, 1]
        np.testing.assert_allclose(point[:2]/point[2], [242,174], atol=1.0)

    def test_textureless_scene_is_unknown(self):
        blank = np.zeros((200, 200), dtype=np.uint8)
        result = estimate_motion(blank, blank, [[0,0],[199,0],[199,199],[0,199]])
        self.assertEqual(result["status"], "insufficient_features")
        self.assertIsNone(result["current_to_reference"])

    def test_rejects_invalid_polygon(self):
        blank = np.zeros((200, 200), dtype=np.uint8)
        with self.assertRaises(ValueError):
            estimate_motion(blank, blank, [[0,0],[1,1]])

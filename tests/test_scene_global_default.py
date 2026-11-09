import unittest
from walkflows.scene_transforms import scene_global_transform

class SceneGlobalDefaultTest(unittest.TestCase):
    def test_missing_global_transform_uses_upstream_identity(self):
        self.assertEqual(scene_global_transform({}), {
            'translation': [0, 0, 0], 'rotation': [0, 0, 0, 1], 'scale': 1
        })

    def test_explicit_transform_is_preserved(self):
        transform = {'translation': [1, 2, 0], 'rotation': [0, 0, 0, 1], 'scale': 1}
        self.assertEqual(scene_global_transform({'global-transformation': transform}), transform)

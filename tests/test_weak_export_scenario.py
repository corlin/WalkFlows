import unittest
from walkflows.scenario_names import valid_scenario_name


class WeakExportScenarioTest(unittest.TestCase):
    def test_inventory_names_allow_optional_suffix(self):
        self.assertTrue(valid_scenario_name("010_site05"))
        self.assertTrue(valid_scenario_name("002_site02_gaze"))
        for invalid in ("../010_site05", "010_site05/", "010_site05_", "site05", "010_site05;bad"):
            self.assertFalse(valid_scenario_name(invalid))

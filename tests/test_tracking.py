import unittest

from walkflows.tracking import observation


class TrackingObservationTests(unittest.TestCase):
    def test_records_frame_time_and_footpoint_without_truncation(self):
        row = observation("HallWide", 125, 25.0, 7, 0.8, [10, 20, 30, 80])
        self.assertEqual(row["timestamp_s"], 5.0)
        self.assertEqual((row["foot_x"], row["foot_y"]), (20.0, 80.0))
        self.assertEqual(row["camera"], "HallWide")
        self.assertEqual(row["local_id"], 7)

    def test_rejects_nonpositive_fps(self):
        with self.assertRaises(ValueError):
            observation("HallSeg", 0, 0, 1, 0.8, [0, 0, 1, 1])


if __name__ == "__main__":
    unittest.main()

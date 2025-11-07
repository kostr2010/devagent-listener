import unittest

from app.devagent.impl.review_patches import worker_get_range


class GetWorkerRangeTest(unittest.TestCase):
    def test_no_tasks(self) -> None:
        self.assertEqual(worker_get_range(0, 0, 1), (0, 0))
        self.assertEqual(worker_get_range(0, 1, 2), (0, 0))
        self.assertEqual(worker_get_range(0, 2, 3), (0, 0))
        self.assertEqual(worker_get_range(0, 0, 1), (0, 0))
        self.assertEqual(worker_get_range(0, 0, 2), (0, 0))

    def test_no_residual(self) -> None:
        self.assertEqual(worker_get_range(10, 0, 5), (0, 2))
        self.assertEqual(worker_get_range(10, 1, 5), (2, 4))
        self.assertEqual(worker_get_range(10, 2, 5), (4, 6))
        self.assertEqual(worker_get_range(10, 3, 5), (6, 8))
        self.assertEqual(worker_get_range(10, 4, 5), (8, 10))
        self.assertEqual(worker_get_range(10, 0, 2), (0, 5))
        self.assertEqual(worker_get_range(10, 1, 2), (5, 10))
        self.assertEqual(worker_get_range(10, 0, 10), (0, 1))
        self.assertEqual(worker_get_range(10, 1, 10), (1, 2))
        self.assertEqual(worker_get_range(10, 2, 10), (2, 3))
        self.assertEqual(worker_get_range(10, 3, 10), (3, 4))
        self.assertEqual(worker_get_range(10, 4, 10), (4, 5))
        self.assertEqual(worker_get_range(10, 5, 10), (5, 6))
        self.assertEqual(worker_get_range(10, 6, 10), (6, 7))
        self.assertEqual(worker_get_range(10, 7, 10), (7, 8))
        self.assertEqual(worker_get_range(10, 8, 10), (8, 9))
        self.assertEqual(worker_get_range(10, 9, 10), (9, 10))

    def test_residual_workers(self) -> None:
        self.assertEqual(worker_get_range(10, 0, 4), (0, 3))
        self.assertEqual(worker_get_range(10, 1, 4), (3, 6))
        self.assertEqual(worker_get_range(10, 2, 4), (6, 8))
        self.assertEqual(worker_get_range(10, 3, 4), (8, 10))
        self.assertEqual(worker_get_range(10, 0, 8), (0, 2))
        self.assertEqual(worker_get_range(10, 1, 8), (2, 4))
        self.assertEqual(worker_get_range(10, 2, 8), (4, 5))
        self.assertEqual(worker_get_range(10, 3, 8), (5, 6))
        self.assertEqual(worker_get_range(10, 4, 8), (6, 7))
        self.assertEqual(worker_get_range(10, 5, 8), (7, 8))
        self.assertEqual(worker_get_range(10, 6, 8), (8, 9))
        self.assertEqual(worker_get_range(10, 7, 8), (9, 10))

    def test_excessive_workers(self) -> None:
        self.assertEqual(worker_get_range(5, 0, 7), (0, 1))
        self.assertEqual(worker_get_range(5, 1, 7), (1, 2))
        self.assertEqual(worker_get_range(5, 2, 7), (2, 3))
        self.assertEqual(worker_get_range(5, 3, 7), (3, 4))
        self.assertEqual(worker_get_range(5, 4, 7), (4, 5))
        self.assertEqual(worker_get_range(5, 5, 7), (5, 5))
        self.assertEqual(worker_get_range(5, 6, 7), (5, 5))

    def test_invalid_idx(self) -> None:
        self.assertRaises(AssertionError, worker_get_range, 10, -5, 5)
        self.assertRaises(AssertionError, worker_get_range, 10, -1, 5)
        self.assertRaises(AssertionError, worker_get_range, 10, 5, 5)
        self.assertRaises(AssertionError, worker_get_range, 10, 6, 5)

    def devagent_invalid_group_size(self) -> None:
        self.assertRaises(AssertionError, worker_get_range, 10, 6, 0)
        self.assertRaises(AssertionError, worker_get_range, 10, 6, -5)
        self.assertRaises(AssertionError, worker_get_range, 10, -7, -5)


if __name__ == "__main__":
    unittest.main()

import argparse
import unittest

import kfac.utils as utils
from kfac.utils import WorkerAllocator


class TestLoadBalance(unittest.TestCase):

    def test1(self):
        self.assertEqual(
            utils.partition_inv_ranks(8, 8),
            [[0], [1], [2], [3], [4], [5], [6], [7]]
        )
        self.assertEqual(
            utils.partition_inv_ranks(8, 5),
            [[0, 5], [1, 6], [2, 7], [3], [4]]
        )
        self.assertEqual(
            utils.partition_inv_ranks(8, 4),
            [[0, 4], [1, 5], [2, 6], [3, 7]]
        )
        self.assertEqual(
            utils.partition_inv_ranks(8, 3),
            [[0, 3, 6], [1, 4, 7], [2, 5]]
        )
        self.assertEqual(
            utils.partition_inv_ranks(8, 2),
            [[0, 2, 4, 6], [1, 3, 5, 7]]
        )
        self.assertEqual(
            utils.partition_inv_ranks(8, 1),
            [[0, 1, 2, 3, 4, 5, 6, 7]]
        )
        self.assertEqual(
            utils.partition_inv_ranks(2, 1),
            [[0, 1]]
        )
        self.assertEqual(
            utils.partition_inv_ranks(2, 2),
            [[0], [1]]
        )
        self.assertEqual(
            utils.partition_inv_ranks(1, 1),
            [[0]]
        )

    def test2(self):
        self.assertEqual(
            utils.partition_grad_ranks(8, 8),
            [[0, 1, 2, 3, 4, 5, 6, 7]]
        )
        self.assertEqual(
            utils.partition_grad_ranks(8, 5),
            [[0, 1, 2, 3, 4], [5, 6, 7]]
        )
        self.assertEqual(
            utils.partition_grad_ranks(8, 4),
            [[0, 1, 2, 3], [4, 5, 6, 7]]
        )
        self.assertEqual(
            utils.partition_grad_ranks(8, 3),
            [[0, 1, 2], [3, 4, 5], [6, 7]]
        )
        self.assertEqual(
            utils.partition_grad_ranks(8, 2),
            [[0, 1], [2, 3], [4, 5], [6, 7]]
        )
        self.assertEqual(
            utils.partition_grad_ranks(8, 1),
            [[0], [1], [2], [3], [4], [5], [6], [7]]
        )
        self.assertEqual(
            utils.partition_grad_ranks(2, 1),
            [[0], [1]]
        )
        self.assertEqual(
            utils.partition_grad_ranks(2, 2),
            [[0, 1]]
        )
        self.assertEqual(
            utils.partition_grad_ranks(1, 1),
            [[0]]
        )

if __name__ == '__main__':
    unittest.main()


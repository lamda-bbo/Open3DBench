"""Small independent oracles for exact guide indexing; no archived code needed."""

from pathlib import Path
import random
import re
import sys
import unittest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from diagnose_guide_connectivity import (
    GuideRect, diagnose_net, guide_component_ids, strict_failure,
)
from guide_spatial_index import GuideSpatialIndex


def metal(layer):
    match = re.fullmatch(r"metal(\d+)", layer, re.I)
    return int(match.group(1)) if match else None


def touches(a, b, margin):
    return (a.x1 <= b.x2 + margin and b.x1 <= a.x2 + margin
            and a.y1 <= b.y2 + margin and b.y1 <= a.y2 + margin)


def partition_oracle(rects, three_d):
    """Build the geometric graph, then flood-fill; independent of union-find."""
    edges = [set() for _ in rects]
    for i, a in enumerate(rects):
        for j, b in enumerate(rects[:i]):
            ma, mb = metal(a.layer), metal(b.layer)
            if three_d:
                if ma is None or mb is None or abs(ma - mb) > 1:
                    continue
                margin = int(ma == mb)
            else:
                if a.layer != b.layer:
                    continue
                margin = 1
            if touches(a, b, margin):
                edges[i].add(j)
                edges[j].add(i)
    labels = [-1] * len(rects)
    for start in range(len(rects)):
        if labels[start] != -1:
            continue
        labels[start] = start
        todo = [start]
        while todo:
            for other in edges[todo.pop()]:
                if labels[other] == -1:
                    labels[other] = start
                    todo.append(other)
    return labels


def canonical_partition(labels):
    first = {}
    return [first.setdefault(label, i) for i, label in enumerate(labels)]


def covering_oracle(rects, x, y, margin):
    return next((i for i, rect in enumerate(rects)
                 if rect.x1 - margin <= x <= rect.x2 + margin
                 and rect.y1 - margin <= y <= rect.y2 + margin), None)


class GuideSpatialIndexTest(unittest.TestCase):
    def assert_partitions(self, rects):
        same, three_d = guide_component_ids(rects, GuideSpatialIndex(rects))
        self.assertEqual(canonical_partition(same), partition_oracle(rects, False))
        self.assertEqual(canonical_partition(three_d), partition_oracle(rects, True))

    def test_boundaries_layer_aliases_nonmetal_and_points(self):
        self.assert_partitions([
            GuideRect("metal2", 0, 0, 10, 10),
            GuideRect("metal2", 11, 0, 20, 10),
            GuideRect("metal3", 21, 0, 30, 10),
            GuideRect("metal3", 20, 10, 20, 10),
            GuideRect("METAL02", -1, 0, -1, 0),
            GuideRect("metal4", 0, 0, 10, 10),
            GuideRect("via2", 0, 0, 10, 10),
            GuideRect("via2", 11, 0, 20, 10),
            GuideRect("VIA2", 0, 0, 10, 10),
            GuideRect("metal0", -30, -30, -20, -20),
            GuideRect("metal1", -20, -20, -20, -20),
        ])

    def test_empty_and_single(self):
        for rects in ([], [GuideRect("metal2", 0, 0, 0, 0)]):
            self.assert_partitions(rects)
            self.assertEqual(GuideSpatialIndex(rects).first_covering_rect(0, 0, 0),
                             covering_oracle(rects, 0, 0, 0))

    def test_pin_coverage_keeps_first_file_index(self):
        rects = [GuideRect("metal2", -100, -100, 100, 100),
                 GuideRect("metal19", 0, 0, 0, 0)]
        rects += [GuideRect("metal2", i * 10, i * 10, i * 10 + 5, i * 10 + 5)
                  for i in range(100)]
        index = GuideSpatialIndex(rects)
        self.assertEqual(index.first_covering_rect(0, 0, 0), 0)
        for margin in (-1, 0, 1, 2100):
            for x, y in [(0, 0), (-101, -101), (-200, 4), (400, 402), (99999, 99999)]:
                self.assertEqual(index.first_covering_rect(x, y, margin),
                                 covering_oracle(rects, x, y, margin))

    def test_random_geometry_and_coverage(self):
        rng = random.Random(20261005)
        layers = ["metal1", "metal2", "metal3", "METAL02", "metal11", "metal12", "via1", "CUT"]
        for trial in range(40):
            rects = []
            for _ in range(rng.randrange(64, 170)):
                x, y = rng.randrange(-25, 26), rng.randrange(-25, 26)
                rects.append(GuideRect(rng.choice(layers), x, y,
                                       x + rng.randrange(20), y + rng.randrange(20)))
            rng.shuffle(rects)
            with self.subTest(trial=trial):
                self.assert_partitions(rects)
                index = GuideSpatialIndex(rects)
                for _ in range(20):
                    x, y = rng.randrange(-45, 46), rng.randrange(-45, 46)
                    margin = rng.choice([0, 1, 4, 2100])
                    self.assertEqual(index.first_covering_rect(x, y, margin),
                                     covering_oracle(rects, x, y, margin))

    def test_strict_failure_and_existing_component_cutoff(self):
        rects = [GuideRect("metal2", i * 20, 0, i * 20 + 10, 10) for i in range(70)]
        pins = [("HBT_0", 0, 0), ("LS_HBT_1", 20, 0)]
        for limit in (0, 63, 69, 70, 5000):
            diag = diagnose_net("signal_BOT", rects, pins, set(), None, 0, limit)
            self.assertEqual(diag.uncovered_pins, 0)
            self.assertEqual(diag.hbt_uncovered, 0)
            self.assertEqual(diag.pin_components, 2 if limit >= 70 else -1)
            self.assertEqual(strict_failure(diag), limit >= 70)
        uncovered = diagnose_net("signal_BOT", rects, [("HBT_bad", -2000, 0)],
                                 set(), None, 0, 0)
        self.assertTrue(strict_failure(uncovered))
        illegal = diagnose_net("signal_TOP", rects, pins, set(), None, 0, 0)
        self.assertTrue(strict_failure(illegal))

    def test_dense_overlap_retains_all_connectivity(self):
        self.assert_partitions([GuideRect("metal2" if i % 2 else "metal3", 0, 0, 100, 100)
                                for i in range(150)])

    def test_long_parallel_guides_without_grid_expansion(self):
        rects = [GuideRect("metal2", -1000000000, i * 20, 1000000000, i * 20 + 10)
                 for i in range(1600)]
        index = GuideSpatialIndex(rects)
        self.assertEqual(sum(len(index.later_neighbors(i)) for i in range(len(rects))), 0)
        self.assertEqual(guide_component_ids(rects, index),
                         (list(range(len(rects))), list(range(len(rects)))))

    def test_cell_boundaries_and_negative_coordinates(self):
        rects = []
        for i in range(-20, 20):
            x = i * 16800
            rects.extend([GuideRect("metal2", x - 4200, -16800, x, 0),
                          GuideRect("METAL02", x + 1, 0, x + 4200, 16800),
                          GuideRect("metal3", x, 0, x, 0)])
        self.assert_partitions(rects)
        index = GuideSpatialIndex(rects)
        for x in (-336001, -16801, -16800, -1, 0, 1, 16799, 16800, 336001):
            for y in (-16801, -16800, -1, 0, 1, 16800, 16801):
                for margin in (-1, 0, 1, 2100):
                    self.assertEqual(index.first_covering_rect(x, y, margin),
                                     covering_oracle(rects, x, y, margin))

    def test_extreme_rectangles_and_bounded_wide_queries(self):
        extent = 10 ** 60
        sparse = [GuideRect("metal2" if i % 2 else "metal3", i * 4200, 0,
                            i * 4200 + 100, 100) for i in range(90)]
        # One enormous box must not allocate every crossed cell. The same
        # oracle checks a huge query on ordinary sparse rectangles as well.
        for rects in (sparse, [GuideRect("metal2", -extent, -extent, extent, extent)] + sparse):
            self.assert_partitions(rects)
            index = GuideSpatialIndex(rects)
            for x, y, margin in [(0, 0, extent), (extent, extent, extent),
                                 (-extent, -extent, extent), (extent, extent, -extent)]:
                self.assertEqual(index.first_covering_rect(x, y, margin),
                                 covering_oracle(rects, x, y, margin))

    def test_noninteger_boxes_and_coverage_queries(self):
        ordinary = [GuideRect("metal2", i * 4200, 0, i * 4200 + 100, 100)
                    for i in range(90)]
        for rects in (ordinary, [GuideRect("metal3", -0.5, -0.5, 100.5, 100.5)] + ordinary):
            self.assert_partitions(rects)
            index = GuideSpatialIndex(rects)
            for x, y, margin in [(0.5, 0.5, 0), (-0.5, -0.5, 0.25),
                                 (100.25, 100.25, 0.5), (100.25, 100.25, -0.25)]:
                self.assertEqual(index.first_covering_rect(x, y, margin),
                                 covering_oracle(rects, x, y, margin))

    def test_sparse_random_geometry_and_large_pin_margins(self):
        rng = random.Random(20261012)
        layers = ["metal2", "METAL02", "metal3", "metal4", "metal11", "via1"]
        for trial in range(12):
            rects = []
            for _ in range(100):
                x, y = rng.randrange(-200, 201) * 4200, rng.randrange(-200, 201) * 4200
                rects.append(GuideRect(rng.choice(layers), x, y,
                                       x + rng.randrange(1, 8) * 4200,
                                       y + rng.randrange(1, 8) * 4200))
            rng.shuffle(rects)
            with self.subTest(trial=trial):
                self.assert_partitions(rects)
                index = GuideSpatialIndex(rects)
                for _ in range(20):
                    x, y = rng.randrange(-220, 221) * 4200, rng.randrange(-220, 221) * 4200
                    margin = rng.choice([-1, 0, 1, 2100, 10 ** 30])
                    self.assertEqual(index.first_covering_rect(x, y, margin),
                                     covering_oracle(rects, x, y, margin))


if __name__ == "__main__":
    unittest.main()

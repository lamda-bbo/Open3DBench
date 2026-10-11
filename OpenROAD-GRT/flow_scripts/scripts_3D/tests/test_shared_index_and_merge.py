"""Behavior tests for shared exact guide indexing and blockwise serialization."""
import random
import tempfile
import unittest
from pathlib import Path

from diagnose_guide_connectivity import GuideRect
from guide_spatial_index import GuideSpatialIndex
from merge_route_guides import iter_guide_text_blocks, merge_guides


class SharedGuideIndexTest(unittest.TestCase):
    def test_neighbor_candidates_have_exact_layer_and_coordinate_rules(self):
        rng = random.Random(20261007)
        layers = ['metal1', 'metal2', 'METAL02', 'metal3', 'metal11', 'via1', 'VIA1']
        for _ in range(40):
            rects = []
            for _ in range(rng.randrange(64, 160)):
                x, y = rng.randrange(-40, 40), rng.randrange(-40, 40)
                rects.append(GuideRect(rng.choice(layers), x, y,
                                       x + rng.randrange(20), y + rng.randrange(20)))
            index = GuideSpatialIndex(rects)
            for i, a in enumerate(rects):
                expected = []
                for j in range(i + 1, len(rects)):
                    b = rects[j]
                    am = int(a.layer[5:]) if a.layer.lower().startswith('metal') else None
                    bm = int(b.layer[5:]) if b.layer.lower().startswith('metal') else None
                    eligible = (abs(am - bm) <= 1 if am is not None and bm is not None
                                else a.layer == b.layer)
                    overlap = (a.x2 >= b.x1 - 1 and b.x2 >= a.x1 - 1
                               and a.y2 >= b.y1 - 1 and b.y2 >= a.y1 - 1)
                    if eligible and overlap:
                        expected.append(j)
                self.assertEqual(index.later_neighbors(i), expected)


class JoinedGuideMergeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_last_complete_duplicate_wins_and_output_is_sorted(self):
        a, b, output = (self.root / n for n in ['a.guide', 'b.guide', 'out.guide'])
        a.write_text('z\n(\n0 0 2 2 metal1\n)\nz\n(\n1 1 3 3 metal2\n)\n')
        b.write_text('a\n(\n2 2 4 4 metal11\n)\n')
        merge_guides([a, b], output)
        self.assertEqual(output.read_text(), 'a\n(\n2 2 4 4 metal11\n)\nz\n(\n1 1 3 3 metal2\n)\n')

    def test_cross_file_duplicate_raises_before_replacing_output(self):
        a, b, output = (self.root / n for n in ['a.guide', 'b.guide', 'out.guide'])
        a.write_text('a\n(\n0 0 1 1 metal1\n)\n')
        b.write_text(a.read_text())
        output.write_text('previous output')
        with self.assertRaisesRegex(ValueError, 'Duplicate net a'):
            merge_guides([a, b], output)
        self.assertEqual(output.read_text(), 'previous output')

    def test_blank_lines_stray_delimiters_and_incomplete_last_block(self):
        source = self.root / 'input.guide'
        source.write_text('(\n)\n\nnet\n(\n\n0 0 1 1 metal1\n)\nunfinished\n(\n0 0 1 1 metal1\n')
        self.assertEqual(list(iter_guide_text_blocks(source)),
                         [('net', 'net\n(\n0 0 1 1 metal1\n)\n')])

    def test_unicode_crlf_and_final_delimiter_without_newline(self):
        source = self.root / 'input.guide'
        source.write_bytes('导线\\x\r\n(\r\n0 0 1 1 metal2\r\n)'.encode())
        self.assertEqual(list(iter_guide_text_blocks(source)),
                         [('导线\\x', '导线\\x\n(\n0 0 1 1 metal2\n)\n')])


if __name__ == '__main__':
    unittest.main()

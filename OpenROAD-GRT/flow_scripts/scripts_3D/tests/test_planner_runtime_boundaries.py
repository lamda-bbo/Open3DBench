#!/usr/bin/env python3
"""Planner behavior at fanout, median, and demand-grid boundaries.

Set MLS_TEST_SCRIPT_DIR only when checking an isolated candidate.
"""
import copy
import math
from pathlib import Path
from statistics import StatisticsError
import sys
import os
import unittest

SCRIPT_DIR = Path(os.environ.get('MLS_TEST_SCRIPT_DIR', Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(SCRIPT_DIR))
import mls_planner as fast


def design(sinks):
    pins = [{'inst': 'driver_bottom', 'pin': 'Z', 'x': 24000, 'y': 24000,
             'die': 'bottom', 'io': 'OUTPUT', 'hbt': False}]
    pins.extend({'inst': f'sink{i}_bottom', 'pin': 'A', 'x': 600000 + (i % 16) * 10000,
                 'y': 180000 + (i // 16) * 10000, 'die': 'bottom', 'io': 'INPUT', 'hbt': False}
                for i in range(sinks))
    return {'dbu_per_micron': 1000, 'manufacturing_grid': 5, 'die_area': [0, 0, 1000000, 1000000],
            'hbt_master_size': [1000, 1000], 'hbts': [{'name': 'HBT_old', 'x': 6900, 'y': 13300}],
            'nets': [{'name': 'literal[3]$data', 'signal_type': 'SIGNAL', 'special': False, 'bterms': False, 'pins': pins}]}


class PlannerRuntimeBoundaryTest(unittest.TestCase):
    def test_bbox_preserves_large_integer_coordinates(self):
        origin = 2**60
        pins = [{'x': origin + 3, 'y': -origin},
                {'x': origin + 1, 'y': -origin + 7}]
        before = copy.deepcopy(pins)
        self.assertEqual(fast.bbox(pins), (origin + 1, -origin, origin + 3, -origin + 7))
        self.assertEqual(pins, before)

    def test_empty_bbox_keeps_the_minimum_error(self):
        with self.assertRaisesRegex(ValueError, r'^min\(\) arg is an empty sequence$'):
            fast.bbox([])

    def test_bbox_keeps_first_nan_and_ignores_later_nan_comparisons(self):
        result = fast.bbox([{'x': float('nan'), 'y': 4},
                           {'x': 2, 'y': float('nan')}, {'x': -1, 'y': 7}])
        self.assertTrue(math.isnan(result[0]))
        self.assertTrue(math.isnan(result[2]))
        self.assertEqual((result[1], result[3]), (4, 7))
        self.assertEqual(fast.bbox([{'x': 2, 'y': 4},
                                   {'x': float('nan'), 'y': float('nan')},
                                   {'x': -1, 'y': 7}]), (-1, 4, 2, 7))

    def test_bbox_keeps_the_first_signed_zero_on_ties(self):
        pins = [{'x': -0.0, 'y': 0.0}, {'x': 0.0, 'y': -0.0}]
        for order, signs in ((pins, (-1.0, 1.0, -1.0, 1.0)),
                             (list(reversed(pins)), (1.0, -1.0, 1.0, -1.0))):
            with self.subTest(signs=signs):
                self.assertEqual(tuple(math.copysign(1.0, n) for n in fast.bbox(order)), signs)

    def test_lower_median_ties_negative_and_large_integer_coordinates(self):
        for coordinates, expected in [([9, -4, 9, 2], (2, 2)), ([4, -9, 4], (4, 4)),
                                      ([2**55 + 5, 2**55 + 1], (2**55 + 1, 2**55 + 1))]:
            pins = [{'x': x, 'y': x} for x in coordinates]
            before = copy.deepcopy(pins)
            self.assertEqual(fast.center(pins), expected)
            self.assertEqual(pins, before)

    def test_empty_center_keeps_existing_failure(self):
        with self.assertRaises(StatisticsError):
            fast.center([])

    def test_minimum_sinks_excludes_driver_and_keeps_exact_threshold(self):
        overrides = {'multi_branch_enabled': True, 'relocation_enabled': False,
                     'multi_branch_min_fanout': 128}
        for sinks in (0, 1, 126, 127, 128, 129, 256):
            with self.subTest(sinks=sinks):
                current = design(sinks)
                config = fast.config_values(overrides)
                site = fast.HbtSites(current['die_area'], current['hbt_master_size'], 6400, 5, current['hbts'])
                result = fast.branch_candidate(current['nets'][0], config, 1000, site)
                if sinks < 128:
                    self.assertIsNone(result)
                else:
                    self.assertIsNotNone(result)
                if result is not None:
                    self.assertEqual(result['proxy']['sink_count'], sinks)
                    self.assertEqual(result['driver']['io'], 'OUTPUT')

    def test_threshold_does_not_admit_undriven_or_multidriver_nets(self):
        for driver_io in ('INPUT', 'INOUT'):
            current = design(128)
            current['nets'][0]['pins'][0]['io'] = driver_io
            plan = fast.plan_design(current, {'multi_branch_enabled': True, 'relocation_enabled': False})
            self.assertEqual(plan['selected'], [])
        current = design(128)
        current['nets'][0]['pins'][1]['io'] = 'OUTPUT'
        self.assertEqual(fast.plan_design(current, {'multi_branch_enabled': True})['selected'], [])

    def test_rectangular_demand_boundary_cells_and_die_isolation(self):
        def net(points, die='bottom', **flags):
            return {'pins': [{'x': x, 'y': y, 'die': die} for x, y in points], **flags}
        grid = fast.DemandGrid((0, 0, 40, 40), 2,
                              [net([(0, 0), (20, 20)]), net([(0, 0), (10, 0)]),
                               net([(20, 0), (40, 0)], 'upper', signal_type='CLOCK'),
                               net([(0, 0), (40, 40)], special=True)], 1)
        self.assertEqual(grid.values['bottom'], [[20.0, 10.0], [10.0, 10.0]])
        self.assertEqual(grid.values['upper'], [[0.0, 20.0], [0.0, 0.0]])
        self.assertEqual(grid.mean('bottom', (0, 0, 40, 40)), 12.5)



if __name__ == '__main__':
    unittest.main()

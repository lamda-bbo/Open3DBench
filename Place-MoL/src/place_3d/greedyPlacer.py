import numpy as np
import os
from typing import Optional, List, Dict, Any

# Optional layout plotter for visualization
try:
    import sys
    _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from src.utils.layout_plotter import LayoutPlotter
except Exception:
    LayoutPlotter = None


def place_macros(upper_macros, bottom_macros, db):
    # internals between macros 
    internal_w = 0.3 * float((db.xh - db.xl) / (len(upper_macros) ** 0.5))
    internal_h = 0.3 * float((db.yh - db.yl) / (len(upper_macros) ** 0.5))
    
    def greedy(macros):
        # sort all the macros by width (first) and height (second)
        sorted_macros = sorted(macros, key=lambda x: (-x['size_x'], -x['size_y']))
        
        placements = []
        skyline = [(db.xl, db.xh, db.yl)]
        failed = False

        for j, macro in enumerate(sorted_macros):
            aw, ah = macro['size_x'] + 2 * internal_w, macro['size_y'] + 2 * internal_h
            
            best_height = float('inf')
            best_pos = None
            best_segment_idx = -1

            # best position for placement
            for i, (x_s, x_e, s_h) in enumerate(skyline):
                if (x_e - x_s >= aw) and (s_h + ah < db.yh):
                    current_height = s_h + ah
                    # lowest and leftest
                    if (current_height < best_height or 
                        (current_height == best_height and x_s < best_pos[0])):
                        best_height = current_height
                        best_pos = (x_s, s_h)
                        best_segment_idx = i
            if best_pos is None:
                failed = True        
                continue
            
            # update skyline
            x_place, y_place = best_pos
            placements.append((x_place + internal_w, y_place + internal_h))
            seg_x_s, seg_x_e, seg_h = skyline[best_segment_idx]

            # insert new skyline
            new_seg = (x_place, x_place + aw, seg_h + ah)
            remaining_right = (x_place + aw, seg_x_e, seg_h) if (x_place + aw < seg_x_e) else None

            del skyline[best_segment_idx]
            skyline.insert(best_segment_idx, new_seg)
            if remaining_right:
                skyline.insert(best_segment_idx + 1, remaining_right)

            # merge neighbor lines
            if best_segment_idx > 0:
                prev = skyline[best_segment_idx - 1]
                current = skyline[best_segment_idx]
                if prev[1] == current[0] and prev[2] == current[2]:
                    merged = (prev[0], current[1], current[2])
                    skyline[best_segment_idx - 1: best_segment_idx + 1] = [merged]
                    best_segment_idx -= 1
            if remaining_right and (len(skyline) > (best_segment_idx + 2)):
                prev = skyline[best_segment_idx + 1]
                current = skyline[best_segment_idx + 2]
                if prev[1] == current[0] and prev[2] == current[2]:
                    merged = (prev[0], current[1], current[2])
                    skyline[best_segment_idx + 1: best_segment_idx + 2] = [merged]

        max_y = np.max(np.array(skyline)[:, 2])           
        sorted_id = [macro['node'] for macro in sorted_macros]
        return placements, sorted_id, failed, max_y, sorted_macros

    # greedy placement for upper_die macros
    max_y = 0.
    while max_y < (0.8 * db.yh):
        internal_w = 1.05 * internal_w
        internal_h = 1.05 * internal_h
        upper_die_placements, upper_die_id, failed, max_y, sorted_macros = greedy(upper_macros)
        if failed:
            while failed:
                internal_w = 0.99 * internal_w
                internal_h = 0.99 * internal_h
                upper_die_placements, upper_die_id, failed, max_y, sorted_macros = greedy(upper_macros)
            break

    # greedy placement for bot_die macros
    bot_die_placements, bot_die_id, failed, _, _ = greedy(bottom_macros)
    if failed:
        while failed:
            internal_w = 0.99 * internal_w
            internal_h = 0.99 * internal_h
            upper_die_placements, upper_die_id, failed, _, _ = greedy(upper_macros)

    # write placedb
    for i, (x, y) in enumerate(upper_die_placements):
        db.node_x[upper_die_id[i]] = x
        db.node_y[upper_die_id[i]] = y
    for i, (x, y) in enumerate(bot_die_placements):
        db.node_x[bot_die_id[i]] = x + 100  # shift to avoid totally overlap
        db.node_y[bot_die_id[i]] = y + 100 
    
    components = [{'x': upper_die_placements[i][0], 'y': upper_die_placements[i][1], 'width': sorted_macros[i]['size_x'], 'height': sorted_macros[i]['size_y']} for i in range(len(sorted_macros))]
    if LayoutPlotter is not None:
        macro_x = np.array([p[0] for p in upper_die_placements])
        macro_y = np.array([p[1] for p in upper_die_placements])
        LayoutPlotter.plot_macros(macro_x, macro_y, np.array([m['size_x'] for m in sorted_macros]), np.array([m['size_y'] for m in sorted_macros]),
                                 db.xl, db.yl, db.xh, db.yh, figure_path=None)
    return db


class GreedyMacroPlacer:
    """
    Skyline-based greedy macro placer.
    Places a single set of macros (e.g. upper-die) using the same skyline algorithm
    as in place_macros(), with interface compatible to MacroPlacer for use in the
    main placement pipeline.
    """

    def __init__(self, problem_instance, macros_to_place: List[str], params: Dict[str, Any], device: Optional[str] = None):
        self.problem_instance = problem_instance
        self.placedb = problem_instance.dmp_placedb
        self.macros_to_place = macros_to_place
        self.params = params or {}
        self.macro_indices = np.array(
            [self.placedb.node_name2id_map[name] for name in macros_to_place],
            dtype=np.int64
        )
        self.xl = float(self.placedb.xl)
        self.yl = float(self.placedb.yl)
        self.xh = float(self.placedb.xh)
        self.yh = float(self.placedb.yh)
        self._placements = None  # (macro_x, macro_y) after _run_greedy

    def _run_greedy(self) -> bool:
        """Run skyline greedy for self.macros_to_place. Write positions to placedb. Return False if any macro failed."""
        n = len(self.macros_to_place)
        if n == 0:
            return True
        internal_scale = self.params.get('internal_scale', 0.3)
        min_fill_ratio = self.params.get('min_fill_ratio', 0.8)
        internal_w = internal_scale * float((self.xh - self.xl) / (n ** 0.5))
        internal_h = internal_scale * float((self.yh - self.yl) / (n ** 0.5))
        macros = [
            {
                'node': int(self.macro_indices[i]),
                'size_x': float(self.placedb.node_size_x[self.macro_indices[i]]),
                'size_y': float(self.placedb.node_size_y[self.macro_indices[i]]),
            }
            for i in range(n)
        ]

        def greedy_one(macros, db_xl, db_xh, db_yl, db_yh, iw, ih):
            sorted_macros = sorted(macros, key=lambda x: (-x['size_x'], -x['size_y']))
            placements = []
            skyline = [(db_xl, db_xh, db_yl)]
            failed = False
            for macro in sorted_macros:
                aw = macro['size_x'] + 2 * iw
                ah = macro['size_y'] + 2 * ih
                best_height = float('inf')
                best_pos = None
                best_segment_idx = -1
                for i, (x_s, x_e, s_h) in enumerate(skyline):
                    if (x_e - x_s >= aw) and (s_h + ah < db_yh):
                        current_height = s_h + ah
                        if (best_pos is None or current_height < best_height or
                            (current_height == best_height and x_s < best_pos[0])):
                            best_height = current_height
                            best_pos = (x_s, s_h)
                            best_segment_idx = i
                if best_pos is None:
                    failed = True
                    continue
                x_place, y_place = best_pos
                placements.append((x_place + iw, y_place + ih))
                seg_x_s, seg_x_e, seg_h = skyline[best_segment_idx]
                new_seg = (x_place, x_place + aw, seg_h + ah)
                remaining_right = (x_place + aw, seg_x_e, seg_h) if (x_place + aw < seg_x_e) else None
                del skyline[best_segment_idx]
                skyline.insert(best_segment_idx, new_seg)
                if remaining_right:
                    skyline.insert(best_segment_idx + 1, remaining_right)
                if best_segment_idx > 0:
                    prev, cur = skyline[best_segment_idx - 1], skyline[best_segment_idx]
                    if prev[1] == cur[0] and prev[2] == cur[2]:
                        skyline[best_segment_idx - 1 : best_segment_idx + 1] = [(prev[0], cur[1], cur[2])]
                        best_segment_idx -= 1
                if remaining_right and len(skyline) > best_segment_idx + 2:
                    prev, cur = skyline[best_segment_idx + 1], skyline[best_segment_idx + 2]
                    if prev[1] == cur[0] and prev[2] == cur[2]:
                        skyline[best_segment_idx + 1 : best_segment_idx + 3] = [(prev[0], cur[1], cur[2])]
            max_y = float(np.max(np.array(skyline)[:, 2])) if skyline else db_yl
            sorted_id = [m['node'] for m in sorted_macros]
            return placements, sorted_id, failed, max_y

        db_xl, db_xh, db_yl, db_yh = self.xl, self.xh, self.yl, self.yh
        placements, sorted_id, failed, max_y = greedy_one(macros, db_xl, db_xh, db_yl, db_yh, internal_w, internal_h)
        # Same retry logic as place_macros: increase internal until max_y >= min_fill_ratio*yh; if failed, decrease until not failed
        while max_y < min_fill_ratio * self.yh and not failed:
            internal_w *= 1.05
            internal_h *= 1.05
            placements, sorted_id, failed, max_y = greedy_one(macros, db_xl, db_xh, db_yl, db_yh, internal_w, internal_h)
            if failed:
                break
        while failed:
            internal_w *= 0.99
            internal_h *= 0.99
            placements, sorted_id, failed, max_y = greedy_one(macros, db_xl, db_xh, db_yl, db_yh, internal_w, internal_h)
        for i, (x, y) in enumerate(placements):
            node_id = sorted_id[i]
            self.placedb.node_x[node_id] = x
            self.placedb.node_y[node_id] = y
        self._placements = (
            np.array([self.placedb.node_x[n] for n in self.macro_indices]),
            np.array([self.placedb.node_y[n] for n in self.macro_indices])
        )
        return not failed

    def optimize(self, num_iterations=100, verbose=True, plot_interval=None, plot_dir=None, log_dir=None):
        """Run greedy placement once. Returns a history dict for API compatibility with MacroPlacer."""
        ok = self._run_greedy()
        if verbose:
            print("GreedyMacroPlacer: skyline placement finished, failed=", not ok)
        if plot_dir and LayoutPlotter is not None and self._placements is not None:
            macro_x, macro_y = self._placements
            macro_w = np.array([self.placedb.node_size_x[i] for i in self.macro_indices])
            macro_h = np.array([self.placedb.node_size_y[i] for i in self.macro_indices])
            path = os.path.join(plot_dir, "greedy_upper_macros.png")
            LayoutPlotter.plot_macros(macro_x, macro_y, macro_w, macro_h,
                                     self.xl, self.yl, self.xh, self.yh,
                                     iteration=0, figure_path=path)
        return {'total_iterations': 1, 'failed': not ok}

    def update_placement(self):
        """Update problem_instance.results['placement'] from placedb (already written by _run_greedy)."""
        node_x = self.placedb.node_x.copy()
        node_y = self.placedb.node_y.copy()
        if not hasattr(self.problem_instance, 'results'):
            self.problem_instance.results = {}
        self.problem_instance.results['placement'] = (node_x, node_y)
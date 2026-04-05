import numpy as np
import random
import os
import copy
import math
import re
import pdb
from pathlib import Path
import logging
import torch as th
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DREAMPLACE_ROOT_DIR = os.path.join(ROOT_DIR, "DREAMPlace")
DREAMPLACE_PARENT_DIR = os.path.join(ROOT_DIR, "DREAMPlace", "install")
DREAMPLACE_DIR = os.path.join(DREAMPLACE_PARENT_DIR, "dreamplace")
sys.path.extend(
    [ROOT_DIR, DREAMPLACE_PARENT_DIR, DREAMPLACE_DIR]
)

from dreamplace.Params import Params
from dreamplace.PlaceDB import PlaceDB
from dreamplace.NonLinearPlace import NonLinearPlace
import dreamplace.Timer as Timer
import dreamplace.EvalMetrics as EvalMetrics
import dreamplace.ops.place_io.place_io as place_io

from itertools import combinations
from PIL import Image

CONFIG_DIR = os.path.join(ROOT_DIR, "config")


def to_str(x):
    if isinstance(x, bytes):
        return x.decode("utf-8", errors="ignore")
    return str(x)


def _resolve_project_path(path):
    if not path or os.path.isabs(path):
        return path
    return os.path.join(ROOT_DIR, path)


def _resolve_dreamplace_path(path):
    if not path or os.path.isabs(path):
        return path
    return os.path.join(DREAMPLACE_ROOT_DIR, path)


class ProblemInstance():
    def __init__(self, args, benchmark, upper_die_macros=None, only_cells=False, worker_id=None, def_path=None, rand_init=True):
        """
        Initialize ProblemInstance.
        
        Args:
            args: Arguments object
            benchmark: Benchmark name
            upper_die_macros: Optional list of upper die macro names (for shrinking)
            only_cells: Whether to place only cells (macros are fixed)
            worker_id: Optional worker ID for parallel processing
            def_path: Optional path to DEF file (overrides default from JSON config)
            rand_init: Whether to use random center initialization (overrides random_center_init_flag in dmp_json, default: True)
        """
        self.benchmark = benchmark
        self.args = args
        self.gp_hpwl = None
        self.regularity = None
        self.database = {}
        self.only_cells = only_cells
        self.worker_id = worker_id

        self.dmp_params = self._load_dmp_params(method=self.args.method, only_cells=only_cells, worker_id=self.worker_id, rand_init=rand_init)
        
        # Override DEF file path if provided
        if def_path is not None:
            abs_def_path = os.path.abspath(def_path)
            self.dmp_params.def_input = abs_def_path
        
        self.dmp_placedb = PlaceDB()
        self.dmp_placedb(self.dmp_params, upper_die_macros=upper_die_macros)
        if args.use_timer_for_evaluation:
            self.timer = Timer.Timer()
            self.timer(self.dmp_params, self.dmp_placedb)
            # This must be done to explicitly execute the parser builders.
            # The parsers in OpenTimer are all in lazy mode.
            self.timer.update_timing()
        else:
            self.timer = None
        self.dmp_placer = NonLinearPlace(self.dmp_params, self.dmp_placedb, timer=self.timer)
        self.results = {}
    
    def _load_dmp_params(self, method="mem-on-logic", only_cells=False, worker_id=None, rand_init=True):
        params = Params()
        if method != "mem-on-logic":
            raise ValueError(f"Unsupported placement method: {method}. Only 'mem-on-logic' is supported.")

        if only_cells:
            # If worker_id is provided, use for_parallel directory with numbered JSON file
            if worker_id is not None:
                json_path = os.path.join(DREAMPLACE_ROOT_DIR, "test", "or_3D", "for_parallel", f'{self.benchmark}_3D_macroFixed_{worker_id}.json')
            else:
                json_path = os.path.join(DREAMPLACE_ROOT_DIR, "test", "or_3D", f'{self.benchmark}_3D_macroFixed.json')
        else:
            json_path = os.path.join(DREAMPLACE_ROOT_DIR, "test", "or_3D", f'{self.benchmark}_3D.json')
        params.load(json_path)

        # Benchmark resources now live under Place-MoL/benchmarks.
        project_path_fields = [
            "aux_input",
            "def_input",
            "verilog_input",
            "early_lib_input",
            "late_lib_input",
        ]
        project_list_path_fields = [
            "lef_input",
            "lib_input",
        ]
        for field in project_path_fields:
            value = getattr(params, field, None)
            if isinstance(value, str):
                setattr(params, field, _resolve_project_path(value))
        for field in project_list_path_fields:
            value = getattr(params, field, None)
            if isinstance(value, list):
                setattr(params, field, [_resolve_project_path(item) for item in value])

        # The compact benchmark package does not ship placeholder Verilog files.
        # DREAMPlace can still run the LEF/DEF-based flow without them.
        if isinstance(getattr(params, "verilog_input", None), str) and not os.path.exists(params.verilog_input):
            logging.warning("Ignoring missing verilog_input: %s", params.verilog_input)
            params.verilog_input = None

        if isinstance(getattr(params, "detailed_place_engine", None), str):
            resolved_engine = _resolve_dreamplace_path(params.detailed_place_engine)
            if os.path.exists(resolved_engine):
                params.detailed_place_engine = resolved_engine
            elif getattr(params, "detailed_place_flag", 0):
                raise FileNotFoundError(f"Detailed placement engine not found: {resolved_engine}")
            else:
                logging.warning("Ignoring missing detailed_place_engine because detailed_place_flag=0: %s", resolved_engine)
                params.detailed_place_engine = None

        # Override random_center_init_flag parameter from dmp_json with the provided parameter
        params.random_center_init_flag = rand_init

        return params
    
    def determine_macro(self):
        self.macros = []
        self.macro_names = []
        self.macro_x = []
        self.macro_y = []
        self.macro_size_x = []
        self.macro_size_y = []
        # Calculate average node area
        self.port_indices = []     
        total_area = 0
        num = 0
        for node_name in self.dmp_placedb.node_names:
            node = self.dmp_placedb.node_name2id_map[node_name.decode('utf-8')]
            if node < (self.dmp_placedb.num_physical_nodes - self.dmp_placedb.num_terminal_NIs):  # exclude IO ports
                total_area += self.dmp_placedb.node_size_x[node] * self.dmp_placedb.node_size_y[node]
                num += 1
            else:
                self.port_indices.append(node)  # store the port indices
        avg_area = total_area / num
        
        # Identify macros based on area and height criteria
        for node_name in self.dmp_placedb.node_names:
            node = self.dmp_placedb.node_name2id_map[node_name.decode('utf-8')]
            if node < (self.dmp_placedb.num_physical_nodes - self.dmp_placedb.num_terminal_NIs):  # exclude IO ports
                area = self.dmp_placedb.node_size_x[node] * self.dmp_placedb.node_size_y[node]
                height = self.dmp_placedb.node_size_y[node]
                is_macro = (area > 10 * avg_area or height > 2 * self.dmp_placedb.row_height)
                if is_macro:
                    self.macros.append(node)
                    self.macro_names.append(node_name.decode('utf-8'))
                    self.macro_x.append(self.dmp_placedb.node_x[node])
                    self.macro_y.append(self.dmp_placedb.node_y[node])
                    self.macro_size_x.append(self.dmp_placedb.node_size_x[node])
                    self.macro_size_y.append(self.dmp_placedb.node_size_y[node])

        self.macro_names = np.array(self.macro_names).astype(np.str_)
        self.n_macro = len(self.macro_names)

    def init_dmp_db(self):
        if self.dmp_caller is None:
            assert False
        else:
            return self.dmp_caller.init_db()

    def place_2D(self):
        metric = self.dmp_placer(self.dmp_params, self.dmp_placedb)[-1]
        if isinstance(metric, list):
            gp_hpwl = metric[0][0].hpwl.item()
        else:
            gp_hpwl = metric.hpwl.item()

        self.results['placement'] = (self.dmp_placedb.node_x.copy(),
                                    self.dmp_placedb.node_y.copy())
        self.results['figure'] = copy.copy(self.dmp_placer.pos[0].data.clone().cpu().numpy())
        
        # Evaluate timing metrics (TNS and WNS) if timing optimization is enabled
        if self.args.use_timer_for_evaluation:
            tns, wns = self.evaluate_timing()
        else:
            tns, wns = 0, 0
       
        return gp_hpwl, tns, wns

    def evaluate_timing(self):
        """
        Evaluate timing metrics (TNS and WNS) using the timing operator.
        Returns:
            tuple: (tns, wns) timing metrics
        """ 
        # Get timing operator from the placer's op_collections
        timing_op = self.dmp_placer.op_collections.timing_op
        time_unit = timing_op.timer.time_unit()
        
        # Perform timing analysis on current placement
        # The timing operator takes the current position as input
        timing_op(self.dmp_placer.pos[0].data.clone().cpu())
        timing_op.timer.update_timing()
        
        # Report TNS and WNS
        # Note: OpenTimer considers early,late,rise,fall for tns/wns
        # The following values are normalized by time units
        tns = timing_op.timer.report_tns_elw(split=1) / (time_unit * 1e17)
        wns = timing_op.timer.report_wns(split=1) / (time_unit * 1e15)
        
        return tns, wns
    
    def legalize(self):
        """
        Legalize all movable components using DREAMPlace's legalize_op.
        """
        
        # Perform legalization
        legalized_pos = self.dmp_placer.op_collections.legalize_op(
            self.dmp_placer.pos[0]
        )
        self.dmp_placer.pos[0].data.copy_(legalized_pos)
        
        # Update placedb with legalized positions
        # Reference: NonLinearPlace.py line 746-753
        # pos[0] is a 1D tensor with format: [x0, x1, ..., xN, y0, y1, ..., yN]
        cur_pos = self.dmp_placer.pos[0].data.clone().cpu().numpy()
        
        # Apply solution using placedb.apply() function
        self.dmp_placedb.apply(
            self.dmp_params,
            cur_pos[0 : self.dmp_placedb.num_nodes],
            cur_pos[self.dmp_placedb.num_nodes:],
        )

        # Eval
        cur_metric = EvalMetrics.EvalMetrics(1000)
        cur_metric.evaluate(self.dmp_placedb, {"hpwl": self.dmp_placer.op_collections.hpwl_op}, self.dmp_placer.pos[0])
        
        return cur_metric.hpwl.item()

    
    def save_placement(self, path=None):
        self.dmp_placedb.node_x[:] = self.results['placement'][0].copy()
        self.dmp_placedb.node_y[:] = self.results['placement'][1].copy()
        # unscale locations
        node_x, node_y = self.dmp_placedb.unscale_pl(self.dmp_params.shift_factor, 
                                                     self.dmp_params.scale_factor)
        # update raw database
        place_io.PlaceIOFunction.apply(self.dmp_placedb.rawdb, node_x, node_y)
        if path is not None:
            self.dmp_placedb.write(
                self.dmp_params,
                path
            )

    def plot(self, hpwl, figure_name):
        pos = self.results['figure']
        self.dmp_placer.plot(
            self.dmp_params,
            None,
            None,
            pos,
            figure_name, 
        )

        img = Image.open(figure_name)
        # out = img.transpose(Image.FLIP_TOP_BOTTOM)
        # img.close()
        # out.save(figure_name)
        img.save(figure_name)

def seed_torch(seed):
    random.seed(seed)
    np.random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    th.manual_seed(seed)
    th.cuda.manual_seed(seed)
    th.manual_seed(seed)
    th.backends.cudnn.deterministic = True
    th.backends.cudnn.benchmark = False

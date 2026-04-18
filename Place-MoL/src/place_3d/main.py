import os
import sys
import json
import csv
import numpy as np
import time
from types import SimpleNamespace
import pdb
import copy
# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)

from src.run_dmp import ProblemInstance, seed_torch
from src.place_3d.macroRefiner import MacroRefiner
from src.place_3d.macroPlacer import MacroPlacer
from src.utils import DefProcessor
from src.place_3d.legalization import MacroLegalizer
import copy

CONFIG_DIR = os.path.join(ROOT_DIR, "config")


def get_result_dir(partition_method):
    """
    Get result directory based on partition method.
    
    Args:
        partition_method: Partition method name ('min-cut', 'max-cut', or 'GNN')
    
    Returns:
        str: Result directory path (e.g., 'results/mol-analytical-min-cut')
    """
    if partition_method == 'min-cut':
        return "results/mol-analytical-min-cut"
    elif partition_method == 'max-cut':
        return "results/mol-analytical-max-cut"
    elif partition_method == 'GNN':
        return "results/mol-analytical"
    else:
        # Default fallback
        return "results/mol-analytical"


def process_args():
    """
    Process command line arguments and load configuration from JSON file
    
    Returns:
        tuple: (args, config_path) where args contains all parameters
    """
    # Command line config
    params = [arg.lstrip("--") for arg in sys.argv if arg.startswith("--")]
    
    cmd_config_dict = {}
    benchmark = None
    seed = None
    config_file = None
    
    for arg in params:
        key, value = arg.split('=')
        try:
            cmd_config_dict[key] = eval(value)
        except:
            cmd_config_dict[key] = value
        
        if key == "benchmark":
            benchmark = value
        elif key == "seed":
            seed = int(value)
        elif key == "config_file":
            config_file = value
    
    # Check required parameters
    if benchmark is None:
        raise ValueError("--benchmark parameter is required")
    if seed is None:
        raise ValueError("--seed parameter is required")
    
    # Load config file (use specified config_file or default to or_3D.json)
    if config_file is None:
        config_file = "or_3D.json"
    
    # Support both relative paths (relative to CONFIG_DIR) and absolute paths
    if os.path.isabs(config_file):
        config_path = config_file
    else:
        config_path = os.path.join(CONFIG_DIR, config_file)
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    # Load config file (JSON only)
    with open(config_path, 'r') as f:
        config_dict = json.load(f)
    
    # Set default values for ProblemInstance if not present
    defaults = {
        'gpu': 0,
        'use_cuda': True,
        'use_timer_for_evaluation': False,
        'grid': 224
    }
    for key, value in defaults.items():
        if key not in config_dict:
            config_dict[key] = value
    
    # Override with command line arguments
    for key, value in cmd_config_dict.items():
        config_dict[key] = value
    
    # Extract parameter dictionaries
    partition_params = config_dict.get('partition_params', {})
    macro_refine_params = config_dict.get('macro_refine_params', {})
    macro_place_params = config_dict.get('macro_place_params', {})
    macro_legalize_params = config_dict.get('macro_legalize_params', {})
    
    
    # Create args object
    args = SimpleNamespace(**config_dict)
    args.benchmark = benchmark
    args.seed = seed
    
    # Add parameter dictionaries to args
    args.partition_params = partition_params
    args.macro_refine_params = macro_refine_params
    args.macro_place_params = macro_place_params
    args.macro_legalize_params = macro_legalize_params
    
    print(f"Config file: {config_path}")
    print(f"Benchmark: {args.benchmark}")
    print(f"Seed: {args.seed}")
    if partition_params:
        print(f"Partition params: {partition_params}")
    if macro_refine_params:
        print(f"Macro refine params: {macro_refine_params}")
    if macro_place_params:
        print(f"Macro place params: {macro_place_params}")
    if macro_legalize_params:
        print(f"Macro legalize params: {macro_legalize_params}")
    
    return args, config_path


def step_1_partition(args, init_problem_instance):
    """
    Step 1: Partition the netlist into upper die and bottom die macros.
    
    Supports multiple partition methods from partition module:
    - 'min-cut': Graph cut algorithm minimizing cut weight
    - 'max-cut': Graph cut algorithm maximizing cut weight
    - 'GNN': Graph Neural Network (contrastive learning) baseline
    
    Args:
        args: Arguments object containing hyperparameters
        init_problem_instance: Initial ProblemInstance object
    
    Returns:
        dict: Partition result containing upper_die_macros, bottom_die_macros, etc.
    """
    print("\n" + "="*50)
    print("Step 1: Partition")
    print("="*50)
    
    partition_params = args.partition_params
    partition_method = partition_params.get('method', 'GNN')  # Default to GNN

    if partition_method not in ['min-cut', 'max-cut', 'GNN']:
        print(f"Warning: Unknown partition method '{partition_method}', defaulting to 'GNN'")
        partition_method = 'GNN'
    
    print(f"Partition method: {partition_method}")
    
    # Use graph-based partition methods from partition module
    from src.partition.common.graph_builder import GraphBuilder
    
    print("Building graph...")
    graph_builder = GraphBuilder(init_problem_instance)
    
    if partition_method in ['min-cut', 'max-cut']:
        # Graph cut methods
        from src.partition.graph_cut.graph_cut import GraphCutPartitioner
        
        area_balance_error = partition_params.get('area_balance_error', 0.1)
        print(f"Creating GraphCutPartitioner (area_balance_error={area_balance_error})...")
        partitioner = GraphCutPartitioner(graph_builder, area_balance_error=area_balance_error)
        
        if partition_method == 'min-cut':
            print("Performing min-cut partitioning...")
            selected_macro_indices = partitioner.min_cut(seed=args.seed)
        else:  # max-cut
            print("Performing max-cut partitioning...")
            selected_macro_indices = partitioner.max_cut(seed=args.seed)
        
        # Convert graph indices to placedb macro IDs
        selected_placedb_macro_ids = [
            graph_builder.graph_idx_to_placedb_macro_id[idx] 
            for idx in selected_macro_indices
        ]
        
        # Get all macro IDs
        all_placedb_macro_ids = set(graph_builder.placedb_macro_ids)
        bottom_die_macro_ids = set(selected_placedb_macro_ids)
        upper_die_macro_ids = all_placedb_macro_ids - bottom_die_macro_ids
        
    elif partition_method == 'GNN':
        # GNN (contrastive learning) method
        from src.partition.GNN.GNN_partition import train_gnn_partition, gnn_partition
        
        # Training config from partition_params
        gnn_config = partition_params.get('GNN', {})
        num_epochs = gnn_config.get('num_epochs', 20)
        lr = gnn_config.get('learning_rate', 0.001)
        hidden_dim = gnn_config.get('hidden_dim', 128)
        embedding_dim = gnn_config.get('embedding_dim', 64)
        num_layers = gnn_config.get('num_layers', 3)
        dropout = gnn_config.get('dropout', 0.1)
        temperature = gnn_config.get('temperature', 0.07)
        n_clusters = gnn_config.get('n_clusters', 2)
        area_balance_error = partition_params.get('area_balance_error', 0.1)
        
        # Determine device
        if args.use_cuda:
            device = f'cuda:{args.gpu}'
        else:
            device = 'cpu'
        
        print(f"Training GNN model (epochs={num_epochs}, device={device})...")
        model, loss_history = train_gnn_partition(
            graph_builder=graph_builder,
            num_epochs=num_epochs,
            lr=lr,
            device=device,
            hidden_dim=hidden_dim,
            embedding_dim=embedding_dim,
            num_layers=num_layers,
            dropout=dropout,
            temperature=temperature
        )
        
        print("Performing GNN partition...")
        gnn_result = gnn_partition(
            model=model,
            graph_builder=graph_builder,
            device=device,
            n_clusters=n_clusters,
            area_balance_error=area_balance_error
        )
        
        # Convert graph indices to placedb macro IDs
        selected_macro_indices = gnn_result['selected_macro_indices']  # These are graph macro indices [0, ..., n_macros-1]
        selected_placedb_macro_ids = [
            graph_builder.graph_idx_to_placedb_macro_id[idx]
            for idx in selected_macro_indices
        ]
        
        # Get all macro IDs
        all_placedb_macro_ids = set(graph_builder.placedb_macro_ids)
        bottom_die_macro_ids = set(selected_placedb_macro_ids)
        upper_die_macro_ids = all_placedb_macro_ids - bottom_die_macro_ids
    
    # Convert macro IDs to names
    def _node_id_to_name(node_id):
        node_name = init_problem_instance.dmp_placedb.node_names[node_id]
        if isinstance(node_name, bytes):
            return node_name.decode('utf-8')
        return str(node_name)
    
    upper_die_macro_names = [_node_id_to_name(mid) for mid in upper_die_macro_ids]
    bottom_die_macro_names = [_node_id_to_name(mid) for mid in bottom_die_macro_ids]
    
    # Calculate areas
    def _get_node_area(node_id):
        return float(init_problem_instance.dmp_placedb.node_size_x[node_id]) * \
               float(init_problem_instance.dmp_placedb.node_size_y[node_id])
    
    def _get_area(node_ids):
        return sum(_get_node_area(nid) for nid in node_ids)
    
    upper_die_area = _get_area(upper_die_macro_ids)
    bottom_die_macro_area = _get_area(bottom_die_macro_ids)
    
    # Get cells area
    all_nodes = set()
    for node_name in init_problem_instance.dmp_placedb.node_names:
        node_name_str = node_name.decode('utf-8') if isinstance(node_name, bytes) else str(node_name)
        node_id = init_problem_instance.dmp_placedb.node_name2id_map[node_name_str]
        all_nodes.add(node_id)
    
    cell_ids = all_nodes - all_placedb_macro_ids
    cells_area = _get_area(cell_ids)
    
    # Apply scale_factor if specified
    scale_factor = partition_params.get('scale_factor', 1.0)
    if 0 < scale_factor <= 1.0:
        cells_area = cells_area / scale_factor
    
    bottom_die_area = bottom_die_macro_area + cells_area
    
    partition_result = {
        'upper_die_macros': list(upper_die_macro_ids),
        'upper_die_macro_names': upper_die_macro_names,
        'bottom_die_macros': list(bottom_die_macro_ids),
        'bottom_die_macro_names': bottom_die_macro_names,
        'upper_die_area': upper_die_area,
        'bottom_die_area': bottom_die_area,
        'cells_area': cells_area,
        'moved_macros_count': len(bottom_die_macro_ids)
    }
    
    # Print partition results
    print("\nPartition Results:")
    print(f"Upper die macros count: {len(partition_result['upper_die_macros'])}")
    print(f"Bottom die macros count: {len(partition_result['bottom_die_macros'])}")
    print(f"Upper die area: {partition_result['upper_die_area']:.2f}")
    print(f"Estimated Bottom die area: {partition_result['bottom_die_area']:.2f}")
    print(f"Estimated Cells area: {partition_result['cells_area']:.2f}")
    print(f"Moved macros count: {partition_result['moved_macros_count']}")
    
    return partition_result


def step_2_prototype(args, init_problem_instance, partition_result):
    """
    Step 2: Perform 2D placement of the netlist.
    
    After placement, fix macro status and change macro directions in the placement result DEF.
    
    Args:
        args: Arguments object containing hyperparameters
        init_problem_instance: Initial ProblemInstance object
        partition_result: Partition result from step_partition
    
    Returns:
        tuple: (problem_instance, gp_hpwl) where problem_instance is the 2D placement result
    """
    print("\n" + "="*50)
    print("Step 2: 2D Placement for prototype")
    print("="*50)

    # Sub-Step 1: Create ProblemInstance for 2D placement
    problem_instance = ProblemInstance(
        args, 
        args.benchmark, 
        upper_die_macros=partition_result['upper_die_macro_names'],
    )
    
    # Sub-Step 2: Perform 2D placement
    gp_hpwl, _, _ = problem_instance.place_2D()
    print(f"Initial 2D HPWL: {gp_hpwl:.2f}")

    # Sub-Step 3: Copy coordinates from problem_instance to init_problem_instance
    print("\nCopying placement coordinates to init_problem_instance...")
    node_x, node_y = problem_instance.results['placement']
    init_problem_instance.results['placement'] = (node_x.copy(), node_y.copy())
    
    # Sub-Step 4: Save initial 2D placement results using init_problem_instance
    partition_method = args.partition_params.get('method', 'GNN')
    result_dir = get_result_dir(partition_method)
    placement_path = os.path.join(result_dir, "2d_prototype", f"{args.benchmark}.def")
    figure_path = os.path.join(result_dir, "2d_prototype", f"{args.benchmark}.png")
    os.makedirs(os.path.dirname(placement_path), exist_ok=True)
    
    init_problem_instance.save_placement(placement_path)
    problem_instance.plot(gp_hpwl, figure_path)
    print(f"2D placement saved to: {placement_path}")
    
    # Sub-Step 5: Fix macro status and change directions in the placement result
    print("\nProcessing placement DEF (fix macros and change directions to N)...")
    fixed_def_path = os.path.join("benchmarks", "or_3D", args.benchmark, "macro_fixed.def")
    
    # Use DefProcessor to fix the DEF file and change macro directions to N
    results = DefProcessor.fix_def_file_from_instance(
        init_problem_instance,
        placement_path,
        fixed_def_path,
        change_direction=True  # Also change macro directions to N
    )
    print(f"Fixed {results['fixed_count']} macros, changed {results['changed_direction_count']} macro directions to N")
    print(f"Fixed DEF with 2D placement saved to: {fixed_def_path}")

    return gp_hpwl


def step_3_bottom_die_macro_refinement(args, partition_result, gp_hpwl):
    """
    Step 3: Refine bottom die macro positions.
    """
    # Check if refinement is enabled
    enable_refinement = getattr(args, 'enable_bottom_die_refinement', False)
    if not enable_refinement:
        print("\n" + "="*50)
        print("Step 3: Bottom-Die Macro Refinement (SKIPPED)")
        print("="*50)
        print("Refinement is disabled. Set enable_bottom_die_refinement=True to enable.")
        
        # Still need to create and return a problem_instance for subsequent steps
        # No upper_die_macros parameter - we don't need shrinking for macro optimization steps
        print("Creating ProblemInstance from macro_fixed.def (without shrinking)...")
        problem_instance = ProblemInstance(
            args,
            args.benchmark,
            only_cells=True,
            rand_init=False
        )
        return problem_instance, gp_hpwl
    
    print("\n" + "="*50)
    print("Step 3: Bottom-Die Macro Refinement")
    print("="*50)
    
    # Re-initialize ProblemInstance from macro_fixed.def
    # No upper_die_macros parameter - we don't need shrinking for macro optimization steps
    print("Re-initializing ProblemInstance from macro_fixed.def (without shrinking)...")
    problem_instance = ProblemInstance(
        args,
        args.benchmark,
        only_cells=True,
        rand_init=False
    )
    
    # Select macros to refine
    macros_to_refine = partition_result['bottom_die_macro_names']

    # Get refinement parameters from params dictionary
    macro_refine_params = args.macro_refine_params
    num_iterations = macro_refine_params.get('iterations', 100)
    
    # Determine device
    if args.use_cuda:
        device = f'cuda:{args.gpu}'
    else:
        device = 'cpu'
    
    # Print refinement parameters
    hpwl_weight = macro_refine_params.get('hpwl_weight', 1.0)
    regularity_weight = macro_refine_params.get('regularity_weight', 0.1)
    learning_rate = macro_refine_params.get('learning_rate', 0.01)
    print(f"HPWL weight: {hpwl_weight}")
    print(f"Regularity weight: {regularity_weight}")
    print(f"Learning rate: {learning_rate}")
    print(f"Iterations: {num_iterations}")
    print(f"Device: {device}")
    
    # Create macro refiner (pass params dictionary)
    refiner = MacroRefiner(
        problem_instance,
        macros_to_refine,
        params=macro_refine_params,
        device=device
    )
    
    # Get plot interval from params
    plot_interval = macro_refine_params.get('plot_interval', None)
    partition_method = args.partition_params.get('method', 'GNN')
    result_dir = get_result_dir(partition_method)
    plot_dir = os.path.join(result_dir, "bottom_refined", f"{args.benchmark}_iterations")
    
    # Get tensorboard log directory from params
    log_dir = macro_refine_params.get('log_dir', None)
    if log_dir is None:
        log_dir = os.path.join(result_dir, "bottom_refined", f"{args.benchmark}_tensorboard")
    
    # Optimize macro positions
    final_hpwl, final_regularity, history = refiner.optimize(
        num_iterations=num_iterations,
        verbose=True,
        plot_interval=plot_interval,
        plot_dir=plot_dir,
        log_dir=log_dir
    )
    
    print("\nMacro Refinement Results:")
    print(f"Final HPWL: {final_hpwl:.2f}")
    print(f"Final Regularity: {final_regularity:.2f}")
    hpwl_improvement = gp_hpwl - final_hpwl
    if gp_hpwl > 0:
        improvement_pct = (hpwl_improvement / gp_hpwl) * 100
        print(f"HPWL improvement: {hpwl_improvement:.2f} ({improvement_pct:.2f}%)")
    else:
        print(f"HPWL improvement: {hpwl_improvement:.2f}")
    
    # Update placement with refined positions
    refiner.update_placement()
    
    # Save refined placement
    partition_method = args.partition_params.get('method', 'GNN')
    result_dir = get_result_dir(partition_method)
    refined_placement_path = os.path.join(result_dir, "bottom_refined", f"{args.benchmark}.def")
    refined_figure_path = os.path.join(result_dir, "bottom_refined", f"{args.benchmark}.png")
    os.makedirs(os.path.dirname(refined_placement_path), exist_ok=True)
    problem_instance.save_placement(refined_placement_path)
    problem_instance.plot(final_hpwl, refined_figure_path)
    
    print(f"\nRefined placement saved to: {refined_placement_path}")
    print(f"Refined figure saved to: {refined_figure_path}")

    return problem_instance, final_hpwl


def step_4_bottom_die_legalization(args, problem_instance, partition_result):
    """
    Step 4: Legalize bottom die macro positions.
    
    Legalization ensures that bottom die macros do not overlap with each other.
    HPWL calculation considers all nets including those connected to upper die cells.
    
    Args:
        args: Arguments object containing hyperparameters
        problem_instance: ProblemInstance from step 3 with bottom die macro refinement results
        partition_result: Partition result containing bottom_die_macros
    
    Returns:
        tuple: (final_hpwl, legalized_problem_instance) where legalized_problem_instance has legalized macro positions
    """
    print("\n" + "="*50)
    print("Step 4: Bottom-Die Macro Legalization")
    print("="*50)
    
    # Get bottom die macro node indices from partition_result
    bottom_die_macro_names = partition_result['bottom_die_macro_names']
    bottom_die_macro_indices = np.array([problem_instance.dmp_placedb.node_name2id_map[name] for name in bottom_die_macro_names], dtype=np.int64)
    
    # Get legalization parameters from params dictionary
    macro_legalize_params = args.macro_legalize_params
    grid_size = macro_legalize_params.get('grid_size', 224)
    
    # Determine device
    if args.use_cuda:
        device = f'cuda:{args.gpu}'
    else:
        device = 'cpu'
    
    print(f"Bottom die macros to legalize: {len(bottom_die_macro_indices)}")
    print(f"Grid size: {grid_size} x {grid_size}")
    print(f"Device: {device}")
    
    # Get regularity_weight from params
    regularity_weight = macro_legalize_params.get('regularity_weight', 0.1)
    
    # Create macro legalizer
    legalizer = MacroLegalizer(
        cell_problem_instance=problem_instance,
        macro_indices=bottom_die_macro_indices,
        grid_size=grid_size,
        die_type='bottom',
        regularity_weight=regularity_weight,
        device=device
    )
    
    # Perform legalization
    legalized_macro_pos_x, legalized_macro_pos_y = legalizer.legalize()
    
    # Update problem_instance with legalized macro positions
    problem_instance.dmp_placedb.node_x[bottom_die_macro_indices] = legalized_macro_pos_x
    problem_instance.dmp_placedb.node_y[bottom_die_macro_indices] = legalized_macro_pos_y
    
    # Update results['placement']
    if not hasattr(problem_instance, 'results'):
        problem_instance.results = {}
    updated_node_x = problem_instance.dmp_placedb.node_x.copy()
    updated_node_y = problem_instance.dmp_placedb.node_y.copy()
    problem_instance.results['placement'] = (updated_node_x, updated_node_y)
    
    # Compute final HPWL after legalization
    final_hpwl = legalizer._compute_hpwl(legalized_macro_pos_x, legalized_macro_pos_y)
    
    print(f"\nLegalization complete")
    print(f"Final HPWL after legalization: {final_hpwl:.2f}")
    
    # Save legalized placement results
    partition_method = args.partition_params.get('method', 'GNN')
    result_dir = get_result_dir(partition_method)
    legalized_placement_path = os.path.join(result_dir, "bottom_legalized", f"{args.benchmark}_legalized.def")
    legalized_figure_path = os.path.join(result_dir, "bottom_legalized", f"{args.benchmark}_legalized.png")
    os.makedirs(os.path.dirname(legalized_placement_path), exist_ok=True)
    problem_instance.save_placement(legalized_placement_path)
    
    # Plot using legalizer's plot function
    legalizer.plot_layout(
        macro_pos_x=legalized_macro_pos_x,
        macro_pos_y=legalized_macro_pos_y,
        hpwl_val=final_hpwl,
        figure_path=legalized_figure_path,
        title=f"Legalized Bottom-Die Macro Placement - HPWL: {final_hpwl:.2f}"
    )
    
    print(f"\nLegalized placement saved to: {legalized_placement_path}")
    print(f"Legalized figure saved to: {legalized_figure_path}")
    
    return final_hpwl, problem_instance


def step_5_upper_die_macro_placement(args, problem_instance, partition_result, gp_hpwl):
    """
    Step 5: Place upper die macros.
    """
    print("\n" + "="*50)
    print("Step 5: Upper-Die Macro Placement")
    print("="*50)
    
    # Select macros to place (upper die macros)
    macros_to_place = partition_result['upper_die_macro_names']

    # Get placement parameters from params dictionary
    macro_place_params = args.macro_place_params
    num_iterations = macro_place_params.get('iterations', 100)
    
    # Determine device
    if args.use_cuda:
        device = f'cuda:{args.gpu}'
    else:
        device = 'cpu'
    
    # Print placement parameters
    hpwl_weight = macro_place_params.get('hpwl_weight', 1.0)
    overlap_weight = macro_place_params.get('overlap_weight', 1.0)
    learning_rate = macro_place_params.get('learning_rate', 0.01)
    print(f"HPWL weight: {hpwl_weight}")
    print(f"Overlap weight: {overlap_weight}")
    print(f"Learning rate: {learning_rate}")
    print(f"Iterations: {num_iterations}")
    print(f"Device: {device}")
    
    # Create macro placer (pass params dictionary)
    placer = MacroPlacer(
        problem_instance,
        macros_to_place,
        params=macro_place_params,
        device=device
    )
    
    # Get plot interval from params
    plot_interval = macro_place_params.get('plot_interval', None)
    partition_method = args.partition_params.get('method', 'GNN')
    result_dir = get_result_dir(partition_method)
    plot_dir = os.path.join(result_dir, "upper_placed", f"{args.benchmark}_iterations")
    
    # Get tensorboard log directory from params
    log_dir = macro_place_params.get('log_dir', None)
    if log_dir is None:
        log_dir = os.path.join(result_dir, "upper_placed", f"{args.benchmark}_tensorboard")
    
    # Optimize macro positions
    history = placer.optimize(
        num_iterations=num_iterations,
        verbose=True,
        plot_interval=plot_interval,
        plot_dir=plot_dir,
        log_dir=log_dir
    )
    placer.update_placement()
    
    # Save macro positions dictionary
    partition_method = args.partition_params.get('method', 'GNN')
    result_dir = get_result_dir(partition_method)
    

def step_6_upper_die_legalization(args, problem_instance, partition_result):
    """
    Step 6: Legalize upper die macro positions.
    
    Legalization ensures that upper die macros do not overlap with each other.
    HPWL calculation considers all nets including those connected to bottom die cells.
    
    Args:
        args: Arguments object containing hyperparameters
        problem_instance: ProblemInstance from step 4 with upper die macro placement results (without upper_die_macros shrinking)
        partition_result: Partition result containing upper_die_macros
    
    Returns:
        tuple: (final_hpwl, legalized_problem_instance) where legalized_problem_instance has legalized macro positions
    """
    print("\n" + "="*50)
    print("Step 6: Upper-Die Macro Legalization")
    print("="*50)
    
    # Get upper die macro node indices from partition_result
    upper_die_macro_names = partition_result['upper_die_macro_names']
    upper_die_macro_indices = np.array([problem_instance.dmp_placedb.node_name2id_map[name] for name in upper_die_macro_names], dtype=np.int64)
    
    # Get legalization parameters from params dictionary
    macro_legalize_params = args.macro_legalize_params
    grid_size = macro_legalize_params.get('grid_size', 224)
    
    # Determine device
    if args.use_cuda:
        device = f'cuda:{args.gpu}'
    else:
        device = 'cpu'
    
    print(f"Upper die macros to legalize: {len(upper_die_macro_indices)}")
    print(f"Grid size: {grid_size} x {grid_size}")
    print(f"Device: {device}")
    
    # Get regularity_weight from params
    regularity_weight = macro_legalize_params.get('regularity_weight', 0.1)
    legalizer = MacroLegalizer(
        cell_problem_instance=problem_instance,
        macro_indices=upper_die_macro_indices,
        grid_size=grid_size,
        die_type='upper',
        regularity_weight=regularity_weight,
        device=device
    )
    
    # Perform legalization
    legalized_macro_pos_x, legalized_macro_pos_y = legalizer.legalize()
    
    # Update problem_instance with legalized macro positions
    # We'll update problem_instance in place
    problem_instance.dmp_placedb.node_x[upper_die_macro_indices] = legalized_macro_pos_x
    problem_instance.dmp_placedb.node_y[upper_die_macro_indices] = legalized_macro_pos_y
    
    # Update results['placement']
    if not hasattr(problem_instance, 'results'):
        problem_instance.results = {}
    updated_node_x = problem_instance.dmp_placedb.node_x.copy()
    updated_node_y = problem_instance.dmp_placedb.node_y.copy()
    problem_instance.results['placement'] = (updated_node_x, updated_node_y)
    
    # Compute final HPWL after legalization
    # We need to compute HPWL manually using the legalizer
    final_hpwl = legalizer._compute_hpwl(legalized_macro_pos_x, legalized_macro_pos_y)
    
    print(f"\nLegalization complete")
    print(f"Final HPWL after legalization: {final_hpwl:.2f}")
    
    # Save legalized placement results
    partition_method = args.partition_params.get('method', 'GNN')
    result_dir = get_result_dir(partition_method)
    legalized_placement_path = os.path.join(result_dir, "upper_legalized", f"{args.benchmark}_legalized.def")
    legalized_figure_path = os.path.join(result_dir, "upper_legalized", f"{args.benchmark}_legalized.png")
    os.makedirs(os.path.dirname(legalized_placement_path), exist_ok=True)
    problem_instance.save_placement(legalized_placement_path)
    
    # Plot using legalizer's plot function (not problem_instance.plot)
    legalizer.plot_layout(
        macro_pos_x=legalized_macro_pos_x,
        macro_pos_y=legalized_macro_pos_y,
        hpwl_val=final_hpwl,
        figure_path=legalized_figure_path,
        title=f"Legalized Macro Placement - HPWL: {final_hpwl:.2f}"
    )
    
    print(f"\nLegalized placement saved to: {legalized_placement_path}")
    print(f"Legalized figure saved to: {legalized_figure_path}")
    
    return final_hpwl, problem_instance


def step_7_cell_replacement(args, problem_instance, partition_result):
    """
    Step 7: Update macro positions and run DMP for cell placement.
    
    Steps:
    1. Run DMP on the current problem_instance to place cells around fixed macros
    2. Save final results (without adding suffixes - that's done in step 8)
    """
    print("\n" + "="*50)
    print("Step 7: Cell Replacement (with Fixed Macros)")
    print("="*50)
    # Step 1: Run DMP to place cells around fixed macros
    print("\nRunning DMP to place cells around fixed macros...")
    final_hpwl, tns, wns = problem_instance.place_2D()
    print(f"Final HPWL after cell placement: {final_hpwl:.2f}")
    
    # Step 2: Save final placement results
    partition_method = args.partition_params.get('method', 'GNN')
    result_dir = get_result_dir(partition_method)
    placement_path = os.path.join(result_dir, "mol_final", f"{args.benchmark}.def")
    figure_path = os.path.join(result_dir, "mol_final", f"{args.benchmark}.png")
    os.makedirs(os.path.dirname(placement_path), exist_ok=True)

    problem_instance.save_placement(placement_path)
    problem_instance.plot(final_hpwl, figure_path)
    
    print(f"Final placement saved to: {placement_path}")
    print(f"Final figure saved to: {figure_path}")
    
    return final_hpwl


def step_8_cell_legalization(args, partition_result):
    """
    Step 8: Legalize cells using DREAMPlace's legalize_op.
    
    Steps:
    1. Read mol_final/{$design}.def
    2. Change upper die macro status from FIXED to PLACED
    3. Read new def, create ProblemInstance
    4. Use legalize_op to legalize all movable components
    5. Restore upper die macro positions from step6
    6. Save new def, change upper die macro status back to FIXED
    7. Add die suffixes
    """
    print("\n" + "="*50)
    print("Step 8: Cell Legalization")
    print("="*50)
        
    # Step 1: Read mol_final/{$design}.def
    partition_method = args.partition_params.get('method', 'GNN')
    result_dir = get_result_dir(partition_method)
    input_def_path = os.path.join(result_dir, "mol_final", f"{args.benchmark}.def")
    
    if not os.path.exists(input_def_path):
        print(f"Error: Input DEF file not found: {input_def_path}")
        return
    
    print(f"Reading input DEF file: {input_def_path}")
    
    # Step 2: Change upper die macro status from FIXED to PLACED
    upper_die_macro_names = set(partition_result['upper_die_macro_names'])
    temp_def_path = input_def_path + ".temp_placed"
    
    print("\nChanging upper die macro status from FIXED to PLACED...")
    changed_count = DefProcessor.change_upper_die_macro_status_to_placed(
        upper_die_macro_names,
        input_def_path,
        temp_def_path
    )
    print(f"Changed {changed_count} upper die macro statuses")
    
    # Step 3: Read new def, create ProblemInstance from modified DEF
    print("\nCreating ProblemInstance from modified DEF...")
    # Create a temporary args object for the new ProblemInstance
    temp_args = copy.deepcopy(args)
    
    # Create new ProblemInstance with the modified DEF file path
    legalize_problem_instance = ProblemInstance(temp_args, args.benchmark, upper_die_macros=upper_die_macro_names, def_path=temp_def_path, rand_init=False)

    # Step 4: Save upper die macro positions before legalization
    print("\nSaving upper die macro positions before legalization...")
    macro_pos_dict = {}
    for macro_name in upper_die_macro_names:
        if macro_name in legalize_problem_instance.dmp_placedb.node_name2id_map:
            macro_idx = legalize_problem_instance.dmp_placedb.node_name2id_map[macro_name]
            macro_pos_dict[macro_name] = (
                legalize_problem_instance.dmp_placedb.node_x[macro_idx],
                legalize_problem_instance.dmp_placedb.node_y[macro_idx]
            )
    print(f"Saved {len(macro_pos_dict)} upper die macro positions")
    
    # Step 5: Use legalize method to legalize all movable components
    print("\nLegalizing all movable components...")
    legalized_hpwl = legalize_problem_instance.legalize()
    print("Legalization complete")
    
    # Step 6: Restore upper die macro positions after legalization
    print("\nRestoring upper die macro positions after legalization...")
    restored_count = 0
    for macro_name in upper_die_macro_names:
        if macro_name in legalize_problem_instance.dmp_placedb.node_name2id_map:
            macro_idx = legalize_problem_instance.dmp_placedb.node_name2id_map[macro_name]
            if macro_name in macro_pos_dict:
                pos_x, pos_y = macro_pos_dict[macro_name]
                legalize_problem_instance.dmp_placedb.node_x[macro_idx] = pos_x
                legalize_problem_instance.dmp_placedb.node_y[macro_idx] = pos_y
                restored_count += 1
    
    # Update results
    legalize_problem_instance.results['placement'] = (
        legalize_problem_instance.dmp_placedb.node_x.copy(),
        legalize_problem_instance.dmp_placedb.node_y.copy()
    )
    
    print(f"Restored {restored_count} upper die macro positions")
    
    # Step 7: Save new def
    legalized_def_path = input_def_path.replace('.def', '_legalized.def')
    figure_path = input_def_path.replace('.def', '_legalized.png')
    print(f"\nSaving legalized placement to: {legalized_def_path}")
    legalize_problem_instance.save_placement(legalized_def_path)
    legalize_problem_instance.results['figure'] = copy.copy(legalize_problem_instance.dmp_placer.pos[0].data.clone().cpu().numpy())
    legalize_problem_instance.plot(0, figure_path)
    # Step 8: DEF post-processing (single-pass: fix status, change direction, round coords, add suffixes)
    print("\n" + "="*50)
    print("Step 8: DEF Post-Processing")
    print("="*50)
    
    all_macro_names = set(partition_result['upper_die_macro_names']) | set(partition_result['bottom_die_macro_names'])
    print(f"Macros: {len(all_macro_names)} total (upper: {len(upper_die_macro_names)}, bottom: {len(partition_result['bottom_die_macro_names'])})")
    
    suffixed_def_path = os.path.join(result_dir, "mol_final", f"{args.benchmark}_suffixed.def")
    res = DefProcessor.def_post_process(
        all_macro_names,
        upper_die_macro_names,
        legalized_def_path,
        suffixed_def_path,
    )
    print(f"Fixed {res['fixed_count']} macros, direction→N {res['direction_count']}, rounded {res['rounded_count']}")
    print(f"Suffixes: {res['upper_count']} _upper, {res['bottom_count']} _bottom")
    print(f"Final DEF: {suffixed_def_path}")
    
    if os.path.exists(temp_def_path):
        os.remove(temp_def_path)
    if os.path.exists(legalized_def_path):
        os.remove(legalized_def_path)
    
    print("\nStep 8 complete!")

    return legalized_hpwl


def main():
    """
    Main function to perform 3D IC netlist partitioning and placement.
    The pipeline consists of 6 steps:
    1. Partition: Divide netlist into upper die and bottom die macros
    2. 2D Placement: Perform initial 2D placement
    3. Bottom-Die Macro Refinement: Refine bottom die macro positions (optional)
    4. Upper-Die Macro Placement: Place upper die macros
    5. Legalization: Legalize upper die macro positions (no overlap)
    6. Cell Replacement: Reload with fixed macros and re-place cells
    """
    # Record start time
    start_time = time.time()
    
    # Process arguments and load config
    args, config_path = process_args()
    
    partition_method = args.partition_params.get('method', 'GNN')
    result_dir = get_result_dir(partition_method)
    os.makedirs(result_dir, exist_ok=True)

    # Set random seed
    seed_torch(args.seed)
    
    # Create initial ProblemInstance
    print("\nCreating ProblemInstance...")
    init_problem_instance = ProblemInstance(args, args.benchmark)
    
    # Step 1: Partition
    partition_result = step_1_partition(args, init_problem_instance)

    # Step 2: 2D Placement for prototype
    gp_hpwl = step_2_prototype(args, init_problem_instance, partition_result)
    
    # Step 3: Bottom-Die Macro Refinement (optional)
    # This step reloads macro_fixed.def from Step 2
    problem_instance, refined_hpwl = step_3_bottom_die_macro_refinement(
        args, 
        partition_result, 
        gp_hpwl
    )
    
    # Step 4: Bottom-Die Macro Legalization
    bottom_legalized_hpwl, problem_instance = step_4_bottom_die_legalization(
        args,
        problem_instance,
        partition_result
    )
    
    # Step 5: Upper-Die Macro Placement
    step_5_upper_die_macro_placement(
        args, 
        problem_instance,
        partition_result, 
        refined_hpwl
    )
    
    # Step 6: Upper-Die Macro Legalization
    upper_legalized_hpwl, legalized_problem_instance = step_6_upper_die_legalization(
        args, 
        problem_instance,
        partition_result
    )
    
    # Use upper_legalized DEF file to initialize shrunk_problem_instance
    # This ensures it uses the correct legalized macro positions
    partition_method = args.partition_params.get('method', 'GNN')
    result_dir = get_result_dir(partition_method)
    upper_legalized_def_path = os.path.join(result_dir, "upper_legalized", f"{args.benchmark}_legalized.def")
    
    print(f"\nCreating shrunk_problem_instance from {upper_legalized_def_path}...")
    shrunk_problem_instance = ProblemInstance(
        args,
        args.benchmark,
        upper_die_macros=partition_result['upper_die_macro_names'],
        only_cells=True,
        def_path=upper_legalized_def_path
    )
    
    # Step 7: Cell Replacement (with fixed macros)
    final_cell_hpwl = step_7_cell_replacement(args, shrunk_problem_instance, partition_result)

    # Step 8: Legalize cells
    legalized_hpwl = step_8_cell_legalization(args, partition_result)

    # Calculate total runtime
    total_runtime = time.time() - start_time
    
    # Print final summary
    print("\n" + "="*50)
    print("Pipeline Summary")
    print("="*50)
    print(f"Initial 2D HPWL: {gp_hpwl:.2f}")
    if getattr(args, 'enable_bottom_die_refinement', False):
        print(f"After Bottom-Die Refinement: {refined_hpwl:.2f}")
    print(f"After Bottom-Die Legalization: {bottom_legalized_hpwl:.2f}")
    print(f"After Upper-Die Legalization: {upper_legalized_hpwl:.2f}")
    print(f"Mem-on-logic HPWL before legalization: {final_cell_hpwl:.2f}")
    print(f"Mem-on-logic HPWL after legalization: {legalized_hpwl:.2f}")
    print(f"Total Runtime: {total_runtime:.2f} seconds ({total_runtime/60:.2f} minutes)")
    print("="*50)


    # Save final_cell_hpwl to CSV file
    partition_method = args.partition_params.get('method', 'GNN')
    result_dir = get_result_dir(partition_method)
    csv_path = os.path.join(result_dir, "mol_final", "mem_on_logic_results.csv")
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    
    # Read existing data if file exists
    existing_rows = []
    if os.path.exists(csv_path):
        with open(csv_path, 'r', newline='') as f:
            existing_rows = list(csv.reader(f))
    
    # Add runtime column if missing
    if existing_rows and 'runtime' not in existing_rows[0]:
        existing_rows[0].append('runtime')
        for row in existing_rows[1:]:
            row.append('')
        with open(csv_path, 'w', newline='') as f:
            csv.writer(f).writerows(existing_rows)
    
    # Append new result
    with open(csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        if not existing_rows:
            writer.writerow(['design_name', 'hpwl', 'hpwl_lg', 'runtime'])
        writer.writerow([args.benchmark, final_cell_hpwl, legalized_hpwl, total_runtime])
    
    print(f"\nSaved result to CSV: {csv_path}")
    print(f"  Design: {args.benchmark}, HPWL: {final_cell_hpwl:.2f}, HPWL after legalization: {legalized_hpwl:.2f}, Runtime: {total_runtime:.2f}s")


if __name__ == "__main__":
    main()

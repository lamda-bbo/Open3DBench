import torch
import torch.nn as nn
import numpy as np
from typing import Optional, Tuple
import pdb
import os
import copy
import math
import time
from torch.utils.tensorboard import SummaryWriter
import sys
# Add parent directory to path for utils import
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)
from utils.hpwl_computer import HPWLComputer
from utils.layout_plotter import LayoutPlotter


class MacroRefiner:
    """
    Gradient descent based macro position optimizer.
    Only optimizes macro positions while keeping cell positions fixed.
    Objective function: HPWL + edge alignment regularity
    """
    
    def __init__(self, problem_instance, macros_to_refine, params: dict, device: Optional[str] = None):
        """
        Initialize the macro refiner.
        
        Args:
            problem_instance: ProblemInstance object containing dmp_placedb and placement results
            macros_to_refine: List of macro node names to refine
            params: Dictionary containing hyperparameters:
                - hpwl_weight: Weight for HPWL term (default: 1.0)
                - regularity_weight: Weight for edge alignment regularity term (default: 0.1)
                - overlap_weight_init: Initial overlap weight for schedule (default: 0.0)
                - overlap_weight: Final overlap weight for schedule (default: 1.0)
                - overlap_weight_alpha: Exponential growth rate for overlap weight schedule (default: 3.0)
                - learning_rate: Learning rate for gradient descent (default: 0.01)
                - learning_rate_decay: Learning rate decay factor (default: 0.9)
                - learning_rate_decay_interval: Decay learning rate every N iterations (None to disable, default: None)
                - learning_rate_min: Minimum learning rate (default: 1e-6)
                - lr_plateau_patience: Patience for plateau-based decay (default: 100)
                - estimate_initial_lr: Whether to estimate initial learning rate (default: False)
                - continue_until_no_overlap: Continue iterating until overlap is near zero (default: True)
                - overlap_threshold: Overlap threshold to stop extra iterations (default: 1e-6)
                - max_extra_iterations: Maximum extra iterations when overlap exists (default: 1000)
                - wa_gamma: Gamma parameter for Weighted-Average Wirelength (WA) approximation (default: 0.1)
                - hpwl_max_group_size: Max group size for HPWL computation (default: 1000)
            device: PyTorch device ('cuda' or 'cpu'), auto-detect if None
        """
        self.problem_instance = problem_instance
        self.placedb = problem_instance.dmp_placedb
        self.macros_to_refine = macros_to_refine
        
        # Get hyperparameters from params dictionary
        self.hpwl_weight = params.get('hpwl_weight', 1.0)
        self.regularity_weight_final = params.get('regularity_weight', 0.1)
        # Regularity weight scheduler removed - using fixed weight
        self.overlap_weight_init = params.get('overlap_weight_init', 0.0)
        self.overlap_weight_final = params.get('overlap_weight', 1.0)
        self.overlap_weight_alpha = params.get('overlap_weight_alpha', 3.0)
        self.learning_rate = params.get('learning_rate', 0.01)
        self.learning_rate_decay = params.get('learning_rate_decay', 0.9)
        self.learning_rate_decay_interval = params.get('learning_rate_decay_interval', None)
        self.learning_rate_min = params.get('learning_rate_min', 1e-6)
        self.continue_until_no_overlap = params.get('continue_until_no_overlap', True)
        self.overlap_threshold = params.get('overlap_threshold', 1e-6)
        self.max_extra_iterations = params.get('max_extra_iterations', 1000)
        # Gamma parameter for Weighted-Average Wirelength (WA) approximation
        # Decreasing gamma enhances accuracy but reduces smoothness
        self.gamma = params.get('wa_gamma', 0.1)
        # Max group size for HPWL computation
        self.hpwl_max_group_size = params.get('hpwl_max_group_size', 1000)
        self.estimate_initial_lr = params.get('estimate_initial_lr', False)
        self.lr_plateau_patience = params.get('lr_plateau_patience', 100)
        
        # Set device
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        # Extract macro and cell information
        self._extract_macro_cell_info()
        
        # Extract pin offset information (needed for _compute_pin_positions)
        self.pin_offset_x = torch.tensor(
            self.placedb.pin_offset_x, 
            dtype=torch.float32, device=self.device
        )
        self.pin_offset_y = torch.tensor(
            self.placedb.pin_offset_y, 
            dtype=torch.float32, device=self.device
        )
        
        # Create HPWL computer for HPWL calculation
        self.hpwl_computer = HPWLComputer(
            placedb=self.placedb,
            macro_indices=self.macro_indices,
            gamma=self.gamma,
            device=self.device,
            use_grouped_mode=True,  # Use grouped mode for efficiency
            max_group_size=self.hpwl_max_group_size
        )
        
        # Initialize optimization variables
        self.macro_pos = None
        self.cell_pos = None
        self._init_positions()
    
    def _extract_macro_cell_info(self):
        """Extract macro and cell node indices."""
        # Get all macro node IDs
        self.macro_indices = np.array([self.placedb.node_name2id_map[name] for name in self.macros_to_refine], dtype=np.int64)
        self.n_macros = len(self.macro_indices)
        
        # Get all cell node IDs
        all_nodes = np.arange(self.placedb.num_physical_nodes)
        self.cell_indices = np.setdiff1d(all_nodes, self.macro_indices)
        self.n_cells = len(self.cell_indices)
        
        # Get macro and cell sizes
        self.macro_size_x = torch.tensor(
            self.placedb.node_size_x[self.macro_indices], 
            dtype=torch.float32, device=self.device
        )
        self.macro_size_y = torch.tensor(
            self.placedb.node_size_y[self.macro_indices], 
            dtype=torch.float32, device=self.device
        )
        self.cell_size_x = torch.tensor(
            self.placedb.node_size_x[self.cell_indices], 
            dtype=torch.float32, device=self.device
        )
        self.cell_size_y = torch.tensor(
            self.placedb.node_size_y[self.cell_indices], 
            dtype=torch.float32, device=self.device
        )
        
        # Get layout boundaries
        self.xl = float(self.placedb.xl)
        self.yl = float(self.placedb.yl)
        self.xh = float(self.placedb.xh)
        self.yh = float(self.placedb.yh)
    
    
    def _init_positions(self):
        """Initialize macro and cell positions from placement results."""
        # Get current positions from placement results
        if hasattr(self.problem_instance, 'results') and 'placement' in self.problem_instance.results:
            node_x, node_y = self.problem_instance.results['placement']
        else:
            node_x = self.placedb.node_x.copy()
            node_y = self.placedb.node_y.copy()
        
        # Extract macro positions (requires gradient)
        # Create as a single tensor with requires_grad=True
        macro_positions = np.stack([
            node_x[self.macro_indices],
            node_y[self.macro_indices]
        ], axis=0)  # Shape: [2, n_macros]
        self.macro_pos = torch.tensor(
            macro_positions,
            dtype=torch.float32, 
            device=self.device, 
            requires_grad=True
        )
        
        # Extract cell positions (fixed, no gradient)
        cell_positions = np.stack([
            node_x[self.cell_indices],
            node_y[self.cell_indices]
        ], axis=0)  # Shape: [2, n_cells]
        self.cell_pos = torch.tensor(
            cell_positions,
            dtype=torch.float32, 
            device=self.device, 
            requires_grad=False
        )
    
    def _compute_pin_positions(self):
        """
        Compute pin positions from node positions using vectorized operations.
        Returns:
            pin_pos: Tensor of shape [2, n_pins] (x, y coordinates)
        """
        n_pins = len(self.placedb.pin2node_map)
        
        # Get node positions
        node_pos = torch.zeros(2, self.placedb.num_physical_nodes, 
                              dtype=torch.float32, device=self.device)
        
        # Fill macro positions using vectorized indexing
        macro_node_ids = torch.tensor(self.macro_indices, dtype=torch.long, device=self.device)
        node_pos[0, macro_node_ids] = self.macro_pos[0, :]
        node_pos[1, macro_node_ids] = self.macro_pos[1, :]
        
        # Fill cell positions using vectorized indexing
        cell_node_ids = torch.tensor(self.cell_indices, dtype=torch.long, device=self.device)
        node_pos[0, cell_node_ids] = self.cell_pos[0, :]
        node_pos[1, cell_node_ids] = self.cell_pos[1, :]
        
        # Compute pin positions: node position + pin offset (vectorized)
        node_ids = torch.tensor(self.placedb.pin2node_map, dtype=torch.long, device=self.device)  # [n_pins]
        pin_pos = torch.zeros(2, n_pins, dtype=torch.float32, device=self.device)
        pin_pos[0, :] = node_pos[0, node_ids] + self.pin_offset_x
        pin_pos[1, :] = node_pos[1, node_ids] + self.pin_offset_y
        
        return pin_pos
    
    def _compute_hpwl(self, pin_pos):
        """
        Compute Weighted-Average Wire Length (WA) for nets connected to macros.
        Uses HPWLComputer for the actual computation.
        
        Args:
            pin_pos: Tensor of shape [2, n_pins] (x, y coordinates)
        
        Returns:
            wa_wl: Scalar tensor representing total WA wirelength of macro-related nets
        """
        return self.hpwl_computer.compute(pin_pos)
    
    def _compute_edge_alignment_regularity(self):
        """
        Compute edge alignment regularity penalty using periphery cost function.
        Based on the paper: "Pu et al., IncreMacro: Incremental Macro Placement Refinement."
        
        Periphery cost function:
        P_i^H = |w_core/2 - x_i| + (w_core/2)^2 / |w_core/2 - x_i|
        P_i^V = |h_core/2 - y_i| + (h_core/2)^2 / |h_core/2 - y_i|
        P_i = P_i^H + P_i^V
        
        Returns:
            regularity_loss: Scalar tensor representing periphery cost
        """
        macro_x = self.macro_pos[0, :]  # [n_macros]
        macro_y = self.macro_pos[1, :]  # [n_macros]
        
        # Compute core dimensions
        w_core = self.xh - self.xl
        h_core = self.yh - self.yl
        
        # Core center coordinates (relative to core left-bottom corner)
        x_center = w_core / 2.0
        y_center = h_core / 2.0
        
        # Macro positions relative to core left-bottom corner
        x_ = macro_x - self.xl
        y_ = macro_y - self.yl
        
        # Distance from macro to core center
        # |w_core/2 - x_i| where x_i is position from left edge
        dist_x_from_center = torch.abs(x_center - x_)
        dist_y_from_center = torch.abs(y_center - y_)
        
        # Add small epsilon to avoid division by zero
        eps = 1e-8
        
        # Horizontal periphery cost: P_i^H = |w_core/2 - x_i| + (w_core/2)^2 / |w_core/2 - x_i|
        P_H = dist_x_from_center + (x_center ** 2) / (dist_x_from_center + eps)
        
        # Vertical periphery cost: P_i^V = |h_core/2 - y_i| + (h_core/2)^2 / |h_core/2 - y_i|
        P_V = dist_y_from_center + (y_center ** 2) / (dist_y_from_center + eps)
        
        # Total periphery cost for each macro: P_i = P_i^H + P_i^V
        P = P_H + P_V
        
        # Regularity loss: sum of periphery costs (minimize to push macros to periphery)
        regularity_loss = P.sum()
        
        return regularity_loss
    
    def _compute_overlap_1d(self, pos_i, pos_j, size_i, size_j):
        """
        Compute pairwise overlap in one direction.
        
        Overlap is defined as:
        - If pos_j <= pos_i and |pos_i - pos_j| < size_j/2 + size_i/2:
          Overlap_hat_ij = (pos_j + size_j/2) - (pos_i - size_i/2)
        - If pos_j > pos_i and |pos_i - pos_j| < size_j/2 + size_i/2:
          Overlap_hat_ij = (pos_i + size_i/2) - (pos_j - size_j/2)
        - Otherwise: Overlap_hat_ij = 0
        
        Args:
            pos_i: Position tensor of shape [n_macros, 1]
            pos_j: Position tensor of shape [1, n_macros]
            size_i: Size tensor of shape [n_macros, 1]
            size_j: Size tensor of shape [1, n_macros]
        
        Returns:
            overlap: Overlap tensor of shape [n_macros, n_macros]
        """
        # Condition: |pos_i - pos_j| < size_j/2 + size_i/2 (modules are overlapping or touching)
        dist = torch.abs(pos_i - pos_j)  # [n_macros, n_macros]
        threshold = (size_i + size_j) / 2.0  # [n_macros, n_macros]
        overlap_condition = dist < threshold
        
        # Case 1: pos_j <= pos_i
        case1 = (pos_j <= pos_i) & overlap_condition
        overlap_case1 = (pos_j + size_j / 2.0) - (pos_i - size_i / 2.0)
        
        # Case 2: pos_j > pos_i
        case2 = (pos_j > pos_i) & overlap_condition
        overlap_case2 = (pos_i + size_i / 2.0) - (pos_j - size_j / 2.0)
        
        # Combine cases and ensure non-negative
        overlap = torch.where(case1, overlap_case1,
                             torch.where(case2, overlap_case2,
                                        torch.zeros_like(dist)))
        overlap = torch.clamp(overlap, min=0.0)  # Ensure non-negative
        
        return overlap
    
    def _compute_robust_overlap(self):
        """
        Compute robust pairwise overlap between all macro pairs.        
        Returns:
            total_overlap: Scalar tensor representing total overlap penalty
        """
        macro_x = self.macro_pos[0, :]  # [n_macros]
        macro_y = self.macro_pos[1, :]  # [n_macros]
        macro_w = self.macro_size_x  # [n_macros]
        macro_h = self.macro_size_y  # [n_macros]
        
        n_macros = self.n_macros
        
        # Expand dimensions for broadcasting: [n_macros, 1] and [1, n_macros]
        x_i = macro_x.unsqueeze(1)  # [n_macros, 1]
        x_j = macro_x.unsqueeze(0)  # [1, n_macros]
        y_i = macro_y.unsqueeze(1)  # [n_macros, 1]
        y_j = macro_y.unsqueeze(0)  # [1, n_macros]
        w_i = macro_w.unsqueeze(1)  # [n_macros, 1]
        w_j = macro_w.unsqueeze(0)  # [1, n_macros]
        h_i = macro_h.unsqueeze(1)  # [n_macros, 1]
        h_j = macro_h.unsqueeze(0)  # [1, n_macros]
        
        # Compute overlap in x and y directions using the same function
        overlap_x = self._compute_overlap_1d(x_i, x_j, w_i, w_j)
        overlap_y = self._compute_overlap_1d(y_i, y_j, h_i, h_j)
        
        # Total overlap: Overlap_hat_ij = Overlap_hat_ijx * Overlap_hat_ijy
        overlap_ij = overlap_x * overlap_y  # [n_macros, n_macros]
        
        # Sum all pairwise overlaps (excluding self-overlap, i.e., diagonal)
        # Create mask to exclude diagonal (self-overlap)
        mask = ~torch.eye(n_macros, dtype=torch.bool, device=self.device)
        total_overlap = torch.sum(overlap_ij * mask.float())
        
        return total_overlap
    
    def _apply_boundary_constraints(self):
        """Apply boundary constraints to keep macros within layout boundaries."""
        with torch.no_grad():
            # First clamp right edge (x + size_x) to ensure macro doesn't exceed xh
            macro_right_edge = self.macro_pos[0, :] + self.macro_size_x
            macro_right_edge.clamp_(max=self.xh)
            self.macro_pos[0, :] = macro_right_edge - self.macro_size_x
            
            # Then clamp left edge (x) to ensure macro doesn't go below xl
            self.macro_pos[0, :].clamp_(min=self.xl)
            
            # First clamp top edge (y + size_y) to ensure macro doesn't exceed yh
            macro_top_edge = self.macro_pos[1, :] + self.macro_size_y
            macro_top_edge.clamp_(max=self.yh)
            self.macro_pos[1, :] = macro_top_edge - self.macro_size_y
            
            # Then clamp bottom edge (y) to ensure macro doesn't go below yl
            self.macro_pos[1, :].clamp_(min=self.yl)
    
    def _get_exponential_weight_schedule(self, iteration: int, num_iterations: int, 
                                        weight_init: float, weight_final: float, alpha: float):
        """
        Compute weight using exponential schedule.
        Weight increases exponentially from weight_init to weight_final.
        
        Formula: weight = init + (final - init) * ((exp(alpha * progress) - 1) / (exp(alpha) - 1))
        where progress = iteration / (num_iterations - 1)
        
        Args:
            iteration: Current iteration (0-indexed)
            num_iterations: Total number of iterations
            weight_init: Initial weight value
            weight_final: Final weight value
            alpha: Exponential growth rate
        
        Returns:
            weight: Current weight value
        """
        if num_iterations <= 1:
            return weight_final
        
        progress = iteration / (num_iterations - 1)
        
        # Exponential schedule: weight = init + (final - init) * ((exp(alpha * progress) - 1) / (exp(alpha) - 1))
        # This ensures weight = init when progress = 0, and weight = final when progress = 1
        exp_alpha = math.exp(alpha)
        exp_alpha_progress = math.exp(alpha * progress)
        exponential_factor = (exp_alpha_progress - 1.0) / (exp_alpha - 1.0)
        
        weight = weight_init + (weight_final - weight_init) * exponential_factor
        
        return weight
    
    def _get_overlap_weight(self, iteration: int, num_iterations: int):
        """
        Compute overlap weight using exponential schedule.
        
        Args:
            iteration: Current iteration (0-indexed)
            num_iterations: Total number of iterations
        
        Returns:
            overlap_weight: Current overlap weight value
        """
        return self._get_exponential_weight_schedule(
            iteration, num_iterations,
            self.overlap_weight_init, self.overlap_weight_final, self.overlap_weight_alpha
        )
    
    def _get_regularity_weight(self, iteration: int, num_iterations: int):
        """
        Get regularity weight (fixed value, scheduler removed).
        
        Args:
            iteration: Current iteration (0-indexed) - unused, kept for compatibility
            num_iterations: Total number of iterations - unused, kept for compatibility
        
        Returns:
            regularity_weight: Fixed regularity weight value
        """
        return self.regularity_weight_final
    
    def _estimate_initial_learning_rate(self, macro_pos_tensor, initial_lr_hint):
        """
        Estimate initial learning rate by moving a small step.
        Based on PlaceObj.estimate_initial_learning_rate in DREAMPlace.
        
        Computed as | x_k - x_k_1 |_2 / | g_k - g_k_1 |_2.
        
        Args:
            macro_pos_tensor: Current macro positions tensor [2, n_macros] with requires_grad=True
            initial_lr_hint: Small step size hint for estimation
        
        Returns:
            estimated_lr: Estimated learning rate (scalar tensor)
        """
        # Store original macro_pos data (we'll restore it as a leaf tensor later)
        original_macro_pos_data = self.macro_pos.detach().clone()
        self.macro_pos = macro_pos_tensor
        
        # Compute objective and gradient at current position
        pin_pos = self._compute_pin_positions()
        hpwl = self._compute_hpwl(pin_pos)
        regularity = self._compute_edge_alignment_regularity()
        overlap = self._compute_robust_overlap()
        current_overlap_weight = self._get_overlap_weight(0, 1)  # Use iteration 0 for estimation
        
        current_regularity_weight = self._get_regularity_weight(0, 1)  # Use iteration 0 for estimation
        total_loss_k = (self.hpwl_weight * hpwl + 
                       current_regularity_weight * regularity +
                       current_overlap_weight * overlap)
        
        # Zero gradients and compute gradient
        if macro_pos_tensor.grad is not None:
            macro_pos_tensor.grad.zero_()
        total_loss_k.backward()
        g_k = macro_pos_tensor.grad.clone() if macro_pos_tensor.grad is not None else torch.zeros_like(macro_pos_tensor)
        
        # Move a small step: x_k_1 = x_k - initial_lr_hint * g_k
        x_k_1 = macro_pos_tensor - initial_lr_hint * g_k
        x_k_1 = x_k_1.detach().clone().requires_grad_(True)
        
        # Compute objective and gradient at new position
        self.macro_pos = x_k_1
        pin_pos_1 = self._compute_pin_positions()
        hpwl_1 = self._compute_hpwl(pin_pos_1)
        regularity_1 = self._compute_edge_alignment_regularity()
        overlap_1 = self._compute_robust_overlap()
        
        total_loss_k_1 = (self.hpwl_weight * hpwl_1 + 
                         current_regularity_weight * regularity_1 +
                         current_overlap_weight * overlap_1)
        
        # Zero gradients and compute gradient at new position
        if x_k_1.grad is not None:
            x_k_1.grad.zero_()
        total_loss_k_1.backward()
        g_k_1 = x_k_1.grad.clone() if x_k_1.grad is not None else torch.zeros_like(x_k_1)
        
        # Estimate learning rate: |x_k - x_k_1|_2 / |g_k - g_k_1|_2
        x_diff = (macro_pos_tensor - x_k_1).norm(p=2)
        g_diff = (g_k - g_k_1).norm(p=2)
        
        if g_diff > 1e-10:  # Avoid division by zero
            estimated_lr = x_diff / g_diff
        else:
            estimated_lr = torch.tensor(initial_lr_hint, dtype=torch.float32, device=self.device)
        
        # Restore original macro_pos as a leaf tensor (important for optimizer)
        self.macro_pos = original_macro_pos_data.requires_grad_(True)
        
        return estimated_lr
    
    def optimize(self, num_iterations: int = 100, verbose: bool = True, plot_interval: Optional[int] = None, plot_dir: Optional[str] = None, log_dir: Optional[str] = None):
        """
        Perform gradient descent optimization using PyTorch SGD.
        
        Args:
            num_iterations: Number of optimization iterations
            verbose: Whether to print progress
            plot_interval: Plot layout every k iterations (None to disable plotting)
            plot_dir: Directory to save plots (required if plot_interval is set)
            log_dir: Directory to save tensorboard logs (None to disable tensorboard)
        
        Returns:
            final_hpwl: Final HPWL value
            final_regularity: Final regularity value
            history: Dictionary containing optimization history
        """
        history = {
            'hpwl': [],
            'regularity': [],
            'overlap': [],
            'total_loss': [],
            'grad_norm': [],
            'iteration_time': [],
            'cumulative_time': []
        }
        
        # Initialize timing
        start_time = time.time()
        cumulative_time = 0.0
        
        # Initialize tensorboard writer
        writer = None
        if log_dir is not None:
            os.makedirs(log_dir, exist_ok=True)
            writer = SummaryWriter(log_dir=log_dir)
        
        # Ensure macro_pos requires grad
        self.macro_pos.requires_grad_(True)
        
        # Estimate initial learning rate if enabled
        if self.estimate_initial_lr:
            if verbose:
                print("Estimating initial learning rate...")
            estimated_lr = self._estimate_initial_learning_rate(self.macro_pos, self.learning_rate)
            estimated_lr_val = estimated_lr.item() if isinstance(estimated_lr, torch.Tensor) else estimated_lr
            # Use estimated LR, but clamp to reasonable range
            estimated_lr_val = max(self.learning_rate_min, min(estimated_lr_val, self.learning_rate * 10))
            if verbose:
                print(f"  Estimated learning rate: {estimated_lr_val:.6f} (hint: {self.learning_rate:.6f})")
            self.learning_rate = estimated_lr_val
        
        # Create optimizer
        optimizer = torch.optim.SGD([self.macro_pos], lr=self.learning_rate, momentum=0.9, nesterov=True)
        
        # Learning rate adjustment tracking
        current_lr = self.learning_rate
        best_loss = float('inf')
        plateau_count = 0
        plateau_patience = self.lr_plateau_patience
        
        iteration = 0
        extra_iterations = 0
        overlap_val = None  # Will be computed in first iteration
        
        while True:
            # Check if we should continue before starting iteration
            if iteration >= num_iterations:
                # Base iterations completed, check if we should continue with extra iterations
                if not (self.continue_until_no_overlap and 
                       overlap_val is not None and 
                       overlap_val > self.overlap_threshold and 
                       extra_iterations < self.max_extra_iterations):
                    # Stop iteration
                    break
                # Continue with extra iterations to eliminate overlap
                if extra_iterations == 0 and verbose:
                    print(f"\nOverlap detected ({overlap_val:.6f} > {self.overlap_threshold:.6f}), continuing optimization...")
                extra_iterations += 1
            
            iter_start_time = time.time()
            optimizer.zero_grad()
            
            # Compute pin positions
            pin_pos = self._compute_pin_positions()
            
            # Compute HPWL
            hpwl = self._compute_hpwl(pin_pos)
            
            # Compute edge alignment regularity
            regularity = self._compute_edge_alignment_regularity()
            
            # Compute robust overlap penalty
            overlap = self._compute_robust_overlap()
            
            # Get current weights from schedule
            if iteration < num_iterations:
                # Use scheduled weights during base iterations
                current_overlap_weight = self._get_overlap_weight(iteration, num_iterations)
                current_regularity_weight = self._get_regularity_weight(iteration, num_iterations)
            else:
                # Use final weights for extra iterations
                current_overlap_weight = self.overlap_weight_final
                current_regularity_weight = self.regularity_weight_final
            
            # Total loss
            total_loss = (self.hpwl_weight * hpwl + 
                         current_regularity_weight * regularity +
                         current_overlap_weight * overlap)
            
            # Backward pass
            total_loss.backward()
            
            # Compute gradient norm
            if self.macro_pos.grad is not None:
                grad_norm = self.macro_pos.grad.norm().item()
            else:
                grad_norm = 0.0
            
            # Update parameters
            optimizer.step()

            # Apply boundary constraints
            self._apply_boundary_constraints()
            
            # Record history
            hpwl_val = hpwl.item()
            regularity_val = regularity.item()
            overlap_val = overlap.item()
            loss_val = total_loss.item()
            
            # Calculate iteration time
            iter_time = time.time() - iter_start_time
            cumulative_time += iter_time
            
            history['hpwl'].append(hpwl_val)
            history['regularity'].append(regularity_val)
            history['overlap'].append(overlap_val)
            history['total_loss'].append(loss_val)
            history['grad_norm'].append(grad_norm)
            history['iteration_time'].append(iter_time)
            history['cumulative_time'].append(cumulative_time)
            
            # Learning rate adjustment based on DREAMPlace strategy
            # Strategy 1: Fixed interval decay (if learning_rate_decay_interval is set)
            if self.learning_rate_decay_interval is not None and (iteration + 1) % self.learning_rate_decay_interval == 0:
                for param_group in optimizer.param_groups:
                    old_lr = param_group['lr']
                    new_lr = old_lr * self.learning_rate_decay
                    new_lr = max(new_lr, self.learning_rate_min)
                    param_group['lr'] = new_lr
                    current_lr = new_lr
                    if verbose:
                        print(f"  Learning rate decayed: {old_lr:.6f} -> {new_lr:.6f}")
            
            # Strategy 2: Plateau-based decay (if loss doesn't improve for plateau_patience iterations)
            if loss_val < best_loss:
                best_loss = loss_val
                plateau_count = 0
            else:
                plateau_count += 1
                if plateau_count >= plateau_patience:
                    for param_group in optimizer.param_groups:
                        old_lr = param_group['lr']
                        new_lr = old_lr * self.learning_rate_decay
                        new_lr = max(new_lr, self.learning_rate_min)
                        if new_lr < old_lr:  # Only decay if not already at minimum
                            param_group['lr'] = new_lr
                            current_lr = new_lr
                            if verbose:
                                print(f"  Learning rate decayed (plateau): {old_lr:.6f} -> {new_lr:.6f}")
                            plateau_count = 0  # Reset counter after decay
            
            # Get current learning rate
            current_lr = optimizer.param_groups[0]['lr']
            
            # Determine total iteration number for logging
            total_iter = iteration if iteration < num_iterations else num_iterations + extra_iterations
            
            # Log to tensorboard
            if writer is not None:
                writer.add_scalar('Loss/HPWL', hpwl_val, total_iter)
                writer.add_scalar('Loss/Regularity', regularity_val, total_iter)
                writer.add_scalar('Loss/Overlap', overlap_val, total_iter)
                writer.add_scalar('Loss/Total', loss_val, total_iter)
                writer.add_scalar('Loss/Overlap_Weight', current_overlap_weight, total_iter)
                writer.add_scalar('Loss/Regularity_Weight', current_regularity_weight, total_iter)
                writer.add_scalar('Training/Gradient_Norm', grad_norm, total_iter)
                writer.add_scalar('Training/Iteration_Time', iter_time, total_iter)
                writer.add_scalar('Training/Cumulative_Time', cumulative_time, total_iter)
                writer.add_scalar('Training/Learning_Rate', current_lr, total_iter)
                writer.add_scalar('Training/Best_Loss', best_loss, total_iter)
            
            # Print initial metrics at first iteration
            if verbose and iteration == 0:
                print(f"\nInitial Metrics (Iteration 0):")
                print(f"  HPWL: {hpwl_val:.6f}")
                print(f"  Regularity: {regularity_val:.6f}")
                print(f"  Overlap: {overlap_val:.6f}")
                print(f"  Regularity Weight: {current_regularity_weight:.6f}")
                print(f"  Overlap Weight: {current_overlap_weight:.6f}")
                print(f"  Total Loss: {loss_val:.6f}")
                print(f"  Gradient Norm: {grad_norm:.6f}")
                print(f"  Learning Rate: {current_lr:.6f}")
                print()
            
            # Print progress
            if iteration < num_iterations:
                # Base iteration progress
                if verbose and (iteration + 1) % 50 == 0:
                    avg_iter_time = cumulative_time / (iteration + 1)
                    remaining_iterations = num_iterations - (iteration + 1)
                    estimated_remaining_time = avg_iter_time * remaining_iterations
                    print(f"Iteration {iteration + 1}/{num_iterations}: "
                          f"HPWL={hpwl_val:.2f}, Regularity={regularity_val:.2f}, "
                          f"Overlap={overlap_val:.2f}, Regularity Weight={current_regularity_weight:.4f}, "
                          f"Overlap Weight={current_overlap_weight:.4f}, "
                          f"Total Loss={loss_val:.2f}, Grad Norm={grad_norm:.4f}, "
                          f"LR={current_lr:.6f}, Time={iter_time:.3f}s, Total={cumulative_time:.1f}s, "
                          f"ETA={estimated_remaining_time:.1f}s")
                
                # Plot layout every k iterations
                if plot_interval is not None and plot_dir is not None and (iteration + 1) % plot_interval == 0:
                    figure_path = self._plot_layout(iteration + 1, hpwl_val, plot_dir)
                    if verbose:
                        print(f"  Layout plot saved to: {figure_path}")
            else:
                # Extra iteration progress
                if verbose and extra_iterations % 50 == 0:
                    print(f"Extra Iteration {extra_iterations}: "
                          f"HPWL={hpwl_val:.2f}, Regularity={regularity_val:.2f}, "
                          f"Overlap={overlap_val:.6f}, Regularity Weight={current_regularity_weight:.4f}, "
                          f"Overlap Weight={current_overlap_weight:.4f}, "
                          f"Total Loss={loss_val:.2f}, Grad Norm={grad_norm:.4f}, LR={current_lr:.6f}")
                # Plot during extra iterations as well
                if plot_interval is not None and plot_dir is not None and total_iter % plot_interval == 0:
                    figure_path = self._plot_layout(total_iter, hpwl_val, plot_dir)
                    if verbose:
                        print(f"  Layout plot saved to: {figure_path}")
            
            # Increment iteration counter
            iteration += 1
            
            # Check if overlap is below threshold (for extra iterations) - after increment
            if iteration > num_iterations and overlap_val <= self.overlap_threshold:
                if verbose:
                    print(f"\nOverlap reduced to {overlap_val:.6f} (threshold: {self.overlap_threshold:.6f}), stopping extra iterations.")
                break
        
        # Check if we reached max extra iterations
        if extra_iterations >= self.max_extra_iterations and overlap_val > self.overlap_threshold:
            if verbose:
                print(f"\nReached maximum extra iterations ({self.max_extra_iterations}), stopping.")
                print(f"  Final overlap: {overlap_val:.6f} (threshold: {self.overlap_threshold:.6f})")
        
        # Final timing statistics
        total_iterations = iteration
        total_time = time.time() - start_time
        avg_iter_time = total_time / total_iterations if total_iterations > 0 else 0.0
        
        if verbose:
            print(f"\nOptimization completed:")
            print(f"  Total iterations: {total_iterations} (base: {num_iterations}, extra: {extra_iterations})")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Average iteration time: {avg_iter_time:.4f}s")
            print(f"  Iterations per second: {total_iterations / total_time:.2f}")
            print(f"  Final overlap: {overlap_val:.6f}")
        
        # Log final statistics to tensorboard
        if writer is not None:
            writer.add_scalar('Summary/Total_Iterations', total_iterations, total_iterations)
            writer.add_scalar('Summary/Extra_Iterations', extra_iterations, total_iterations)
            writer.add_scalar('Summary/Total_Time', total_time, total_iterations)
            writer.add_scalar('Summary/Average_Iteration_Time', avg_iter_time, total_iterations)
            writer.add_scalar('Summary/Iterations_Per_Second', total_iterations / total_time, total_iterations)
            writer.add_scalar('Summary/Final_Overlap', overlap_val, total_iterations)
            writer.close()
        
        final_hpwl = history['hpwl'][-1]
        final_regularity = history['regularity'][-1]
        
        # Add timing summary to history
        history['total_time'] = total_time
        history['avg_iteration_time'] = avg_iter_time
        history['total_iterations'] = total_iterations
        history['extra_iterations'] = extra_iterations
        history['final_learning_rate'] = current_lr
        history['best_loss'] = best_loss
        history['final_overlap'] = overlap_val
        
        return final_hpwl, final_regularity, history
    
    def get_optimized_positions(self):
        """
        Get optimized macro positions.
        
        Returns:
            macro_x: Optimized macro x coordinates (numpy array)
            macro_y: Optimized macro y coordinates (numpy array)
        """
        macro_x = self.macro_pos[0, :].detach().cpu().numpy()
        macro_y = self.macro_pos[1, :].detach().cpu().numpy()
        return macro_x, macro_y
    
    def update_placement(self):
        """
        Update the problem_instance's placement results with optimized positions.
        Updates placedb, results['placement'], and results['figure'].
        """
        macro_x, macro_y = self.get_optimized_positions()
        # Update placedb and results
        self.placedb.node_x[self.macro_indices] = macro_x
        self.placedb.node_y[self.macro_indices] = macro_y
        
        if not hasattr(self.problem_instance, 'results'):
            self.problem_instance.results = {}
        self.problem_instance.results['placement'] = (self.placedb.node_x.copy(), self.placedb.node_y.copy())
        
        # Format for plotting: flat array [x1, x2, ..., xn, y1, y2, ..., yn]
        # First, create figure from dmp_placer
        self.problem_instance.results['figure'] = copy.copy(self.problem_instance.dmp_placer.pos[0].data.clone().cpu().numpy())
        
        # Then, update macro coordinates in the figure
        n_nodes = int(len(self.problem_instance.results['figure']) / 2)
        # Update x coordinates for macros (first n_nodes elements)
        self.problem_instance.results['figure'][self.macro_indices] = macro_x
        # Update y coordinates for macros (last n_nodes elements)
        self.problem_instance.results['figure'][n_nodes + self.macro_indices] = macro_y

    def _plot_layout(self, iteration, hpwl_val, plot_dir):
        """
        Plot layout at current iteration.
        Draws only macros without cells, similar to place_3d_v2 style.
        
        Args:
            iteration: Current iteration number
            hpwl_val: Current HPWL value
            plot_dir: Directory to save plots
        """
        # Create plot directory if it doesn't exist
        os.makedirs(plot_dir, exist_ok=True)
        
        # Generate figure filename
        figure_path = os.path.join(plot_dir, f"iter_{iteration:04d}.png")
        
        # Get macro positions and sizes
        macro_x = self.macro_pos[0, :].detach().cpu().numpy()
        macro_y = self.macro_pos[1, :].detach().cpu().numpy()
        macro_w = self.macro_size_x.detach().cpu().numpy()
        macro_h = self.macro_size_y.detach().cpu().numpy()
        
        # Use LayoutPlotter to plot only macros (no cells)
        # MacroRefiner is used for bottom die refinement, so use die_type='bottom'
        return LayoutPlotter.plot_single_die_macros(
            macro_x=macro_x,
            macro_y=macro_y,
            macro_w=macro_w,
            macro_h=macro_h,
            xl=self.xl,
            yl=self.yl,
            xh=self.xh,
            yh=self.yh,
            die_type='bottom',
            hpwl_val=hpwl_val,
            title=f'Bottom Die Macro Refinement - Iteration {iteration}, HPWL: {hpwl_val:.2f}',
            figure_path=figure_path
        )
"""
Macro legalization algorithm using discrete grid-based greedy placement.
"""

import numpy as np
import torch
from typing import Optional, List, Tuple
import sys
import os
import pdb
import random
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)
from utils.layout_plotter import LayoutPlotter


class MacroLegalizer:
    """Legalizes macro positions using grid-based greedy algorithm."""
    
    def __init__(self, cell_problem_instance, macro_indices: np.ndarray, grid_size: int = 224, 
                 die_type: str = 'upper', regularity_weight: float = 0.1, device: Optional[str] = None):
        """
        Args:
            cell_problem_instance: Problem instance containing placedb
            macro_indices: Array of macro node indices to legalize
            grid_size: Grid size for legalization
            die_type: 'bottom' or 'upper' - determines if regularity should be considered
            regularity_weight: Weight for regularity term (only used for bottom die)
            device: Device to use ('cuda' or 'cpu')
        """
        self.placedb = cell_problem_instance.dmp_placedb
        self.macro_indices = np.array(macro_indices, dtype=np.int64)
        self.n_macros = len(self.macro_indices)
        self.grid_size = grid_size
        self.die_type = die_type  # 'bottom' or 'upper'
        self.regularity_weight = regularity_weight if die_type == 'bottom' else 0.0
        
        self.device = torch.device(device if device else 'cuda' if torch.cuda.is_available() else 'cpu')
        
        cell_node_x, cell_node_y = self.placedb.node_x, self.placedb.node_y
        self.macro_pos_x = torch.tensor(cell_node_x[self.macro_indices], dtype=torch.float32, device=self.device)
        self.macro_pos_y = torch.tensor(cell_node_y[self.macro_indices], dtype=torch.float32, device=self.device)
        self.macro_size_x = torch.tensor(self.placedb.node_size_x[self.macro_indices], dtype=torch.float32, device=self.device)
        self.macro_size_y = torch.tensor(self.placedb.node_size_y[self.macro_indices], dtype=torch.float32, device=self.device)
        
        self.xl, self.yl = float(self.placedb.xl), float(self.placedb.yl)
        self.xh, self.yh = float(self.placedb.xh), float(self.placedb.yh)
        self.grid_step_x = (self.xh - self.xl) / grid_size
        self.grid_step_y = (self.yh - self.yl) / grid_size
        self.macro_grid_w = torch.ceil(self.macro_size_x / self.grid_step_x).to(torch.int32)
        self.macro_grid_h = torch.ceil(self.macro_size_y / self.grid_step_y).to(torch.int32)
        
        all_node_indices = np.arange(self.placedb.num_physical_nodes)
        self.cell_indices = np.setdiff1d(all_node_indices, self.macro_indices)
        self.cell_pos_x_tensor = torch.tensor(cell_node_x[self.cell_indices], dtype=torch.float32, device=self.device)
        self.cell_pos_y_tensor = torch.tensor(cell_node_y[self.cell_indices], dtype=torch.float32, device=self.device)
        
        self.pin_offset_x_tensor = torch.tensor(self.placedb.pin_offset_x, dtype=torch.float32, device=self.device)
        self.pin_offset_y_tensor = torch.tensor(self.placedb.pin_offset_y, dtype=torch.float32, device=self.device)
        
        # Build net info and groups
        self.net2pin_map = self.placedb.net2pin_map
        self.pin2node_map_tensor = torch.tensor(self.placedb.pin2node_map, dtype=torch.long, device=self.device)
        pin2net_np = np.array(self.placedb.pin2net_map)
        macro_related_nets = set()
        for macro_node_id in self.macro_indices:
            for pin_id in self.placedb.node2pin_map[int(macro_node_id)]:
                macro_related_nets.add(pin2net_np[pin_id])
        self.macro_related_nets = sorted(macro_related_nets)
        self._build_net_groups()
        
        # Pre-allocate tensors
        self.macro_node_ids_tensor = torch.tensor(self.macro_indices, dtype=torch.long, device=self.device)
        self.cell_node_ids_tensor = torch.tensor(self.cell_indices, dtype=torch.long, device=self.device)
        self.net_weights = torch.tensor(self.placedb.net_weights if self.placedb.net_weights is not None 
                                       else np.ones(self.placedb.num_nets), dtype=torch.float32, device=self.device)
        
        # Sort macros by connection density
        densities = torch.zeros(self.n_macros, dtype=torch.int32, device=self.device)
        for macro_idx, macro_node_id in enumerate(self.macro_indices):
            net_ids = {pin2net_np[pin_id] for pin_id in self.placedb.node2pin_map[int(macro_node_id)]}
            densities[macro_idx] = len(net_ids)
        self.sorted_macro_order = torch.argsort(densities, descending=True)
        # Save original order for retry mechanism
        self.original_macro_order = self.sorted_macro_order.clone()
        
        self.legalized_macro_pos_x = None
        self.legalized_macro_pos_y = None
    
    def _build_net_groups(self, max_group_size: int = 1000):
        """Build grouped net matrices for parallel HPWL computation."""
        if len(self.macro_related_nets) == 0:
            self.net_groups = []
            return
        
        net_pin_lists = [(net_id, self.net2pin_map[int(net_id)]) for net_id in self.macro_related_nets if len(self.net2pin_map[int(net_id)]) > 0]
        if not net_pin_lists:
            self.net_groups = []
            return
        
        net_pin_lists_sorted = sorted(net_pin_lists, key=lambda x: len(x[1]))
        net_groups = []
        current_group, current_group_max_pins = [], 0
        
        for net_id, pin_ids in net_pin_lists_sorted:
            num_pins = len(pin_ids)
            if len(current_group) > 0 and ((num_pins > current_group_max_pins * 2 and current_group_max_pins > 0) or len(current_group) >= max_group_size):
                net_groups.append((current_group, current_group_max_pins))
                current_group, current_group_max_pins = [], 0
            current_group.append((net_id, pin_ids))
            current_group_max_pins = max(current_group_max_pins, num_pins)
        if current_group:
            net_groups.append((current_group, current_group_max_pins))
        
        self.net_groups = []
        for group_nets, max_pins_in_group in net_groups:
            num_nets_in_group = len(group_nets)
            padded_netpin = torch.zeros((num_nets_in_group, max_pins_in_group), dtype=torch.long, device=self.device)
            netpin_mask = torch.zeros((num_nets_in_group, max_pins_in_group), dtype=torch.bool, device=self.device)
            group_net_ids = []
            
            for net_idx_in_group, (net_id, pin_ids) in enumerate(group_nets):
                if len(pin_ids) > 0:
                    padded_netpin[net_idx_in_group, :len(pin_ids)] = torch.tensor(pin_ids, dtype=torch.long, device=self.device)
                    netpin_mask[net_idx_in_group, :len(pin_ids)] = True
                group_net_ids.append(net_id)
            
            self.net_groups.append({
                'padded_netpin': padded_netpin,
                'netpin_mask': netpin_mask,
                'net_ids': torch.tensor(group_net_ids, dtype=torch.long, device=self.device),
                'max_pins': max_pins_in_group
            })
    
    def _compute_pin_positions(self, macro_pos_x_batch, macro_pos_y_batch) -> torch.Tensor:
        """Compute pin positions from batch of macro positions."""
        batch_size = macro_pos_x_batch.shape[0]
        n_pins = self.pin2node_map_tensor.shape[0]
        node_pos = torch.zeros(batch_size, 2, self.placedb.num_physical_nodes, dtype=torch.float32, device=self.device)

        node_pos[:, 0, self.macro_node_ids_tensor] = macro_pos_x_batch
        node_pos[:, 1, self.macro_node_ids_tensor] = macro_pos_y_batch
        node_pos[:, 0, self.cell_node_ids_tensor] = self.cell_pos_x_tensor.unsqueeze(0).expand(batch_size, -1)
        node_pos[:, 1, self.cell_node_ids_tensor] = self.cell_pos_y_tensor.unsqueeze(0).expand(batch_size, -1)
        pin_pos = torch.zeros(batch_size, 2, n_pins, dtype=torch.float32, device=self.device)
        pin_pos[:, 0, :] = node_pos[:, 0, self.pin2node_map_tensor] + self.pin_offset_x_tensor.unsqueeze(0)
        pin_pos[:, 1, :] = node_pos[:, 1, self.pin2node_map_tensor] + self.pin_offset_y_tensor.unsqueeze(0)
        return pin_pos
    
    def _compute_hpwl_group(self, pin_x_batch: torch.Tensor, pin_y_batch: torch.Tensor, group: dict) -> torch.Tensor:
        """Compute HPWL for a single group of nets."""
        padded_netpin, netpin_mask, group_net_ids = group['padded_netpin'], group['netpin_mask'], group['net_ids']
        if len(group_net_ids) == 0:
            return torch.zeros(pin_x_batch.shape[0], dtype=torch.float32, device=self.device)
        
        batch_size = pin_x_batch.shape[0]
        netpin_expanded = padded_netpin.unsqueeze(0).expand(batch_size, -1, -1)
        pin_x_expanded = pin_x_batch.unsqueeze(1)
        pin_y_expanded = pin_y_batch.unsqueeze(1)
        padded_pin_x = torch.gather(pin_x_expanded.expand(-1, len(group_net_ids), -1), 2, netpin_expanded)
        padded_pin_y = torch.gather(pin_y_expanded.expand(-1, len(group_net_ids), -1), 2, netpin_expanded)
        
        mask_float = netpin_mask.float().unsqueeze(0).expand(batch_size, -1, -1)
        large_pos, large_neg = torch.tensor(1e10, dtype=torch.float32, device=self.device), torch.tensor(-1e10, dtype=torch.float32, device=self.device)
        padded_pin_x_for_min = padded_pin_x * mask_float + (1.0 - mask_float) * large_pos
        padded_pin_x_for_max = padded_pin_x * mask_float + (1.0 - mask_float) * large_neg
        padded_pin_y_for_min = padded_pin_y * mask_float + (1.0 - mask_float) * large_pos
        padded_pin_y_for_max = padded_pin_y * mask_float + (1.0 - mask_float) * large_neg
        
        x_min, x_max = torch.min(padded_pin_x_for_min, dim=2)[0], torch.max(padded_pin_x_for_max, dim=2)[0]
        y_min, y_max = torch.min(padded_pin_y_for_min, dim=2)[0], torch.max(padded_pin_y_for_max, dim=2)[0]
        net_hpwl = (x_max - x_min) + (y_max - y_min)
        net_weights = self.net_weights[group_net_ids].unsqueeze(0)
        return torch.sum(net_weights * net_hpwl, dim=1)
    
    def _compute_hpwl(self, macro_pos_x_batch, macro_pos_y_batch):
        """Compute total HPWL for batch of macro positions. Accepts numpy arrays or tensors."""
        # Convert to tensor if needed
        if isinstance(macro_pos_x_batch, np.ndarray):
            macro_pos_x_batch = torch.tensor(macro_pos_x_batch, dtype=torch.float32, device=self.device)
        if isinstance(macro_pos_y_batch, np.ndarray):
            macro_pos_y_batch = torch.tensor(macro_pos_y_batch, dtype=torch.float32, device=self.device)
        # Ensure 2D (add batch dimension if 1D)
        if macro_pos_x_batch.dim() == 1:
            macro_pos_x_batch = macro_pos_x_batch.unsqueeze(0)
        if macro_pos_y_batch.dim() == 1:
            macro_pos_y_batch = macro_pos_y_batch.unsqueeze(0)
        
        pin_pos = self._compute_pin_positions(macro_pos_x_batch, macro_pos_y_batch)
        pin_x, pin_y = pin_pos[:, 0, :], pin_pos[:, 1, :]
        total_hpwl = torch.zeros(pin_x.shape[0], dtype=torch.float32, device=self.device)
        for group in self.net_groups:
            total_hpwl = total_hpwl + self._compute_hpwl_group(pin_x, pin_y, group)
        # Return float for single value, tensor for batch
        return float(total_hpwl[0].item()) if total_hpwl.shape[0] == 1 else total_hpwl
    
    def _is_legal_position_grid(self, macro_idx: int, macro_grid_x: int, macro_grid_y: int, placed_macros: List[Tuple[int, int, int]]) -> bool:
        """Check if a macro position is legal (no overlap and within bounds)."""
        macro_grid_w = int(self.macro_grid_w[macro_idx].item())
        macro_grid_h = int(self.macro_grid_h[macro_idx].item())
        if macro_grid_x < 0 or macro_grid_y < 0 or macro_grid_x + macro_grid_w > self.grid_size or macro_grid_y + macro_grid_h > self.grid_size:
            return False
        for placed_macro_idx, placed_grid_x, placed_grid_y in placed_macros:
            placed_grid_w = int(self.macro_grid_w[placed_macro_idx].item())
            placed_grid_h = int(self.macro_grid_h[placed_macro_idx].item())
            if max(macro_grid_x, placed_grid_x) < min(macro_grid_x + macro_grid_w, placed_grid_x + placed_grid_w) and \
               max(macro_grid_y, placed_grid_y) < min(macro_grid_y + macro_grid_h, placed_grid_y + placed_grid_h):
                return False
        return True
    
    def _find_nearest_legal_positions(self, macro_idx: int, current_grid_x: float, current_grid_y: float,
                                      placed_macros: List[Tuple[int, int, int]], num_candidates: int = 100) -> List[Tuple[int, int]]:
        """Find the N nearest legal grid positions for a macro using position mask."""
        macro_grid_w = int(self.macro_grid_w[macro_idx].item())
        macro_grid_h = int(self.macro_grid_h[macro_idx].item())
        
        # Create position mask: True indicates invalid (overlapping) positions
        max_valid_x = self.grid_size - macro_grid_w + 1
        max_valid_y = self.grid_size - macro_grid_h + 1
        mask = torch.zeros((max_valid_x, max_valid_y), dtype=torch.bool, device=self.device)
        
        # Mask edges (hard-coded margin = 3)
        edge_margin = 3
        mask[:edge_margin, :] = True
        mask[-edge_margin:, :] = True
        mask[:, :edge_margin] = True
        mask[:, -edge_margin:] = True
        
        # Mark positions that would overlap with placed macros
        # For each candidate position (x, y), check if placing macro at (x, y) overlaps with placed macro at (px, py)
        # Overlap condition: x < px + pw AND x + w > px AND y < py + ph AND y + h > py
        # This means: x in [px - w + 1, px + pw - 1] AND y in [py - h + 1, py + ph - 1]
        for placed_macro_idx, placed_grid_x, placed_grid_y in placed_macros:
            placed_grid_w = int(self.macro_grid_w[placed_macro_idx].item())
            placed_grid_h = int(self.macro_grid_h[placed_macro_idx].item())
            
            # Calculate overlap region: positions (x,y) where placing current macro would overlap with placed macro
            # leave one grid cell between the macros
            start_x = max(0, placed_grid_x - macro_grid_w)
            end_x = min(placed_grid_x + placed_grid_w, max_valid_x - 1)
            start_y = max(0, placed_grid_y - macro_grid_h)
            end_y = min(placed_grid_y + placed_grid_h, max_valid_y - 1)
            
            # Mark overlapping region (inclusive range)
            if start_x <= end_x and start_y <= end_y:
                mask[start_x:end_x + 1, start_y:end_y + 1] = True
        
        # Find legal positions using 2D indexing
        legal_mask = ~mask  # True where legal, False where illegal
        legal_positions_2d = torch.where(legal_mask)
        legal_gx_2d = legal_positions_2d[0]  # x coordinates (row indices)
        legal_gy_2d = legal_positions_2d[1]  # y coordinates (column indices)
        
        if len(legal_gx_2d) == 0:
            return []
        
        # Convert to float for distance calculation
        legal_gx_float = legal_gx_2d.float()
        legal_gy_float = legal_gy_2d.float()
        
        # Calculate distances in 2D space
        distances = torch.sqrt((legal_gx_float - current_grid_x) ** 2 + (legal_gy_float - current_grid_y) ** 2)
        
        # Find k nearest positions
        k = min(num_candidates, len(legal_gx_2d))
        _, nearest_indices = torch.topk(distances, k, largest=False)
        
        # Extract coordinates of nearest positions
        nearest_gx = legal_gx_2d[nearest_indices]
        nearest_gy = legal_gy_2d[nearest_indices]
        
        # Convert to list of tuples
        candidate_positions = [(int(nearest_gx[i].item()), int(nearest_gy[i].item())) for i in range(k)]
        
        return candidate_positions
    
    def _compute_hpwl_change_for_positions(self, macro_idx: int, candidate_positions: List[Tuple[int, int]],
                                           current_macro_pos_x: torch.Tensor, current_macro_pos_y: torch.Tensor) -> Tuple[int, int, float]:
        """Compute HPWL (+ regularity for bottom die) for candidate positions and return the best one."""
        if len(candidate_positions) == 0:
            return None, None, float('inf')
        
        n_candidates = len(candidate_positions)
        macro_pos_x_batch = current_macro_pos_x.unsqueeze(0).expand(n_candidates, -1).clone()
        macro_pos_y_batch = current_macro_pos_y.unsqueeze(0).expand(n_candidates, -1).clone()
        
        for idx, (gx, gy) in enumerate(candidate_positions):
            macro_pos_x_batch[idx, macro_idx] = self.xl + gx * self.grid_step_x
            macro_pos_y_batch[idx, macro_idx] = self.yl + gy * self.grid_step_y
        
        hpwl_values = self._compute_hpwl(macro_pos_x_batch, macro_pos_y_batch)
        if isinstance(hpwl_values, (int, float)):
            hpwl_values = torch.tensor([hpwl_values], dtype=torch.float32, device=self.device)
        
        # Compute regularity for bottom die macros
        is_bottom = self.die_type == 'bottom'
        reg = None
        if is_bottom and self.regularity_weight > 0:
            reg = self._compute_regularity(macro_pos_x_batch[:, macro_idx], macro_pos_y_batch[:, macro_idx],
                                          self.macro_size_x[macro_idx], self.macro_size_y[macro_idx])
        
        # Normalize and combine HPWL and regularity for bottom die
        if is_bottom and reg is not None:
            hpwl_range = (float(hpwl_values.min().item()), float(hpwl_values.max().item()))
            reg_range = (float(reg.min().item()), float(reg.max().item()))
            hpwl_norm = (hpwl_values - hpwl_range[0]) / (hpwl_range[1] - hpwl_range[0] + 1e-8)
            reg_norm = (reg - reg_range[0]) / (reg_range[1] - reg_range[0] + 1e-8)
            combined = hpwl_norm + self.regularity_weight * reg_norm
            best_idx = torch.argmin(combined)
        else:
            # For upper die macros, use raw HPWL
            best_idx = torch.argmin(hpwl_values)
        
        return candidate_positions[best_idx][0], candidate_positions[best_idx][1], float(hpwl_values[best_idx].item())
    
    def _compute_regularity(self, macro_x: torch.Tensor, macro_y: torch.Tensor, 
                            macro_w: torch.Tensor, macro_h: torch.Tensor) -> torch.Tensor:
        """Compute regularity: distance from macro center to nearest edge."""
        w = macro_w.item() if isinstance(macro_w, torch.Tensor) else macro_w
        h = macro_h.item() if isinstance(macro_h, torch.Tensor) else macro_h
        cx, cy = macro_x + w / 2.0, macro_y + h / 2.0
        dists = torch.stack([cx - self.xl, self.xh - cx, cy - self.yl, self.yh - cy], dim=1)
        return torch.min(dists, dim=1)[0]
    
    def _shuffle_macro_order(self, shuffle_ratio: float = 0.3):
        """Randomly shuffle a portion of macro order to create perturbation.
        
        Args:
            shuffle_ratio: Ratio of macros to shuffle (default: 0.3, meaning 30% of macros)
        """
        sorted_order_list = self.sorted_macro_order.cpu().numpy() if isinstance(self.sorted_macro_order, torch.Tensor) else self.sorted_macro_order
        n_shuffle = max(1, int(len(sorted_order_list) * shuffle_ratio))
        
        # Randomly select indices to shuffle
        shuffle_indices = random.sample(range(len(sorted_order_list)), n_shuffle)
        shuffle_values = [sorted_order_list[i] for i in shuffle_indices]
        
        # Shuffle the selected values
        random.shuffle(shuffle_values)
        
        # Put shuffled values back
        new_order = sorted_order_list.copy()
        for idx, val in zip(shuffle_indices, shuffle_values):
            new_order[idx] = val
        
        # Update sorted_macro_order
        self.sorted_macro_order = torch.tensor(new_order, dtype=torch.long, device=self.device)
    
    def _legalize_once(self) -> Tuple[bool, np.ndarray, np.ndarray]:
        """
        Perform one attempt of legalization.
        
        Returns:
            success: True if legalization succeeded, False if failed (no legal position found)
            legalized_pos_x: Array of legalized x positions
            legalized_pos_y: Array of legalized y positions
        """
        legalized_pos_x, legalized_pos_y = self.macro_pos_x.clone(), self.macro_pos_y.clone()
        placed_macros = []
        
        sorted_order_list = self.sorted_macro_order.cpu().numpy() if isinstance(self.sorted_macro_order, torch.Tensor) else self.sorted_macro_order
        for order_idx, macro_idx in enumerate(sorted_order_list):
            if order_idx % 50 == 0:
                print(f"Processing macro {order_idx + 1}/{self.n_macros}")
            
            current_x = float(legalized_pos_x[macro_idx].item())
            current_y = float(legalized_pos_y[macro_idx].item())
            current_grid_x = (current_x - self.xl) / self.grid_step_x
            current_grid_y = (current_y - self.yl) / self.grid_step_y
            macro_grid_w_int = int(self.macro_grid_w[macro_idx].item())
            macro_grid_h_int = int(self.macro_grid_h[macro_idx].item())
            # Clamp to valid grid range and convert to integer
            current_grid_x_int = max(0, min(int(current_grid_x), self.grid_size - macro_grid_w_int))
            current_grid_y_int = max(0, min(int(current_grid_y), self.grid_size - macro_grid_h_int))
            if self._is_legal_position_grid(macro_idx, current_grid_x_int, current_grid_y_int, placed_macros):
                placed_macros.append((macro_idx, current_grid_x_int, current_grid_y_int))
                continue
            
            candidate_positions = self._find_nearest_legal_positions(macro_idx, current_grid_x, current_grid_y, placed_macros, 100)
            if len(candidate_positions) == 0:
                # No legal position found, return failure
                return False, legalized_pos_x.cpu().numpy(), legalized_pos_y.cpu().numpy()
            
            best_grid_x, best_grid_y, _ = self._compute_hpwl_change_for_positions(macro_idx, candidate_positions, legalized_pos_x, legalized_pos_y)
            legalized_pos_x[macro_idx] = self.xl + best_grid_x * self.grid_step_x
            legalized_pos_y[macro_idx] = self.yl + best_grid_y * self.grid_step_y
            placed_macros.append((macro_idx, best_grid_x, best_grid_y))
        
        self.legalized_macro_pos_x, self.legalized_macro_pos_y = legalized_pos_x, legalized_pos_y
        return True, legalized_pos_x.cpu().numpy(), legalized_pos_y.cpu().numpy()
    
    def legalize(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Legalize macro positions.
        If legalization fails (no legal position found), randomly shuffle macro order and retry up to 5 times.
        """
        print(f"Starting macro legalization with {self.n_macros} macros")
        
        max_retries = 5
        for attempt in range(max_retries):
            if attempt > 0:
                print(f"\nRetry attempt {attempt}/{max_retries - 1}: Shuffling macro order...")
                # Restore original order first, then randomly shuffle for retry
                self.sorted_macro_order = self.original_macro_order.clone()
                self._shuffle_macro_order(shuffle_ratio=0.3)
            
            success, legalized_pos_x, legalized_pos_y = self._legalize_once()
            
            if success:
                print(f"Legalization complete")
                return legalized_pos_x, legalized_pos_y
            else:
                print(f"Legalization failed at attempt {attempt + 1}: No legal position found for a macro")
                if attempt < max_retries - 1:
                    print(f"Will retry with shuffled macro order...")
        
        # All retries failed
        print(f"\nLegalization failed after {max_retries} attempts. Stopping.")
        assert False, f"No legal position found after {max_retries} retry attempts"
    
    def plot_layout(self, macro_pos_x, macro_pos_y, hpwl_val: float, 
                   figure_path: str, title: Optional[str] = None):
        """Plot macro layout without cells. Accepts numpy arrays or tensors."""
        # Convert to numpy arrays if needed
        if isinstance(macro_pos_x, torch.Tensor):
            macro_pos_x = macro_pos_x.cpu().numpy()
        if isinstance(macro_pos_y, torch.Tensor):
            macro_pos_y = macro_pos_y.cpu().numpy()
        macro_size_x_np = self.macro_size_x.cpu().numpy() if isinstance(self.macro_size_x, torch.Tensor) else self.macro_size_x
        macro_size_y_np = self.macro_size_y.cpu().numpy() if isinstance(self.macro_size_y, torch.Tensor) else self.macro_size_y
        
        os.makedirs(os.path.dirname(figure_path) if os.path.dirname(figure_path) else '.', exist_ok=True)
        # Use plot_single_die_macros for consistent style with place_3d_v2
        return LayoutPlotter.plot_single_die_macros(
            macro_x=macro_pos_x, macro_y=macro_pos_y, macro_w=macro_size_x_np, macro_h=macro_size_y_np,
            xl=self.xl, yl=self.yl, xh=self.xh, yh=self.yh, 
            die_type=self.die_type, hpwl_val=hpwl_val, title=title, figure_path=figure_path
        )

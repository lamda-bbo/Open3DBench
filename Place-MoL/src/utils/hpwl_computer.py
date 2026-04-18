import torch
import pdb
import numpy as np
from typing import Optional, List, Set, Dict


class HPWLComputer:
    """
    Compute Weighted-Average Wirelength (WA) for nets.
    WA_e = ( (Σ_{v_i ∈ e} x_i e^(x_i / γ)) / (Σ_{v_i ∈ e} e^(x_i / γ)) - (Σ_{v_i ∈ e} x_i e^(-x_i / γ)) / (Σ_{v_i ∈ e} e^(-x_i / γ)) ) 
           + ( (Σ_{v_i ∈ e} y_i e^(y_i / γ)) / (Σ_{v_i ∈ e} e^(y_i / γ)) - (Σ_{v_i ∈ e} y_i e^(-y_i / γ)) / (Σ_{v_i ∈ e} e^(-y_i / γ)) )
    
    Supports two computation modes:
    1. Grouped vectorized mode: Efficient for large numbers of nets (default)
    2. Simple loop mode: Simpler implementation for small numbers of nets
    """
    
    def __init__(self, 
                 placedb,
                 macro_indices: np.ndarray,
                 gamma: float = 0.1,
                 device: Optional[str] = None,
                 use_grouped_mode: bool = True,
                 max_group_size: int = 1000):
        """
        Initialize HPWL computer.
        
        Args:
            placedb: Placement database object containing net and pin information
            macro_indices: Array of macro node IDs
            gamma: Parameter for WA approximation (smaller = more accurate but less smooth)
            device: PyTorch device ('cuda' or 'cpu'), auto-detect if None
            use_grouped_mode: Whether to use grouped vectorized mode (default: True)
            max_group_size: Maximum number of nets per group for grouped mode
        """
        self.placedb = placedb
        self.macro_indices = macro_indices
        self.gamma = gamma
        self.use_grouped_mode = use_grouped_mode
        self.max_group_size = max_group_size
        
        # Set device
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        # Extract net information
        self._extract_net_info()
        
        if self.use_grouped_mode:
            self._build_net_groups()
    
    def _extract_net_info(self):
        """Extract net information for HPWL calculation."""
        # Get pin information
        self.pin_offset_x = torch.tensor(
            self.placedb.pin_offset_x, 
            dtype=torch.float32, device=self.device
        )
        self.pin_offset_y = torch.tensor(
            self.placedb.pin_offset_y, 
            dtype=torch.float32, device=self.device
        )
        
        # Get net weights
        if self.placedb.net_weights is not None:
            self.net_weights = torch.tensor(
                self.placedb.net_weights, 
                dtype=torch.float32, device=self.device
            )
        else:
            self.net_weights = torch.ones(
                self.placedb.num_nets, 
                dtype=torch.float32, device=self.device
            )
        
        # Store net2pin_map for efficient pin lookup
        self.net2pin_map = self.placedb.net2pin_map
        
        # Identify nets connected to macros
        # A net is considered macro-related if at least one pin of that net belongs to a macro
        macro_related_nets = set()
        
        # Get nets connected to each macro node
        pin2net_np = np.array(self.placedb.pin2net_map)
        for macro_node_id in self.macro_indices:
            # Get all pins belonging to this macro node
            pin_ids = self.placedb.node2pin_map[int(macro_node_id)]
            # Get nets connected to these pins
            for pin_id in pin_ids:
                net_id = pin2net_np[pin_id]
                macro_related_nets.add(net_id)
        
        # Convert to tensor for efficient filtering
        self.macro_related_nets = torch.tensor(
            list(macro_related_nets), 
            dtype=torch.long, 
            device=self.device
        )
        self.macro_related_nets_set = macro_related_nets  # Keep as set for fast lookup
    
    def _build_net_groups(self):
        """
        Build grouped padded netpin matrices for efficient parallel computation.
        Groups nets by pin count to minimize padding overhead.
        """
        # Build flat_netpin and netpin_start for vectorized computation
        # Only include macro_related_nets, sorted by net_id for consistency
        sorted_macro_related_nets = sorted(self.macro_related_nets_set)
        
        # Group nets by pin count to minimize padding overhead
        net_groups = []  # List of groups, each group is (net_indices, max_pins_in_group)
        net_pin_lists = []
        net_id_to_index = {}
        
        # Collect net information
        for idx, net_id in enumerate(sorted_macro_related_nets):
            pin_ids = self.net2pin_map[int(net_id)]
            if len(pin_ids) > 0:
                net_pin_lists.append((idx, net_id, pin_ids))
                net_id_to_index[net_id] = idx
        
        # Group nets by pin count to minimize padding overhead
        if len(net_pin_lists) > 0:
            # Sort nets by pin count for better grouping
            net_pin_lists_sorted = sorted(net_pin_lists, key=lambda x: len(x[2]))
            
            current_group = []
            current_group_max_pins = 0
            
            for idx, net_id, pin_ids in net_pin_lists_sorted:
                num_pins = len(pin_ids)
                
                # Check if we should start a new group
                should_start_new_group = False
                if len(current_group) > 0:
                    # If this net is much larger than current group max, start new group
                    # This avoids excessive padding when a large net is added to a group of small nets
                    if num_pins > current_group_max_pins * 2 and current_group_max_pins > 0:
                        should_start_new_group = True
                    # Or if current group is getting too large (memory efficiency)
                    elif len(current_group) >= self.max_group_size:
                        should_start_new_group = True
                
                if should_start_new_group and len(current_group) > 0:
                    # Save current group
                    net_groups.append((current_group, current_group_max_pins))
                    current_group = []
                    current_group_max_pins = 0
                
                # Add to current group
                current_group.append((idx, net_id, pin_ids))
                current_group_max_pins = max(current_group_max_pins, num_pins)
            
            # Add last group
            if len(current_group) > 0:
                net_groups.append((current_group, current_group_max_pins))
        
        # Build padded matrices for each group
        self.net_groups = []
        for group_idx, (group_nets, max_pins_in_group) in enumerate(net_groups):
            num_nets_in_group = len(group_nets)
            
            # Create padded pin matrix for this group: [num_nets_in_group, max_pins_in_group]
            padded_netpin = torch.full(
                (num_nets_in_group, max_pins_in_group),
                -1,
                dtype=torch.long,
                device=self.device
            )
            
            # Create mask: [num_nets_in_group, max_pins_in_group]
            netpin_mask = torch.zeros(
                (num_nets_in_group, max_pins_in_group),
                dtype=torch.bool,
                device=self.device
            )
            
            # Store net IDs for this group
            group_net_ids = []
            
            # Fill padded matrix and mask
            for net_idx_in_group, (original_idx, net_id, pin_ids) in enumerate(group_nets):
                if len(pin_ids) > 0:
                    padded_netpin[net_idx_in_group, :len(pin_ids)] = torch.tensor(
                        pin_ids,
                        dtype=torch.long,
                        device=self.device
                    )
                    netpin_mask[net_idx_in_group, :len(pin_ids)] = True
                group_net_ids.append(net_id)
            
            # Store group information
            group_net_ids_tensor = torch.tensor(
                group_net_ids,
                dtype=torch.long,
                device=self.device
            )
            self.net_groups.append({
                'padded_netpin': padded_netpin,
                'netpin_mask': netpin_mask,
                'net_ids': group_net_ids_tensor,
                'max_pins': max_pins_in_group
            })
    
    def _compute_wa_group(self, pin_x: torch.Tensor, pin_y: torch.Tensor, group: Dict) -> torch.Tensor:
        """
        Compute WA wirelength for a single group of nets (grouped vectorized mode).
        
        Args:
            pin_x: Tensor of shape [n_pins] (x coordinates)
            pin_y: Tensor of shape [n_pins] (y coordinates)
            group: Dictionary containing 'padded_netpin', 'netpin_mask', 'net_ids', 'max_pins'
        
        Returns:
            wa_wl: Scalar tensor representing total WA wirelength for this group
        """
        gamma = self.gamma
        padded_netpin = group['padded_netpin']
        netpin_mask = group['netpin_mask']
        group_net_ids = group['net_ids']
        
        num_nets_in_group = len(group_net_ids)
        if num_nets_in_group == 0:
            return torch.tensor(0.0, dtype=torch.float32, device=self.device)
        # pdb.set_trace()
        # Get pin positions for all nets in this group: [num_nets_in_group, max_pins_in_group]
        max_valid_pin_id = len(pin_x) - 1
        safe_netpin = torch.clamp(padded_netpin, min=0, max=max_valid_pin_id)
        padded_pin_x = pin_x[safe_netpin]  # [num_nets_in_group, max_pins_in_group]
        padded_pin_y = pin_y[safe_netpin]  # [num_nets_in_group, max_pins_in_group]
        
        # Compute exponentials for all pins at once (fully vectorized)
        exp_x_pos = torch.exp(padded_pin_x / gamma)  # e^(x_i/γ)
        exp_x_neg = torch.exp(-padded_pin_x / gamma)  # e^(-x_i/γ)
        exp_y_pos = torch.exp(padded_pin_y / gamma)  # e^(y_i/γ)
        exp_y_neg = torch.exp(-padded_pin_y / gamma)  # e^(-y_i/γ)
        
        # Apply mask to pin positions and exponentials (set padding to 0)
        mask_float = netpin_mask.float()
        padded_pin_x = padded_pin_x * mask_float
        padded_pin_y = padded_pin_y * mask_float
        exp_x_pos = exp_x_pos * mask_float
        exp_x_neg = exp_x_neg * mask_float
        exp_y_pos = exp_y_pos * mask_float
        exp_y_neg = exp_y_neg * mask_float
        
        # Compute products: [num_nets_in_group, max_pins_in_group]
        x_exp_x_pos = padded_pin_x * exp_x_pos  # x_i * e^(x_i/γ)
        x_exp_x_neg = padded_pin_x * exp_x_neg  # x_i * e^(-x_i/γ)
        y_exp_y_pos = padded_pin_y * exp_y_pos  # y_i * e^(y_i/γ)
        y_exp_y_neg = padded_pin_y * exp_y_neg  # y_i * e^(-y_i/γ)
        
        # Compute sums for each net (parallel across all nets in group): [num_nets_in_group]
        sum_x_exp_pos = torch.sum(x_exp_x_pos, dim=1)
        sum_exp_x_pos = torch.sum(exp_x_pos, dim=1)
        sum_x_exp_neg = torch.sum(x_exp_x_neg, dim=1)
        sum_exp_x_neg = torch.sum(exp_x_neg, dim=1)
        
        sum_y_exp_pos = torch.sum(y_exp_y_pos, dim=1)
        sum_exp_y_pos = torch.sum(exp_y_pos, dim=1)
        sum_y_exp_neg = torch.sum(y_exp_y_neg, dim=1)
        sum_exp_y_neg = torch.sum(exp_y_neg, dim=1)
        
        # Compute WA wirelength for each net: [num_nets_in_group]
        wa_x = (sum_x_exp_pos / (sum_exp_x_pos + 1e-8)) - (sum_x_exp_neg / (sum_exp_x_neg + 1e-8))
        wa_y = (sum_y_exp_pos / (sum_exp_y_pos + 1e-8)) - (sum_y_exp_neg / (sum_exp_y_neg + 1e-8))
        net_wa_wl = wa_x + wa_y  # [num_nets_in_group]
        
        # Apply net weights and sum: [num_nets_in_group]
        net_weights = self.net_weights[group_net_ids]  # [num_nets_in_group]
        weighted_wa_wl = net_weights * net_wa_wl  # [num_nets_in_group]
        
        # Sum all weighted wirelengths for this group
        group_wa_wl = torch.sum(weighted_wa_wl)
        
        return group_wa_wl
    
    def _compute_wa_simple(self, pin_x: torch.Tensor, pin_y: torch.Tensor) -> torch.Tensor:
        """
        Compute WA wirelength using simple loop mode (net-by-net).
        
        Args:
            pin_x: Tensor of shape [n_pins] (x coordinates)
            pin_y: Tensor of shape [n_pins] (y coordinates)
        
        Returns:
            wa_wl: Scalar tensor representing total WA wirelength of macro-related nets
        """
        wa_wl = torch.tensor(0.0, dtype=torch.float32, device=self.device)
        gamma = self.gamma
        
        # Compute WA wirelength only for macro-related nets
        for net_id in self.macro_related_nets_set:
            # Get pins belonging to this net directly from net2pin_map
            pin_ids = self.net2pin_map[int(net_id)]
            if len(pin_ids) == 0:
                continue
            
            # Convert pin_ids to tensor for indexing
            pin_ids_tensor = torch.tensor(pin_ids, dtype=torch.long, device=self.device)
            
            # Get pin positions for this net
            net_pin_x = pin_x[pin_ids_tensor]
            net_pin_y = pin_y[pin_ids_tensor]
            
            # Compute weighted-average wirelength (WA) for x coordinates.
            exp_x_pos = torch.exp(net_pin_x / gamma)  # e^(x_i/γ)
            exp_x_neg = torch.exp(-net_pin_x / gamma)  # e^(-x_i/γ)
            
            sum_x_exp_pos = torch.sum(net_pin_x * exp_x_pos)  # Σ x_i e^(x_i/γ)
            sum_exp_x_pos = torch.sum(exp_x_pos)  # Σ e^(x_i/γ)
            sum_x_exp_neg = torch.sum(net_pin_x * exp_x_neg)  # Σ x_i e^(-x_i/γ)
            sum_exp_x_neg = torch.sum(exp_x_neg)  # Σ e^(-x_i/γ)
            
            wa_x = (sum_x_exp_pos / (sum_exp_x_pos + 1e-8)) - (sum_x_exp_neg / (sum_exp_x_neg + 1e-8))
            
            # Compute weighted-average wirelength (WA) for y coordinates.
            exp_y_pos = torch.exp(net_pin_y / gamma)  # e^(y_i/γ)
            exp_y_neg = torch.exp(-net_pin_y / gamma)  # e^(-y_i/γ)
            
            sum_y_exp_pos = torch.sum(net_pin_y * exp_y_pos)  # Σ y_i e^(y_i/γ)
            sum_exp_y_pos = torch.sum(exp_y_pos)  # Σ e^(y_i/γ)
            sum_y_exp_neg = torch.sum(net_pin_y * exp_y_neg)  # Σ y_i e^(-y_i/γ)
            sum_exp_y_neg = torch.sum(exp_y_neg)  # Σ e^(-y_i/γ)
            
            wa_y = (sum_y_exp_pos / (sum_exp_y_pos + 1e-8)) - (sum_y_exp_neg / (sum_exp_y_neg + 1e-8))
            
            # Total WA wirelength for this net
            net_wa_wl = wa_x + wa_y
            # Add weighted net wirelength to total
            wa_wl = wa_wl + self.net_weights[net_id] * net_wa_wl
        
        return wa_wl
    
    def compute(self, pin_pos: torch.Tensor) -> torch.Tensor:
        """
        Compute Weighted-Average Wire Length (WA) for nets connected to macros.
        
        Args:
            pin_pos: Tensor of shape [2, n_pins] (x, y coordinates)
        
        Returns:
            wa_wl: Scalar tensor representing total WA wirelength of macro-related nets
        """
        pin_x = pin_pos[0, :]  # [n_pins]
        pin_y = pin_pos[1, :]  # [n_pins]
        
        if self.use_grouped_mode:
            if not hasattr(self, 'net_groups') or len(self.net_groups) == 0:
                return torch.tensor(0.0, dtype=torch.float32, device=self.device)
            
            # Compute wirelength for each group and sum
            total_wa_wl = torch.tensor(0.0, dtype=torch.float32, device=self.device)
            for group in self.net_groups:
                group_wa_wl = self._compute_wa_group(pin_x, pin_y, group)
                total_wa_wl = total_wa_wl + group_wa_wl
            
            return total_wa_wl
        else:
            return self._compute_wa_simple(pin_x, pin_y)


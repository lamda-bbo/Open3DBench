"""
Graph Cut Algorithms for Macro Partition
Implements min-cut and max-cut algorithms with area balance constraints.
"""
import numpy as np
from typing import List, Set, Tuple, Dict
import random
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class GraphCutPartitioner:
    """
    Graph cut partitioner with area balance constraints.
    """
    
    def __init__(self, graph_builder, area_balance_error=0.1):
        """
        Initialize graph cut partitioner.
        
        Args:
            graph_builder: GraphBuilder instance
            area_balance_error: Maximum allowed area imbalance ratio (default: 0.1 = 10%)
        """
        self.graph_builder = graph_builder
        self.area_balance_error = area_balance_error
        
        # Get area info
        area_info = graph_builder.get_area_info()
        self.macro_areas = area_info['macro_areas']
        self.cell_area = area_info['cell_area']
        self.total_macro_area = np.sum(self.macro_areas)
        self.total_area = area_info['total_area']
        
        # Build adjacency matrix for efficient lookup
        self._build_adjacency()
    
    def _build_adjacency(self):
        """
        Build adjacency matrix and edge weight map.
        """
        n_nodes = self.graph_builder.n_macros + 1  # macros + cell node
        self.adjacency = np.zeros((n_nodes, n_nodes), dtype=np.float32)
        
        edges = self.graph_builder.edges
        edge_weights = self.graph_builder.edge_weights
        
        for i, (n1, n2) in enumerate(edges):
            self.adjacency[n1, n2] = edge_weights[i]
            self.adjacency[n2, n1] = edge_weights[i]
    
    def _compute_cut_weight(self, partition: Set[int], complement: Set[int]) -> float:
        """
        Compute the total weight of edges crossing the cut.
        
        Args:
            partition: Set of node indices in one partition
            complement: Set of node indices in the other partition
        
        Returns:
            float: Total weight of cut edges
        """
        cut_weight = 0.0
        for n1 in partition:
            for n2 in complement:
                cut_weight += self.adjacency[n1, n2]
        return cut_weight
    
    def _compute_partition_area(self, partition: Set[int]) -> float:
        """
        Compute total area of a partition (excluding cell node).
        
        Args:
            partition: Set of macro node indices
        
        Returns:
            float: Total area of macros in partition
        """
        area = 0.0
        for macro_idx in partition:
            if macro_idx < self.graph_builder.n_macros:  # Exclude cell node
                area += self.macro_areas[macro_idx]
        return area
    
    def _is_area_balanced(self, partition: Set[int]) -> bool:
        """
        Check if partition satisfies area balance constraint.
        
        Args:
            partition: Set of macro node indices in bottom die
        
        Returns:
            bool: True if area balanced
        """
        bottom_area = self._compute_partition_area(partition)
        upper_area = self.total_macro_area - bottom_area
        
        # Bottom die includes cells
        bottom_total_area = bottom_area + self.cell_area
        upper_total_area = upper_area
        
        # Check balance
        area_diff = abs(bottom_total_area - upper_total_area)
        max_diff = self.total_area * self.area_balance_error
        
        return area_diff <= max_diff
    
    def min_cut(self, seed=None) -> List[int]:
        """
        Find min-cut partition with area balance constraint.
        Minimizes the weight of edges crossing the cut.
        
        Args:
            seed: Random seed for reproducibility
        
        Returns:
            List[int]: Selected macro indices for bottom die
        """
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)
        
        n_macros = self.graph_builder.n_macros
        
        # Initialize partition using area-balanced random assignment
        selected = self._initialize_area_balanced_partition()
        
        # Kernighan-Lin algorithm for refinement
        improved = True
        max_iterations = 10
        
        for iteration in range(max_iterations):
            if not improved:
                break
            
            improved = False
            best_gain = 0.0
            best_swap = None
            
            # Try swapping each pair of nodes
            selected_list = list(selected)
            complement_list = [i for i in range(n_macros) if i not in selected]
            
            for s_idx in selected_list:
                for c_idx in complement_list:
                    # Compute gain from swapping
                    gain = self._compute_swap_gain(s_idx, c_idx, selected)
                    
                    # Check if swap improves cut and maintains balance
                    if gain < best_gain:  # Negative gain is better for min-cut
                        new_selected = selected.copy()
                        new_selected.remove(s_idx)
                        new_selected.add(c_idx)
                        
                        if self._is_area_balanced(new_selected):
                            best_gain = gain
                            best_swap = (s_idx, c_idx)
                            improved = True
            
            # Perform best swap
            if best_swap is not None:
                s_idx, c_idx = best_swap
                selected.remove(s_idx)
                selected.add(c_idx)
        
        return sorted(list(selected))
    
    def max_cut(self, seed=None) -> List[int]:
        """
        Find max-cut partition with area balance constraint.
        Maximizes the weight of edges crossing the cut.
        
        Args:
            seed: Random seed for reproducibility
        
        Returns:
            List[int]: Selected macro indices for bottom die
        """
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)
        
        n_macros = self.graph_builder.n_macros
        
        # Initialize partition using area-balanced random assignment
        selected = self._initialize_area_balanced_partition()
        
        # Kernighan-Lin algorithm for refinement (maximize cut)
        improved = True
        max_iterations = 10
        
        for iteration in range(max_iterations):
            if not improved:
                break
            
            improved = False
            best_gain = 0.0
            best_swap = None
            
            # Try swapping each pair of nodes
            selected_list = list(selected)
            complement_list = [i for i in range(n_macros) if i not in selected]
            
            for s_idx in selected_list:
                for c_idx in complement_list:
                    # Compute gain from swapping
                    gain = self._compute_swap_gain(s_idx, c_idx, selected)
                    
                    # Check if swap improves cut and maintains balance
                    # For max-cut, positive gain is better
                    if gain > best_gain:
                        new_selected = selected.copy()
                        new_selected.remove(s_idx)
                        new_selected.add(c_idx)
                        
                        if self._is_area_balanced(new_selected):
                            best_gain = gain
                            best_swap = (s_idx, c_idx)
                            improved = True
            
            # Perform best swap
            if best_swap is not None:
                s_idx, c_idx = best_swap
                selected.remove(s_idx)
                selected.add(c_idx)
        
        return sorted(list(selected))
    
    def _initialize_area_balanced_partition(self) -> Set[int]:
        """
        Initialize a partition that satisfies area balance constraint.
        
        Returns:
            Set[int]: Initial set of macro indices for bottom die
        """
        n_macros = self.graph_builder.n_macros
        
        # Target area for bottom die (including cells)
        target_bottom_area = (self.total_area) / 2.0
        target_bottom_macro_area = target_bottom_area - self.cell_area
        
        # Greedy assignment: sort macros by area and assign to balance
        macro_indices = list(range(n_macros))
        macro_areas_list = [(i, self.macro_areas[i]) for i in macro_indices]
        macro_areas_list.sort(key=lambda x: x[1], reverse=True)  # Sort by area descending
        
        selected = set()
        current_area = 0.0
        
        for macro_idx, area in macro_areas_list:
            # Check if adding this macro maintains balance
            new_area = current_area + area
            new_bottom_total = new_area + self.cell_area
            new_upper_total = self.total_macro_area - new_area
            
            area_diff = abs(new_bottom_total - new_upper_total)
            max_diff = self.total_area * self.area_balance_error
            
            if area_diff <= max_diff or current_area < target_bottom_macro_area:
                selected.add(macro_idx)
                current_area = new_area
                
                # If we've reached target, try to stop
                if current_area >= target_bottom_macro_area:
                    break
        
        # Ensure we have at least one macro in bottom die
        if len(selected) == 0:
            selected.add(0)
        elif len(selected) == n_macros:
            # If all macros selected, remove one
            selected.remove(macro_areas_list[-1][0])
        
        return selected
    
    def _compute_swap_gain(self, node1: int, node2: int, partition: Set[int]) -> float:
        """
        Compute the gain from swapping two nodes between partitions.
        Positive gain means cut weight increases (good for max-cut), 
        negative gain means cut weight decreases (good for min-cut).
        
        Args:
            node1: Node index in partition
            node2: Node index in complement
            partition: Current partition set
        
        Returns:
            float: Gain from swapping (positive = cut increases, negative = cut decreases)
        """
        complement = set(range(self.graph_builder.n_macros)) - partition
        
        # Current state: node1 in partition, node2 in complement
        # Cut edges: node1 -> complement, node2 -> partition
        node1_to_complement = sum(self.adjacency[node1, c] for c in complement)
        node2_to_partition = sum(self.adjacency[node2, p] for p in partition)
        current_cut_contribution = node1_to_complement + node2_to_partition
        
        # After swap: node1 moves to complement, node2 moves to partition
        # New cut edges: node1 -> partition, node2 -> complement
        node1_to_partition = sum(self.adjacency[node1, p] for p in partition if p != node1)
        node2_to_complement = sum(self.adjacency[node2, c] for c in complement if c != node2)
        new_cut_contribution = node1_to_partition + node2_to_complement
        
        # The edge between node1 and node2:
        # Before: node1 (partition) <-> node2 (complement) -> in cut
        # After: node1 (complement) <-> node2 (partition) -> still in cut
        # So this edge doesn't change the cut weight
        
        # However, we need to account for it properly:
        # In current_cut_contribution, we counted adjacency[node1, node2] in node1_to_complement
        # In new_cut_contribution, we counted adjacency[node1, node2] in node2_to_complement
        # So it cancels out
        
        # Gain = new_cut - current_cut
        # Positive gain means cut increases (good for max-cut)
        # Negative gain means cut decreases (good for min-cut)
        gain = new_cut_contribution - current_cut_contribution
        
        return gain
    
    def evaluate_cut(self, selected_macro_indices: List[int]) -> Dict:
        """
        Evaluate a cut partition.
        
        Args:
            selected_macro_indices: List of macro indices in bottom die
        
        Returns:
            dict: Evaluation metrics including cut weight and area balance
        """
        selected_set = set(selected_macro_indices)
        complement_set = set(range(self.graph_builder.n_macros)) - selected_set
        
        cut_weight = self._compute_cut_weight(selected_set, complement_set)
        
        bottom_area = self._compute_partition_area(selected_set)
        upper_area = self.total_macro_area - bottom_area
        bottom_total_area = bottom_area + self.cell_area
        upper_total_area = upper_area
        
        area_diff = abs(bottom_total_area - upper_total_area)
        area_imbalance_ratio = area_diff / self.total_area if self.total_area > 0 else 0.0
        
        return {
            'cut_weight': cut_weight,
            'bottom_area': bottom_total_area,
            'upper_area': upper_total_area,
            'area_diff': area_diff,
            'area_imbalance_ratio': area_imbalance_ratio,
            'is_balanced': self._is_area_balanced(selected_set)
        }

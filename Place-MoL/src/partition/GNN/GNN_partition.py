"""
GNN Partition Module for Macro Partition
Uses graph contrastive learning to learn node embeddings, then performs k-means clustering
to partition macros.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Data
from typing import Optional, List, Dict, Tuple
import numpy as np
from sklearn.cluster import KMeans
import copy
from ..common.gin_network import GINNetwork


class GNNPartitioner(nn.Module):
    """
    GNN-based partitioner for macro partition using contrastive learning.
    """
    def __init__(self, input_dim, hidden_dim, embedding_dim, num_layers=3, dropout=0.1, temperature=0.07):
        """
        Initialize GNN partitioner.
        
        Args:
            input_dim: Input feature dimension
            hidden_dim: Hidden dimension
            embedding_dim: Output embedding dimension
            num_layers: Number of GIN layers
            dropout: Dropout rate
            temperature: Temperature parameter for contrastive loss
        """
        super(GNNPartitioner, self).__init__()
        
        self.temperature = temperature
        
        # GIN
        self.encoder = GINNetwork(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            output_dim=embedding_dim,
            num_layers=num_layers,
            dropout=dropout
        )
        
        # Projection head
        self.projection_head = nn.Sequential(
            nn.Linear(embedding_dim, embedding_dim),
            nn.BatchNorm1d(embedding_dim),
            nn.ReLU(),
            nn.Linear(embedding_dim, embedding_dim)
        )
    
    def forward(self, data: Data):
        """
        Forward pass to get node embeddings.
        
        Args:
            data: PyG Data object
        
        Returns:
            embeddings: Node embeddings [n_nodes, embedding_dim]
        """
        embeddings = self.encoder(data)
        return embeddings
    
    def get_projected_embeddings(self, data: Data):
        """
        Get projected embeddings for contrastive learning.
        
        Args:
            data: PyG Data object
        
        Returns:
            projected: Projected embeddings [n_nodes, embedding_dim]
        """
        embeddings = self.forward(data)
        projected = self.projection_head(embeddings)
        # L2 norm
        projected = F.normalize(projected, p=2, dim=1)
        return projected
    
    def contrastive_loss(self, data: Data):
        """
        Compute unsupervised loss based on the formula:
        L_unsup = -sum_{v in G_m} [sum_{u in N(v)} log(tanh(y_v^T y_u)) + sum_{n in Neg(v)} log(tanh(-y_v^T y_n))]
        
        Where:
        - v: nodes in the graph (macros)
        - N(v): neighbors of node v (positive samples)
        - Neg(v): negative samples of node v (non-neighbors)
        - y_v: embedding vector of node v
        - tanh: hyperbolic tangent activation function
        - weights w are ignored (set to 1)
        
        Args:
            data: PyG Data object
        
        Returns:
            loss: Unsupervised loss scalar
        """
        # Use L2-normalized projected embeddings to prevent collapse
        y = self.get_projected_embeddings(data)  # [n_nodes, embedding_dim], L2 norm = 1
        
        # Build adjacency matrix
        n_nodes = y.shape[0]
        edge_index = data.edge_index
        
        # Check if there are edges
        if edge_index.shape[1] == 0:
            return torch.tensor(0.1, device=y.device, requires_grad=True)
        
        # Build adjacency matrix (undirected graph)
        adj = torch.zeros(n_nodes, n_nodes, device=y.device, dtype=torch.bool)
        adj[edge_index[0], edge_index[1]] = True
        adj[edge_index[1], edge_index[0]] = True
        
        # Dot products with temperature (L2-normed: dot in [-1,1]; use tau>=0.5 to avoid tanh saturation)
        tau = max(self.temperature, 0.5)
        dot_products = torch.matmul(y, y.t()) / tau
        
        # Accumulate loss for all nodes v in G_m
        total_loss = 0.0
        valid_nodes = 0
        
        for v in range(n_nodes):
            # Get neighbors N(v)
            neighbors = torch.where(adj[v])[0]  # Indices of neighbors
            
            # Get negative samples Neg(v): non-neighbors (excluding self)
            non_neighbors_mask = ~adj[v]
            non_neighbors_mask[v] = False  # Exclude self
            neg_samples = torch.where(non_neighbors_mask)[0]  # Indices of negative samples
            
            if len(neighbors) == 0 or len(neg_samples) == 0:
                # Skip nodes without neighbors or negative samples
                continue
            
            # First term: sum_{u in N(v)} log(tanh(y_v^T y_u))
            # For positive samples, we want y_v^T y_u to be large (positive), so tanh(y_v^T y_u) is positive
            pos_dot_products = dot_products[v, neighbors]  # [|N(v)|]
            pos_tanh = torch.tanh(pos_dot_products)  # [|N(v)|]
            # Clamp to ensure positive values for log (tanh range is [-1, 1], we need [epsilon, 1])
            pos_tanh = torch.clamp(pos_tanh, min=1e-8, max=1.0 - 1e-8)
            pos_term = torch.log(pos_tanh).sum()
            
            # Second term: sum_{n in Neg(v)} log(tanh(-y_v^T y_n))
            # For negative samples, we want y_v^T y_n to be small, so -y_v^T y_n is positive
            # tanh(-y_v^T y_n) will be positive when -y_v^T y_n > 0
            neg_dot_products = dot_products[v, neg_samples]  # [|Neg(v)|]
            neg_tanh = torch.tanh(-neg_dot_products)  # [|Neg(v)|]
            # Clamp to ensure positive values for log
            # Note: tanh can be negative, so we use abs or shift to ensure positivity
            # Using abs to ensure log is defined: log(|tanh(-y_v^T y_n)|)
            neg_tanh = torch.abs(neg_tanh)
            neg_tanh = torch.clamp(neg_tanh, min=1e-8, max=1.0 - 1e-8)
            neg_term = torch.log(neg_tanh).sum()
            
            # Loss for node v: -(pos_term + neg_term)
            node_loss = -(pos_term + neg_term)
            total_loss += node_loss
            valid_nodes += 1
        
        if valid_nodes == 0:
            return torch.tensor(0.1, device=y.device, requires_grad=True)
        
        contrastive_loss = total_loss / valid_nodes
        
        # Anti-collapse: penalize when mean embedding has large norm (all embeddings similar)
        mean_emb = y.mean(dim=0)
        collapse_reg = (mean_emb ** 2).sum()
        
        return contrastive_loss + 0.1 * collapse_reg
    
    def train_step(self, data: Data, optimizer):
        """
        Perform one training step.
        
        Args:
            data: PyG Data object
            optimizer: Optimizer
        
        Returns:
            loss: Training loss
        """
        self.train()
        optimizer.zero_grad()
        
        loss = self.contrastive_loss(data)
        loss.backward()
        optimizer.step()
        
        return loss.item()


def train_gnn_partition(
    graph_builder,
    num_epochs=100,
    lr=0.001,
    device='cpu',
    hidden_dim=128,
    embedding_dim=64,
    num_layers=3,
    dropout=0.1,
    temperature=0.07
):
    """
    Train GNN partition model.
    
    Args:
        graph_builder: GraphBuilder instance
        num_epochs: Number of training epochs
        lr: Learning rate
        device: Device to use
        hidden_dim: Hidden dimension
        embedding_dim: Embedding dimension
        num_layers: Number of GIN layers
        dropout: Dropout rate
        temperature: Temperature parameter for contrastive loss
    
    Returns:
        model: Trained model
        loss_history: List of training losses
    """
    # Get graph data
    data = graph_builder.get_pyg_data(device=device)
    input_dim = data.x.shape[1]
    
    # Create model
    model = GNNPartitioner(
        input_dim=input_dim,
        hidden_dim=hidden_dim,
        embedding_dim=embedding_dim,
        num_layers=num_layers,
        dropout=dropout,
        temperature=temperature
    ).to(device)
    
    # Optimizer
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    
    # Training loop
    model.train()
    loss_history = []
    
    # Track best model (lowest loss)
    best_loss = float('inf')
    best_model_state = None
    best_epoch = 0
    
    # Debug: print graph statistics
    print(f"\nGraph Statistics:")
    print(f"  Number of nodes: {data.x.shape[0]}")
    print(f"  Number of edges: {data.edge_index.shape[1]}")
    print(f"  Node feature dim: {data.x.shape[1]}")
    
    for epoch in range(num_epochs):
        loss = model.train_step(data, optimizer)
        loss_value = float(loss)
        loss_history.append(loss_value)
        
        # Track best model
        if loss_value < best_loss:
            best_loss = loss_value
            best_model_state = copy.deepcopy(model.state_dict())
            best_epoch = epoch + 1
        
        # Print loss for first 10 epochs, then every 10 epochs
        if (epoch + 1) <= 10 or (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{num_epochs}, Loss: {loss_value:.6f}")
    
    # Load best model state
    if best_model_state is not None:
        model.load_state_dict(best_model_state)
        print(f"\nBest model loaded from epoch {best_epoch} with loss: {best_loss:.6f}")
    
    return model, loss_history


def partition_with_kmeans(
    model: GNNPartitioner,
    graph_builder,
    device='cpu',
    n_clusters=2,
    area_balance_error=0.1,
    max_iterations=100
) -> List[int]:
    """
    Partition macros using k-means clustering on embeddings.
    
    Args:
        model: Trained GNNPartitioner model
        graph_builder: GraphBuilder instance
        device: Device to use
        n_clusters: Number of clusters (should be 2 for upper/bottom die)
        area_balance_error: Allowed error for area balance (default: 0.1, i.e., 10%)
        max_iterations: Maximum iterations for area balancing
    
    Returns:
        selected_macro_indices: List of macro indices assigned to bottom die
    """
    model.eval()
    
    # Get graph data
    data = graph_builder.get_pyg_data(device=device)
    
    # Get node embeddings (use raw embeddings, not projected)
    with torch.no_grad():
        embeddings = model.forward(data)  # [n_nodes, embedding_dim]
        embeddings_np = embeddings.cpu().numpy()
    
    # Get macro node indices (excluding cell node)
    macro_indices = graph_builder.get_graph_macro_indices()
    cell_node_idx = graph_builder.get_graph_cell_node_idx()
    
    # Get macro embeddings (exclude cell node)
    macro_embeddings = embeddings_np[macro_indices]  # [n_macros, embedding_dim]
    
    # Get cell node embedding
    cell_embedding = embeddings_np[cell_node_idx]  # [embedding_dim]
    
    # Perform k-means clustering on macros only
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(macro_embeddings)
    cluster_centers = kmeans.cluster_centers_  # [n_clusters, embedding_dim]
    
    # Find the cluster closest to cell node embedding
    # This cluster will be assigned to bottom die
    cell_to_center_distances = np.linalg.norm(cluster_centers - cell_embedding, axis=1)
    bottom_die_cluster_id = np.argmin(cell_to_center_distances)
    
    # Get area info
    area_info = graph_builder.get_area_info()
    macro_areas = area_info['macro_areas']
    cell_area = area_info['cell_area']
    
    # Calculate target area for bottom die
    total_macro_area = macro_areas.sum()
    target_bottom_area = (total_macro_area + cell_area) / 2.0
    
    # Initially assign macros in the cell's cluster to bottom die
    bottom_die_mask = (cluster_labels == bottom_die_cluster_id)
    selected_macro_indices = [macro_indices[i] for i in range(len(macro_indices)) if bottom_die_mask[i]]
    selected_set = set(selected_macro_indices)
    
    # Calculate current bottom die area
    current_bottom_area = macro_areas[bottom_die_mask].sum() + cell_area
    
    # Refine by moving macros based on distance to cell embedding
    selected_macro_indices = _refine_partition_by_embedding_distance(
        selected_macro_indices,
        macro_indices,
        macro_embeddings,
        macro_areas,
        cell_embedding,
        cell_area,
        target_bottom_area,
        area_balance_error,
        max_iterations
    )
    
    return selected_macro_indices


def _refine_partition_by_embedding_distance(
    initial_selection: List[int],
    all_macro_indices: List[int],
    macro_embeddings: np.ndarray,
    macro_areas: np.ndarray,
    cell_embedding: np.ndarray,
    cell_area: float,
    target_bottom_area: float,
    area_balance_error: float,
    max_iterations: int
) -> List[int]:
    """
    Refine partition by moving macros based on distance to cell embedding.
    If bottom die area is too large, move macros farthest from cell to upper die.
    If bottom die area is too small, move macros closest to cell to bottom die.
    
    Args:
        initial_selection: Initial list of macro indices in bottom die
        all_macro_indices: All macro indices
        macro_embeddings: Array of macro embeddings [n_macros, embedding_dim]
        macro_areas: Array of macro areas
        cell_embedding: Cell node embedding [embedding_dim]
        cell_area: Total cell area
        target_bottom_area: Target area for bottom die
        area_balance_error: Allowed error
        max_iterations: Maximum iterations
    
    Returns:
        refined_selection: Refined list of macro indices in bottom die
    """
    selected_set = set(initial_selection)
    macro_idx_to_area = {idx: macro_areas[i] for i, idx in enumerate(all_macro_indices)}
    macro_idx_to_embedding = {idx: macro_embeddings[i] for i, idx in enumerate(all_macro_indices)}
    
    # Calculate distances from each macro to cell embedding
    macro_idx_to_distance = {}
    for idx in all_macro_indices:
        macro_emb = macro_idx_to_embedding[idx]
        distance = np.linalg.norm(macro_emb - cell_embedding)
        macro_idx_to_distance[idx] = distance
    
    current_bottom_area = sum(macro_idx_to_area[idx] for idx in selected_set) + cell_area
    current_diff = abs(current_bottom_area - target_bottom_area)
    target_diff = target_bottom_area * area_balance_error
    
    for iteration in range(max_iterations):
        if current_diff <= target_diff:
            break
        
        area_needed = target_bottom_area - current_bottom_area
        
        if area_needed < 0:
            # Bottom die is too large: move macros farthest from cell to upper die
            bottom_die_macros = [idx for idx in all_macro_indices if idx in selected_set]
            # Sort by distance (descending: farthest first)
            bottom_die_macros.sort(key=lambda idx: macro_idx_to_distance[idx], reverse=True)
            
            # Move macros until area is balanced
            for macro_idx in bottom_die_macros:
                if current_diff <= target_diff:
                    break
                selected_set.remove(macro_idx)
                current_bottom_area -= macro_idx_to_area[macro_idx]
                current_diff = abs(current_bottom_area - target_bottom_area)
        else:
            # Bottom die is too small: move macros closest to cell to bottom die
            upper_die_macros = [idx for idx in all_macro_indices if idx not in selected_set]
            # Sort by distance (ascending: closest first)
            upper_die_macros.sort(key=lambda idx: macro_idx_to_distance[idx])
            
            # Move macros until area is balanced
            for macro_idx in upper_die_macros:
                if current_diff <= target_diff:
                    break
                selected_set.add(macro_idx)
                current_bottom_area += macro_idx_to_area[macro_idx]
                current_diff = abs(current_bottom_area - target_bottom_area)
    
    return sorted(list(selected_set))


def _refine_partition_by_area(
    initial_selection: List[int],
    all_macro_indices: List[int],
    macro_areas: np.ndarray,
    cell_area: float,
    target_bottom_area: float,
    area_balance_error: float,
    max_iterations: int
) -> List[int]:
    """
    Refine partition by swapping macros to improve area balance.
    
    Args:
        initial_selection: Initial list of macro indices in bottom die
        all_macro_indices: All macro indices
        macro_areas: Array of macro areas
        cell_area: Total cell area
        target_bottom_area: Target area for bottom die
        area_balance_error: Allowed error
        max_iterations: Maximum iterations
    
    Returns:
        refined_selection: Refined list of macro indices in bottom die
    """
    selected_set = set(initial_selection)
    macro_idx_to_area = {idx: macro_areas[i] for i, idx in enumerate(all_macro_indices)}
    
    current_bottom_area = sum(macro_idx_to_area[idx] for idx in selected_set) + cell_area
    current_diff = abs(current_bottom_area - target_bottom_area)
    
    for iteration in range(max_iterations):
        if current_diff <= target_bottom_area * area_balance_error:
            break
        
        # Try swapping a macro from bottom to upper or vice versa
        best_swap = None
        best_new_diff = current_diff
        
        # Try moving a macro from bottom to upper
        for macro_idx in list(selected_set):
            new_bottom_area = current_bottom_area - macro_idx_to_area[macro_idx]
            new_diff = abs(new_bottom_area - target_bottom_area)
            if new_diff < best_new_diff:
                best_new_diff = new_diff
                best_swap = ('remove', macro_idx)
        
        # Try moving a macro from upper to bottom
        for macro_idx in all_macro_indices:
            if macro_idx not in selected_set:
                new_bottom_area = current_bottom_area + macro_idx_to_area[macro_idx]
                new_diff = abs(new_bottom_area - target_bottom_area)
                if new_diff < best_new_diff:
                    best_new_diff = new_diff
                    best_swap = ('add', macro_idx)
        
        # Apply best swap
        if best_swap is not None:
            op, macro_idx = best_swap
            if op == 'remove':
                selected_set.remove(macro_idx)
                current_bottom_area -= macro_idx_to_area[macro_idx]
            else:
                selected_set.add(macro_idx)
                current_bottom_area += macro_idx_to_area[macro_idx]
            current_diff = best_new_diff
        else:
            break
    
    return list(selected_set)


def gnn_partition(
    model: GNNPartitioner,
    graph_builder,
    device='cpu',
    n_clusters=2,
    area_balance_error=0.1
) -> Dict:
    """
    Perform GNN-based partition.
    
    Args:
        model: Trained GNNPartitioner model
        graph_builder: GraphBuilder instance
        device: Device to use
        n_clusters: Number of clusters
        area_balance_error: Area balance error tolerance
    
    Returns:
        result: Dictionary with partition results
    """
    print("\n" + "="*50)
    print("Performing GNN Partition")
    print("="*50)
    
    # Perform partition
    selected_macro_indices = partition_with_kmeans(
        model=model,
        graph_builder=graph_builder,
        device=device,
        n_clusters=n_clusters,
        area_balance_error=area_balance_error
    )
    
    # Get partition statistics
    area_info = graph_builder.get_area_info()
    macro_areas = area_info['macro_areas']
    cell_area = area_info['cell_area']
    
    all_macro_indices = graph_builder.get_graph_macro_indices()
    
    # Calculate areas using macro indices directly
    # macro_indices[i] corresponds to macro_areas[i]
    selected_set = set(selected_macro_indices)
    bottom_die_macro_area = sum(
        macro_areas[i] for i, idx in enumerate(all_macro_indices) if idx in selected_set
    )
    bottom_die_total_area = bottom_die_macro_area + cell_area
    
    upper_die_indices = [idx for idx in all_macro_indices if idx not in selected_set]
    upper_die_area = sum(
        macro_areas[i] for i, idx in enumerate(all_macro_indices) if idx not in selected_set
    )
    
    print(f"\nPartition Statistics:")
    print(f"  Bottom die macros: {len(selected_macro_indices)}")
    print(f"  Upper die macros: {len(upper_die_indices)}")
    print(f"  Bottom die macro area: {bottom_die_macro_area:.2f}")
    print(f"  Bottom die total area (with cells): {bottom_die_total_area:.2f}")
    print(f"  Upper die area: {upper_die_area:.2f}")
    print(f"  Area difference: {abs(upper_die_area - bottom_die_total_area):.2f}")
    
    result = {
        'selected_macro_indices': selected_macro_indices,
        'bottom_die_macros_count': len(selected_macro_indices),
        'upper_die_macros_count': len(upper_die_indices),
        'bottom_die_area': bottom_die_total_area,
        'upper_die_area': upper_die_area
    }
    
    return result

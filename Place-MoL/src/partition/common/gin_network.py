"""
GIN (Graph Isomorphism Network) for node embedding with edge weight support
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import MessagePassing
from torch_geometric.data import Data
from torch_geometric.utils import add_self_loops
import pdb


class WeightedGINConv(MessagePassing):
    """
    GIN convolution layer with edge weight support.
    Based on: h_v^(k) = MLP((1 + ε) * h_v^(k-1) + Σ_{u∈N(v)} w_{uv} * h_u^(k-1))
    """
    def __init__(self, nn, eps=0.0, train_eps=False, **kwargs):
        super(WeightedGINConv, self).__init__(aggr='add', **kwargs)
        self.nn = nn
        self.initial_eps = eps
        if train_eps:
            self.eps = torch.nn.Parameter(torch.Tensor([eps]))
        else:
            self.register_buffer('eps', torch.Tensor([eps]))
        self.reset_parameters()

    def reset_parameters(self):
        self.eps.data.fill_(self.initial_eps)
        for module in self.nn.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                nn.init.zeros_(module.bias)

    def forward(self, x, edge_index, edge_weight=None):
        """
        Args:
            x: Node features [N, in_dim]
            edge_index: Edge indices [2, E]
            edge_weight: Edge weights [E] (optional)
        """
        if edge_weight is None:
            edge_weight = torch.ones(edge_index.size(1), device=edge_index.device, dtype=x.dtype)
        
        # Add self-loops with weight (1 + eps) for GIN formula
        edge_index, edge_weight = add_self_loops(edge_index, edge_weight, num_nodes=x.size(0), fill_value=1.0)
        self_loop_mask = edge_index[0] == edge_index[1]
        edge_weight[self_loop_mask] = 1.0 + self.eps
        
        # Propagate messages
        out = self.propagate(edge_index, x=x, edge_weight=edge_weight)
        
        # Apply MLP
        out = self.nn(out)
        return out

    def message(self, x_j, edge_weight):
        """
        Message function: computes message from node j to node i.
        Message = edge_weight * x_j
        """
        return edge_weight.view(-1, 1) * x_j


class GINLayer(nn.Module):
    """
    Single GIN layer with MLP and edge weight support.
    """
    def __init__(self, in_dim, out_dim, num_layers=2, train_eps=True):
        super(GINLayer, self).__init__()
        mlp_layers = []
        mlp_layers.append(nn.Linear(in_dim, out_dim))
        for _ in range(num_layers - 1):
            mlp_layers.append(nn.ReLU())
            mlp_layers.append(nn.Linear(out_dim, out_dim))
        
        self.mlp = nn.Sequential(*mlp_layers)
        self.gin_conv = WeightedGINConv(self.mlp, train_eps=train_eps)
    
    def forward(self, x, edge_index, edge_attr=None):
        """
        Args:
            x: Node features [N, in_dim]
            edge_index: Edge indices [2, E]
            edge_attr: Edge attributes/weights [E] or [E, edge_dim]
        """
        # Handle edge_attr: extract edge weights from edge attributes
        if edge_attr is not None:
            if edge_attr.dim() > 1:
                edge_weight = edge_attr[:, 0] if edge_attr.size(1) > 0 else edge_attr.sum(dim=1)
            else:
                edge_weight = edge_attr
        else:
            edge_weight = None
        
        return self.gin_conv(x, edge_index, edge_weight)


class GINNetwork(nn.Module):
    """
    Multi-layer GIN network for node embedding.
    """
    def __init__(self, input_dim, hidden_dim, output_dim, num_layers=3, dropout=0.1):
        """
        Initialize GIN network.
        
        Args:
            input_dim: Input feature dimension
            hidden_dim: Hidden dimension
            output_dim: Output embedding dimension
            num_layers: Number of GIN layers
            dropout: Dropout rate
        """
        super(GINNetwork, self).__init__()
        
        self.num_layers = num_layers
        self.dropout = dropout
        
        # Input projection
        self.input_proj = nn.Linear(input_dim, hidden_dim)
        
        # GIN layers
        self.gin_layers = nn.ModuleList()
        for i in range(num_layers):
            if i == 0:
                self.gin_layers.append(GINLayer(hidden_dim, hidden_dim))
            else:
                self.gin_layers.append(GINLayer(hidden_dim, hidden_dim))
        
        # Output projection
        self.output_proj = nn.Linear(hidden_dim, output_dim)
        
        # Output normalization
        self.output_norm = nn.LayerNorm(output_dim)
        
        # Batch normalization layers
        self.batch_norms = nn.ModuleList()
        for i in range(num_layers):
            self.batch_norms.append(nn.BatchNorm1d(hidden_dim))
        
    def forward(self, data: Data):
        """
        Forward pass.
        
        Args:
            data: PyG Data object with x, edge_index, edge_attr
        
        Returns:
            node_embeddings: Node embeddings [n_nodes, output_dim]
        """
        x, edge_index = data.x, data.edge_index
        edge_attr = getattr(data, 'edge_attr', None)

        # Input projection
        x = self.input_proj(x)
        x = F.relu(x)
        x = F.dropout(x, p=self.dropout, training=self.training)
        
        # GIN layers
        for i, (gin_layer, bn) in enumerate(zip(self.gin_layers, self.batch_norms)):
            x_new = gin_layer(x, edge_index, edge_attr=edge_attr)
            x_new = bn(x_new)
            x_new = F.relu(x_new)
            x_new = F.dropout(x_new, p=self.dropout, training=self.training)
            
            # Residual connection (if dimensions match)
            if x.shape == x_new.shape:
                x = x + x_new
            else:
                x = x_new
        
        # Output projection and normalize
        x = self.output_proj(x)
        x = self.output_norm(x)
        
        return x

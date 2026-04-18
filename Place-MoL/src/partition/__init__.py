"""
Macro Partition Module

This module contains two main approaches:
- graph_cut: Graph cut algorithms (min-cut, max-cut)
- GNN: Graph Neural Network baseline (contrastive learning)
- common: Shared utilities (graph builder, evaluator, GIN network)
"""
from .common import GraphBuilder, GINNetwork
from .graph_cut import GraphCutPartitioner
from .GNN import GNNPartitioner, train_gnn_partition

__all__ = [
    'GraphBuilder', 'GINNetwork',
    'GraphCutPartitioner',
    'GNNPartitioner', 'train_gnn_partition'
]
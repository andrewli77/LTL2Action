import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

import dgl
from dgl.nn.pytorch.conv import GraphConv

from gnns.graphs.GNN import GNN

class GCN(GNN):
    def __init__(self, input_dim, output_dim, **kwargs):
        hidden_dims = kwargs.get('hidden_dims', [32])
        super().__init__(input_dim, output_dim)

        self.num_layers = len(hidden_dims)
        self.convs = nn.ModuleList([GraphConv(in_dim, out_dim, activation=F.relu) for (in_dim, out_dim)
                      in zip([input_dim] + hidden_dims[:-1], hidden_dims)])

        self.g_embed = nn.Linear(hidden_dims[-1], output_dim)

    # Uses the base implementation which averages hidden representations of all nodes
    def forward(self, g):
        g = np.array(g).reshape((1, -1)).tolist()[0]
        g = dgl.batch(g)
        h = g.ndata["feat"].float()
        for i in range(self.num_layers):
            h = self.convs[i](g, h)
        g.ndata['h'] = h

        # Calculate graph representation by averaging all the hidden node representations.
        hg = dgl.mean_nodes(g, 'h')
        return self.g_embed(hg).squeeze(1)


# GCN, but the graph representation is only the representation of the root node.
class GCNRoot(GCN):
    def __init__(self, input_dim, output_dim, **kwargs):
        super().__init__(input_dim, output_dim, **kwargs)

    def forward(self, g):
        g = np.array(g).reshape((1, -1)).tolist()[0]
        g = dgl.batch(g)
        h = g.ndata["feat"].float()
        for i in range(self.num_layers):
            h = self.convs[i](g, h)
        g.ndata['h'] = h

        gs = dgl.unbatch(g)
        hg = torch.cat([gi.ndata['h'][0] for gi in gs])
        return self.g_embed(hg).squeeze(1)


class GCNRootShared(GNN):
    def __init__(self, input_dim, output_dim, **kwargs):
        super().__init__(input_dim, output_dim)
        hidden_dim = kwargs.get('hidden_dim', 32)
        num_layers = kwargs.get('num_layers', 2)

        self.num_layers = num_layers
        self.linear_in = nn.Linear(input_dim, hidden_dim)
        self.conv = GraphConv(hidden_dim, hidden_dim, activation=F.relu)
        self.g_embed = nn.Linear(hidden_dim, output_dim)

    # Uses the base implementation which averages hidden representations of all nodes
    def forward(self, g):
        g = np.array(g).reshape((1, -1)).tolist()[0]
        g = dgl.batch(g)
        h = g.ndata["feat"].float()
        h = self.linear_in(h)

        # Apply convolution layers
        for i in range(self.num_layers):
            h = self.conv(g, h)
        g.ndata['h'] = h

        gs = dgl.unbatch(g)
        hg = torch.cat([gi.ndata['h'][0] for gi in gs])
        return self.g_embed(hg).squeeze(1)

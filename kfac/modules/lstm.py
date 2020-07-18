"""Custom LSTM implementation using Linear layers

Based on the only PyTorch functional implementation:
https://github.com/pytorch/pytorch/blob/ceb4f84d12304d03a6a46693e54390869c0c208e/torch/nn/_functions/rnn.py
"""
import math
import torch
import torch.nn as nn
import torch.nn.functional as F

from torch.nn.utils.rnn import PackedSequence, pad_packed_sequence, pack_padded_sequence

class LSTMCell(nn.Module):
    def __init__(self, input_size, hidden_size, bias=True, init_weight=None):
        super(LSTMCell, self).__init__()

        self.input_size = input_size
        self.hidden_size = hidden_size
        self.bias = bias
        self.linear_ih = nn.Linear(input_size, 4 * hidden_size, bias=bias)
        self.linear_hh = nn.Linear(hidden_size, 4 * hidden_size, bias=bias)

        if init_weight is not None:
            self.init_weights(init_weight)

    def forward(self, input, hidden):
        """Compute forward pass.

        Args:
          input: shape (batch, input_size)
          hidden: tuple(hx, cx) where hx and cx have shape (batch, hidden_size)

        Returns:
          (hy, cy) where hy and cy have shape (batch, hidden_size)
        """
        hx, cx = hidden
        gates = self.linear_ih(input) + self.linear_hh(hx)
        ingate, forgetgate, cellgate, outgate = gates.chunk(4, 1)

        ingate = torch.sigmoid(ingate)
        forgetgate = torch.sigmoid(forgetgate)
        cellgate = torch.tanh(cellgate)
        outgate = torch.sigmoid(outgate)

        cy = (forgetgate * cx) + (ingate * cellgate)
        hy = outgate * torch.tanh(cy)

        return hy, cy

    def init_weights(self, init_weight):
        nn.init.uniform_(self.linear_ih.weight.data, -init_weight, init_weight)
        nn.init.uniform_(self.linear_hh.weight.data, -init_weight, init_weight)
        if self.bias:
            nn.init.uniform_(self.linear_ih.bias.data, -init_weight, init_weight)
            nn.init.zeros_(self.linear_hh.bias.data)

class LSTMLayer(nn.Module):
    def __init__(self, input_size, hidden_size, bias=True, batch_first=False,
            reverse=False, init_weight=None):
        super(LSTMLayer, self).__init__()

        self.input_size = input_size
        self.hidden_size = hidden_size
        self.bias = bias
        self.batch_first = batch_first
        self.reverse = reverse
        self.cell = LSTMCell(input_size, hidden_size, bias=bias, init_weight=init_weight)
        self.seq_dim = 1 if batch_first else 0

    def forward(self, input, hidden):
        output = []
        steps = (range(input.size(self.seq_dim) - 1, -1, -1) if self.reverse 
                else range(input.size(self.seq_dim)))
        for i in steps:
            hidden = self.cell(input[i], hidden)
            output.append(hidden[0])

        if self.reverse:
            output.reverse()
        output = torch.stack(output, self.seq_dim)

        return output, hidden

class LSTM(nn.Module):
    """Applies a multi-layer long short-term memory (LSTM) RNN to an input sequence.

    Uses custom LSTMCells to allow for KFAC support
    """

    def __init__(self,
                 input_size,
                 hidden_size,
                 num_layers=1,
                 bias=True,
                 batch_first=False,
                 dropout=0.0,
                 bidirectional=False,
                 init_weight=0.1):
        super(LSTM, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bias = bias
        self.batch_first = batch_first
        self.dropout = dropout
        self.bidirectional = bidirectional
        self.num_directions = 2 if bidirectional else 1
        self.init_weight = init_weight

        layers = []
        # TODO(gpauloski): flatten to single module list and update forward()
        for i in range(num_layers):
            layer = [LSTMLayer(input_size, hidden_size, bias=bias, batch_first=batch_first,
                    init_weight=init_weight)]
            if self.bidirectional:
                layer.append(LSTMLayer(input_size, hidden_size, bias=bias,
                        batch_first=batch_first, init_weight=init_weight, reverse=True))
            layers.append(nn.ModuleList(layer))

        self.layers = nn.ModuleList(layers)
        self.dropout = nn.Dropout(dropout) if dropout > 0 else None

    def forward(self, input, hx=None):
        orig_input = input
        if isinstance(input, PackedSequence):
            batch_sizes = input.batch_sizes
            max_batch_size = batch_sizes[0]
            sorted_indices = input.sorted_indices
            unsorted_indices = input.unsorted_indices
            input, lens_unpacked = pad_packed_sequence(input, batch_first=self.batch_first)
        else:
            batch_sizes = None
            max_batch_size = input.size(0) if self.batch_first else input.size(1)
            sorted_indices = None
            unsorted_indices = None

        if hx is None:
            num_directions = 2 if self.bidirectional else 1
            zeros = torch.zeros(self.num_layers * num_directions,
                                max_batch_size, self.hidden_size,
                                dtype=input.dtype, device=input.device)
            hx = (zeros, zeros)
        else:
            # Each batch of the hidden state should match the input sequence that
            # the user believes he/she is passing in.
            hx = self.permute_hidden(hx, sorted_indices)

        output, hidden = self._lstm_impl(input, hx)

        if isinstance(orig_input, PackedSequence):
            output_packed = pack_padded_sequence(output, lens_unpacked, batch_first=self.batch_first)
            return output_packed, self.permute_hidden(hidden, unsorted_indices)
        else:
            return output, self.permute_hidden(hidden, unsorted_indices)

    def permute_hidden(self, hx, permutation):
        # type: (Tuple[Tensor, Tensor], Optional[Tensor]) -> Tuple[Tensor, Tensor]
        if permutation is None:
            return hx
        return apply_permutation(hx[0], permutation), apply_permutation(hx[1], permutation)

    def _lstm_impl(self, input, hidden):
        next_hidden = []
        hidden = list(zip(*hidden))

        for i in range(self.num_layers):
            all_output = []
            for j, direction in enumerate(self.layers[i]):
                l = i * self.num_directions + j
                output, hy = direction(input, hidden[l])
                next_hidden.append(hy)
                all_output.append(output)

            input = torch.cat(all_output, -1)

            if self.dropout is not None and i < self.num_layers - 1:
                input = self.dropout(input)

        next_h, next_c = zip(*next_hidden)
        next_hidden = (torch.stack(next_h), torch.stack(next_c))

        return input, next_hidden

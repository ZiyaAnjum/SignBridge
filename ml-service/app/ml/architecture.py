"""PyTorch neural network architectures for SignBridge ISL recognition.
Stored in app/ml/ (versioned with git), keeping models/ strictly for trained weights.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class SignBridgeGRU(nn.Module):
    """Sequence classifier for (batch, 30, 225) landmark sequences.
    Defaults to 1 layer and 64 hidden units as specified.
    """

    def __init__(
        self,
        num_classes: int,
        input_size: int = 225,
        hidden_size: int = 64,
        num_layers: int = 1,
        bidirectional: bool = True,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        self.num_directions = 2 if bidirectional else 1

        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=bidirectional,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        gru_output_dim = hidden_size * self.num_directions

        self.classifier = nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(gru_output_dim, 32),
            nn.ReLU(),
            nn.Dropout(p=dropout / 2.0),
            nn.Linear(32, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.
        Args:
            x: Tensor of shape (batch_size, sequence_length=30, features=225)
        Returns:
            Logits of shape (batch_size, num_classes)
        """
        out, _ = self.gru(x)  # (batch_size, seq_len, gru_output_dim)
        # Global temporal average pooling across the 30 frames
        pooled = torch.mean(out, dim=1)  # (batch_size, gru_output_dim)
        logits = self.classifier(pooled)
        return logits


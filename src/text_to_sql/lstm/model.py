"""Bidirectional LSTM encoder, attention decoder, and pointer-generator output head.

Architecture follows the spec in docs/lstm-baseline-design.md §2:
  - 2-layer bidirectional LSTM encoder (embedding_dim=256, hidden_dim=512)
  - 2-layer unidirectional LSTM decoder with additive attention
  - Pointer-generator mixture over fixed vocab + per-example extended vocab
  - CPU-only smoke target; CUDA optional when available
"""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn


class Encoder(nn.Module):
    """2-layer bidirectional LSTM encoder with packed sequences."""

    def __init__(
        self,
        vocab_size: int,
        embedding_dim: int = 256,
        hidden_dim: int = 512,
        num_layers: int = 2,
        dropout: float = 0.2,
        padding_idx: int = 0,
    ) -> None:
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=padding_idx)
        self.lstm = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=hidden_dim // 2,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=True,
            batch_first=True,
        )
        # Project concatenated final fwd+bwd states to decoder hidden size
        self.hidden_projection = nn.Linear(hidden_dim, hidden_dim)
        self.cell_projection = nn.Linear(hidden_dim, hidden_dim)
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

    def forward(
        self,
        src: torch.Tensor,
        src_lengths: torch.Tensor,
    ) -> tuple[torch.Tensor, tuple[torch.Tensor, torch.Tensor]]:
        """
        Args:
            src: (batch, src_len) token indices
            src_lengths: (batch,) true sequence lengths
        Returns:
            encoder_outputs: (batch, src_len, hidden_dim)
            (h_n, c_n): decoder initial states (num_layers, batch, hidden_dim)
        """
        embedded = self.embedding(src)
        packed = nn.utils.rnn.pack_padded_sequence(
            embedded, src_lengths.cpu(), batch_first=True, enforce_sorted=False
        )
        outputs_packed, (h_n, c_n) = self.lstm(packed)
        encoder_outputs, _ = nn.utils.rnn.pad_packed_sequence(outputs_packed, batch_first=True)

        # h_n: (2*num_layers, batch, hidden_dim//2) — reshape to (num_layers, batch, hidden_dim)
        batch_size = src.size(0)
        h_n = h_n.view(self.num_layers, 2, batch_size, self.hidden_dim // 2)
        h_n = torch.cat([h_n[:, 0, :, :], h_n[:, 1, :, :]], dim=-1)  # (num_layers, batch, hidden_dim)
        c_n = c_n.view(self.num_layers, 2, batch_size, self.hidden_dim // 2)
        c_n = torch.cat([c_n[:, 0, :, :], c_n[:, 1, :, :]], dim=-1)

        h_n = torch.tanh(self.hidden_projection(h_n))
        c_n = torch.tanh(self.cell_projection(c_n))
        return encoder_outputs, (h_n, c_n)


class AdditiveAttention(nn.Module):
    """Bahdanau-style additive attention."""

    def __init__(self, hidden_dim: int) -> None:
        super().__init__()
        self.W_enc = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.W_dec = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.v = nn.Linear(hidden_dim, 1, bias=False)

    def forward(
        self,
        decoder_hidden: torch.Tensor,
        encoder_outputs: torch.Tensor,
        src_mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            decoder_hidden: (batch, hidden_dim)  — top decoder layer hidden state
            encoder_outputs: (batch, src_len, hidden_dim)
            src_mask: (batch, src_len) bool — True where positions are padding
        Returns:
            context: (batch, hidden_dim)
            attention_weights: (batch, src_len)
        """
        energy = self.v(
            torch.tanh(
                self.W_enc(encoder_outputs) + self.W_dec(decoder_hidden).unsqueeze(1)
            )
        ).squeeze(-1)  # (batch, src_len)
        energy = energy.masked_fill(src_mask, float("-inf"))
        attention_weights = F.softmax(energy, dim=-1)
        # Replace NaN from all-padding rows (shouldn't happen in practice)
        attention_weights = attention_weights.nan_to_num(0.0)
        context = (attention_weights.unsqueeze(1) @ encoder_outputs).squeeze(1)
        return context, attention_weights


class PointerGeneratorDecoder(nn.Module):
    """2-layer unidirectional LSTM decoder with pointer-generator output."""

    def __init__(
        self,
        vocab_size: int,
        embedding_dim: int = 256,
        hidden_dim: int = 512,
        num_layers: int = 2,
        dropout: float = 0.2,
        padding_idx: int = 0,
    ) -> None:
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=padding_idx)
        self.lstm = nn.LSTM(
            input_size=embedding_dim + hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.attention = AdditiveAttention(hidden_dim)
        # Vocab projection over fixed vocabulary
        self.W_vocab = nn.Linear(hidden_dim * 2, vocab_size)
        # p_gen switch
        self.W_gen = nn.Linear(hidden_dim * 2 + embedding_dim, 1)
        self.hidden_dim = hidden_dim
        self.vocab_size = vocab_size

    def forward_step(
        self,
        prev_token: torch.Tensor,
        prev_context: torch.Tensor,
        decoder_state: tuple[torch.Tensor, torch.Tensor],
        encoder_outputs: torch.Tensor,
        src_mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, tuple[torch.Tensor, torch.Tensor], torch.Tensor]:
        """Single decoder step.

        Returns:
            logits_combined: (batch, hidden_dim*2)  — for caller to project
            attn_weights: (batch, src_len)
            new_state: updated (h, c)
        """
        embedded = self.embedding(prev_token)  # (batch, embedding_dim)
        lstm_input = torch.cat([embedded, prev_context], dim=-1).unsqueeze(1)
        lstm_output, new_state = self.lstm(lstm_input, decoder_state)
        lstm_output = lstm_output.squeeze(1)  # (batch, hidden_dim)

        top_hidden = new_state[0][-1]  # top layer
        context, attn_weights = self.attention(top_hidden, encoder_outputs, src_mask)
        combined = torch.cat([lstm_output, context], dim=-1)  # (batch, hidden_dim*2)
        return combined, attn_weights, new_state, embedded

    def compute_output_distribution(
        self,
        combined: torch.Tensor,
        embedded: torch.Tensor,
        attn_weights: torch.Tensor,
        extended_vocab_size: int,
        src_token_indices: torch.Tensor,
    ) -> torch.Tensor:
        """Compute the full pointer-generator distribution over V_x.

        Args:
            combined: (batch, hidden_dim*2)
            embedded: (batch, embedding_dim)
            attn_weights: (batch, src_len)
            extended_vocab_size: |V_x| for this batch
            src_token_indices: (batch, src_len) — index of each source token in V_x

        Returns:
            full_dist: (batch, extended_vocab_size)
        """
        p_vocab = F.softmax(self.W_vocab(combined), dim=-1)  # (batch, vocab_size)
        p_gen = torch.sigmoid(self.W_gen(torch.cat([combined, embedded], dim=-1)))  # (batch, 1)

        # Pad p_vocab to extended_vocab_size
        batch_size = combined.size(0)
        full_dist = torch.zeros(batch_size, extended_vocab_size, device=combined.device)
        full_dist[:, : self.vocab_size] = p_gen * p_vocab

        # Accumulate copy probabilities — sum over duplicate source tokens
        copy_weights = (1.0 - p_gen) * attn_weights  # (batch, src_len)
        full_dist.scatter_add_(1, src_token_indices, copy_weights)
        return full_dist


class Seq2SeqLSTM(nn.Module):
    """Assembled encoder + decoder seq2seq model."""

    def __init__(
        self,
        vocab_size: int,
        embedding_dim: int = 256,
        hidden_dim: int = 512,
        num_encoder_layers: int = 2,
        num_decoder_layers: int = 2,
        dropout: float = 0.2,
        padding_idx: int = 0,
    ) -> None:
        super().__init__()
        self.encoder = Encoder(
            vocab_size=vocab_size,
            embedding_dim=embedding_dim,
            hidden_dim=hidden_dim,
            num_layers=num_encoder_layers,
            dropout=dropout,
            padding_idx=padding_idx,
        )
        self.decoder = PointerGeneratorDecoder(
            vocab_size=vocab_size,
            embedding_dim=embedding_dim,
            hidden_dim=hidden_dim,
            num_layers=num_decoder_layers,
            dropout=dropout,
            padding_idx=padding_idx,
        )
        self.hidden_dim = hidden_dim
        self.vocab_size = vocab_size
        self.padding_idx = padding_idx

    def forward(
        self,
        src: torch.Tensor,
        src_lengths: torch.Tensor,
        tgt: torch.Tensor,
        tgt_lengths: torch.Tensor,
        src_token_indices: torch.Tensor,
        extended_vocab_size: int,
        teacher_forcing_ratio: float = 1.0,
    ) -> torch.Tensor:
        """Teacher-forced forward pass.

        Args:
            src: (batch, src_len) encoder input indices
            src_lengths: (batch,) true source lengths
            tgt: (batch, tgt_len) decoder target indices (including <bos>)
            tgt_lengths: (batch,) true target lengths
            src_token_indices: (batch, src_len) extended-vocab index per source token
            extended_vocab_size: |V_x| for this batch
            teacher_forcing_ratio: fraction of steps using gold prev token

        Returns:
            log_probs: (batch, tgt_len-1, extended_vocab_size)
        """
        encoder_outputs, decoder_state = self.encoder(src, src_lengths)
        src_mask = src == self.padding_idx  # (batch, src_len)

        batch_size, tgt_len = tgt.size()
        outputs: list[torch.Tensor] = []
        prev_token = tgt[:, 0]
        prev_context = torch.zeros(batch_size, self.hidden_dim, device=src.device)

        for t in range(1, tgt_len):
            combined, attn_weights, decoder_state, embedded = self.decoder.forward_step(
                prev_token, prev_context, decoder_state, encoder_outputs, src_mask
            )
            prev_context = combined[:, : self.hidden_dim]

            full_dist = self.decoder.compute_output_distribution(
                combined, embedded, attn_weights, extended_vocab_size, src_token_indices
            )
            outputs.append(full_dist.unsqueeze(1))

            use_teacher = torch.rand(1).item() < teacher_forcing_ratio
            prev_token = tgt[:, t] if use_teacher else full_dist.argmax(-1).clamp(max=self.vocab_size - 1)

        return torch.cat(outputs, dim=1)  # (batch, tgt_len-1, extended_vocab_size)

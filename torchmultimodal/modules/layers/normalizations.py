# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Any
import torch
from torch import nn, Tensor


class Fp32LayerNorm(nn.LayerNorm):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def forward(self, x: Tensor) -> Tensor:
        output = nn.functional.layer_norm(
            x.float(),
            self.normalized_shape,
            self.weight.float() if self.weight is not None else None,
            self.bias.float() if self.bias is not None else None,
            self.eps,
        )
        return output.type_as(x)


class Fp32GroupNorm(nn.GroupNorm):
    """
    GroupNorm that supports mixed-precision / fp16 training by performing normalization
    in fp32 and converting back.

    Code ref:
    https://github.com/facebookresearch/fairseq/blob/0338cdc3094ca7d29ff4d36d64791f7b4e4b5e6e/fairseq/modules/fp32_group_norm.py#L13
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def forward(self, x: Tensor) -> Tensor:
        output = nn.functional.group_norm(
            x.float(),
            self.num_groups,
            self.weight.float() if self.weight is not None else None,
            self.bias.float() if self.bias is not None else None,
            self.eps,
        )
        return output.type_as(x)


class RMSNorm(nn.Module):
    """Root Mean Square layer normalization
    as proposed in: https://arxiv.org/abs/1910.07467

    params:
    dim = model size
    eps = epsilon
    """

    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.scale = nn.Parameter(torch.ones(dim))

    def _norm(self, x):
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)

    def forward(self, x):
        x_normed = self._norm(x.float()).type_as(x)
        return x_normed * self.scale

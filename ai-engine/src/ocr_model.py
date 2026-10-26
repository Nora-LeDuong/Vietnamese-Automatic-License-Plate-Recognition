"""
ocr_model.py - CRNN (CNN + BiLSTM + CTC) cho nhan dang bien so VN
------------------------------------------------------------------
Input  : anh bien so grayscale, resize ve 32 x 128
Output : chuoi ky tu bien so (vi du: "51F63034")
"""

import torch
import torch.nn as nn
from torch.nn import functional as F

# ============================================================
# Bo ky tu bien so Viet Nam
# ============================================================
CHARSET    = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
BLANK_IDX  = len(CHARSET)          # CTC blank token
NUM_CLASSES = len(CHARSET) + 1     # 37 chars + 1 blank = 38

# Chieu cao anh input (co dinh)
IMG_H = 32
IMG_W = 128


def char2idx(c: str) -> int:
    return CHARSET.index(c)


def idx2char(i: int) -> str:
    if i == BLANK_IDX:
        return ''
    return CHARSET[i]


# ============================================================
# CNN Backbone
# ============================================================
class ConvBnRelu(nn.Module):
    def __init__(self, in_ch, out_ch, k=3, s=1, p=1):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, k, s, p, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class CNN(nn.Module):
    """
    5 tang Conv: [1,32,128] -> feature map [512,1,32]
    (chieu cao giam ve 1, chieu rong giu nguyen lam sequence)
    """
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(
            # Block 1: 1x32x128 -> 64x16x64
            ConvBnRelu(1, 64),
            nn.MaxPool2d(2, 2),

            # Block 2: 64x16x64 -> 128x8x32
            ConvBnRelu(64, 128),
            nn.MaxPool2d(2, 2),

            # Block 3: 128x8x32 -> 256x4x32
            ConvBnRelu(128, 256),
            ConvBnRelu(256, 256),
            nn.MaxPool2d((2, 1), (2, 1)),   # chi pool chieu cao

            # Block 4: 256x4x32 -> 512x2x32
            ConvBnRelu(256, 512),
            ConvBnRelu(512, 512),
            nn.MaxPool2d((2, 1), (2, 1)),

            # Block 5: 512x2x32 -> 512x1x32
            ConvBnRelu(512, 512, k=2, s=1, p=0),
        )

    def forward(self, x):
        # x: [B, 1, 32, 128]
        f = self.layers(x)          # [B, 512, 1, 32]
        f = f.squeeze(2)            # [B, 512, 32]
        f = f.permute(2, 0, 1)      # [32, B, 512]  (seq, batch, feat)
        return f


# ============================================================
# CRNN = CNN + BiLSTM + Linear
# ============================================================
class CRNN(nn.Module):
    def __init__(self, hidden=256, num_layers=2):
        super().__init__()
        self.cnn  = CNN()
        self.rnn  = nn.LSTM(
            input_size=512,
            hidden_size=hidden,
            num_layers=num_layers,
            bidirectional=True,
            batch_first=False,
            dropout=0.2 if num_layers > 1 else 0.0,
        )
        self.fc   = nn.Linear(hidden * 2, NUM_CLASSES)

    def forward(self, x):
        # x: [B, 1, H, W]
        feat  = self.cnn(x)              # [T, B, 512]
        out, _ = self.rnn(feat)          # [T, B, hidden*2]
        logits = self.fc(out)            # [T, B, num_classes]
        return F.log_softmax(logits, dim=2)


# ============================================================
# CTC Decoder
# ============================================================
class CTCDecoder:
    """Greedy CTC decoder."""

    @staticmethod
    def decode(log_probs: torch.Tensor) -> list[str]:
        """
        Args:
            log_probs: [T, B, C]  (output cua CRNN)
        Returns:
            list of decoded strings, len = B
        """
        # Lay argmax theo class dim
        pred_ids = log_probs.argmax(dim=2)   # [T, B]
        pred_ids = pred_ids.permute(1, 0)    # [B, T]

        results = []
        for ids in pred_ids:
            decoded = CTCDecoder._collapse(ids.tolist())
            results.append(decoded)
        return results

    @staticmethod
    def _collapse(ids: list[int]) -> str:
        """Bo blank va ky tu lap lien tiep."""
        result = []
        prev   = BLANK_IDX
        for idx in ids:
            if idx != BLANK_IDX and idx != prev:
                result.append(idx2char(idx))
            prev = idx
        return ''.join(result)


# ============================================================
# Utility: dem tham so model
# ============================================================
def count_params(model: nn.Module) -> str:
    total = sum(p.numel() for p in model.parameters())
    train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return f"Total: {total:,}  Trainable: {train:,}"


if __name__ == '__main__':
    import torch
    model = CRNN()
    print(f"CRNN params: {count_params(model)}")

    # Test forward pass
    x = torch.randn(4, 1, IMG_H, IMG_W)
    y = model(x)
    print(f"Input:  {x.shape}")
    print(f"Output: {y.shape}  (T, B, C)")

    # Test decoder
    decoded = CTCDecoder.decode(y)
    print(f"Decoded: {decoded}")

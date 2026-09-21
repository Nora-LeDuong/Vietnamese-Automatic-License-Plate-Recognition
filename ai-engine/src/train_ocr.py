"""
train_ocr.py - Train CRNN OCR model cho bien so Viet Nam
---------------------------------------------------------
Usage:
  # Train voi Kaggle dataset + synthetic:
  python ai-engine/src/train_ocr.py --data ai-engine/data/vn_plate_ocr

  # Train chi synthetic (khong can dataset):
  python ai-engine/src/train_ocr.py --synthetic-only

  # Resume tu checkpoint:
  python ai-engine/src/train_ocr.py --resume ai-engine/models/ocr_crnn/last.pt
"""

import argparse
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split

from ocr_model   import CRNN, CTCDecoder, count_params
from ocr_dataset import (KagglePlateDataset, SyntheticPlateDataset,
                          MixedPlateDataset, collate_fn, decode_label)

# ============================================================
# Config mac dinh
# ============================================================
EPOCHS      = 40
BATCH_SIZE  = 128
LR          = 1e-3
LR_MIN      = 1e-5
SYNTH_SIZE  = 20_000    # synthetic bo sung (Kaggle la chinh)
VAL_SPLIT   = 0.1       # 10% du lieu Kaggle lam val
SAVE_DIR    = Path('ai-engine/models/ocr_crnn')
DEVICE      = 'cuda' if torch.cuda.is_available() else 'cpu'


# ============================================================
# CER (Character Error Rate)
# ============================================================
def compute_cer(preds: list[str], targets: list[str]) -> float:
    """Tinh Character Error Rate trung binh."""
    total_dist  = 0
    total_chars = 0
    for p, t in zip(preds, targets):
        total_dist  += edit_distance(p, t)
        total_chars += max(len(t), 1)
    return total_dist / total_chars if total_chars > 0 else 1.0


def edit_distance(s1: str, s2: str) -> int:
    m, n = len(s1), len(s2)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            temp = dp[j]
            if s1[i-1] == s2[j-1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j-1])
            prev = temp
    return dp[n]


# ============================================================
# Validation
# ============================================================
@torch.no_grad()
def validate(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0
    all_preds, all_targets = [], []

    for imgs, targets, lengths in loader:
        imgs    = imgs.to(device)
        targets = targets.to(device)

        logits = model(imgs)                        # [T, B, C]
        T, B, _ = logits.shape
        input_lengths = torch.full((B,), T, dtype=torch.long, device=device)

        loss = criterion(logits, targets, input_lengths, lengths)
        total_loss += loss.item()

        # Decode
        preds = CTCDecoder.decode(logits.cpu())

        # Unpack targets
        offset = 0
        for i, l in enumerate(lengths.tolist()):
            gt = decode_label(targets[offset:offset+l].cpu())
            all_targets.append(gt)
            offset += l
        all_preds.extend(preds)

    cer = compute_cer(all_preds, all_targets)
    acc = sum(p == t for p, t in zip(all_preds, all_targets)) / max(len(all_preds), 1)
    return total_loss / len(loader), cer, acc


# ============================================================
# Training loop
# ============================================================
def train(args):
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n{'='*60}")
    print(f"  VN Plate OCR - CRNN Training")
    print(f"  Device : {DEVICE}")
    print(f"  Epochs : {EPOCHS}")
    print(f"  Batch  : {BATCH_SIZE}")
    print(f"{'='*60}\n")

    # ---- Dataset ----
    synth_train = SyntheticPlateDataset(size=SYNTH_SIZE, augment=True)
    synth_val   = SyntheticPlateDataset(size=5_000,      augment=True)

    if not args.synthetic_only and args.data and Path(args.data).exists():
        print(f"Loading Kaggle dataset from: {args.data}")
        try:
            kaggle_full = KagglePlateDataset(args.data, split='train', augment=True)
            val_n       = max(1, int(len(kaggle_full) * VAL_SPLIT))
            train_n     = len(kaggle_full) - val_n
            kaggle_train, kaggle_val = random_split(kaggle_full, [train_n, val_n])

            train_ds = MixedPlateDataset(synth_train, kaggle_train)
            val_ds   = MixedPlateDataset(synth_val,   kaggle_val)
            print(f"  Kaggle: {len(kaggle_full)} images")
        except Exception as e:
            print(f"  WARNING: Kaggle load failed ({e}), dung synthetic only")
            train_ds = synth_train
            val_ds   = synth_val
    else:
        print("Dung 100% Synthetic data")
        train_ds = synth_train
        val_ds   = synth_val

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              collate_fn=collate_fn, num_workers=0,
                              pin_memory=torch.cuda.is_available())
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,
                              collate_fn=collate_fn, num_workers=0)

    print(f"  Train: {len(train_ds):,}   Val: {len(val_ds):,}")

    # ---- Model ----
    model = CRNN().to(DEVICE)
    print(f"\nModel: {count_params(model)}")

    start_epoch = 1
    best_cer    = 1.0

    if args.resume and Path(args.resume).exists():
        ckpt        = torch.load(args.resume, map_location=DEVICE)
        model.load_state_dict(ckpt['model'])
        start_epoch = ckpt.get('epoch', 0) + 1
        best_cer    = ckpt.get('cer',   1.0)
        print(f"Resumed from epoch {start_epoch-1}, best CER={best_cer:.4f}")

    # ---- Optimizer + Scheduler ----
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=EPOCHS, eta_min=LR_MIN
    )
    criterion = nn.CTCLoss(blank=36, reduction='mean', zero_infinity=True)

    # ---- Training ----
    for epoch in range(start_epoch, EPOCHS + 1):
        model.train()
        total_loss = 0.0
        t0 = time.time()

        for batch_idx, (imgs, targets, lengths) in enumerate(train_loader):
            imgs    = imgs.to(DEVICE)
            targets = targets.to(DEVICE)

            logits = model(imgs)                    # [T, B, C]
            T, B, _ = logits.shape
            input_lengths = torch.full((B,), T, dtype=torch.long, device=DEVICE)

            loss = criterion(logits, targets, input_lengths, lengths)

            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()

            total_loss += loss.item()

            if (batch_idx + 1) % 100 == 0:
                avg = total_loss / (batch_idx + 1)
                print(f"  Epoch {epoch} [{batch_idx+1}/{len(train_loader)}]"
                      f"  loss={avg:.4f}", end='\r', flush=True)

        scheduler.step()

        # ---- Validation ----
        val_loss, cer, acc = validate(model, val_loader, criterion, DEVICE)
        elapsed = time.time() - t0
        lr_now  = optimizer.param_groups[0]['lr']

        print(f"Epoch {epoch:3d}/{EPOCHS}"
              f"  train_loss={total_loss/len(train_loader):.4f}"
              f"  val_loss={val_loss:.4f}"
              f"  CER={cer:.4f}"
              f"  Acc={acc:.4f}"
              f"  lr={lr_now:.2e}"
              f"  [{elapsed:.0f}s]", flush=True)

        # ---- Luu checkpoint ----
        ckpt = {
            'epoch'  : epoch,
            'model'  : model.state_dict(),
            'cer'    : cer,
            'acc'    : acc,
            'config' : {'hidden': 256, 'num_layers': 2},
        }

        # Last checkpoint
        torch.save(ckpt, SAVE_DIR / 'last.pt')

        # Best checkpoint
        if cer < best_cer:
            best_cer = cer
            torch.save(ckpt, SAVE_DIR / 'best.pt')
            print(f"  >>> best.pt saved! (CER={cer:.4f}, Acc={acc:.4f})")

    print(f"\nTraining done! Best CER = {best_cer:.4f}")
    print(f"Model saved: {SAVE_DIR / 'best.pt'}")


# ============================================================
# Entry point
# ============================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data',           type=str,  default='',
                        help='Duong dan Kaggle dataset (tuy chon)')
    parser.add_argument('--synthetic-only', action='store_true',
                        help='Chi dung synthetic data')
    parser.add_argument('--resume',         type=str,  default='',
                        help='Resume tu checkpoint .pt')
    parser.add_argument('--epochs',         type=int,  default=EPOCHS)
    parser.add_argument('--batch',          type=int,  default=BATCH_SIZE)
    args = parser.parse_args()

    EPOCHS     = args.epochs
    BATCH_SIZE = args.batch

    train(args)

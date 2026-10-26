"""
train.py - Huan luyen YOLOv8-OBB de phat hien bien so xe

Dataset: 3779 train + 1232 val, dinh dang OBB (9 gia tri moi label)
Su dung: python src/train.py
"""

import sys
from pathlib import Path
from ultralytics import YOLO
import torch

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# ========================================
# CẤU HÌNH
# ========================================
BASE_DIR     = Path(__file__).resolve().parent.parent
DATASET_YAML = BASE_DIR / "data" / "yolo_dataset" / "dataset.yaml"
MODELS_DIR   = BASE_DIR / "models"

# Chon device
if torch.cuda.is_available():
    device = "0"
    gpu    = torch.cuda.get_device_name(0)
    vram   = torch.cuda.get_device_properties(0).total_memory // 1024**2
    print(f"GPU: {gpu}  ({vram} MB VRAM)")
    # RTX 4050 6GB: batch 16 an toan
    batch  = 16
    epochs = 100
else:
    device = "cpu"
    print("Khong co GPU -> dung CPU (se rat cham)")
    batch  = 8
    epochs = 30

CONFIG = {
    # Model detect tieu chuan - labels da duoc chuyen sang AABB 5-value
    "model":       "yolov8n.pt",
    "epochs":      epochs,
    "imgsz":       640,
    "batch":       batch,
    "device":      device,
    "patience":    20,          # Early stopping
    "save":        True,
    "save_period": 10,
    "project":     str(MODELS_DIR),
    "name":        "license_plate_det",
    "exist_ok":    True,
    "pretrained":  True,        # Dung pretrained COCO weights
    "optimizer":   "AdamW",
    "lr0":         0.001,       # AdamW hoat dong tot hon SGD voi lr thap hon
    "lrf":         0.01,
    "warmup_epochs": 3,
    "cos_lr":      True,        # Cosine LR scheduler
    "augment":     True,
    "hsv_h":       0.015,
    "hsv_s":       0.7,
    "hsv_v":       0.4,
    "degrees":     5.0,         # Rotation aug (bien so hoi nghieng)
    "translate":   0.1,
    "scale":       0.5,
    "mosaic":      1.0,
    "mixup":       0.1,
    "verbose":     True,
    "workers":     4,
    "cache":       False,       # Tat cache neu RAM it
}


def train():
    print("=" * 60)
    print("  HUAN LUYEN YOLOv8-OBB NHAN DIEN BIEN SO XE")
    print("=" * 60)
    print(f"\nDataset : {DATASET_YAML}")
    print(f"Model   : {CONFIG['model']}")
    print(f"Epochs  : {CONFIG['epochs']}")
    print(f"Batch   : {CONFIG['batch']}")
    print(f"Device  : {CONFIG['device']}")
    print(f"ImgSz   : {CONFIG['imgsz']}")

    if not DATASET_YAML.exists():
        print(f"\nLOI: Khong tim thay {DATASET_YAML}")
        sys.exit(1)

    train_dir = DATASET_YAML.parent / "images" / "train"
    n_train   = len(list(train_dir.glob("*"))) if train_dir.exists() else 0
    val_dir   = DATASET_YAML.parent / "images" / "val"
    n_val     = len(list(val_dir.glob("*"))) if val_dir.exists() else 0
    print(f"\nAnh train: {n_train}   Anh val: {n_val}")

    if n_train == 0:
        print("LOI: Khong co anh train!")
        sys.exit(1)

    # Tai model pretrained
    print(f"\nDang tai model {CONFIG['model']} ...")
    model = YOLO(CONFIG["model"])

    print(f"\nBat dau huan luyen {CONFIG['epochs']} epochs ...\n")
    results = model.train(
        data        = str(DATASET_YAML),
        epochs      = CONFIG["epochs"],
        imgsz       = CONFIG["imgsz"],
        batch       = CONFIG["batch"],
        device      = CONFIG["device"],
        patience    = CONFIG["patience"],
        save        = CONFIG["save"],
        save_period = CONFIG["save_period"],
        project     = CONFIG["project"],
        name        = CONFIG["name"],
        exist_ok    = CONFIG["exist_ok"],
        pretrained  = CONFIG["pretrained"],
        optimizer   = CONFIG["optimizer"],
        lr0         = CONFIG["lr0"],
        lrf         = CONFIG["lrf"],
        warmup_epochs = CONFIG["warmup_epochs"],
        cos_lr      = CONFIG["cos_lr"],
        augment     = CONFIG["augment"],
        hsv_h       = CONFIG["hsv_h"],
        hsv_s       = CONFIG["hsv_s"],
        hsv_v       = CONFIG["hsv_v"],
        degrees     = CONFIG["degrees"],
        translate   = CONFIG["translate"],
        scale       = CONFIG["scale"],
        mosaic      = CONFIG["mosaic"],
        mixup       = CONFIG["mixup"],
        verbose     = CONFIG["verbose"],
        workers     = CONFIG["workers"],
        cache       = CONFIG["cache"],
    )

    print("\n" + "=" * 60)
    print("  HUAN LUYEN HOAN TAT!")
    print("=" * 60)

    best = MODELS_DIR / "license_plate_det" / "weights" / "best.pt"
    if best.exists():
        print(f"Model tot nhat: {best}")
    else:
        print(f"Kiem tra thu muc: {MODELS_DIR / 'license_plate_det'}")

    return results


if __name__ == "__main__":
    train()

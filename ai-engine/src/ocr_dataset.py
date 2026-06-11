"""
ocr_dataset.py - Dataset loader cho train OCR bien so VN
---------------------------------------------------------
Ho tro cac format pho bien cua Kaggle VN plate OCR dataset:
  1. Ten file = label:  "51F63034.jpg"  hoac  "51F-630.34.jpg"
  2. CSV file:          image,label
  3. Thu muc con = label: labels/51F63034/img001.jpg
  4. Synthetic generator (khong can download gi)
"""

import re
import csv
import random
import string
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from ocr_model import CHARSET, BLANK_IDX, IMG_H, IMG_W


# ============================================================
# Helper: chuan hoa label -> chi giu A-Z, 0-9
# ============================================================
def clean_label(text: str) -> str:
    return re.sub(r'[^A-Z0-9]', '', text.upper())


# ============================================================
# Preprocess anh bien so -> tensor [1, H, W]
# ============================================================
def preprocess_plate(img: np.ndarray) -> torch.Tensor:
    """
    Chuyen anh BGR / Gray ve tensor [1, 32, 128] normalized.
    """
    # Gray
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Resize
    img = cv2.resize(img, (IMG_W, IMG_H), interpolation=cv2.INTER_CUBIC)

    # Normalize [0,1]
    img = img.astype(np.float32) / 255.0

    # [H, W] -> [1, H, W]
    return torch.from_numpy(img).unsqueeze(0)


# ============================================================
# Label encode / decode
# ============================================================
def encode_label(text: str) -> torch.Tensor:
    """Chuyen text -> tensor int64, bo qua ky tu khong trong CHARSET."""
    indices = [CHARSET.index(c) for c in text if c in CHARSET]
    return torch.tensor(indices, dtype=torch.long)


def decode_label(tensor: torch.Tensor) -> str:
    return ''.join(CHARSET[i] for i in tensor.tolist() if i < len(CHARSET))


# ============================================================
# 1. Dataset tu Kaggle (tu dong nhan dien format)
# ============================================================
class KagglePlateDataset(Dataset):
    """
    Tu dong nhan dien format dataset:
      - Format A: label la ten file (khong co extension)
      - Format B: CSV file voi cot 'image' va 'label'
      - Format C: Thu muc con la label
    """

    def __init__(self, root: str, split: str = 'train',
                 augment: bool = False):
        self.root    = Path(root)
        self.augment = augment
        self.samples = []   # list of (img_path, label_str)

        # Thu tu uu tien tim du lieu
        self._load(split)
        print(f"[KagglePlateDataset] {split}: {len(self.samples)} samples "
              f"(root={self.root})")

    def _load(self, split: str):
        data_root = self.root

        # --- Format nay: labels/crop_labels.csv + labels/gen_labels.csv ---
        # Anh nam trong: cropped/ va generated/
        loaded = 0
        for csv_name in ['crop_labels.csv', 'gen_labels.csv']:
            csv_path = data_root / 'labels' / csv_name
            if not csv_path.exists():
                continue

            # Thu muc anh tuong ung
            if 'crop' in csv_name:
                img_dir = data_root / 'cropped'
            else:
                img_dir = data_root / 'generated'

            with open(csv_path, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name  = row.get('Name', '').strip()
                    label = row.get('Label', '').strip()
                    if not name or not label:
                        continue
                    label = clean_label(label)        # bo khoang trang, dau
                    if not (4 <= len(label) <= 10):
                        continue
                    img_path = img_dir / name
                    if img_path.exists():
                        self.samples.append((img_path, label))
                        loaded += 1

        if loaded > 0:
            return

        # --- Fallback: Format A (ten file = label) ---
        for d in [data_root / split, data_root / 'images' / split,
                  data_root / split / 'images', data_root]:
            if d.exists():
                self._load_filename_label(d)
                if self.samples:
                    return

        self._load_filename_label(data_root, recursive=True)

    def _load_subfolders(self, parent: Path):
        for sub in sorted(parent.iterdir()):
            if not sub.is_dir():
                continue
            label = clean_label(sub.name)
            if not (4 <= len(label) <= 9):
                continue
            for ext in ('*.jpg', '*.jpeg', '*.png', '*.bmp'):
                for img_path in sub.glob(ext):
                    self.samples.append((img_path, label))

    def _load_filename_label(self, directory: Path, recursive: bool = False):
        pattern = '**/*' if recursive else '*'
        for img_path in directory.glob(pattern):
            if img_path.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.bmp'):
                continue
            label = clean_label(img_path.stem)
            if 4 <= len(label) <= 9:
                self.samples.append((img_path, label))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]

        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            img = np.zeros((IMG_H, IMG_W), dtype=np.uint8)

        if self.augment:
            img = augment_plate(img)

        tensor = preprocess_plate(img)
        target = encode_label(label)
        return tensor, target, len(label)


# ============================================================
# 2. Synthetic plate generator
# ============================================================

# Ma tinh pho bien
_PROVINCES = [
    '11','12','14','15','16','17','18','19',
    '20','21','22','23','24','25','26','27','28','29',
    '30','31','32','33','34','36','37','38',
    '40','41','43','47','48','49',
    '51','52','53','54','55','56','57','58','59',
    '60','61','62','63','64','65','66','67','68','69',
    '70','71','72','73','74','75','76','77','78','79',
    '81','82','83','84','85','86','88','89',
    '92','93','94',
]

_SERIES_1 = list('ABCDEFGHKLMNPRSTUVXY')   # chu cai hay gap tren bien VN
_SERIES_2 = [a+b for a in _SERIES_1 for b in _SERIES_1]


def random_vn_plate() -> str:
    """Tao bien so VN ngau nhien hop le (chi alphanumeric)."""
    prov = random.choice(_PROVINCES)
    if random.random() < 0.15:                          # 15% bien 2 chu
        series = random.choice(_SERIES_2)
        num    = str(random.randint(10000, 99999))
    else:
        series = random.choice(_SERIES_1)
        num    = str(random.randint(10000, 99999)).zfill(5)
    return prov + series + num


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Tim font Arial Bold hoac fallback."""
    candidates = [
        'C:/Windows/Fonts/arialbd.ttf',
        'C:/Windows/Fonts/arial.ttf',
        'C:/Windows/Fonts/calibrib.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def render_plate(text: str, w: int = IMG_W, h: int = IMG_H) -> np.ndarray:
    """
    Render bien so tren nen trang, text den, tra ve anh grayscale.
    text: chuoi alphanumeric (vi du: "51F63034")
    """
    img  = Image.new('L', (w, h), color=240)   # nen sang
    draw = ImageDraw.Draw(img)

    # Tim kich thuoc font phu hop
    font_size = int(h * 0.75)
    font = _get_font(font_size)

    # Tinh vi tri de can giua
    try:
        bb = draw.textbbox((0, 0), text, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
    except Exception:
        tw, th = font_size * len(text) // 2, font_size

    x = (w - tw) // 2
    y = (h - th) // 2

    draw.text((x, y), text, fill=20, font=font)   # text mau toi
    return np.array(img)


def augment_plate(img: np.ndarray) -> np.ndarray:
    """Augmentation nhe cho anh bien so grayscale (an toan voi moi input)."""
    # Kiem tra input hop le
    if img is None or img.size == 0:
        return np.zeros((IMG_H, IMG_W), dtype=np.uint8)

    # Dam bao uint8 grayscale 2D
    img = np.clip(img, 0, 255).astype(np.uint8)
    if img.ndim != 2:
        img = img[:, :, 0] if img.ndim == 3 else np.zeros((IMG_H, IMG_W), dtype=np.uint8)

    try:
        # 1. Do sang ngau nhien
        delta = random.randint(-30, 30)
        img   = np.clip(img.astype(np.int16) + delta, 0, 255).astype(np.uint8)
    except Exception:
        pass

    try:
        # 2. Noise Gaussian nhe
        if random.random() < 0.5:
            noise = np.random.randn(*img.shape) * random.uniform(3, 12)
            img   = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    except Exception:
        pass

    try:
        # 3. Blur nhe
        if random.random() < 0.3:
            k   = random.choice([3, 5])
            img = cv2.GaussianBlur(img.copy(), (k, k), 0)
            img = np.clip(img, 0, 255).astype(np.uint8)
    except Exception:
        pass

    try:
        # 4. Xoay nhe +-5 do
        if random.random() < 0.5:
            angle = random.uniform(-5, 5)
            M     = cv2.getRotationMatrix2D(
                (img.shape[1] // 2, img.shape[0] // 2), angle, 1.0)
            img = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]),
                                 borderValue=240)
            img = np.clip(img, 0, 255).astype(np.uint8)
    except Exception:
        pass

    try:
        # 5. Co gian phoi canh nhe
        if random.random() < 0.3:
            pts1 = np.float32([[0,0],[IMG_W,0],[0,IMG_H],[IMG_W,IMG_H]])
            dx, dy = random.randint(0, 4), random.randint(0, 3)
            pts2 = np.float32([[dx,dy],[IMG_W-dx,dy],[dx,IMG_H-dy],[IMG_W-dx,IMG_H-dy]])
            M    = cv2.getPerspectiveTransform(pts1, pts2)
            img  = cv2.warpPerspective(img, M, (IMG_W, IMG_H), borderValue=240)
            img  = np.clip(img, 0, 255).astype(np.uint8)
    except Exception:
        pass

    return img


class SyntheticPlateDataset(Dataset):
    """
    Generator on-the-fly: moi epoch tao anh khac nhau.
    Khong can download gi.
    """
    def __init__(self, size: int = 100_000, augment: bool = True):
        self.size    = size
        self.augment = augment
        # Pre-generate labels, anh render on-the-fly
        self.labels  = [random_vn_plate() for _ in range(size)]

    def __len__(self):
        return self.size

    def __getitem__(self, idx):
        label = self.labels[idx]
        img   = render_plate(label)           # render
        if self.augment:
            img = augment_plate(img)          # augment
        tensor = preprocess_plate(img)
        target = encode_label(label)
        return tensor, target, len(label)


# ============================================================
# ConcatDataset tien ich
# ============================================================
class MixedPlateDataset(Dataset):
    """Gop Kaggle dataset + Synthetic."""
    def __init__(self, *datasets):
        self.datasets = datasets
        self.lengths  = [len(d) for d in datasets]
        self.cumlen   = []
        s = 0
        for l in self.lengths:
            s += l
            self.cumlen.append(s)

    def __len__(self):
        return self.cumlen[-1]

    def __getitem__(self, idx):
        for i, cl in enumerate(self.cumlen):
            if idx < cl:
                offset = idx - (self.cumlen[i-1] if i > 0 else 0)
                return self.datasets[i][offset]
        raise IndexError(idx)


# ============================================================
# Collate function cho DataLoader (labels co chieu dai khac nhau)
# ============================================================
def collate_fn(batch):
    imgs, targets, lengths = zip(*batch)
    imgs   = torch.stack(imgs, 0)                      # [B, 1, H, W]
    targets = torch.cat(targets, 0)                    # [sum_lengths]
    lengths = torch.tensor(lengths, dtype=torch.long)  # [B]
    return imgs, targets, lengths


# ============================================================
# Test nhanh
# ============================================================
if __name__ == '__main__':
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    ds = SyntheticPlateDataset(size=8, augment=True)
    fig, axes = plt.subplots(2, 4, figsize=(16, 4))
    for i, ax in enumerate(axes.flat):
        tensor, target, length = ds[i]
        label = decode_label(target)
        ax.imshow(tensor.squeeze().numpy(), cmap='gray')
        ax.set_title(label, fontsize=9)
        ax.axis('off')
    plt.tight_layout()
    plt.savefig('ai-engine/temp/synthetic_samples.png', dpi=100)
    print(f"Saved: ai-engine/temp/synthetic_samples.png")
    print(f"Sample labels: {[decode_label(ds[i][1]) for i in range(8)]}")

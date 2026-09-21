"""
data_prep.py - Chuẩn bị dữ liệu từ Kaggle cho YOLOv8

Chức năng:
1. Tải dataset andrewmvd/car-plate-detection từ Kaggle
2. Parse file XML (PASCAL VOC format) sang TXT (YOLO format)
3. Chia tập train/val (80/20)
"""

import os
import sys
import shutil
import random
import xml.etree.ElementTree as ET
from pathlib import Path

# Đảm bảo in được emoji và tiếng Việt trên Windows CMD/Powershell
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


# ========================================
# CẤU HÌNH
# ========================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATASET_NAME = "andrewmvd/car-plate-detection"

# Thư mục đầu ra cho YOLO
YOLO_DIR = DATA_DIR / "yolo_dataset"
TRAIN_IMAGES = YOLO_DIR / "images" / "train"
TRAIN_LABELS = YOLO_DIR / "labels" / "train"
VAL_IMAGES = YOLO_DIR / "images" / "val"
VAL_LABELS = YOLO_DIR / "labels" / "val"

# Class mapping - dataset này chỉ có 1 class: licence (biển số xe)
CLASS_MAP = {"licence": 0}

TRAIN_RATIO = 0.8  # 80% train, 20% val


def download_dataset():
    """Tải dataset từ Kaggle sử dụng kagglehub."""
    print("=" * 60)
    print("📥 Đang tải dataset từ Kaggle...")
    print(f"   Dataset: {DATASET_NAME}")
    print("=" * 60)

    try:
        import kagglehub
        dataset_path = kagglehub.dataset_download(DATASET_NAME)
        print(f"✅ Tải thành công! Dữ liệu tại: {dataset_path}")
        return Path(dataset_path)
    except ImportError:
        print("❌ Chưa cài kagglehub. Đang thử cài đặt...")
        os.system(f'"{sys.executable}" -m pip install kagglehub')
        import kagglehub
        dataset_path = kagglehub.dataset_download(DATASET_NAME)
        print(f"✅ Tải thành công! Dữ liệu tại: {dataset_path}")
        return Path(dataset_path)
    except Exception as e:
        print(f"❌ Lỗi khi tải dataset: {e}")
        print("\n💡 Hướng dẫn thủ công:")
        print(f"   1. Truy cập: https://www.kaggle.com/datasets/{DATASET_NAME}")
        print(f"   2. Tải về và giải nén vào: {DATA_DIR / 'raw'}")
        sys.exit(1)


def convert_voc_to_yolo(xml_file: Path, img_width: int, img_height: int):
    """
    Chuyển đổi annotation từ PASCAL VOC (XML) sang YOLO (TXT).

    YOLO format: <class_id> <x_center> <y_center> <width> <height>
    Tất cả giá trị được chuẩn hóa (normalized) về [0, 1].
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()
    yolo_lines = []

    for obj in root.findall("object"):
        class_name = obj.find("name").text.strip().lower()
        if class_name not in CLASS_MAP:
            print(f"   ⚠️ Bỏ qua class không xác định: '{class_name}' trong {xml_file.name}")
            continue

        class_id = CLASS_MAP[class_name]
        bndbox = obj.find("bndbox")
        xmin = float(bndbox.find("xmin").text)
        ymin = float(bndbox.find("ymin").text)
        xmax = float(bndbox.find("xmax").text)
        ymax = float(bndbox.find("ymax").text)

        # Chuẩn hóa tọa độ
        x_center = ((xmin + xmax) / 2.0) / img_width
        y_center = ((ymin + ymax) / 2.0) / img_height
        width = (xmax - xmin) / img_width
        height = (ymax - ymin) / img_height

        # Clamp giá trị trong [0, 1]
        x_center = max(0.0, min(1.0, x_center))
        y_center = max(0.0, min(1.0, y_center))
        width = max(0.0, min(1.0, width))
        height = max(0.0, min(1.0, height))

        yolo_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")

    return yolo_lines


def get_image_size_from_xml(xml_file: Path):
    """Đọc kích thước ảnh từ file XML annotation."""
    tree = ET.parse(xml_file)
    root = tree.getroot()
    size = root.find("size")
    if size is not None:
        w = int(size.find("width").text)
        h = int(size.find("height").text)
        if w > 0 and h > 0:
            return w, h

    # Fallback: đọc trực tiếp từ ảnh
    return None, None


def get_image_size_from_file(img_path: Path):
    """Đọc kích thước ảnh trực tiếp từ file ảnh."""
    try:
        from PIL import Image
        with Image.open(img_path) as img:
            return img.size  # (width, height)
    except Exception:
        return None, None


def prepare_dataset():
    """Quy trình chính: tải dữ liệu, convert và chia tập."""

    # Bước 1: Tải dataset
    raw_path = download_dataset()

    # Tìm thư mục chứa ảnh và annotations
    images_dir = None
    annotations_dir = None

    for root_dir, dirs, files in os.walk(raw_path):
        root_p = Path(root_dir)
        if root_p.name.lower() == "images" and any(f.lower().endswith(('.png', '.jpg', '.jpeg')) for f in files):
            images_dir = root_p
        if root_p.name.lower() == "annotations" and any(f.lower().endswith('.xml') for f in files):
            annotations_dir = root_p

    if images_dir is None or annotations_dir is None:
        # Thử tìm kiếm trực tiếp
        all_images = list(raw_path.rglob("*.png")) + list(raw_path.rglob("*.jpg")) + list(raw_path.rglob("*.jpeg"))
        all_xmls = list(raw_path.rglob("*.xml"))
        if all_images and all_xmls:
            images_dir = all_images[0].parent
            annotations_dir = all_xmls[0].parent
        else:
            print(f"❌ Không tìm thấy thư mục images/annotations trong: {raw_path}")
            print(f"   Nội dung: {list(raw_path.iterdir())}")
            sys.exit(1)

    print(f"\n📁 Thư mục ảnh:        {images_dir}")
    print(f"📁 Thư mục annotation: {annotations_dir}")

    # Bước 2: Tạo thư mục đầu ra
    for d in [TRAIN_IMAGES, TRAIN_LABELS, VAL_IMAGES, VAL_LABELS]:
        d.mkdir(parents=True, exist_ok=True)

    # Bước 3: Lấy danh sách các cặp ảnh-annotation
    xml_files = sorted(annotations_dir.glob("*.xml"))
    print(f"\n📊 Tổng số annotation: {len(xml_files)}")

    pairs = []
    for xml_file in xml_files:
        stem = xml_file.stem
        img_file = None
        for ext in [".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"]:
            candidate = images_dir / (stem + ext)
            if candidate.exists():
                img_file = candidate
                break
        if img_file:
            pairs.append((img_file, xml_file))
        else:
            print(f"   ⚠️ Không tìm thấy ảnh cho: {xml_file.name}")

    print(f"📊 Số cặp ảnh-annotation hợp lệ: {len(pairs)}")

    # Bước 4: Shuffle và chia tập
    random.seed(42)
    random.shuffle(pairs)
    split_idx = int(len(pairs) * TRAIN_RATIO)
    train_pairs = pairs[:split_idx]
    val_pairs = pairs[split_idx:]

    print(f"   🔹 Train: {len(train_pairs)} ảnh")
    print(f"   🔹 Val:   {len(val_pairs)} ảnh")

    # Bước 5: Convert và copy
    def process_pairs(pair_list, img_dir, lbl_dir, set_name):
        success = 0
        for img_file, xml_file in pair_list:
            # Đọc kích thước ảnh
            w, h = get_image_size_from_xml(xml_file)
            if w is None or h is None:
                w, h = get_image_size_from_file(img_file)
            if w is None or h is None:
                print(f"   ⚠️ Không đọc được kích thước: {img_file.name}")
                continue

            # Convert annotation
            yolo_lines = convert_voc_to_yolo(xml_file, w, h)
            if not yolo_lines:
                continue

            # Copy ảnh
            dst_img = img_dir / img_file.name
            shutil.copy2(img_file, dst_img)

            # Lưu label
            label_file = lbl_dir / (img_file.stem + ".txt")
            with open(label_file, "w") as f:
                f.write("\n".join(yolo_lines))

            success += 1
        print(f"   ✅ {set_name}: {success}/{len(pair_list)} ảnh đã xử lý thành công")

    print("\n🔄 Đang chuyển đổi dữ liệu...")
    process_pairs(train_pairs, TRAIN_IMAGES, TRAIN_LABELS, "Train")
    process_pairs(val_pairs, VAL_IMAGES, VAL_LABELS, "Val")

    print(f"\n🎉 Hoàn tất! Dữ liệu YOLO được lưu tại: {YOLO_DIR}")
    print(f"   📂 images/train: {len(list(TRAIN_IMAGES.iterdir()))} files")
    print(f"   📂 images/val:   {len(list(VAL_IMAGES.iterdir()))} files")
    print(f"   📂 labels/train: {len(list(TRAIN_LABELS.iterdir()))} files")
    print(f"   📂 labels/val:   {len(list(VAL_LABELS.iterdir()))} files")


if __name__ == "__main__":
    prepare_dataset()

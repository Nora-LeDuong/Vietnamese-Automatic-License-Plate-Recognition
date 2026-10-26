"""
inference.py - Pipeline nhận diện biển số xe (YOLO + CRNN OCR)

Pipeline: Ảnh/Video → YOLOv8 detect biển số → Crop → CRNN OCR đọc chữ
→ Vẽ bounding box + text lên ảnh/video gốc → Trả kết quả
"""

import os
import sys
import cv2
import numpy as np
import base64
from pathlib import Path
from ultralytics import YOLO

# Đảm bảo in được emoji và tiếng Việt trên Windows CMD/Powershell
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


# ========================================
# CẤU HÌNH
# ========================================
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_PATH = BASE_DIR / "models" / "license_plate_det" / "weights" / "best.pt"

# Nguong confidence cho YOLO detection
CONF_THRESHOLD = 0.25

# Cau hinh ve bounding box
BOX_THICKNESS  = 2
FONT_SCALE     = 0.65
FONT_THICKNESS = 2
TEXT_COLOR     = (255, 255, 255)   # Trang

# Ty le bo sat bien (% theo chieu rong/cao cua bbox)
# Giup khung hien thi bam sat bien so hon khi YOLO du doan box rong
BBOX_INSET_X = 0.04   # Bo 4% trai + 4% phai
BBOX_INSET_Y = 0.05   # Bo 5% tren + 5% duoi


def _inset_bbox(x1: int, y1: int, x2: int, y2: int):
    """Thu nho bbox ve phia trong de bam sat bien so hon."""
    w  = x2 - x1
    h  = y2 - y1
    dx = max(1, int(w * BBOX_INSET_X))
    dy = max(1, int(h * BBOX_INSET_Y))
    return x1 + dx, y1 + dy, x2 - dx, y2 - dy

# ============================================================
# Bien so Viet Nam: bang ma tinh va map nham lan OCR
# ============================================================
_VN_PROVINCE_CODES = frozenset({
    '11','12','14','15','16','17','18','19',
    '20','21','22','23','24','25','26','27','28','29',
    '30','31','32','33','34','36','37','38',
    '40','41','43','47','48','49',
    '51','52','53','54','55','56','57','58','59',
    '60','61','62','63','64','65','66','67','68','69',
    '70','71','72','73','74','75','76','77','78','79',
    '80','81','82','83','84','85','86','88','89',
    '92','93','94','95','96','97','98','99',
})

# Ky tu hay bi OCR nham trong VUNG SO (can la so)
_OCR_CHAR_TO_DIGIT = {
    'O': '0', 'Q': '0', 'D': '0',
    'I': '1', 'L': '1', 'J': '1',
    'Z': '2',
    'E': '3',
    'A': '4',
    'S': '5', 'F': '5',          # 5 mat net cong duoi -> bi doc la F
    'G': '6',
    'T': '7',
    'B': '8',
    'P': '9',
}

# So hay bi OCR nham trong VUNG CHU (can la chu cai)
_OCR_DIGIT_TO_CHAR = {
    '0': 'O',
    '1': 'I',
    '2': 'Z',
    '4': 'A',
    '5': 'S',
    '6': 'G',
    '7': 'T',
    '8': 'B',
    '9': 'P',
}

# Mau theo confidence (BGR)
def _conf_color(conf: float):
    """Tra ve mau (BGR) theo confidence: xanh >= 80%, vang >= 50%, do < 50%."""
    if conf >= 0.80:
        return (50, 205, 50)     # Xanh la tuoi  (lime green)
    elif conf >= 0.50:
        return (0, 200, 255)     # Vang cam      (yellow-orange BGR)
    else:
        return (60, 60, 220)     # Do tuoi       (red BGR)


class ALPREngine:
    """Engine nhận diện biển số xe tích hợp YOLO + EasyOCR."""

    def __init__(self, model_path: str = None):
        """
        Khoi tao ALPR Engine.
        Tu dong chon GPU (CUDA) neu co, fallback sang CPU.
        """
        import torch

        model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        if not model_path.exists():
            raise FileNotFoundError(
                f"Khong tim thay model YOLO tai: {model_path}\n"
                "Hay chay 'python src/train.py' de huan luyen model truoc!"
            )

        # --- Chon device ---
        if torch.cuda.is_available():
            self.device = "cuda:0"
            gpu_name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory // 1024**2
            print(f"GPU: {gpu_name}  ({vram} MB VRAM)  [CUDA {torch.version.cuda}]")
        else:
            self.device = "cpu"
            print("GPU: khong co CUDA -> dung CPU")

        # --- YOLO ---
        print(f"Dang tai YOLO model: {model_path.name}  [device={self.device}]")
        self.yolo_model = YOLO(str(model_path))
        self.yolo_model.to(self.device)

        # --- CRNN OCR Engine ---
        print(f"Dang khoi tao CRNN OCR engine...")
        # Import o day tranh circular import va delay load GPU
        sys.path.insert(0, str(Path(__file__).parent))
        from ocr_engine import PlateOCREngine
        self.plate_ocr = PlateOCREngine(device=self.device)
        print(f"Engine san sang!  (device={self.device})")

    def detect_plates(self, frame: np.ndarray):
        """
        Phát hiện biển số trong một frame ảnh.

        Returns:
            List[dict]: Mỗi dict chứa {bbox, confidence, plate_text}
        """
        results = self.yolo_model(frame, conf=CONF_THRESHOLD, verbose=False, device=self.device)
        detections = []

        for result in results:
            if result.boxes is None or len(result.boxes) == 0:
                continue

            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = float(box.conf[0])

                # Crop vùng biển số
                plate_crop = frame[y1:y2, x1:x2]

                # Đọc chữ bằng EasyOCR
                plate_text = self._read_plate_text(plate_crop)

                # Sửa lỗi OCR theo định dạng biển số Việt Nam
                if plate_text:
                    corrected = self._correct_vn_plate(plate_text)
                    if corrected != plate_text:
                        print(f"   [VN-fix] '{plate_text}' → '{corrected}'")
                    plate_text = corrected

                detections.append({
                    "bbox": [x1, y1, x2, y2],
                    "confidence": round(conf, 4),
                    "plate_text": plate_text,
                })

        return detections

    @staticmethod
    def _is_plate_component(alnum: str) -> bool:
        """
        Kiem tra chuoi alphanumeric co phai thanh phan bien so hop le khong.

        Bien so xe co ty le so/chu cao. Cac nhan hieu, ban chieu, ten dia phuong
        thuong toan chu hoac it so -> bi loai.

        Vi du hop le  : '30G', '636', '11', '88A', '39307', '51F', 'B1G85'
        Vi du bi loai : 'VIE', 'IO1LL', 'LIMITED', 'EDITION', 'XE'
        """
        import re
        t = alnum.upper()
        if len(t) < 2 or len(t) > 12:
            return False

        digits  = sum(1 for c in t if c.isdigit())
        letters = sum(1 for c in t if c.isalpha())
        total   = digits + letters
        if total == 0:
            return False

        # Toan so (>= 2 chu so) -> hop le (phan so tren bien)
        if letters == 0 and digits >= 2:
            return True

        # Kieu ma dia phuong VN: 2 so + 1-2 chu  (30G, 51F, 88AB)
        if re.match(r'^\d{2}[A-Z]{1,2}$', t):
            return True

        # Kieu bien quoc te co so: ty le so >= 35% -> hop le
        if digits >= 1 and digits / total >= 0.35:
            return True

        # Con lai: chu nhieu hon so -> likely nhan hieu / ban chieu
        return False

    @staticmethod
    def _clean_token(text: str) -> str:
        """Lam sach 1 token OCR va kiem tra tinh hop le cua no."""
        import re
        # Thay the ky tu khong phai alphanumeric bang khoang trang
        cleaned = re.sub(r'[^A-Za-z0-9]', ' ', text).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)          # Gop khoang trang kep
        alnum   = cleaned.replace(' ', '')              # Chi alphanumeric
        if not ALPREngine._is_plate_component(alnum):
            return ''
        return cleaned.upper().strip()

    def _read_plate_text(self, plate_crop: np.ndarray) -> str:
        """
        Doc text bien so tu anh da crop.

        Su dung CRNN OCR engine de doc bien so tu anh da crop.
        CRNN xu ly toan bo bien so trong 1 lan inference (~0.5ms/plate).
        """
        if plate_crop is None or plate_crop.size == 0:
            return ''
        try:
            return self.plate_ocr.read(plate_crop)
        except Exception as e:
            print(f'   OCR error: {e}')
            return ''


    def _draw_results(self, frame: np.ndarray, detections: list,
                      best_only: bool = False) -> np.ndarray:
        """
        Ve bounding box va text len frame.

        Args:
            frame:      Frame goc.
            detections: Danh sach detection [{bbox, confidence, plate_text}].
            best_only:  Neu True, chi ve detection co confidence cao nhat (dung cho video).
        """
        if not detections:
            return frame.copy()

        annotated = frame.copy()

        # Neu best_only: chi lay detection cao nhat
        to_draw = sorted(detections, key=lambda d: d["confidence"], reverse=True)
        if best_only:
            to_draw = to_draw[:1]

        for det in to_draw:
            x1, y1, x2, y2 = det["bbox"]
            text = det["plate_text"]
            conf = det["confidence"]
            color = _conf_color(conf)   # (B, G, R)

            # --- Bounding box (thu nho vao de bam sat bien so) ---
            rx1, ry1, rx2, ry2 = _inset_bbox(x1, y1, x2, y2)
            cv2.rectangle(annotated, (rx1, ry1), (rx2, ry2), color, BOX_THICKNESS)

            # --- Label text ---
            conf_pct    = int(round(conf * 100))
            label       = f"{text} ({conf_pct}%)" if text else f"({conf_pct}%)"
            (tw, th), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, FONT_THICKNESS
            )
            pad = 5

            # Nen label nam phia tren bbox (hoac ben trong neu sat mep anh)
            bg_y1 = ry1 - th - pad * 2
            bg_y2 = ry1
            if bg_y1 < 0:
                bg_y1 = ry1
                bg_y2 = ry1 + th + pad * 2

            # Ve hinh chu nhat nen mau (filled)
            cv2.rectangle(annotated,
                          (rx1, bg_y1),
                          (rx1 + tw + pad * 2, bg_y2),
                          color, -1)

            # Ve text mau trang len nen
            cv2.putText(
                annotated, label,
                (rx1 + pad, bg_y2 - pad),
                cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE,
                (255, 255, 255), FONT_THICKNESS, cv2.LINE_AA
            )

        return annotated

    def _dedup_by_confidence(self, detections: list) -> list:
        """
        Gop cac detection co cung plate_text CHINH XAC, chi giu lai confidence cao nhat.
        Tra ve list sap xep theo confidence giam dan.
        """
        best = {}   # plate_text -> detection dict voi confidence cao nhat
        for det in detections:
            text = det["plate_text"]
            if not text:
                continue
            if text not in best or det["confidence"] > best[text]["confidence"]:
                best[text] = det
        return sorted(best.values(), key=lambda d: d["confidence"], reverse=True)

    @staticmethod
    def _normalize_plate(text: str) -> str:
        """Chuan hoa bien so de so sanh: bo khoang trang, dau cham, gach ngang, viet hoa."""
        import re
        return re.sub(r"[^A-Z0-9]", "", text.upper())

    @staticmethod
    def _correct_vn_plate(text: str) -> str:
        """
        Sua loi OCR theo dinh dang bien so Viet Nam:
          [2 so tinh][1-2 chu cai series][3-5 so]

        Quy tac ap dung:
          - Vi tri 1-2 : PHAI LA SO  -> sua chu nham thanh so, kiem tra ma tinh
          - Vi tri 3(-4): PHAI LA CHU -> sua so nham thanh chu
          - Phan con lai : PHAI LA SO  -> sua chu nham thanh so

        Vi du:
          '514 05227' -> '51A 05227'   (4 → A)
          'S1A 05227' -> '51A 05227'   (S → 5)
          '5IA 05227' -> '51A 05227'   (I → 1)
          '30G 63611' -> '30G 63611'   (giu nguyen, da dung)
        """
        import re

        raw = re.sub(r'[^A-Z0-9]', '', text.upper())
        n   = len(raw)
        if n < 5 or n > 10:
            return text   # Qua ngan/dai, khong xu ly

        # --- Buoc 1: 2 ky tu dau phai la so (ma tinh) ---
        d0   = _OCR_CHAR_TO_DIGIT.get(raw[0], raw[0])
        d1   = _OCR_CHAR_TO_DIGIT.get(raw[1], raw[1])
        prov = d0 + d1

        if prov not in _VN_PROVINCE_CODES:
            # Thu toan bo hoán vi (goc + da sua) de tim ma tinh hop le
            valid_set = set()
            for c0 in {raw[0], d0}:
                for c1 in {raw[1], d1}:
                    p = c0 + c1
                    if len(p) == 2 and p.isdigit() and p in _VN_PROVINCE_CODES:
                        valid_set.add(p)
            if not valid_set:
                return text   # Khong sua duoc ma tinh -> giu nguyen
            # Chon ma tinh gan gia tri so nhat voi ket qua OCR
            try:
                ref  = int(d0 + d1) if (d0 + d1).isdigit() else 50
                prov = min(valid_set, key=lambda p: abs(int(p) - ref))
            except Exception:
                prov = next(iter(valid_set))

        rest = raw[2:]

        # --- Buoc 2: Doc 1-2 ky tu series (PHAI LA CHU CAI) ---
        series = ''
        i      = 0

        # Ky tu thu nhat: sua so → chu neu can
        if i < len(rest):
            ch    = rest[i]
            fixed = _OCR_DIGIT_TO_CHAR.get(ch, ch) if ch.isdigit() else ch
            if fixed.isalpha():
                series += fixed
                i += 1

        # Ky tu thu hai: chi doc neu la CHU CAI THUC SU (khong ep so → chu)
        if series and i < len(rest) and rest[i].isalpha():
            series += rest[i]
            i += 1

        if not series:
            return text   # Khong tim duoc series -> giu nguyen

        # --- Buoc 3: Phan so bien – sua chu nham → so ---
        num_fixed = ''.join(_OCR_CHAR_TO_DIGIT.get(c, c) for c in rest[i:])

        return f"{prov}{series} {num_fixed}"

    @staticmethod
    def _calculate_iou(box1, box2):
        """Tinh IoU giua 2 bbox [x1,y1,x2,y2]."""
        xa = max(box1[0], box2[0])
        ya = max(box1[1], box2[1])
        xb = min(box1[2], box2[2])
        yb = min(box1[3], box2[3])
        inter = max(0, xb - xa) * max(0, yb - ya)
        if inter == 0:
            return 0.0
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter
        return inter / union if union > 0 else 0.0

    @staticmethod
    def _box_center(box):
        """Tra ve (cx, cy) cua bbox [x1,y1,x2,y2]."""
        return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)

    @staticmethod
    def _box_max_dim(box):
        """Tra ve max(width, height) cua bbox."""
        return max(box[2] - box[0], box[3] - box[1])

    def _cluster_similar_plates(self, plates: list, threshold: float = 0.82) -> list:
        """
        Gop cac bien so la cung 1 bien vat ly (OCR doc khac nhau moi frame).
        Dung fuzzy matching tren chuoi da chuan hoa.
        Chi giu lai 1 ket qua confidence cao nhat moi nhom.
        """
        import difflib

        sorted_plates = sorted(plates, key=lambda x: x["confidence"], reverse=True)
        clusters = []

        for plate in sorted_plates:
            norm = self._normalize_plate(plate["plate_text"])
            if not norm:
                continue

            merged = False
            for c_norm, _ in clusters:
                # Tieu chi 1: ty le tuong dong >= threshold
                ratio = difflib.SequenceMatcher(None, norm, c_norm).ratio()
                if ratio >= threshold:
                    merged = True
                    break

                short, long = (norm, c_norm) if len(norm) <= len(c_norm) else (c_norm, norm)

                # Tieu chi 2: prefix chinh xac (>= 5 ky tu) va chuoi ngan
                # la sub-read cua chuoi dai (vi du: "29C32" la dau cua "29C32744")
                if len(short) >= 5 and long.startswith(short):
                    merged = True
                    break

            if not merged:
                clusters.append((norm, plate))

        result = [p for _, p in clusters]

        # Bo loc chat luong: loai cac ban ghi qua ngan (< 5 ky tu alphanumeric)
        if len(result) > 1:
            def alen(p):
                return len(self._normalize_plate(p["plate_text"]))
            filtered = [p for p in result if alen(p) >= 5]
            if filtered:
                result = filtered

        return result

    def process_image(self, image_path: str, output_path: str = None) -> dict:
        """
        Xử lý một file ảnh và lưu file kết quả (dùng cho CLI).

        Args:
            image_path: Đường dẫn ảnh đầu vào.
            output_path: Đường dẫn ảnh đầu ra.

        Returns:
            dict: {output_path, detections, total_plates}
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Không tìm thấy ảnh: {image_path}")

        print(f"\n🖼️ Đang xử lý ảnh: {image_path.name}")

        frame = cv2.imread(str(image_path))
        if frame is None:
            raise ValueError(f"Không thể đọc ảnh: {image_path}")

        detections = self.detect_plates(frame)
        print(f"   📍 Phát hiện {len(detections)} biển số")
        for i, det in enumerate(detections):
            print(f"      [{i+1}] {det['plate_text'] or 'N/A'} (conf: {det['confidence']:.2%})")

        annotated = self._draw_results(frame, detections)

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(output_path), annotated)
            print(f"   💾 Ảnh kết quả: {output_path}")

        return {
            "output_path": str(output_path) if output_path else None,
            "detections": detections,
            "total_plates": len(detections),
        }

    def process_image_to_base64(self, image_path: str) -> dict:
        """
        Xử lý một file ảnh và trả về kết quả dạng base64 (dùng cho API web).
        Không lưu file output.

        Args:
            image_path: Đường dẫn ảnh đầu vào.

        Returns:
            dict: {image_base64, image_mime, detections, total_plates}
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Không tìm thấy ảnh: {image_path}")

        print(f"\n🖼️ Đang xử lý ảnh (base64): {image_path.name}")

        frame = cv2.imread(str(image_path))
        if frame is None:
            raise ValueError(f"Không thể đọc ảnh: {image_path}")

        # Detect bien so
        raw_detections = self.detect_plates(frame)

        # Buoc 1: gop chinh xac (cung plate_text)
        deduped = self._dedup_by_confidence(raw_detections)

        # Buoc 2: gop bien so tuong tu (cung bien vat ly, OCR khac nhau)
        detections = self._cluster_similar_plates(deduped)

        print(f"   Phat hien: {len(raw_detections)} bbox -> {len(deduped)} exact -> {len(detections)} physical plates")
        for i, det in enumerate(detections):
            print(f"      [{i+1}] {det['plate_text']} (conf: {det['confidence']:.2%})")

        # Ve ket qua len anh (dung raw_detections de ve tat ca bbox)
        annotated = self._draw_results(frame, raw_detections)

        # Encode sang base64
        success, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 95])
        if not success:
            raise ValueError("Khong the encode anh sang JPEG")

        img_base64 = base64.b64encode(buffer).decode('utf-8')
        print(f"   Encode base64 OK ({len(img_base64) // 1024} KB)")

        return {
            "image_base64": img_base64,
            "image_mime":   "image/jpeg",
            "detections":   detections,          # unique, confidence cao nhat
            "total_plates": len(detections),
        }

    def process_video(self, video_path: str, output_path: str = None) -> dict:
        """
        Xu ly mot file video va tra ve video H.264 tuong thich voi trinh duyet.

        Su dung spatial IoU tracker de nhom cac detection cua cung 1 bien so
        vat ly qua nhieu frame, chi giu lai ket qua OCR co confidence cao nhat
        cho moi bien vat ly.

        Quy trinh:
          1. OpenCV doc frame, detect bien so, track bbox qua cac frame
          2. Moi track giu best_text (confidence cao nhat) -> nhan on dinh
          3. FFmpeg re-encode sang H.264 + faststart (tuong thich browser)

        Args:
            video_path: Duong dan video dau vao.
            output_path: Duong dan video dau ra (H.264 .mp4).

        Returns:
            dict: {output_path, all_plates, total_frames, processed_frames}
        """
        import subprocess
        import shutil as _shutil
        import math

        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Khong tim thay video: {video_path}")

        print(f"\n Video: {video_path.name}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Khong the mo video: {video_path}")

        fps   = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(f"   Resolution: {width}x{height}  FPS: {fps}  Frames: {total_frames}")

        # Duong dan output cuoi cung
        if output_path is None:
            BASE_DIR_local = Path(__file__).resolve().parent.parent
            temp_dir = BASE_DIR_local / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            output_path = temp_dir / f"result_{video_path.stem}.mp4"
        else:
            output_path = Path(output_path)

        # File tam OpenCV (mp4v) – chi dung lam buoc trung gian
        raw_temp = output_path.with_name(output_path.stem + "_raw.mp4")

        # Ghi bang mp4v (OpenCV native)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(raw_temp), fourcc, fps, (width, height))

        # ===== Spatial Tracker =====
        # Moi track: {id, last_bbox, last_seen, best_conf, best_text, hit_count}
        tracks = []              # active tracks dang theo doi
        finished_tracks = []     # tracks da het han (luu ket qua truoc khi xoa)
        next_track_id = 0
        IOU_THRESHOLD     = 0.15    # IoU toi thieu de match
        CENTROID_FACTOR   = 1.5     # fallback: khoang cach tam < factor * max_dim
        MAX_AGE_FRAMES    = fps     # chuyen track sang finished sau N processed-frames

        frame_count     = 0
        processed_count = 0
        process_every_n = max(1, fps // 10)   # ~10 frames/giay

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1

                if frame_count % process_every_n == 0:
                    detections = self.detect_plates(frame)
                    processed_count += 1

                    # --- Match detections vao tracks ---
                    used_tracks = set()
                    for det in detections:
                        bbox = det["bbox"]
                        text = det["plate_text"]
                        conf = det["confidence"]

                        best_tid  = -1
                        best_iou  = 0.0

                        # Tim track co IoU cao nhat
                        for idx, trk in enumerate(tracks):
                            if idx in used_tracks:
                                continue
                            iou = self._calculate_iou(bbox, trk["last_bbox"])
                            if iou > best_iou:
                                best_iou = iou
                                best_tid = idx

                        # Fallback: centroid distance neu IoU qua thap
                        if best_iou < IOU_THRESHOLD:
                            best_tid = -1
                            best_dist = float('inf')
                            cx, cy = self._box_center(bbox)
                            max_d  = self._box_max_dim(bbox)
                            for idx, trk in enumerate(tracks):
                                if idx in used_tracks:
                                    continue
                                tcx, tcy = self._box_center(trk["last_bbox"])
                                dist = math.hypot(cx - tcx, cy - tcy)
                                t_max_d = self._box_max_dim(trk["last_bbox"])
                                limit = CENTROID_FACTOR * max(max_d, t_max_d)
                                if dist < limit and dist < best_dist:
                                    best_dist = dist
                                    best_tid = idx

                        if best_tid >= 0:
                            # Cap nhat track
                            trk = tracks[best_tid]
                            trk["last_bbox"]  = bbox
                            trk["last_seen"]  = processed_count
                            trk["hit_count"] += 1
                            if text and conf > trk["best_conf"]:
                                trk["best_conf"] = conf
                                trk["best_text"] = text
                            used_tracks.add(best_tid)
                        else:
                            # Tao track moi
                            tracks.append({
                                "id":        next_track_id,
                                "last_bbox": bbox,
                                "last_seen": processed_count,
                                "best_conf": conf if text else 0.0,
                                "best_text": text or "",
                                "hit_count": 1,
                            })
                            best_tid = len(tracks) - 1
                            used_tracks.add(best_tid)
                            next_track_id += 1

                        # Gan best_text cua track vao detection hien tai
                        # de hien thi on dinh tren video (khong nhap nhay)
                        trk = tracks[best_tid]
                        if trk["best_text"]:
                            det["plate_text"] = trk["best_text"]
                            det["confidence"]  = trk["best_conf"]

                    # Chuyen cac track het han sang finished_tracks (giu ket qua)
                    still_active = []
                    for t in tracks:
                        if processed_count - t["last_seen"] <= MAX_AGE_FRAMES:
                            still_active.append(t)
                        else:
                            if t["best_text"]:
                                finished_tracks.append(t)
                    tracks = still_active

                    # Ve frame: chi hien best detection (best_only=True)
                    annotated = self._draw_results(frame, detections, best_only=True)
                    writer.write(annotated)

                    if frame_count % (fps * 2) == 0:
                        active = sum(1 for t in tracks if t["best_text"])
                        progress = (frame_count / total_frames) * 100 if total_frames > 0 else 0
                        print(f"   {progress:.1f}% ({frame_count}/{total_frames}) - "
                              f"Active tracks: {active}  Total tracks created: {next_track_id}")
                else:
                    writer.write(frame)

        finally:
            cap.release()
            writer.release()

        # --- Thu thap ket qua tu TAT CA tracks (finished + con active) ---
        # Loc: xuat hien >= 3 frame VA confidence >= 60%
        MIN_HITS = 3
        MIN_CONF = 0.60
        all_tracks = finished_tracks + tracks
        raw_list = sorted(
            [{"plate_text": t["best_text"], "confidence": round(t["best_conf"], 4)}
             for t in all_tracks
             if t["best_text"] and t["hit_count"] >= MIN_HITS and t["best_conf"] >= MIN_CONF],
            key=lambda x: x["confidence"],
            reverse=True,
        )

        # Gop text tuong tu (truong hop track bi mat roi tao lai)
        all_plates_list = self._cluster_similar_plates(raw_list)

        print(f"\n   Done! Processed: {processed_count}/{frame_count} frames")
        print(f"   Tracks created: {next_track_id} -> After text-dedup: {len(all_plates_list)}")
        for p in all_plates_list:
            print(f"      {p['plate_text']:30s}  {p['confidence']:.2%}")

        # -------------------------------------------------------
        # Re-encode sang H.264 bang FFmpeg (tuong thich browser)
        # -------------------------------------------------------
        ffmpeg_exe = None
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            print(f"   FFmpeg (imageio): {ffmpeg_exe}")
        except Exception:
            import shutil as _sh2
            ffmpeg_exe = _sh2.which("ffmpeg")
            if ffmpeg_exe:
                print(f"   FFmpeg (system): {ffmpeg_exe}")

        if ffmpeg_exe:
            print(f"   Re-encoding to H.264...")
            cmd = [
                ffmpeg_exe,
                "-y",
                "-i", str(raw_temp),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                "-an",
                str(output_path),
            ]
            result_proc = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=600,
            )
            if result_proc.returncode != 0:
                err = result_proc.stderr.decode("utf-8", errors="replace")
                print(f"   FFmpeg error: {err[-400:]}")
                _shutil.move(str(raw_temp), str(output_path))
            else:
                print(f"   H.264 encode OK -> {output_path}")
                if raw_temp.exists():
                    raw_temp.unlink()
        else:
            print("   [WARN] FFmpeg not found. Using mp4v (may not play in browser).")
            _shutil.move(str(raw_temp), str(output_path))

        print(f"   Output: {output_path}")

        return {
            "output_path":     str(output_path),
            "all_plates":      all_plates_list,   # [{plate_text, confidence}]
            "total_frames":    frame_count,
            "processed_frames": processed_count,
        }



# ========================================
# CLI - Chạy thử nhanh
# ========================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ALPR - Nhận diện biển số xe")
    parser.add_argument("input", help="Đường dẫn file ảnh hoặc video")
    parser.add_argument("--model", default=None, help="Đường dẫn model YOLO (.pt)")
    parser.add_argument("--output", default=None, help="Đường dẫn file kết quả")
    args = parser.parse_args()

    engine = ALPREngine(model_path=args.model)
    input_path = Path(args.input)

    if input_path.suffix.lower() in [".mp4", ".avi", ".mov", ".mkv", ".wmv"]:
        result = engine.process_video(str(input_path), args.output)
    else:
        result = engine.process_image(str(input_path), args.output)

    print(f"\n📋 Kết quả: {result}")

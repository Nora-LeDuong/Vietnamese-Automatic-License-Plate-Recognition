"""
ocr_engine.py - Inference wrapper cho CRNN OCR model
-----------------------------------------------------
Thay the EasyOCR trong inference.py
"""

from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch

from ocr_model   import CRNN, CTCDecoder, IMG_H, IMG_W
from ocr_dataset import preprocess_plate

DEFAULT_MODEL = Path(__file__).parent.parent / 'models' / 'ocr_crnn' / 'best.pt'


class PlateOCREngine:
    """
    OCR engine nhe gon cho bien so Viet Nam.
    Fallback sang EasyOCR neu model chua ton tai.
    """

    def __init__(self, model_path: Optional[str] = None,
                 device: Optional[str] = None):
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model  = None
        self._easy  = None           # EasyOCR fallback

        path = Path(model_path) if model_path else DEFAULT_MODEL
        if path.exists():
            self._load_model(path)
        else:
            print(f"[PlateOCREngine] Model chua co tai {path}")
            print(f"[PlateOCREngine] Dung EasyOCR fallback")
            self._init_easyocr()

    # ----------------------------------------------------------
    def _load_model(self, path: Path):
        ckpt = torch.load(path, map_location=self.device, weights_only=False)
        cfg  = ckpt.get('config', {})
        self.model = CRNN(
            hidden=cfg.get('hidden', 256),
            num_layers=cfg.get('num_layers', 2),
        ).to(self.device)
        self.model.load_state_dict(ckpt['model'])
        self.model.eval()
        acc = ckpt.get('acc', 0)
        cer = ckpt.get('cer', 1)
        print(f"[PlateOCREngine] Loaded CRNN: Acc={acc:.3f}  CER={cer:.4f}")

    def _init_easyocr(self):
        import easyocr
        self.model = None
        self._easy = easyocr.Reader(['en'], gpu=False, verbose=False)

    # ----------------------------------------------------------
    @torch.no_grad()
    def read(self, plate_crop: np.ndarray) -> str:
        """
        Doc text tu anh bien so (BGR hoac Grayscale).
        Returns:
            Chuoi ky tu bien so (vi du: "51F 63034")
        """
        if plate_crop is None or plate_crop.size == 0:
            return ''

        if self.model is not None:
            return self._read_crnn(plate_crop)
        else:
            return self._read_easyocr(plate_crop)

    def _read_crnn(self, img: np.ndarray) -> str:
        tensor = preprocess_plate(img)                    # [1, H, W]
        tensor = tensor.unsqueeze(0).to(self.device)      # [1, 1, H, W]

        logits  = self.model(tensor)                      # [T, 1, C]
        decoded = CTCDecoder.decode(logits.cpu())         # list[str]
        raw     = decoded[0] if decoded else ''

        # Format: 2 so + chu + so bien -> them space truoc so bien
        import re
        m = re.match(r'^(\d{2})([A-Z]{1,2})(\d+)$', raw)
        if m:
            return f"{m.group(1)}{m.group(2)} {m.group(3)}"
        return raw

    def _read_easyocr(self, img: np.ndarray) -> str:
        """EasyOCR fallback (giu nguyen logic cu)."""
        import re
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        h, w = gray.shape
        if w < 320:
            gray = cv2.resize(gray, None, fx=320/w, fy=320/w,
                              interpolation=cv2.INTER_CUBIC)
        clahe    = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(4, 4))
        enhanced = clahe.apply(gray)
        blurred  = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=1.2)
        sharp    = cv2.addWeighted(enhanced, 1.8, blurred, -0.8, 0)
        enhanced = np.clip(sharp, 0, 255).astype(np.uint8)

        results = self._easy.readtext(enhanced, detail=0)
        text    = ' '.join(results).upper()
        text    = re.sub(r'[^A-Z0-9 ]', '', text).strip()
        return text

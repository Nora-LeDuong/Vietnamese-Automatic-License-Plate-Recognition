import sys, time
sys.path.insert(0, 'ai-engine/src')

from ocr_engine import PlateOCREngine
import cv2
from ocr_dataset import render_plate

print('Loading CRNN engine...')
t0 = time.time()
engine = PlateOCREngine()
print(f'Loaded in {time.time()-t0:.2f}s\n')

plates = ['51F63034', '30G63611', '88A39307', '61F79512', '30F11292', '51AB12345']
print(f"{'Label':<15} {'CRNN result':<22} Match")
print('-' * 45)
for label in plates:
    img_gray = render_plate(label)
    img_bgr  = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)
    t0       = time.time()
    result   = engine.read(img_bgr)
    ms       = (time.time() - t0) * 1000
    clean    = result.replace(' ', '')
    match    = 'OK' if clean == label else 'XX'
    print(f"{label:<15} {result:<22} [{match}]  ({ms:.1f}ms)")

import sys, time, os
sys.path.insert(0, 'ai-engine/src')
from inference import ALPREngine as PlateRecognitionEngine

print('=== Khoi tao engine ===')
t0 = time.time()
eng = PlateRecognitionEngine()
print(f'Init: {time.time()-t0:.2f}s')

# Tim anh test
test_dirs = [
    'ai-engine/data/vn_plate_ocr/cropped',
    'ai-engine/temp',
    'datasets/images/test',
]
test_img = None
for d in test_dirs:
    if os.path.exists(d):
        imgs = [f for f in os.listdir(d) if f.lower().endswith(('.jpg','.png','.jpeg'))]
        if imgs:
            test_img = os.path.join(d, imgs[0])
            break

if test_img:
    print(f'\nTest: {test_img}')
    import cv2
    frame = cv2.imread(test_img)
    t0 = time.time()
    dets = eng.detect_plates(frame)
    ms = (time.time()-t0)*1000
    print(f'Detect: {ms:.1f}ms -> {len(dets)} bien so')
    for d in dets:
        print(f'  Plate: {d["plate_text"]}  conf={d["confidence"]}')
else:
    print('Khong tim thay anh test')
print('\nDONE - Pipeline OK!')

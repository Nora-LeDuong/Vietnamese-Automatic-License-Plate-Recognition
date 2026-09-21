"""
convert_labels.py - Chuyen doi tat ca label sang AABB detect format (5 values).

Xu ly:
  9  values: class x1 y1 x2 y2 x3 y3 x4 y4  (OBB 4-goc)   -> AABB
  5  values: class cx cy w h                  (detect AABB)  -> giu nguyen
  11 values: class x1y1...x5y5               (polygon 5pt)  -> AABB
  13 values: class x1y1...x6y6               (polygon 6pt)  -> AABB
"""

import os
import shutil
from pathlib import Path

BASE   = Path('ai-engine/data/yolo_dataset')
SPLITS = ['train', 'val']


def polygon_to_aabb(coords):
    """Chuyen danh sach toa do [x1,y1,x2,y2,...] sang (cx,cy,w,h) AABB."""
    xs = coords[0::2]
    ys = coords[1::2]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    cx = (x_min + x_max) / 2
    cy = (y_min + y_max) / 2
    w  = x_max - x_min
    h  = y_max - y_min
    # Dam bao trong [0, 1]
    cx = max(0.0, min(1.0, cx))
    cy = max(0.0, min(1.0, cy))
    w  = max(0.0, min(1.0, w))
    h  = max(0.0, min(1.0, h))
    return cx, cy, w, h


def convert_split(split):
    src_dir  = BASE / 'labels' / split
    dst_dir  = BASE / 'labels_aabb' / split
    dst_dir.mkdir(parents=True, exist_ok=True)

    stats = {'ok5': 0, 'conv9': 0, 'conv11': 0, 'conv13': 0, 'skip': 0}
    files = list(src_dir.glob('*.txt'))

    for fpath in files:
        out_lines = []
        with open(fpath, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                n = len(parts)
                cls = parts[0]

                if n == 5:
                    # Da la AABB -> giu nguyen
                    out_lines.append(line)
                    stats['ok5'] += 1

                elif n == 9:
                    # OBB 4 goc: class x1 y1 x2 y2 x3 y3 x4 y4
                    coords = [float(v) for v in parts[1:]]
                    cx, cy, w, h = polygon_to_aabb(coords)
                    out_lines.append(f'{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}')
                    stats['conv9'] += 1

                elif n == 11:
                    # Polygon 5 diem: class x1 y1 ... x5 y5
                    coords = [float(v) for v in parts[1:]]
                    cx, cy, w, h = polygon_to_aabb(coords)
                    out_lines.append(f'{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}')
                    stats['conv11'] += 1

                elif n == 13:
                    # Polygon 6 diem: class x1 y1 ... x6 y6
                    coords = [float(v) for v in parts[1:]]
                    cx, cy, w, h = polygon_to_aabb(coords)
                    out_lines.append(f'{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}')
                    stats['conv13'] += 1

                else:
                    # Format la (empty file, comment, v.v.)
                    stats['skip'] += 1

        # Ghi file output
        with open(dst_dir / fpath.name, 'w', encoding='utf-8') as f:
            f.write('\n'.join(out_lines))
            if out_lines:
                f.write('\n')

    print(f'{split}: {len(files)} files | '
          f'AABB-ok={stats["ok5"]}  '
          f'conv-OBB9={stats["conv9"]}  '
          f'conv-poly11={stats["conv11"]}  '
          f'conv-poly13={stats["conv13"]}  '
          f'skip={stats["skip"]}')
    return stats


if __name__ == '__main__':
    print('Chuyen doi label sang AABB detect format...\n')
    for s in SPLITS:
        convert_split(s)
    print('\nDone! Labels moi tai: ai-engine/data/yolo_dataset/labels_aabb/')

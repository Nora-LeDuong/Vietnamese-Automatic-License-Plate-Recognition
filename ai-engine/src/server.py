"""
server.py - FastAPI Server v3.0

Endpoints:
- POST /predict/image  -> JSON { image_base64, detections, plates, ... }
- POST /predict/video  -> JSON { video_url, all_plates, ... }
- GET  /video/{token}  -> Stream H.264 MP4 voi HTTP Range support (cho browser)
- GET  /health         -> { status, model_loaded }
"""

import os
import sys
import json
import uuid
import shutil
import time
import threading
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from inference import ALPREngine

# ============================================================
# CONFIG
# ============================================================
BASE_DIR   = Path(__file__).resolve().parent.parent
TEMP_DIR   = BASE_DIR / "temp"
OUTPUT_DIR = BASE_DIR / "output"          # video da xu ly (H.264)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ALLOWED_VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".wmv"}
MAX_FILE_SIZE_MB   = 500
VIDEO_TTL_SECONDS  = 3600   # tu dong xoa video sau 1 tieng

# ============================================================
# APP
# ============================================================
app = FastAPI(
    title="ALPR API",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length",
                    "X-Plates", "X-Total-Plates", "X-Total-Frames", "X-Processed-Frames"],
)

_engine = None


def get_engine() -> ALPREngine:
    global _engine
    if _engine is None:
        print("Loading ALPR Engine...")
        _engine = ALPREngine()
        print("Engine ready!")
    return _engine


def save_upload(upload_file: UploadFile, prefix: str = "") -> Path:
    ext = Path(upload_file.filename).suffix.lower()
    path = TEMP_DIR / f"{prefix}{uuid.uuid4().hex[:8]}{ext}"
    with open(path, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)
    return path


def schedule_delete(path: Path, delay: int = VIDEO_TTL_SECONDS):
    """Xoa file sau `delay` giay trong background thread."""
    def _delete():
        time.sleep(delay)
        try:
            path.unlink(missing_ok=True)
            print(f"[cleanup] Deleted {path.name}")
        except Exception:
            pass
    t = threading.Thread(target=_delete, daemon=True)
    t.start()


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": _engine is not None}


@app.post("/predict/image")
async def predict_image(file: UploadFile = File(...)):
    """Nhan dien bien so tu anh. Tra ve JSON voi anh ket qua dang base64."""
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        raise HTTPException(400, f"Dinh dang khong ho tro: {ext}")

    file.file.seek(0, 2)
    if file.file.tell() / 1024 / 1024 > MAX_FILE_SIZE_MB:
        raise HTTPException(400, "File qua lon")
    file.file.seek(0)

    temp = None
    try:
        temp = save_upload(file, "img_")
        result = get_engine().process_image_to_base64(str(temp))
        return JSONResponse({
            "success": True,
            "type": "image",
            "image_base64": result["image_base64"],
            "image_mime":   result["image_mime"],
            "detections":   result["detections"],
            "total_plates": result["total_plates"],
            "plates":       [d["plate_text"] for d in result["detections"] if d["plate_text"]],
        })
    except Exception as e:
        raise HTTPException(500, f"Loi xu ly anh: {e}")
    finally:
        if temp and temp.exists():
            temp.unlink()


@app.post("/predict/video")
async def predict_video(file: UploadFile = File(...)):
    """
    Nhan dien bien so tu video.
    Xu ly xong, luu ket qua H.264 vao OUTPUT_DIR roi tra JSON chua URL de browser play.
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTS:
        raise HTTPException(400, f"Dinh dang khong ho tro: {ext}")

    file.file.seek(0, 2)
    if file.file.tell() / 1024 / 1024 > MAX_FILE_SIZE_MB:
        raise HTTPException(400, "File qua lon")
    file.file.seek(0)

    token      = uuid.uuid4().hex
    temp_input = None
    out_path   = OUTPUT_DIR / f"{token}.mp4"
    try:
        temp_input = save_upload(file, "vid_")
        result     = get_engine().process_video(str(temp_input), str(out_path))

        # Lên lịch xóa sau 1 tiếng
        schedule_delete(out_path)

        return JSONResponse({
            "success":          True,
            "type":             "video",
            "token":            token,
            "video_url":        f"/video/{token}",
            "all_plates":       result["all_plates"],           # [{plate_text, confidence}]
            "total_plates":     len(result["all_plates"]),
            "total_frames":     result["total_frames"],
            "processed_frames": result["processed_frames"],
        })

    except Exception as e:
        if out_path.exists():
            out_path.unlink()
        raise HTTPException(500, f"Loi xu ly video: {e}")
    finally:
        if temp_input and temp_input.exists():
            temp_input.unlink()


@app.get("/video/{token}")
async def serve_video(token: str, request: Request):
    """
    Phu vu video ket qua voi HTTP Range support day du.
    Trinh duyet can Range requests de play/seek video HTML5.
    """
    # Bao ve path traversal
    if not token.replace("-", "").isalnum():
        raise HTTPException(400, "Token khong hop le")

    path = OUTPUT_DIR / f"{token}.mp4"
    if not path.exists():
        raise HTTPException(404, "Video khong ton tai hoac da het han")

    file_size = path.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        # Parse "bytes=start-end"
        try:
            byte_range = range_header.replace("bytes=", "").strip()
            parts      = byte_range.split("-")
            start      = int(parts[0])
            end        = int(parts[1]) if parts[1] else file_size - 1
        except Exception:
            raise HTTPException(416, "Range header khong hop le")

        end    = min(end, file_size - 1)
        length = end - start + 1

        def iterfile():
            with open(path, "rb") as f:
                f.seek(start)
                remaining = length
                chunk_size = 1024 * 256  # 256 KB
                while remaining > 0:
                    chunk = f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    yield chunk
                    remaining -= len(chunk)

        return StreamingResponse(
            iterfile(),
            status_code=206,
            media_type="video/mp4",
            headers={
                "Content-Range":  f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges":  "bytes",
                "Content-Length": str(length),
                "Cache-Control":  "no-cache",
            },
        )
    else:
        # Full file
        def iterfile_full():
            with open(path, "rb") as f:
                while chunk := f.read(1024 * 256):
                    yield chunk

        return StreamingResponse(
            iterfile_full(),
            status_code=200,
            media_type="video/mp4",
            headers={
                "Accept-Ranges":  "bytes",
                "Content-Length": str(file_size),
                "Cache-Control":  "no-cache",
            },
        )


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 55)
    print("  ALPR API Server v3.0")
    print("  http://127.0.0.1:8000")
    print("  /predict/image  -> base64 JSON")
    print("  /predict/video  -> JSON + /video/{token}")
    print("  /video/{token}  -> H.264 MP4 with Range")
    print("=" * 55)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)

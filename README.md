# Vietnamese Automatic License Plate Recognition (ALPR)

Hệ thống nhận diện biển số xe Việt Nam tự động hai giai đoạn (Two-stage ALPR) sử dụng **YOLOv8** để phát hiện vị trí biển số và mạng nơ-ron **CRNN (CNN + RNN + CTC Loss)** tự huấn luyện để nhận diện ký tự biển số. Dự án tích hợp giao diện Web thân thiện viết bằng **Laravel** và Backend AI viết bằng **FastAPI (Python)**.

---

## 🏗️ Kiến trúc Hệ thống

Hệ thống hoạt động theo mô hình Pipeline khép kín:
1. **Giai đoạn 1 (Detection)**: Mô hình **YOLOv8n** phát hiện và định vị tọa độ biển số từ ảnh/video gốc, sau đó cắt vùng ảnh biển số (Crop).
2. **Giai đoạn 2 (OCR)**: Ảnh biển số đã cắt được tiền xử lý và đưa vào mô hình **CRNN** để đọc toàn bộ ký tự chữ và số.
3. **Bộ sửa lỗi tiếng Việt (VN-Fix)**: Chuỗi kết quả OCR được chuẩn hóa và sửa lỗi nhầm lẫn phổ biến (ví dụ: `8` thành `B` trong vùng chữ, hoặc `O` thành `0` trong vùng số) dựa trên quy chuẩn định dạng biển số xe Việt Nam.

```text
[Ảnh/Video gốc] ──> (YOLOv8n Detect) ──> [Ảnh biển số Crop] ──> (CRNN OCR) ──> [Định dạng VN-Fix] ──> [Kết quả dạng Văn bản]
```

---

## 📂 Cấu trúc Thư mục Dự án

```text
├── ai-engine/               # Backend xử lý AI (Python FastAPI)
│   ├── models/              # Chứa các file trọng số mô hình tốt nhất (.pt)
│   │   ├── license_plate_det/weights/best.pt  # Model YOLOv8n tốt nhất
│   │   └── ocr_crnn/best.pt                   # Model CRNN OCR tốt nhất
│   ├── src/                 # Mã nguồn Python xử lý chính
│   │   ├── server.py        # FastAPI Server API cung cấp kết quả
│   │   ├── inference.py     # Pipeline nhận diện kết hợp YOLOv8 + CRNN
│   │   ├── ocr_engine.py    # Bộ giải mã nhận diện chữ (CRNN OCR Engine)
│   │   ├── train.py         # Huấn luyện YOLOv8 phát hiện biển số
│   │   └── train_ocr.py     # Huấn luyện CRNN nhận diện ký tự biển số
│   ├── temp/                # Thư mục chứa các tệp tin tạm thời khi chạy gỡ lỗi
│   └── requirements.txt     # Các thư viện Python cần thiết
│
├── laravel-app/             # Giao diện Web hiển thị kết quả (PHP Laravel 11)
│   ├── app/Http/Controllers/ALPRController.php # Controller điều hướng gọi API AI Engine
│   ├── resources/views/     # Giao diện Blade (Upload, hiển thị ảnh/video kết quả)
│   └── routes/web.php       # Định tuyến Laravel
│
├── start-ai-engine.bat      # File chạy nhanh API AI Engine Backend (Windows)
├── start-laravel.bat        # File chạy nhanh Laravel Frontend Web (Windows)
└── README.md                # Hướng dẫn sử dụng dự án
```

---

## 🚀 Hướng dẫn Cài đặt & Chạy ứng dụng

### 1. Chuẩn bị Môi trường
* Máy tính đã cài đặt: **Python 3.10+**, **PHP 8.2+**, **Composer**, và **Node.js (kèm NPM)**.

---

### 2. Cài đặt AI Backend (FastAPI)
1. Di chuyển vào thư mục `ai-engine`:
   ```bash
   cd ai-engine
   ```
2. Tạo môi trường ảo Python và kích hoạt:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```
3. Cài đặt các thư viện cần thiết:
   ```bash
   pip install -r requirements.txt
   ```

---

### 3. Cài đặt Frontend Web (Laravel)
1. Di chuyển vào thư mục `laravel-app`:
   ```bash
   cd ../laravel-app
   ```
2. Cài đặt các thư viện PHP qua Composer:
   ```bash
   composer install
   ```
3. Tạo file cấu hình môi trường `.env`:
   ```bash
   copy .env.example .env
   ```
4. Tạo khóa ứng dụng (App Key) và cấu hình link storage:
   ```bash
   php artisan key:generate
   php artisan storage:link
   ```
5. Cài đặt các thư viện Javascript và build asset:
   ```bash
   npm install
   npm run build
   ```

---

### 4. Khởi động nhanh ứng dụng trên Windows
Tại thư mục gốc của dự án, bạn chỉ cần chạy hai file `.bat` song song:
1. Nhấp đúp chuột vào file **`start-ai-engine.bat`** để khởi chạy API AI Engine (chạy tại cổng `http://127.0.0.1:8000`).
2. Nhấp đúp chuột vào file **`start-laravel.bat`** để khởi chạy Web Laravel (chạy tại cổng `http://127.0.0.1:8000` hoặc cổng chỉ định trên cmd).
3. Mở trình duyệt web và truy cập địa chỉ hiển thị của Laravel để bắt đầu sử dụng giao diện nhận diện biển số xe (tải ảnh/video lên trực tiếp).

---

## 💻 Hướng dẫn Nhận diện bằng dòng lệnh (CLI)

Dự án hỗ trợ câu lệnh CLI trong thư mục `ai-engine` để chạy thử nhận diện ảnh/video đơn lẻ:

```bash
# Chạy nhận diện một bức ảnh xe
python src/inference.py path/to/car.jpg --output temp/result.jpg

# Chạy nhận diện một video xe chạy
python src/inference.py path/to/traffic.mp4 --output temp/result.mp4
```

---

## 📊 Thông số Kết quả Huấn luyện Hiện tại
* **YOLOv8n (Phát hiện biển số)**: Đạt tỉ lệ phát hiện (DR) **~98%** trên tập ảnh thử nghiệm.
* **CRNN OCR (Đọc chữ biển số)**:
  * **Độ chính xác (Acc)**: **91.62%** (đọc đúng hoàn hảo toàn bộ biển số).
  * **Tỉ lệ lỗi ký tự (CER)**: **3.64%** (sai lệch trung bình cực thấp).

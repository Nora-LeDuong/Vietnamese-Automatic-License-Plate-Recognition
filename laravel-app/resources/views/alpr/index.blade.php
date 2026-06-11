@extends('layouts.app')

@section('title', 'ALPR - Tải lên Ảnh / Video')

@section('content')
    {{-- Hero Section --}}
    <section class="hero">
        <div class="hero-badge">
            <i class="fas fa-microchip"></i>
            Powered by YOLOv8 & EasyOCR
        </div>
        <h1>
            Nhận diện <span class="gradient-text">Biển số Xe</span><br>
            bằng Trí tuệ Nhân tạo
        </h1>
        <p>
            Tải lên hình ảnh hoặc video chứa phương tiện giao thông.
            Hệ thống AI sẽ tự động phát hiện và đọc biển số xe trong vài giây.
        </p>
    </section>

    {{-- Upload Card --}}
    <div class="upload-card">
        {{-- Error Messages --}}
        @if ($errors->any())
            <div class="alert-error">
                <i class="fas fa-exclamation-circle"></i>
                <div>
                    @foreach ($errors->all() as $error)
                        <p>{{ $error }}</p>
                    @endforeach
                </div>
            </div>
        @endif

        <form action="{{ route('alpr.upload') }}" method="POST" enctype="multipart/form-data" id="uploadForm">
            @csrf

            {{-- Dropzone --}}
            <div class="dropzone" id="dropzone">
                <div class="dropzone-icon">
                    <i class="fas fa-cloud-upload-alt"></i>
                </div>
                <div class="dropzone-title">
                    Kéo thả file vào đây hoặc <span style="color: var(--accent-primary); cursor: pointer;">Chọn file</span>
                </div>
                <div class="dropzone-subtitle">
                    Hỗ trợ hình ảnh và video — Dung lượng tối đa 200MB
                </div>
                <div class="dropzone-formats">
                    <span class="format-tag">JPG</span>
                    <span class="format-tag">PNG</span>
                    <span class="format-tag">BMP</span>
                    <span class="format-tag">WEBP</span>
                    <span class="format-tag">MP4</span>
                    <span class="format-tag">AVI</span>
                    <span class="format-tag">MOV</span>
                    <span class="format-tag">MKV</span>
                </div>
                <input type="file" name="file" id="fileInput" accept=".jpg,.jpeg,.png,.bmp,.webp,.mp4,.avi,.mov,.mkv,.wmv" hidden>
            </div>

            {{-- File Preview --}}
            <div class="file-preview" id="filePreview">
                <div class="file-preview-icon" id="filePreviewIcon">
                    <i class="fas fa-image"></i>
                </div>
                <div class="file-preview-info">
                    <div class="file-preview-name" id="fileName">—</div>
                    <div class="file-preview-size" id="fileSize">—</div>
                </div>
                <button type="button" class="file-preview-remove" id="fileRemoveBtn" title="Xóa file">
                    <i class="fas fa-times"></i>
                </button>
            </div>

            {{-- Submit Button --}}
            <div class="submit-section">
                <button type="submit" class="btn-submit" id="submitBtn" disabled>
                    <i class="fas fa-bolt btn-icon"></i>
                    <span class="btn-text">Bắt đầu Nhận diện</span>
                    <div class="spinner"></div>
                </button>
            </div>
        </form>
    </div>
@endsection

@push('scripts')
<script>
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const filePreview = document.getElementById('filePreview');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const filePreviewIcon = document.getElementById('filePreviewIcon');
    const fileRemoveBtn = document.getElementById('fileRemoveBtn');
    const submitBtn = document.getElementById('submitBtn');
    const uploadForm = document.getElementById('uploadForm');
    const loadingOverlay = document.getElementById('loadingOverlay');

    // Click dropzone → open file dialog
    dropzone.addEventListener('click', () => fileInput.click());

    // Drag & Drop
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('drag-over');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('drag-over');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    // File input change
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleFileSelect(fileInput.files[0]);
        }
    });

    // Handle file selection
    function handleFileSelect(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        const imageExts = ['jpg', 'jpeg', 'png', 'bmp', 'webp'];
        const videoExts = ['mp4', 'avi', 'mov', 'mkv', 'wmv'];

        // Update preview icon
        if (imageExts.includes(ext)) {
            filePreviewIcon.innerHTML = '<i class="fas fa-image"></i>';
        } else if (videoExts.includes(ext)) {
            filePreviewIcon.innerHTML = '<i class="fas fa-video"></i>';
        } else {
            filePreviewIcon.innerHTML = '<i class="fas fa-file"></i>';
        }

        // Format file size
        const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
        const sizeStr = sizeMB >= 1 ? `${sizeMB} MB` : `${(file.size / 1024).toFixed(1)} KB`;

        fileName.textContent = file.name;
        fileSize.textContent = sizeStr;
        filePreview.classList.add('active');
        submitBtn.disabled = false;
    }

    // Remove file
    fileRemoveBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.value = '';
        filePreview.classList.remove('active');
        submitBtn.disabled = true;
    });

    // Form submit → show loading
    uploadForm.addEventListener('submit', (e) => {
        if (!fileInput.files.length) {
            e.preventDefault();
            return;
        }
        submitBtn.classList.add('loading');
        submitBtn.disabled = true;
        loadingOverlay.classList.add('active');
    });
</script>
@endpush

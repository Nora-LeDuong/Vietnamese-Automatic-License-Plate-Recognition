<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Ứng dụng AI nhận diện biển số phương tiện giao thông - ALPR System">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>@yield('title', 'ALPR - Nhận diện Biển số Xe')</title>

    {{-- Google Fonts --}}
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">

    {{-- Font Awesome Icons --}}
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">

    <style>
        /* ========================================
           CSS RESET & DESIGN SYSTEM
           ======================================== */
        *, *::before, *::after {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            /* Color Palette - Deep Tech / AI Aesthetic */
            --bg-primary: #0a0e1a;
            --bg-secondary: #111827;
            --bg-card: rgba(17, 24, 39, 0.8);
            --bg-card-hover: rgba(31, 41, 55, 0.9);
            --bg-glass: rgba(255, 255, 255, 0.03);

            --accent-primary: #6366f1;     /* Indigo */
            --accent-secondary: #8b5cf6;   /* Violet */
            --accent-tertiary: #06b6d4;    /* Cyan */
            --accent-success: #10b981;     /* Emerald */
            --accent-warning: #f59e0b;     /* Amber */
            --accent-danger: #ef4444;      /* Red */

            --text-primary: #f9fafb;
            --text-secondary: #9ca3af;
            --text-muted: #6b7280;

            --border-color: rgba(75, 85, 99, 0.4);
            --border-glow: rgba(99, 102, 241, 0.3);

            /* Gradients */
            --gradient-primary: linear-gradient(135deg, #6366f1, #8b5cf6, #06b6d4);
            --gradient-bg: linear-gradient(180deg, #0a0e1a 0%, #111827 50%, #0f172a 100%);
            --gradient-card: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.05));

            /* Shadows */
            --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
            --shadow-glow: 0 0 20px rgba(99, 102, 241, 0.15);
            --shadow-glow-lg: 0 0 40px rgba(99, 102, 241, 0.2);

            /* Spacing & Sizing */
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
            --radius-xl: 24px;

            --transition-fast: 0.15s ease;
            --transition-base: 0.3s ease;
            --transition-slow: 0.5s ease;
        }

        html {
            scroll-behavior: smooth;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--gradient-bg);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
            overflow-x: hidden;
            position: relative;
        }

        /* Background animated particles */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background:
                radial-gradient(circle at 20% 20%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(6, 182, 212, 0.06) 0%, transparent 50%),
                radial-gradient(circle at 50% 50%, rgba(139, 92, 246, 0.04) 0%, transparent 60%);
            pointer-events: none;
            z-index: 0;
        }

        /* ========================================
           LAYOUT
           ======================================== */
        .app-wrapper {
            position: relative;
            z-index: 1;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* HEADER / NAVBAR */
        .navbar {
            padding: 1rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(10, 14, 26, 0.85);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .navbar-brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            text-decoration: none;
            color: var(--text-primary);
        }

        .navbar-logo {
            width: 42px;
            height: 42px;
            background: var(--gradient-primary);
            border-radius: var(--radius-md);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            color: white;
            box-shadow: var(--shadow-glow);
        }

        .navbar-title {
            font-size: 1.25rem;
            font-weight: 700;
            letter-spacing: -0.02em;
        }

        .navbar-title span {
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .navbar-status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.8rem;
            color: var(--text-muted);
            padding: 0.4rem 0.8rem;
            border: 1px solid var(--border-color);
            border-radius: 999px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent-danger);
            animation: pulse 2s infinite;
        }

        .status-dot.online {
            background: var(--accent-success);
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        /* MAIN CONTENT */
        .main-content {
            flex: 1;
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
            width: 100%;
        }

        /* ========================================
           COMPONENTS
           ======================================== */

        /* Hero Section */
        .hero {
            text-align: center;
            padding: 3rem 0 2rem;
        }

        .hero-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.4rem 1rem;
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 999px;
            font-size: 0.8rem;
            color: var(--accent-primary);
            margin-bottom: 1.5rem;
            font-weight: 500;
        }

        .hero h1 {
            font-size: 2.8rem;
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: 1rem;
            letter-spacing: -0.03em;
        }

        .hero h1 .gradient-text {
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .hero p {
            font-size: 1.1rem;
            color: var(--text-secondary);
            max-width: 600px;
            margin: 0 auto;
        }

        /* Upload Card */
        .upload-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-xl);
            padding: 2.5rem;
            margin-top: 2rem;
            backdrop-filter: blur(10px);
            transition: var(--transition-base);
            box-shadow: var(--shadow-lg);
        }

        .upload-card:hover {
            box-shadow: var(--shadow-glow-lg);
            border-color: var(--border-glow);
        }

        /* Dropzone */
        .dropzone {
            border: 2px dashed var(--border-color);
            border-radius: var(--radius-lg);
            padding: 3rem 2rem;
            text-align: center;
            cursor: pointer;
            transition: var(--transition-base);
            background: var(--bg-glass);
            position: relative;
            overflow: hidden;
        }

        .dropzone::before {
            content: '';
            position: absolute;
            inset: 0;
            background: var(--gradient-primary);
            opacity: 0;
            transition: var(--transition-base);
        }

        .dropzone:hover,
        .dropzone.drag-over {
            border-color: var(--accent-primary);
            background: rgba(99, 102, 241, 0.05);
        }

        .dropzone:hover::before,
        .dropzone.drag-over::before {
            opacity: 0.03;
        }

        .dropzone-icon {
            width: 72px;
            height: 72px;
            margin: 0 auto 1.5rem;
            background: rgba(99, 102, 241, 0.1);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.8rem;
            color: var(--accent-primary);
            transition: var(--transition-base);
        }

        .dropzone:hover .dropzone-icon {
            transform: translateY(-4px);
            background: rgba(99, 102, 241, 0.15);
        }

        .dropzone-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            position: relative;
        }

        .dropzone-subtitle {
            font-size: 0.85rem;
            color: var(--text-muted);
            position: relative;
        }

        .dropzone-formats {
            display: flex;
            justify-content: center;
            gap: 0.5rem;
            margin-top: 1.25rem;
            flex-wrap: wrap;
            position: relative;
        }

        .format-tag {
            padding: 0.25rem 0.6rem;
            background: rgba(99, 102, 241, 0.08);
            border: 1px solid rgba(99, 102, 241, 0.15);
            border-radius: 6px;
            font-size: 0.7rem;
            color: var(--text-secondary);
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* File Preview */
        .file-preview {
            display: none;
            align-items: center;
            gap: 1rem;
            padding: 1rem 1.25rem;
            background: rgba(99, 102, 241, 0.06);
            border: 1px solid rgba(99, 102, 241, 0.15);
            border-radius: var(--radius-md);
            margin-top: 1.5rem;
        }

        .file-preview.active {
            display: flex;
        }

        .file-preview-icon {
            width: 48px;
            height: 48px;
            background: var(--gradient-primary);
            border-radius: var(--radius-sm);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.2rem;
            flex-shrink: 0;
        }

        .file-preview-info {
            flex: 1;
            min-width: 0;
        }

        .file-preview-name {
            font-weight: 600;
            font-size: 0.9rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .file-preview-size {
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .file-preview-remove {
            background: none;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            padding: 0.5rem;
            border-radius: 8px;
            transition: var(--transition-fast);
            font-size: 1rem;
        }

        .file-preview-remove:hover {
            color: var(--accent-danger);
            background: rgba(239, 68, 68, 0.1);
        }

        /* Submit Button */
        .submit-section {
            margin-top: 2rem;
            display: flex;
            justify-content: center;
        }

        .btn-submit {
            display: inline-flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.9rem 2.5rem;
            background: var(--gradient-primary);
            color: white;
            border: none;
            border-radius: var(--radius-md);
            font-size: 1rem;
            font-weight: 600;
            font-family: inherit;
            cursor: pointer;
            transition: var(--transition-base);
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
            position: relative;
            overflow: hidden;
        }

        .btn-submit::before {
            content: '';
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, rgba(255,255,255,0.1), transparent);
            opacity: 0;
            transition: var(--transition-base);
        }

        .btn-submit:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 6px 25px rgba(99, 102, 241, 0.4);
        }

        .btn-submit:hover::before {
            opacity: 1;
        }

        .btn-submit:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        .btn-submit .spinner {
            display: none;
            width: 20px;
            height: 20px;
            border: 2px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        .btn-submit.loading .spinner {
            display: block;
        }

        .btn-submit.loading .btn-text {
            display: none;
        }

        .btn-submit.loading .btn-icon {
            display: none;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Error Alert */
        .alert-error {
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            padding: 1rem 1.25rem;
            background: rgba(239, 68, 68, 0.08);
            border: 1px solid rgba(239, 68, 68, 0.2);
            border-radius: var(--radius-md);
            margin-bottom: 1.5rem;
            font-size: 0.9rem;
            color: #fca5a5;
        }

        .alert-error i {
            color: var(--accent-danger);
            margin-top: 2px;
        }

        /* ========================================
           RESULT PAGE STYLES
           ======================================== */

        .result-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 2rem;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .result-header h2 {
            font-size: 1.5rem;
            font-weight: 700;
        }

        .btn-back {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.6rem 1.2rem;
            background: var(--bg-card);
            color: var(--text-secondary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            font-size: 0.85rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            text-decoration: none;
            transition: var(--transition-base);
        }

        .btn-back:hover {
            border-color: var(--accent-primary);
            color: var(--text-primary);
            background: var(--bg-card-hover);
        }

        /* Stats Row */
        .stats-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 1.25rem;
            text-align: center;
            backdrop-filter: blur(10px);
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 800;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .stat-label {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 500;
        }

        /* Result Grid */
        .result-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        @media (max-width: 768px) {
            .result-grid {
                grid-template-columns: 1fr;
            }
            .hero h1 {
                font-size: 2rem;
            }
        }

        .result-panel {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            overflow: hidden;
            backdrop-filter: blur(10px);
        }

        .result-panel-header {
            padding: 1rem 1.25rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-weight: 600;
            font-size: 0.9rem;
        }

        .result-panel-header i {
            color: var(--accent-primary);
        }

        .result-panel-body {
            padding: 1rem;
        }

        .result-panel-body img,
        .result-panel-body video {
            width: 100%;
            border-radius: var(--radius-sm);
            display: block;
        }

        /* Plate List */
        .plate-list {
            list-style: none;
            padding: 0;
        }

        .plate-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border-color);
            transition: var(--transition-fast);
        }

        .plate-item:last-child {
            border-bottom: none;
        }

        .plate-item:hover {
            background: rgba(99, 102, 241, 0.05);
        }

        .plate-number {
            font-family: 'Courier New', monospace;
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--accent-tertiary);
            background: rgba(6, 182, 212, 0.08);
            padding: 0.3rem 0.8rem;
            border-radius: 6px;
            border: 1px solid rgba(6, 182, 212, 0.15);
            letter-spacing: 0.1em;
        }

        .plate-confidence {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-left: auto;
        }

        .no-plates {
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
        }

        .no-plates i {
            font-size: 2rem;
            margin-bottom: 0.5rem;
            display: block;
        }

        /* FOOTER */
        .footer {
            padding: 1.5rem 2rem;
            text-align: center;
            font-size: 0.8rem;
            color: var(--text-muted);
            border-top: 1px solid var(--border-color);
        }

        .footer a {
            color: var(--accent-primary);
            text-decoration: none;
        }

        /* ========================================
           LOADING OVERLAY
           ======================================== */
        .loading-overlay {
            display: none;
            position: fixed;
            inset: 0;
            z-index: 1000;
            background: rgba(10, 14, 26, 0.9);
            backdrop-filter: blur(8px);
            align-items: center;
            justify-content: center;
            flex-direction: column;
            gap: 1.5rem;
        }

        .loading-overlay.active {
            display: flex;
        }

        .loading-spinner-ring {
            width: 64px;
            height: 64px;
            border: 3px solid var(--border-color);
            border-top-color: var(--accent-primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        .loading-text {
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--text-secondary);
        }

        .loading-subtext {
            font-size: 0.85rem;
            color: var(--text-muted);
        }
    </style>

    @stack('styles')
</head>
<body>
    <div class="app-wrapper">
        {{-- NAVBAR --}}
        <nav class="navbar">
            <a href="{{ route('alpr.index') }}" class="navbar-brand">
                <div class="navbar-logo">
                    <i class="fas fa-car"></i>
                </div>
                <div class="navbar-title">
                    <span>ALPR</span> System
                </div>
            </a>
            <div class="navbar-status" id="engineStatus">
                <div class="status-dot" id="statusDot"></div>
                <span id="statusText">Đang kiểm tra...</span>
            </div>
        </nav>

        {{-- MAIN --}}
        <main class="main-content">
            @yield('content')
        </main>

        {{-- FOOTER --}}
        <footer class="footer">
            <p>ALPR System &copy; {{ date('Y') }} — Powered by <a href="#">YOLOv8</a> + <a href="#">EasyOCR</a> + <a href="#">Laravel</a></p>
        </footer>
    </div>

    {{-- Loading Overlay --}}
    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-spinner-ring"></div>
        <div class="loading-text">Đang xử lý nhận diện biển số...</div>
        <div class="loading-subtext">Quá trình này có thể mất vài giây cho ảnh, hoặc vài phút cho video.</div>
    </div>

    <script>
        // Kiểm tra trạng thái AI Engine
        async function checkEngineStatus() {
            const dot = document.getElementById('statusDot');
            const text = document.getElementById('statusText');
            try {
                const response = await fetch('{{ route("alpr.engine-status") }}');
                const data = await response.json();
                if (data.online) {
                    dot.classList.add('online');
                    text.textContent = 'AI Engine Online';
                } else {
                    dot.classList.remove('online');
                    text.textContent = 'AI Engine Offline';
                }
            } catch (e) {
                dot.classList.remove('online');
                text.textContent = 'AI Engine Offline';
            }
        }

        // Kiểm tra khi load trang
        checkEngineStatus();
        // Kiểm tra lại mỗi 30 giây
        setInterval(checkEngineStatus, 30000);
    </script>

    @stack('scripts')
</body>
</html>

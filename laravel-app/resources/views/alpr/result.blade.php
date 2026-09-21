@extends('layouts.app')

@section('title', 'Kết quả Nhận diện Biển số')

@section('content')
    {{-- Header --}}
    <div class="result-header">
        <h2>
            <i class="fas fa-check-circle" style="color: var(--accent-success); margin-right: 0.5rem;"></i>
            Kết quả Nhận diện
        </h2>
        <a href="{{ route('alpr.index') }}" class="btn-back">
            <i class="fas fa-arrow-left"></i> Tải file mới
        </a>
    </div>

    {{-- Stats --}}
    <div class="stats-row">
        <div class="stat-card">
            <div class="stat-value">{{ $totalPlates }}</div>
            <div class="stat-label">Biển số phát hiện</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ $type === 'image' ? 'Ảnh' : 'Video' }}</div>
            <div class="stat-label">Loại file</div>
        </div>
        @if ($type === 'video' && $totalFrames)
            <div class="stat-card">
                <div class="stat-value">{{ $processedFrames }}</div>
                <div class="stat-label">Frames xử lý</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ $totalFrames }}</div>
                <div class="stat-label">Tổng frames</div>
            </div>
        @endif
        <div class="stat-card">
            <div class="stat-value">{{ strtoupper(pathinfo($originalName, PATHINFO_EXTENSION)) }}</div>
            <div class="stat-label">Định dạng</div>
        </div>
    </div>

    {{-- ============================================================ --}}
    {{-- MEDIA RESULT                                                 --}}
    {{-- ============================================================ --}}
    <div class="result-panel media-result-panel">
        <div class="result-panel-header">
            @if ($type === 'image')
                <i class="fas fa-magic"></i> Kết quả nhận diện: {{ $originalName }}
            @else
                <i class="fas fa-play-circle"></i> Video kết quả: {{ $originalName }}
                <span class="video-badge">
                    <i class="fas fa-circle" style="color:#ef4444;font-size:.6rem;"></i>
                    LIVE DETECTION
                </span>
            @endif
        </div>

        <div class="result-panel-body media-body">
            @if ($type === 'image' && $imageBase64)
                {{-- Ảnh: hiển thị base64 inline --}}
                <img
                    src="data:{{ $imageMime }};base64,{{ $imageBase64 }}"
                    alt="Kết quả nhận diện biển số"
                    class="result-media"
                    loading="lazy"
                >

            @elseif ($type === 'video' && $videoSrc)
                {{-- Video: trỏ thẳng tới FastAPI /video/{token} --}}
                <video
                    id="resultVideo"
                    class="result-media"
                    controls
                    autoplay
                    preload="auto"
                    playsinline
                    crossorigin="anonymous"
                >
                    <source src="{{ $videoSrc }}" type="video/mp4">
                    Trình duyệt không hỗ trợ HTML5 video.
                </video>
                <div class="video-hint">
                    <i class="fas fa-info-circle"></i>
                    Video H.264 đã xử lý — bounding box hiển thị vị trí biển số trên từng frame.
                    Video sẽ tự xóa sau 1 giờ.
                </div>

            @else
                <div class="no-plates">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Không tải được kết quả.</p>
                </div>
            @endif
        </div>
    </div>

    {{-- Plates List --}}
    <div class="result-panel" style="margin-bottom:2rem;">
        <div class="result-panel-header">
            <i class="fas fa-list-ol"></i> Danh sách biển số đọc được
            <span style="margin-left:auto;font-size:.75rem;color:var(--text-muted);font-weight:400;">
                Sắp xếp theo confidence giảm dần
            </span>
        </div>
        <div class="result-panel-body" style="padding:0;">
            @php
                // Chuan hoa: moi phan tu co plate_text va confidence
                $normalizedPlates = [];
                if ($type === 'image') {
                    foreach ($detections as $det) {
                        if (!empty($det['plate_text'])) {
                            $normalizedPlates[] = [
                                'plate_text' => $det['plate_text'],
                                'confidence' => $det['confidence'],
                            ];
                        }
                    }
                } else {
                    // Video: $plates da la [{plate_text, confidence}]
                    $normalizedPlates = array_values(array_filter($plates, fn($p) => !empty($p['plate_text'])));
                }
            @endphp

            @if (count($normalizedPlates) > 0)
                <ul class="plate-list">
                    @foreach ($normalizedPlates as $i => $plate)
                        @php $conf = round($plate['confidence'] * 100, 1); @endphp
                        <li class="plate-item">
                            <span style="color:var(--text-muted);font-size:.8rem;width:24px;">{{ $i + 1 }}.</span>
                            <span class="plate-number">{{ $plate['plate_text'] }}</span>
                            <span class="plate-confidence {{ $conf >= 80 ? 'conf-high' : ($conf >= 50 ? 'conf-mid' : 'conf-low') }}">
                                {{ $conf }}%
                            </span>
                        </li>
                    @endforeach
                </ul>
            @else
                <div class="no-plates">
                    <i class="fas fa-search"></i>
                    <p>Không phát hiện biển số nào.</p>
                    <p style="font-size:.8rem;margin-top:.5rem;">Hãy thử với ảnh/video có biển số rõ hơn.</p>
                </div>
            @endif
        </div>
    </div>

    {{-- Detection details (ảnh) --}}
    @if ($type === 'image' && count($detections) > 0)
        <div class="result-panel">
            <div class="result-panel-header">
                <i class="fas fa-info-circle"></i> Chi tiết kỹ thuật
            </div>
            <div class="result-panel-body">
                <table style="width:100%;font-size:.85rem;border-collapse:collapse;">
                    <thead>
                        <tr style="border-bottom:1px solid var(--border-color);">
                            <th style="padding:.5rem;text-align:left;color:var(--text-muted);">#</th>
                            <th style="padding:.5rem;text-align:left;color:var(--text-muted);">Biển số</th>
                            <th style="padding:.5rem;text-align:left;color:var(--text-muted);">Confidence</th>
                            <th style="padding:.5rem;text-align:left;color:var(--text-muted);">Bbox (px)</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach ($detections as $i => $det)
                            <tr style="border-bottom:1px solid var(--border-color);">
                                <td style="padding:.5rem;">{{ $i + 1 }}</td>
                                <td style="padding:.5rem;">
                                    <span class="plate-number" style="font-size:.9rem;">{{ $det['plate_text'] ?: 'N/A' }}</span>
                                </td>
                                <td style="padding:.5rem;">{{ number_format($det['confidence'] * 100, 1) }}%</td>
                                <td style="padding:.5rem;font-family:monospace;color:var(--text-secondary);">
                                    [{{ implode(', ', $det['bbox']) }}]
                                </td>
                            </tr>
                        @endforeach
                    </tbody>
                </table>
            </div>
        </div>
    @endif
@endsection

@push('styles')
<style>
    .media-result-panel { margin-bottom: 2rem; }

    .media-body {
        padding: 0 !important;
        display: flex;
        flex-direction: column;
        align-items: center;
        background: #000;
        border-radius: 0 0 12px 12px;
        overflow: hidden;
        min-height: 200px;
    }

    .result-media {
        width: 100%;
        max-height: 72vh;
        object-fit: contain;
        display: block;
        background: #000;
    }

    video.result-media {
        width: 100%;
    }

    .video-badge {
        margin-left: auto;
        background: rgba(239,68,68,.15);
        border: 1px solid rgba(239,68,68,.4);
        color: #ef4444;
        padding: .2rem .6rem;
        border-radius: 20px;
        font-size: .7rem;
        font-weight: 700;
        letter-spacing: .05em;
        display: flex;
        align-items: center;
        gap: .3rem;
        animation: pulse-badge 2s ease-in-out infinite;
    }

    @keyframes pulse-badge {
        0%, 100% { opacity: 1; }
        50%       { opacity: .6; }
    }

    .video-hint {
        width: 100%;
        background: rgba(99,102,241,.08);
        border-top: 1px solid rgba(99,102,241,.2);
        color: var(--text-secondary);
        font-size: .8rem;
        padding: .7rem 1.2rem;
        display: flex;
        align-items: center;
        gap: .5rem;
    }
    .video-hint i { color: var(--accent-primary); flex-shrink: 0; }

    /* Confidence badge colors */
    .plate-confidence {
        margin-left: auto;
        font-size: .75rem;
        font-weight: 700;
        padding: .15rem .55rem;
        border-radius: 20px;
        letter-spacing: .03em;
    }
    .conf-high {
        background: rgba(34,197,94,.15);
        color: #22c55e;
        border: 1px solid rgba(34,197,94,.3);
    }
    .conf-mid {
        background: rgba(234,179,8,.15);
        color: #eab308;
        border: 1px solid rgba(234,179,8,.3);
    }
    .conf-low {
        background: rgba(239,68,68,.12);
        color: #f87171;
        border: 1px solid rgba(239,68,68,.25);
    }
</style>
@endpush

@push('scripts')
<script>
    // Nếu video lỗi, hiện thông báo
    const vid = document.getElementById('resultVideo');
    if (vid) {
        vid.addEventListener('error', () => {
            vid.insertAdjacentHTML('afterend',
                '<p style="color:#ef4444;padding:1rem;text-align:center">' +
                '<i class="fas fa-exclamation-circle"></i> ' +
                'Không tải được video. Hãy đảm bảo AI Engine đang chạy tại ' +
                '<a href="{{ $videoSrc ?? '#' }}" target="_blank" style="color:#6366f1">{{ $videoSrc ?? '' }}</a>' +
                '</p>'
            );
        });
    }
</script>
@endpush

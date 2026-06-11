<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;

class ALPRController extends Controller
{
    private string $aiEngineUrl;

    public function __construct()
    {
        $this->aiEngineUrl = env('AI_ENGINE_URL', 'http://127.0.0.1:8000');
    }

    /** Trang chủ */
    public function index()
    {
        return view('alpr.index');
    }

    /**
     * Xử lý upload:
     *  - Ảnh  → AI trả base64 → hiển thị inline
     *  - Video → AI xử lý, lưu trên FastAPI server → trả URL → browser play thẳng
     */
    public function upload(Request $request)
    {
        set_time_limit(0);

        $request->validate(['file' => 'required|file|max:512000']);

        $file      = $request->file('file');
        $extension = strtolower($file->getClientOriginalExtension());
        $imageExts = ['jpg', 'jpeg', 'png', 'bmp', 'webp'];
        $videoExts = ['mp4', 'avi', 'mov', 'mkv', 'wmv'];

        if (in_array($extension, $imageExts)) {
            $type = 'image';
        } elseif (in_array($extension, $videoExts)) {
            $type = 'video';
        } else {
            return back()->withErrors(['file' => 'Định dạng không hỗ trợ: ' . $extension]);
        }

        // Kiểm tra AI Engine
        try {
            $health = Http::timeout(5)->get("{$this->aiEngineUrl}/health");
            if (!$health->successful()) {
                return back()->withErrors(['file' => 'AI Engine không phản hồi.']);
            }
        } catch (\Exception $e) {
            return back()->withErrors([
                'file' => "Không kết nối được AI Engine ({$this->aiEngineUrl}). Hãy chạy start-ai-engine.bat."
            ]);
        }

        try {
            $originalName = $file->getClientOriginalName();
            $endpoint     = $type === 'image' ? '/predict/image' : '/predict/video';

            $timeout  = $type === 'video' ? 3600 : 120;   // video: tối đa 1 tiếng
            $response = Http::timeout($timeout)
                ->attach('file', fopen($file->getRealPath(), 'r'), $originalName)
                ->post("{$this->aiEngineUrl}{$endpoint}");

            if (!$response->successful()) {
                $err = $response->json('detail') ?? $response->body();
                return back()->withErrors(['file' => "AI Engine lỗi: {$err}"]);
            }

            $result = $response->json();

            if ($type === 'image') {
                return view('alpr.result', [
                    'type'            => 'image',
                    'originalName'    => $originalName,
                    'imageBase64'     => $result['image_base64'] ?? null,
                    'imageMime'       => $result['image_mime']   ?? 'image/jpeg',
                    'detections'      => $result['detections']   ?? [],
                    'plates'          => $result['plates']        ?? [],
                    'totalPlates'     => $result['total_plates']  ?? 0,
                    'totalFrames'     => null,
                    'processedFrames' => null,
                    'videoSrc'        => null,
                ]);
            } else {
                // URL video trực tiếp từ FastAPI — browser play thẳng, có Range support
                $videoSrc = $this->aiEngineUrl . ($result['video_url'] ?? '');

                // all_plates = [{plate_text, confidence}] sorted by confidence desc
                return view('alpr.result', [
                    'type'            => 'video',
                    'originalName'    => $originalName,
                    'imageBase64'     => null,
                    'imageMime'       => null,
                    'detections'      => [],
                    'plates'          => $result['all_plates']       ?? [],  // [{plate_text, confidence}]
                    'totalPlates'     => $result['total_plates']     ?? 0,
                    'totalFrames'     => $result['total_frames']     ?? 0,
                    'processedFrames' => $result['processed_frames'] ?? 0,
                    'videoSrc'        => $videoSrc,
                ]);
            }

        } catch (\Illuminate\Http\Client\ConnectionException $e) {
            return back()->withErrors(['file' => 'Kết nối AI Engine timeout. Video quá lớn hoặc server bị quá tải.']);
        } catch (\Exception $e) {
            return back()->withErrors(['file' => 'Lỗi: ' . $e->getMessage()]);
        }
    }

    /** Kiểm tra trạng thái AI Engine (AJAX) */
    public function checkEngineStatus()
    {
        try {
            $res = Http::timeout(5)->get("{$this->aiEngineUrl}/health");
            return response()->json(['online' => $res->successful(), 'data' => $res->json()]);
        } catch (\Exception $e) {
            return response()->json(['online' => false, 'error' => $e->getMessage()]);
        }
    }
}

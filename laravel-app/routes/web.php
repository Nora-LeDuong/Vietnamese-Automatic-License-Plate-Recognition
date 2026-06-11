<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\ALPRController;

Route::get('/',          [ALPRController::class, 'index'])->name('alpr.index');
Route::post('/upload',   [ALPRController::class, 'upload'])->name('alpr.upload');
Route::get('/api/engine-status', [ALPRController::class, 'checkEngineStatus'])->name('alpr.engine-status');

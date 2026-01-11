#!/usr/bin/env python3
"""
效能分析腳本
測量各階段處理時間，識別瓶頸
"""

import numpy as np
import cv2
import time
from pathlib import Path
import sys

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from film_models import get_film_profile, PhysicsMode


def create_test_image(size=(2000, 3000)):
    """
    創建標準測試影像
    - 高光：模擬路燈、霓虹燈
    - 中間調：一般場景
    - 陰影：暗部
    """
    img = np.zeros((*size, 3), dtype=np.float32)
    
    # 背景（中間調 0.3）
    img[:, :] = 0.3
    
    # 添加高光區域（10個圓形路燈）
    for i in range(2):
        for j in range(5):
            cx = 300 + j * 500
            cy = 300 + i * 1400
            y, x = np.ogrid[:size[0], :size[1]]
            mask = ((x - cx)**2 + (y - cy)**2) <= 30**2
            img[mask] = [0.95, 0.90, 0.85]  # 暖色高光
    
    return img


def benchmark_function(func, *args, repeat=3, **kwargs):
    """
    測量函數執行時間（重複測試取平均）
    
    Returns:
        (平均時間, 標準差)
    """
    times = []
    for _ in range(repeat):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    
    return np.mean(times), np.std(times), result


def profile_full_pipeline(film_name="Portra400", image_size=(2000, 3000)):
    """
    完整流程效能分析
    
    測量各階段耗時：
    1. 光譜響應計算
    2. Bloom 散射
    3. Halation 背層反射
    4. H&D 曲線
    5. 顆粒噪聲
    6. Tone mapping
    """
    print("=" * 70)
    print(f"  效能分析：{film_name} ({image_size[0]}×{image_size[1]})")
    print("=" * 70)
    
    # 載入膠片配置
    film = get_film_profile(film_name)
    
    # 創建測試影像
    print("\n[1] 創建測試影像...")
    img_rgb = create_test_image(image_size)
    print(f"    影像尺寸: {img_rgb.shape}, 記憶體: {img_rgb.nbytes / 1024**2:.2f} MB")
    
    # 分離 BGR 通道（匹配實際流程）
    b, g, r = cv2.split(img_rgb)
    
    # 2. 光譜響應計算
    print("\n[2] 光譜響應計算...")
    def spectral_response_stage():
        # 簡化版本（實際更複雜）
        response_r = 0.32*r + 0.12*g + 0.06*b
        response_g = 0.09*r + 0.45*g + 0.12*b
        response_b = 0.06*r + 0.12*g + 0.77*b
        return response_r, response_g, response_b
    
    t_spectral, std_spectral, (resp_r, resp_g, resp_b) = benchmark_function(spectral_response_stage)
    print(f"    時間: {t_spectral*1000:.1f} ± {std_spectral*1000:.1f} ms")
    
    # 3. Bloom 散射（如果啟用物理模式）
    print("\n[3] Bloom 散射...")
    if film.physics_mode == PhysicsMode.PHYSICAL:
        # 模擬波長依賴 Bloom
        def bloom_stage():
            # 提取高光
            threshold = 0.7
            highlight_r = np.maximum(resp_r - threshold, 0)
            highlight_g = np.maximum(resp_g - threshold, 0)
            highlight_b = np.maximum(resp_b - threshold, 0)
            
            # 散射（高斯卷積）
            sigma = 20
            ksize = int(sigma * 6) | 1
            bloom_r = cv2.GaussianBlur(highlight_r * 0.08, (ksize, ksize), sigma)
            bloom_g = cv2.GaussianBlur(highlight_g * 0.08, (ksize, ksize), sigma)
            bloom_b = cv2.GaussianBlur(highlight_b * 0.08, (ksize, ksize), sigma)
            
            return bloom_r, bloom_g, bloom_b
        
        t_bloom, std_bloom, _ = benchmark_function(bloom_stage)
        print(f"    時間: {t_bloom*1000:.1f} ± {std_bloom*1000:.1f} ms")
    else:
        t_bloom = 0
        print("    跳過（Artistic 模式）")
    
    # 4. Halation 背層反射（最大瓶頸）
    print("\n[4] Halation 背層反射...")
    if hasattr(film, 'halation_params') and film.halation_params.enabled:
        def halation_stage():
            # 提取高光
            threshold = 0.5
            highlight = np.maximum(resp_r - threshold, 0)
            
            # 三層指數近似（大核卷積）
            sigma_base = 20
            ksize = 201
            
            # 核生成
            kernel_small = cv2.getGaussianKernel(ksize // 3, sigma_base)
            kernel_small = kernel_small @ kernel_small.T
            
            kernel_medium = cv2.getGaussianKernel(ksize, sigma_base * 2)
            kernel_medium = kernel_medium @ kernel_medium.T
            
            kernel_large = cv2.getGaussianKernel(ksize, sigma_base * 4)
            kernel_large = kernel_large @ kernel_large.T
            
            # 三次卷積
            hal_1 = cv2.filter2D(highlight, -1, kernel_small, borderType=cv2.BORDER_REFLECT)
            hal_2 = cv2.filter2D(highlight, -1, kernel_medium, borderType=cv2.BORDER_REFLECT)
            hal_3 = cv2.filter2D(highlight, -1, kernel_large, borderType=cv2.BORDER_REFLECT)
            
            halation = 0.5 * hal_1 + 0.3 * hal_2 + 0.2 * hal_3
            
            return halation
        
        t_halation, std_halation, _ = benchmark_function(halation_stage)
        print(f"    時間: {t_halation*1000:.1f} ± {std_halation*1000:.1f} ms")
        print(f"    ⚠️  最大瓶頸（{t_halation / (t_spectral + t_bloom + t_halation + 0.001) * 100:.1f}%）")
    else:
        t_halation = 0
        print("    跳過（Halation 未啟用）")
    
    # 5. H&D 曲線
    print("\n[5] H&D 曲線...")
    def hd_curve_stage():
        # log 響應 + Toe/Shoulder 處理
        exposure = np.clip(resp_r, 1e-10, None)
        density = 0.65 * np.log10(exposure) + 0.3
        transmittance = 10**(-density)
        return transmittance
    
    t_hd, std_hd, _ = benchmark_function(hd_curve_stage)
    print(f"    時間: {t_hd*1000:.1f} ± {std_hd*1000:.1f} ms")
    
    # 6. 顆粒噪聲
    print("\n[6] 顆粒噪聲...")
    def grain_stage():
        grain = np.random.normal(0, 0.1, resp_r.shape).astype(np.float32)
        grain_blurred = cv2.GaussianBlur(grain, (5, 5), 1.5)
        return grain_blurred
    
    t_grain, std_grain, _ = benchmark_function(grain_stage)
    print(f"    時間: {t_grain*1000:.1f} ± {std_grain*1000:.1f} ms")
    
    # 7. Tone Mapping
    print("\n[7] Tone Mapping...")
    def tone_mapping_stage():
        # S-curve + color grading
        result = resp_r ** (1/2.2)
        result = np.clip(result, 0, 1)
        return result
    
    t_tone, std_tone, _ = benchmark_function(tone_mapping_stage)
    print(f"    時間: {t_tone*1000:.1f} ± {std_tone*1000:.1f} ms")
    
    # 總計
    print("\n" + "=" * 70)
    total_time = t_spectral + t_bloom + t_halation + t_hd + t_grain + t_tone
    print(f"  總處理時間: {total_time*1000:.1f} ms ({total_time:.3f} s)")
    print("=" * 70)
    
    # 瓶頸分析
    print("\n🔍 瓶頸分析:")
    stages = [
        ("光譜響應", t_spectral),
        ("Bloom 散射", t_bloom),
        ("Halation 反射", t_halation),
        ("H&D 曲線", t_hd),
        ("顆粒噪聲", t_grain),
        ("Tone Mapping", t_tone)
    ]
    
    for name, t in sorted(stages, key=lambda x: x[1], reverse=True):
        if total_time > 0:
            percentage = (t / total_time) * 100
            bar = "█" * int(percentage / 2)
            print(f"  {name:20s} {t*1000:6.1f} ms  {percentage:5.1f}%  {bar}")
    
    return total_time


def compare_convolution_methods():
    """
    對比不同卷積方法效能
    """
    print("\n" + "=" * 70)
    print("  卷積方法對比（2000×3000 影像）")
    print("=" * 70)
    
    img = np.random.rand(2000, 3000).astype(np.float32)
    
    kernel_sizes = [51, 101, 201, 301]
    
    print(f"\n{'核大小':>10s}  {'filter2D':>12s}  {'GaussianBlur':>12s}  {'FFT (理論)':>12s}")
    print("-" * 70)
    
    for ksize in kernel_sizes:
        sigma = ksize / 6
        
        # filter2D
        kernel = cv2.getGaussianKernel(ksize, sigma)
        kernel = kernel @ kernel.T
        t_filter, _, _ = benchmark_function(cv2.filter2D, img, -1, kernel, 
                                           borderType=cv2.BORDER_REFLECT)
        
        # GaussianBlur
        t_gaussian, _, _ = benchmark_function(cv2.GaussianBlur, img, (ksize, ksize), sigma)
        
        # FFT 理論（假設 1.7x 加速）
        t_fft_theory = t_filter / 1.7 if ksize > 150 else t_filter
        
        print(f"  {ksize:3d}×{ksize:3d}  {t_filter*1000:9.1f} ms  {t_gaussian*1000:9.1f} ms  {t_fft_theory*1000:9.1f} ms")


def test_fft_available():
    """測試 FFT 卷積是否已實作"""
    print("\n" + "=" * 70)
    print("  FFT 卷積實作檢查")
    print("=" * 70)
    
    try:
        # 動態匯入主程式模組
        import importlib.util
        spec = importlib.util.spec_from_file_location("phos_main", 
                                                       Path(__file__).parent.parent / "Phos_0.3.0.py")
        phos_main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(phos_main)
        
        convolve_fft = phos_main.convolve_fft
        convolve_adaptive = phos_main.convolve_adaptive
        
        print("  ✅ convolve_fft 已實作")
        print("  ✅ convolve_adaptive 已實作")
        
        # 簡單測試
        img = np.random.rand(1000, 1000).astype(np.float32)
        kernel = cv2.getGaussianKernel(201, 33)
        kernel = kernel @ kernel.T
        
        t_fft, _, result_fft = benchmark_function(convolve_fft, img, kernel)
        t_spatial, _, result_spatial = benchmark_function(cv2.filter2D, img, -1, kernel,
                                                          borderType=cv2.BORDER_REFLECT)
        
        # 精度驗證
        diff = np.abs(result_fft - result_spatial)
        max_diff = np.max(diff)
        mean_diff = np.mean(diff)
        
        print(f"\n  效能對比（1000×1000, 201px核）:")
        print(f"    FFT 卷積:   {t_fft*1000:.1f} ms")
        print(f"    空域卷積:   {t_spatial*1000:.1f} ms")
        print(f"    加速比:     {t_spatial / t_fft:.2f}x")
        
        print(f"\n  精度驗證:")
        print(f"    最大誤差:   {max_diff:.6f}")
        print(f"    平均誤差:   {mean_diff:.6f}")
        
        if max_diff < 1e-4:
            print("    ✅ 精度符合要求")
        else:
            print(f"    ⚠️  誤差過大（閾值 1e-4）")
            
    except ImportError as e:
        print(f"  ❌ 無法導入 FFT 函數: {e}")
        print("  💡 建議: 檢查 Phos_0.3.0.py 是否存在 convolve_fft()")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phos 效能分析工具")
    parser.add_argument("--film", default="Portra400_MediumPhysics", 
                       help="膠片配置名稱")
    parser.add_argument("--size", default="2000x3000", 
                       help="測試影像尺寸（格式：WxH）")
    parser.add_argument("--test-fft", action="store_true",
                       help="測試 FFT 卷積實作")
    parser.add_argument("--compare-conv", action="store_true",
                       help="對比卷積方法")
    
    args = parser.parse_args()
    
    # 解析尺寸
    w, h = map(int, args.size.split('x'))
    
    # 執行測試
    if args.test_fft:
        test_fft_available()
    
    if args.compare_conv:
        compare_convolution_methods()
    
    # 完整流程分析
    profile_full_pipeline(args.film, (h, w))
    
    print("\n" + "=" * 70)
    print("  分析完成")
    print("=" * 70)

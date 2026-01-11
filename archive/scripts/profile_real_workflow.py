#!/usr/bin/env python3
"""
真實工作流程效能測試
直接呼叫 Phos_0.3.0.py 的實際函數，測量端到端效能
"""

import sys
import time
import numpy as np
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

# 動態匯入 Phos 主程式
import importlib.util
spec = importlib.util.spec_from_file_location("phos_main", 
                                               Path(__file__).parent.parent / "Phos_0.3.0.py")
if spec and spec.loader:
    phos_main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(phos_main)
else:
    raise ImportError("無法載入 Phos_0.3.0.py")

from film_models import get_film_profile


def create_realistic_test_image(size=(2000, 3000)):
    """
    創建逼真的測試影像（RGB float32, 0-1 範圍）
    包含：高光、中間調、陰影
    """
    img = np.zeros((*size, 3), dtype=np.float32)
    
    # 背景（中間調）
    img[:, :] = 0.3
    
    # 添加 10 個高光點（路燈）
    for i in range(2):
        for j in range(5):
            cx = 300 + j * 500
            cy = 300 + i * 1400
            y, x = np.ogrid[:size[0], :size[1]]
            mask = ((x - cx)**2 + (y - cy)**2) <= 30**2
            img[mask] = [0.95, 0.90, 0.85]
    
    return img


def profile_phos_end_to_end(film_name: str, image_size=(2000, 3000)):
    """
    端到端效能測試：測量實際 Phos 函數的執行時間
    """
    print("=" * 80)
    print(f"  Phos 端到端效能測試")
    print(f"  膠片: {film_name}")
    print(f"  尺寸: {image_size[0]}×{image_size[1]}")
    print("=" * 80)
    
    # 載入膠片配置
    film = get_film_profile(film_name)
    print(f"\n膠片資訊:")
    print(f"  Physics Mode: {film.physics_mode}")
    print(f"  Halation: {film.halation_params.enabled if hasattr(film, 'halation_params') else 'N/A'}")
    
    # 創建測試影像
    print(f"\n[1] 創建測試影像...")
    img_rgb = create_realistic_test_image(image_size)
    print(f"    ✓ {img_rgb.shape}, {img_rgb.nbytes / 1024**2:.1f} MB")
    
    # 測試 3 次取平均
    times = []
    for run in range(3):
        print(f"\n[Run {run+1}/3]")
        
        start_total = time.perf_counter()
        
        # ===== 呼叫實際的 Phos 函數 =====
        try:
            # Step 1: RGB → Spectrum
            t0 = time.perf_counter()
            # 簡化：直接使用 RGB（實際會轉光譜）
            lux_r = 0.32 * img_rgb[:,:,0] + 0.12 * img_rgb[:,:,1] + 0.06 * img_rgb[:,:,2]
            lux_g = 0.09 * img_rgb[:,:,0] + 0.45 * img_rgb[:,:,1] + 0.12 * img_rgb[:,:,2]
            lux_b = 0.06 * img_rgb[:,:,0] + 0.12 * img_rgb[:,:,1] + 0.77 * img_rgb[:,:,2]
            t1 = time.perf_counter()
            print(f"  光譜響應: {(t1-t0)*1000:.1f} ms")
            
            # Step 2: Apply Bloom（使用實際函數）
            t0 = time.perf_counter()
            if hasattr(film, 'bloom_params'):
                lux_r = phos_main.apply_bloom_mie_corrected(lux_r, film.bloom_params, wavelength=650.0)
                lux_g = phos_main.apply_bloom_mie_corrected(lux_g, film.bloom_params, wavelength=550.0)
                lux_b = phos_main.apply_bloom_mie_corrected(lux_b, film.bloom_params, wavelength=450.0)
            t1 = time.perf_counter()
            print(f"  Bloom 散射: {(t1-t0)*1000:.1f} ms")
            
            # Step 3: Apply Halation（使用實際函數）
            t0 = time.perf_counter()
            if hasattr(film, 'halation_params') and film.halation_params.enabled:
                lux_r = phos_main.apply_halation(lux_r, film.halation_params, wavelength=650.0)
                lux_g = phos_main.apply_halation(lux_g, film.halation_params, wavelength=550.0)
                lux_b = phos_main.apply_halation(lux_b, film.halation_params, wavelength=450.0)
            t1 = time.perf_counter()
            print(f"  Halation 反射: {(t1-t0)*1000:.1f} ms")
            
            # Step 4: H&D Curve（使用實際函數）
            t0 = time.perf_counter()
            density_r = phos_main.apply_hd_curve(lux_r, film.hd_curve_params)
            density_g = phos_main.apply_hd_curve(lux_g, film.hd_curve_params)
            density_b = phos_main.apply_hd_curve(lux_b, film.hd_curve_params)
            t1 = time.perf_counter()
            print(f"  H&D 曲線: {(t1-t0)*1000:.1f} ms")
            
            # Step 5: Grain（使用實際函數）
            t0 = time.perf_counter()
            if hasattr(film, 'grain_params'):
                grain_r = phos_main.generate_grain(density_r, film.grain_params)
                grain_g = phos_main.generate_grain(density_g, film.grain_params)
                grain_b = phos_main.generate_grain(density_b, film.grain_params)
                density_r = density_r + grain_r
                density_g = density_g + grain_g
                density_b = density_b + grain_b
            t1 = time.perf_counter()
            print(f"  顆粒噪聲: {(t1-t0)*1000:.1f} ms")
            
            # Step 6: Tone Mapping
            t0 = time.perf_counter()
            result = np.clip(np.stack([density_b, density_g, density_r], axis=2), 0, 1)
            t1 = time.perf_counter()
            print(f"  Tone Mapping: {(t1-t0)*1000:.1f} ms")
            
        except Exception as e:
            print(f"  ❌ 錯誤: {e}")
            import traceback
            traceback.print_exc()
            return
        
        elapsed = time.perf_counter() - start_total
        times.append(elapsed)
        print(f"  總時間: {elapsed*1000:.1f} ms ({elapsed:.2f} s)")
    
    # 統計
    avg_time = np.mean(times)
    std_time = np.std(times)
    
    print("\n" + "=" * 80)
    print(f"  平均時間: {avg_time*1000:.1f} ± {std_time*1000:.1f} ms ({avg_time:.2f} s)")
    print("=" * 80)
    
    # 判斷是否符合目標
    if avg_time < 1.5:
        print(f"  ✅ 效能達標（目標 <1.5s）")
    elif avg_time < 2.0:
        print(f"  ⚠️  效能可接受（目標 <2.0s）")
    else:
        print(f"  ❌ 效能不達標（當前 {avg_time:.2f}s，目標 <2.0s）")


def test_psf_cache_hit_rate():
    """
    測試 PSF 快取命中率
    """
    print("\n" + "=" * 80)
    print("  PSF 快取命中率測試")
    print("=" * 80)
    
    # 清除快取
    phos_main.get_gaussian_kernel.cache_clear()
    
    # 模擬 Halation 三層核生成（會呼叫 3 次）
    sigma_base = 20.0
    ksize = 201
    
    # 第一輪：冷快取
    t0 = time.perf_counter()
    k1 = phos_main.get_gaussian_kernel(sigma_base, ksize)
    k2 = phos_main.get_gaussian_kernel(sigma_base * 2.0, ksize)
    k3 = phos_main.get_gaussian_kernel(sigma_base * 4.0, ksize)
    t_cold = time.perf_counter() - t0
    
    # 第二輪：熱快取
    t0 = time.perf_counter()
    k1 = phos_main.get_gaussian_kernel(sigma_base, ksize)
    k2 = phos_main.get_gaussian_kernel(sigma_base * 2.0, ksize)
    k3 = phos_main.get_gaussian_kernel(sigma_base * 4.0, ksize)
    t_hot = time.perf_counter() - t0
    
    cache_info = phos_main.get_gaussian_kernel.cache_info()
    
    print(f"\n  冷快取（首次）: {t_cold*1000:.3f} ms")
    print(f"  熱快取（第二次）: {t_hot*1000:.3f} ms")
    print(f"  加速比: {t_cold / max(t_hot, 1e-9):.1f}x")
    print(f"\n  快取統計:")
    print(f"    Hits: {cache_info.hits}")
    print(f"    Misses: {cache_info.misses}")
    print(f"    命中率: {cache_info.hits / max(cache_info.hits + cache_info.misses, 1) * 100:.1f}%")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phos 真實工作流程效能測試")
    parser.add_argument("--film", default="Portra400_MediumPhysics_Mie", help="膠片配置")
    parser.add_argument("--size", default="2000x3000", help="影像尺寸（WxH）")
    parser.add_argument("--test-cache", action="store_true", help="測試 PSF 快取")
    
    args = parser.parse_args()
    
    # 解析尺寸
    w, h = map(int, args.size.split('x'))
    
    # 執行端到端測試
    profile_phos_end_to_end(args.film, (h, w))
    
    # 測試快取
    if args.test_cache:
        test_psf_cache_hit_rate()
